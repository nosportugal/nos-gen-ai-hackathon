"""Run context and the result contract common to all agents.

Every agent returns a dict with the same top-level keys:

    contract_version, agent_id, agent_name, run_id, trial, mode, label,
    started_utc, hashes, model, status, failure_reason,
    competition_eligibility, artifacts, validation, usage, timings, stages

status is one of:
    CANDIDATE_VALID    a candidate exists and passed structural validation
    CANDIDATE_INVALID  a candidate exists but failed validation
    PIPELINE_FAILED    no usable candidate (API error, truncation, block,
                       invalid ledger, budget, oversized input)
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from . import artifacts, config
from .gemini_client import (
    LiveClient,
    MockClient,
    RequestBudget,
    load_api_key,
    load_model_config,
)
from .policy import load_policy

CONTRACT_VERSION = "1.0"
VALID = "CANDIDATE_VALID"
INVALID = "CANDIDATE_INVALID"
FAILED = "PIPELINE_FAILED"
MOCK_LABEL = "MOCK - produced by a local stand-in, not a Gemini result"


class NoCredentials(Exception):
    pass


@dataclass
class RunContext:
    mode: str
    doc: object
    source_sha256: str
    policy: object
    model_cfg: dict
    model_cfg_sha256: str
    client: object
    freeze_sha256: str = None


def build_context(mode: str, client=None, source_text=None) -> RunContext:
    """Assemble the shared inputs. ``mode`` is 'mock' or 'live'."""
    mode = mode.upper()
    policy = load_policy()
    if source_text is None:
        if not config.CANONICAL_SOURCE.exists():
            raise FileNotFoundError(
                "BLOCKED: canonical source missing; run prepare_source.py"
            )
        source_text = config.read_text_exact(config.CANONICAL_SOURCE)
    doc = policy.make_doc(source_text)
    cfg = load_model_config()
    if client is None:
        if mode == "LIVE":
            key, _name = load_api_key(cfg)
            if not key:
                raise NoCredentials(
                    "BLOCKED: no API key in "
                    + " / ".join(cfg["api_key_env"])
                    + " (environment or .env)"
                )
            budget = RequestBudget(cfg["global_request_budget"])
            client = LiveClient(cfg, key, budget)
        else:
            client = MockClient(doc)
    freeze = None
    if config.FREEZE_MANIFEST.exists():
        freeze = config.sha256_file(config.FREEZE_MANIFEST)
    return RunContext(
        mode=client.mode,
        doc=doc,
        source_sha256=config.sha256_text(source_text),
        policy=policy,
        model_cfg=cfg,
        model_cfg_sha256=config.sha256_file(config.MODEL_CONFIG_PATH),
        client=client,
        freeze_sha256=freeze,
    )


def load_agent_files(agent_dir: Path, names) -> dict:
    """Read prompt templates; CRLF is folded to LF so prompts carry no CR."""
    return {
        name: config.read_text_exact(agent_dir / name).replace("\r\n", "\n")
        for name in names
    }


def file_hashes(agent_dir: Path, names) -> dict:
    return {name: config.sha256_file(agent_dir / name) for name in names}


class Run:
    """Collects stages, artifacts and timings for one agent run."""

    def __init__(self, ctx, agent_id, agent_name, folder, trial, cfg,
                 prompt_hashes):
        self.ctx = ctx
        self.t0 = time.perf_counter()
        self.run_id, self.dir = artifacts.new_run(
            agent_id, folder, ctx.mode, trial
        )
        self.stages = []
        self.paths = {}
        self.timings = {"model_s": 0.0, "render_s": 0.0,
                        "validation_s": 0.0}
        self.result = {
            "contract_version": CONTRACT_VERSION,
            "agent_id": agent_id,
            "agent_name": agent_name,
            "run_id": self.run_id,
            "trial": trial,
            "mode": ctx.mode,
            "label": MOCK_LABEL if ctx.mode == "MOCK" else "LIVE Gemini run",
            "started_utc": artifacts.utc_now(),
            "hashes": {
                "source_sha256": ctx.source_sha256,
                "policy_sha256": ctx.policy.sha256,
                "model_config_sha256": ctx.model_cfg_sha256,
                "freeze_manifest_sha256": ctx.freeze_sha256,
                "agent_files_sha256": prompt_hashes,
            },
            "model": {
                "id": ctx.model_cfg["model_id"],
                "id_source": ctx.model_cfg["model_id_source"],
                "temperature": ctx.model_cfg["temperature"]
                if ctx.model_cfg["temperature"] is not None
                else "model default (not sent)",
                "max_output_tokens": ctx.model_cfg["max_output_tokens"],
            },
            "status": FAILED,
            "failure_reason": None,
            "competition_eligibility": cfg["competition_eligibility"],
        }

    def call(self, name: str, request):
        """Send one stage, save its raw content, record usage."""
        resp = self.ctx.client.generate(request, self.run_id)
        self.paths.update(artifacts.save_stage(self.dir, name, resp))
        self.stages.append(artifacts.stage_summary(name, resp))
        self.timings["model_s"] += resp.latency_s
        return resp

    def save(self, key: str, filename: str, content) -> None:
        self.paths[key] = artifacts.write_once(self.dir / filename, content)

    def save_request(self, key: str, filename: str, request) -> None:
        """Save exactly what a stage sends (no credentials are in it)."""
        self.save(key, filename, {
            "stage": request.stage,
            "system_instruction": request.system_instruction,
            "user_text": request.user_text,
            "response_schema": request.response_schema,
            "system_sha256": config.sha256_text(request.system_instruction),
            "user_sha256": config.sha256_text(request.user_text),
        })

    def timed(self, bucket: str):
        return _Timer(self.timings, bucket)

    def finish(self, status, failure_reason, validation_summary) -> dict:
        totals = {}
        for field in ("prompt_tokens", "output_tokens", "thoughts_tokens",
                      "total_tokens"):
            values = [s["usage"].get(field) for s in self.stages]
            known = values and all(v is not None for v in values)
            totals[field] = sum(values) if known else "UNKNOWN"
        self.result["status"] = status
        self.result["failure_reason"] = failure_reason
        self.result["validation"] = validation_summary
        self.result["usage"] = {
            "calls_submitted": sum(
                1 for s in self.stages if s["http_attempts"]
            ),
            "http_attempts": sum(s["http_attempts"] for s in self.stages),
            **totals,
            "cost": "UNKNOWN",
        }
        self.result["stages"] = self.stages
        self.timings["pipeline_s"] = time.perf_counter() - self.t0
        self.result["timings"] = {
            k: round(v, 4) for k, v in self.timings.items()
        }
        self.paths["result"] = config.rel(self.dir / "result.json")
        self.result["artifacts"] = dict(self.paths)
        artifacts.write_once(self.dir / "result.json", self.result)
        artifacts.seal(self.dir)
        return self.result


class _Timer:
    def __init__(self, timings, bucket):
        self.timings, self.bucket = timings, bucket

    def __enter__(self):
        self.t0 = time.perf_counter()
        return self

    def __exit__(self, *exc):
        self.timings[self.bucket] += time.perf_counter() - self.t0
        return False
