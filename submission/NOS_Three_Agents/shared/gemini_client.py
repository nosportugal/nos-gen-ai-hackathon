"""Gemini REST adapter, request budget, and mock/scripted backends.

The live client calls the REST endpoint directly with the standard
library, so there are no hidden SDK retries: every HTTP attempt is
reserved in the persistent request budget before it is sent, including
attempts that fail. At most one retry per stage is made, and only for a
transient transport or service error. Invalid model content is never
retried or repaired.

The API key is sent in a header, never in a URL, and is removed from any
error text before it is stored or displayed.
"""
from __future__ import annotations

import json
import math
import os
import re
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from . import config
from .schema import to_gemini_schema

TRANSIENT_HTTP = (429, 500, 502, 503, 504)
BLOCK_FINISH = ("SAFETY", "RECITATION", "BLOCKLIST", "PROHIBITED_CONTENT",
                "SPII")
HTTP_KINDS = {400: "BAD_REQUEST", 401: "ACCESS_DENIED",
              403: "ACCESS_DENIED", 404: "MODEL_NOT_FOUND",
              429: "RATE_LIMITED"}


class BudgetExhausted(Exception):
    pass


class InputTooLarge(Exception):
    pass


@dataclass
class GenRequest:
    stage: str
    system_instruction: str
    user_text: str
    response_schema: dict = None
    mock_hint: dict = None


@dataclass
class GenResponse:
    ok: bool
    status: str
    mode: str
    text: str = None
    finish_reason: str = None
    usage: dict = field(default_factory=dict)
    model_version: str = None
    latency_s: float = 0.0
    attempts: int = 0
    http_status: int = None
    error: str = None
    raw: dict = None


def empty_usage() -> dict:
    """None means UNKNOWN; it is never reported as zero."""
    return {
        "prompt_tokens": None,
        "output_tokens": None,
        "thoughts_tokens": None,
        "total_tokens": None,
    }


def load_model_config(path=None) -> dict:
    cfg = config.load_json(path or config.MODEL_CONFIG_PATH)
    override = os.environ.get(cfg["model_id_env_override"], "").strip()
    cfg["model_id_source"] = "config"
    if override:
        cfg["model_id"] = override
        cfg["model_id_source"] = "env:" + cfg["model_id_env_override"]
    return cfg


def load_api_key(cfg: dict):
    """Return (key, variable name) or (None, None). Never logs the key."""
    for name in cfg["api_key_env"]:
        value = os.environ.get(name, "").strip()
        if value:
            return value, name
    env_file = config.ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            name, sep, value = line.partition("=")
            value = value.strip().strip("\"'")
            if sep and name.strip() in cfg["api_key_env"] and value:
                return value, name.strip() + " (.env)"
    return None, None


def sanitize(text, secret=None, limit=400) -> str:
    text = str(text)
    if secret:
        text = text.replace(secret, "[REDACTED]")
    text = re.sub(r"(key=)[^&\s\"']+", r"\1[REDACTED]", text)
    text = re.sub(r"AIza[0-9A-Za-z_\-]{10,}", "[REDACTED]", text)
    return text[:limit]


def check_input_size(cfg: dict, prompt_chars: int, expected_output_chars=0):
    """Refuse oversized input before any request. No silent chunking."""
    floor = cfg["chars_per_token_floor"]
    est_in = math.ceil(prompt_chars / floor)
    est_out = math.ceil(expected_output_chars / floor)
    report = {
        "estimated_input_tokens_upper_bound": est_in,
        "input_token_limit_applied": cfg["max_input_tokens_allowed"],
        "estimated_output_tokens_upper_bound": est_out,
        "max_output_tokens": cfg["max_output_tokens"],
        "method": f"characters / {floor} (deliberately pessimistic)",
    }
    if est_in > cfg["max_input_tokens_allowed"]:
        raise InputTooLarge(
            f"estimated {est_in} input tokens exceeds the allowed "
            f"{cfg['max_input_tokens_allowed']}; chunking is not enabled"
        )
    if est_out * 2 > cfg["max_output_tokens"]:
        raise InputTooLarge(
            f"expected output (~{est_out} tokens) leaves too little "
            f"headroom under max_output_tokens={cfg['max_output_tokens']}"
        )
    return report


class RequestBudget:
    """Persistent count of live inference attempts for the whole task."""

    def __init__(self, limit: int, log_path=None):
        self.limit = limit
        self.log_path = Path(
            log_path or config.RUNS_DIR / "_budget" / "live_requests.jsonl"
        )

    def used(self) -> int:
        if not self.log_path.exists():
            return 0
        with self.log_path.open(encoding="utf-8") as fh:
            return sum(1 for line in fh if line.strip())

    def remaining(self) -> int:
        return self.limit - self.used()

    def reserve(self, stage: str, run_id: str, attempt: int) -> int:
        used = self.used()
        if used >= self.limit:
            raise BudgetExhausted(
                f"request budget exhausted ({used}/{self.limit})"
            )
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "n": used + 1,
            "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "stage": stage,
            "run_id": run_id,
            "attempt": attempt,
        }
        with self.log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
        return used + 1


class MemoryBudget:
    """In-memory budget for mock and scripted backends (tests)."""

    def __init__(self, limit: int = 10 ** 6):
        self.limit = limit
        self.count = 0

    def used(self) -> int:
        return self.count

    def remaining(self) -> int:
        return self.limit - self.count

    def reserve(self, stage, run_id, attempt) -> int:
        if self.count >= self.limit:
            raise BudgetExhausted(
                f"request budget exhausted ({self.count}/{self.limit})"
            )
        self.count += 1
        return self.count


def _budget_response(mode, exc, attempts, latency) -> GenResponse:
    return GenResponse(
        ok=False, status="BUDGET_EXHAUSTED", mode=mode, error=str(exc),
        attempts=attempts, latency_s=latency, usage=empty_usage(),
    )


class LiveClient:
    mode = "LIVE"

    def __init__(self, cfg: dict, api_key: str, budget):
        self.cfg = cfg
        self._key = api_key
        self.budget = budget

    def _url(self, suffix: str) -> str:
        return f"{self.cfg['api_base']}/models/{self.cfg['model_id']}{suffix}"

    def _headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "x-goog-api-key": self._key,
        }

    def body(self, req: GenRequest) -> dict:
        gen = {
            "maxOutputTokens": self.cfg["max_output_tokens"],
            "candidateCount": 1,
        }
        if self.cfg["temperature"] is not None:
            # null in the config means: do not send, use the model default
            gen["temperature"] = self.cfg["temperature"]
        if req.response_schema is not None:
            gen["responseMimeType"] = "application/json"
            gen["responseSchema"] = to_gemini_schema(req.response_schema)
        return {
            "systemInstruction": {
                "parts": [{"text": req.system_instruction}]
            },
            "contents": [
                {"role": "user", "parts": [{"text": req.user_text}]}
            ],
            "generationConfig": gen,
        }

    def _open(self, request):
        timeout = self.cfg["timeout_s"]
        try:
            with urllib.request.urlopen(request, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                return "OK", resp.status, payload
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            kind = "TRANSIENT" if exc.code in TRANSIENT_HTTP else "HTTP"
            return kind, exc.code, detail
        except (urllib.error.URLError, socket.timeout, TimeoutError,
                ConnectionError) as exc:
            return "TRANSIENT", None, f"{type(exc).__name__}: {exc}"
        except json.JSONDecodeError as exc:
            return "HTTP", None, f"non-JSON response body: {exc}"

    def model_info(self) -> dict:
        """Model metadata (not an inference request)."""
        request = urllib.request.Request(
            self._url(""), headers=self._headers(), method="GET"
        )
        kind, code, payload = self._open(request)
        if kind != "OK":
            return {
                "ok": False,
                "http_status": code,
                "error": sanitize(payload, self._key),
            }
        methods = payload.get("supportedGenerationMethods", [])
        return {
            "ok": "generateContent" in methods,
            "http_status": code,
            "name": payload.get("name"),
            "version": payload.get("version"),
            "input_token_limit": payload.get("inputTokenLimit"),
            "output_token_limit": payload.get("outputTokenLimit"),
            "default_temperature": payload.get("temperature"),
            "supported_generation_methods": methods,
        }

    def generate(self, req: GenRequest, run_id: str = "") -> GenResponse:
        data = json.dumps(self.body(req)).encode("utf-8")
        max_attempts = 1 + self.cfg["max_transient_retries_per_stage"]
        attempts, latency = 0, 0.0
        kind, code, payload = "TRANSIENT", None, "not attempted"
        while attempts < max_attempts:
            try:
                self.budget.reserve(req.stage, run_id, attempts + 1)
            except BudgetExhausted as exc:
                return _budget_response(self.mode, exc, attempts, latency)
            attempts += 1
            request = urllib.request.Request(
                self._url(":generateContent"), data=data,
                headers=self._headers(), method="POST",
            )
            t0 = time.perf_counter()
            kind, code, payload = self._open(request)
            latency += time.perf_counter() - t0
            if kind != "TRANSIENT":
                break
        if kind != "OK":
            if code is None:
                status = "TRANSPORT_ERROR"
            elif code >= 500:
                status = "SERVICE_ERROR"
            else:
                status = HTTP_KINDS.get(code, "HTTP_ERROR")
            return GenResponse(
                ok=False, status=status, mode=self.mode, http_status=code,
                error=sanitize(payload, self._key), attempts=attempts,
                latency_s=latency, usage=empty_usage(),
                raw={"error_body": sanitize(payload, self._key, 2000)},
            )
        resp = interpret_payload(payload, self.mode)
        resp.attempts, resp.latency_s, resp.http_status = (
            attempts, latency, code,
        )
        return resp


def interpret_payload(payload: dict, mode: str) -> GenResponse:
    """Turn a generateContent payload into an explicit status."""
    meta = payload.get("usageMetadata") or {}
    usage = {
        "prompt_tokens": meta.get("promptTokenCount"),
        "output_tokens": meta.get("candidatesTokenCount"),
        "thoughts_tokens": meta.get("thoughtsTokenCount"),
        "total_tokens": meta.get("totalTokenCount"),
    }
    common = {
        "mode": mode, "usage": usage, "raw": payload,
        "model_version": payload.get("modelVersion"),
    }
    feedback = payload.get("promptFeedback") or {}
    if feedback.get("blockReason"):
        return GenResponse(
            ok=False, status="BLOCKED",
            error="prompt blocked: " + str(feedback["blockReason"]),
            **common,
        )
    candidates = payload.get("candidates") or []
    if not candidates:
        return GenResponse(
            ok=False, status="NO_CANDIDATES",
            error="response contains no candidates", **common,
        )
    cand = candidates[0]
    finish = cand.get("finishReason")
    parts = (cand.get("content") or {}).get("parts") or []
    text = "".join(
        p.get("text", "") for p in parts if not p.get("thought")
    )
    has_text = bool(parts) and text != ""
    if finish == "STOP":
        status = "OK" if has_text else "EMPTY"
    elif finish == "MAX_TOKENS":
        status = "TRUNCATED"
    elif finish in BLOCK_FINISH:
        status = "BLOCKED"
    else:
        status = "UNEXPECTED_FINISH"
    error = None
    if status != "OK":
        error = f"finishReason={finish}; text present={has_text}"
    return GenResponse(
        ok=status == "OK", status=status, text=text if has_text else None,
        finish_reason=finish, error=error, **common,
    )


# ---------------------------------------------------------------------
# Mock backend: proves the pipelines run. Its outputs are NOT Gemini
# results and say nothing about model accuracy.
# ---------------------------------------------------------------------
MOCK_LABELS = {
    "Nome:": "PERSON_NAME",
    "Telefone:": "PHONE",
    "Email:": "EMAIL",
    "NIF:": "GOV_ID",
}


def mock_detect(doc) -> list:
    """Trivial label heuristic. Returns runs of (category, [tokens])."""
    runs = []
    for line_no in sorted(doc.line_tokens):
        category, current = None, []
        for tok in doc.line_tokens[line_no]:
            if tok.text in MOCK_LABELS:
                category, current = MOCK_LABELS[tok.text], []
                continue
            if tok.text.startswith("(") and current:
                runs.append((category, current))
                category, current = None, []
            if category and tok.maskable:
                current.append(tok)
        if category and current:
            runs.append((category, current))
    return runs


def _mock_entries(doc) -> list:
    return [
        {
            "line": toks[0].line,
            "first_token": toks[0].index,
            "last_token": toks[-1].index,
            "quote": doc.run_quotes(toks[0], toks[-1])[0],
            "decision": "MASK",
            "category": category,
            "reason": "MOCK label heuristic",
        }
        for category, toks in mock_detect(doc)
    ]


class MockClient:
    mode = "MOCK"

    def __init__(self, doc, budget=None):
        self.doc = doc
        self.budget = budget or MemoryBudget()

    def model_info(self) -> dict:
        return {"ok": True, "name": "MOCK", "note": "no network call"}

    def generate(self, req: GenRequest, run_id: str = "") -> GenResponse:
        try:
            self.budget.reserve(req.stage, run_id, 1)
        except BudgetExhausted as exc:
            return _budget_response(self.mode, exc, 0, 0.0)
        t0 = time.perf_counter()
        ids = [t.comp_id for _, toks in mock_detect(self.doc) for t in toks]
        if req.stage == "B.ledger":
            text = json.dumps(
                {"entries": _mock_entries(self.doc)}, ensure_ascii=False
            )
        elif req.stage == "C.spans":
            text = json.dumps(
                {"spans": _mock_entries(self.doc)}, ensure_ascii=False
            )
        elif req.stage == "B.render":
            text = self.doc.render((req.mock_hint or {}).get("mask_ids", []))
        else:
            text = self.doc.render(ids)
        return GenResponse(
            ok=True, status="OK", mode=self.mode, text=text,
            finish_reason="STOP", usage=empty_usage(), attempts=1,
            latency_s=time.perf_counter() - t0, model_version="MOCK",
            raw={"mock": True, "note": "MOCK backend - not a Gemini "
                 "response; produced by a local label heuristic"},
        )


class ScriptedClient:
    """Returns queued responses in order. Used only by tests."""

    mode = "MOCK"

    def __init__(self, responses, budget=None):
        self.responses = list(responses)
        self.requests = []
        self.budget = budget or MemoryBudget()

    def model_info(self) -> dict:
        return {"ok": True, "name": "SCRIPTED"}

    def generate(self, req: GenRequest, run_id: str = "") -> GenResponse:
        try:
            self.budget.reserve(req.stage, run_id, 1)
        except BudgetExhausted as exc:
            return _budget_response(self.mode, exc, 0, 0.0)
        self.requests.append(req)
        item = self.responses.pop(0)
        if isinstance(item, GenResponse):
            return item
        return GenResponse(
            ok=True, status="OK", mode=self.mode, text=item,
            finish_reason="STOP", usage=empty_usage(), attempts=1,
            raw={"mock": True, "note": "scripted test response"},
        )
