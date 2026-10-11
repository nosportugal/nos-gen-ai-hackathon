"""API adapter: statuses, budget, retries, sanitising, size checks.

No network is used: the HTTP layer is replaced by a stub.
"""
import pytest

from shared import config
from shared.gemini_client import (
    BudgetExhausted,
    GenRequest,
    InputTooLarge,
    LiveClient,
    MemoryBudget,
    RequestBudget,
    check_input_size,
    interpret_payload,
    load_model_config,
    sanitize,
)

KEY = "AIzaSyTESTKEY0123456789"
REQ = GenRequest("A.rewrite", "system rules", "<document>\nx\n</document>")
OK_PAYLOAD = {
    "candidates": [{"finishReason": "STOP",
                    "content": {"parts": [{"text": "x"}]}}],
    "usageMetadata": {"promptTokenCount": 7, "candidatesTokenCount": 1,
                      "totalTokenCount": 8},
    "modelVersion": "stub-1",
}


def payload(finish, text="partial"):
    parts = [{"text": text}] if text is not None else []
    return {"candidates": [{"finishReason": finish,
                            "content": {"parts": parts}}]}


def test_stop_with_text_is_ok_and_usage_is_read():
    resp = interpret_payload(OK_PAYLOAD, "LIVE")
    assert resp.ok and resp.text == "x" and resp.model_version == "stub-1"
    assert resp.usage["prompt_tokens"] == 7
    assert resp.usage["thoughts_tokens"] is None  # UNKNOWN, not zero


@pytest.mark.parametrize("finish,status", [
    ("MAX_TOKENS", "TRUNCATED"), ("SAFETY", "BLOCKED"),
    ("SPII", "BLOCKED"), ("RECITATION", "BLOCKED"),
    ("OTHER", "UNEXPECTED_FINISH"),
])
def test_non_stop_finishes_are_failures(finish, status):
    resp = interpret_payload(payload(finish), "LIVE")
    assert not resp.ok and resp.status == status
    assert resp.text == "partial"  # kept for the record, never accepted


def test_missing_and_blocked_responses_are_explicit():
    assert interpret_payload({}, "LIVE").status == "NO_CANDIDATES"
    blocked = interpret_payload(
        {"promptFeedback": {"blockReason": "SAFETY"}}, "LIVE")
    assert blocked.status == "BLOCKED" and not blocked.ok
    empty = interpret_payload(payload("STOP", None), "LIVE")
    assert empty.status == "EMPTY" and empty.text is None
    thought = {"candidates": [{"finishReason": "STOP", "content": {
        "parts": [{"text": "hidden", "thought": True}]}}]}
    assert interpret_payload(thought, "LIVE").status == "EMPTY"


def test_persistent_budget_counts_every_attempt(tmp_path):
    log = tmp_path / "budget.jsonl"
    budget = RequestBudget(2, log)
    assert budget.reserve("s", "r", 1) == 1
    assert RequestBudget(2, log).reserve("s", "r", 1) == 2
    with pytest.raises(BudgetExhausted):
        RequestBudget(2, log).reserve("s", "r", 1)
    assert budget.used() == 2 and budget.remaining() == 0


def make_client(outcomes, limit=24):
    cfg = load_model_config()
    client = LiveClient(cfg, KEY, MemoryBudget(limit))
    calls = []

    def fake_open(request):
        calls.append(request)
        return outcomes[len(calls) - 1]

    client._open = fake_open
    return client, calls


def test_one_retry_for_a_transient_error_then_success():
    client, calls = make_client([("TRANSIENT", 503, "busy"),
                                 ("OK", 200, OK_PAYLOAD)])
    resp = client.generate(REQ, "run")
    assert resp.ok and resp.attempts == 2 and len(calls) == 2
    assert client.budget.used() == 2  # the failed attempt is counted


def test_no_third_attempt_and_no_retry_for_bad_requests():
    client, calls = make_client([("TRANSIENT", 503, "busy")] * 3)
    resp = client.generate(REQ, "run")
    assert resp.status == "SERVICE_ERROR" and len(calls) == 2
    client, calls = make_client([("HTTP", 400, "bad schema")] * 2)
    resp = client.generate(REQ, "run")
    assert resp.status == "BAD_REQUEST" and len(calls) == 1
    client, calls = make_client([("HTTP", 404, "no such model")])
    assert client.generate(REQ, "run").status == "MODEL_NOT_FOUND"
    client, calls = make_client([("TRANSIENT", None, "timed out")] * 2)
    assert client.generate(REQ, "run").status == "TRANSPORT_ERROR"


def test_exhausted_budget_sends_nothing():
    client, calls = make_client([("OK", 200, OK_PAYLOAD)], limit=0)
    resp = client.generate(REQ, "run")
    assert resp.status == "BUDGET_EXHAUSTED" and not resp.ok
    assert calls == [] and resp.attempts == 0


def test_request_body_separates_instructions_from_document():
    client, _ = make_client([])
    body = client.body(GenRequest("C.spans", "RULES", "<doc>DATA</doc>",
                                  {"type": "object", "properties": {}}))
    assert body["systemInstruction"]["parts"][0]["text"] == "RULES"
    assert body["contents"][0]["parts"][0]["text"] == "<doc>DATA</doc>"
    gen = body["generationConfig"]
    assert gen["responseMimeType"] == "application/json"
    assert gen["maxOutputTokens"] == client.cfg["max_output_tokens"]
    assert KEY not in str(body) and KEY not in client._url(":x")
    # A null temperature in the config is not sent (model default).
    assert ("temperature" in gen) == (client.cfg["temperature"] is not None)
    client.cfg["temperature"] = 0.2
    assert client.body(REQ)["generationConfig"]["temperature"] == 0.2
    assert "responseSchema" not in client.body(REQ)["generationConfig"]


def test_errors_are_sanitised():
    client, _ = make_client([("HTTP", 403, f"key {KEY} rejected ?key={KEY}")])
    resp = client.generate(REQ, "run")
    assert resp.status == "ACCESS_DENIED" and KEY not in resp.error
    assert KEY not in str(resp.raw)
    assert sanitize("x AIzaSyABCDEFGHIJKLMNOP y") == "x [REDACTED] y"


def test_oversized_input_is_refused_before_any_request():
    cfg = load_model_config()
    assert check_input_size(cfg, 4000, 2000)[
        "estimated_input_tokens_upper_bound"] == 2000
    with pytest.raises(InputTooLarge):
        check_input_size(cfg, 10 ** 7)
    with pytest.raises(InputTooLarge):
        check_input_size(cfg, 1000, cfg["max_output_tokens"] * 2)


def test_live_adapter_against_a_local_stub_server():
    """Real HTTP round trip to a local stub; proves the wire format only.

    This is not a Gemini call and says nothing about model behaviour.
    """
    import http.server
    import json
    import threading

    seen = {}
    model = {"name": "models/stub", "inputTokenLimit": 1000,
             "outputTokenLimit": 100, "temperature": 1.0,
             "supportedGenerationMethods": ["generateContent"]}

    class Handler(http.server.BaseHTTPRequestHandler):
        def _send(self, obj):
            data = json.dumps(obj).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            self._send(model)

        def do_POST(self):
            size = int(self.headers["Content-Length"])
            seen["path"] = self.path
            seen["key"] = self.headers.get("x-goog-api-key")
            seen["body"] = json.loads(self.rfile.read(size))
            self._send(OK_PAYLOAD)

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        cfg = load_model_config()
        cfg["api_base"] = f"http://127.0.0.1:{server.server_port}/v1beta"
        cfg["model_id"] = "stub-model"
        client = LiveClient(cfg, KEY, MemoryBudget(5))
        info = client.model_info()
        assert info["ok"] and info["default_temperature"] == 1.0
        resp = client.generate(REQ, "run")
    finally:
        server.shutdown()
        server.server_close()
    assert resp.ok and resp.text == "x" and resp.attempts == 1
    assert resp.usage["total_tokens"] == 8 and resp.latency_s > 0
    assert seen["path"] == "/v1beta/models/stub-model:generateContent"
    assert seen["key"] == KEY and KEY not in seen["path"]
    sent = seen["body"]
    assert sent["systemInstruction"]["parts"][0]["text"] == "system rules"
    assert sent["contents"][0]["parts"][0]["text"].startswith("<document>")
    assert client.budget.used() == 1  # the metadata call is not counted


def test_env_example_contains_no_values():
    for line in (config.ROOT / ".env.example").read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            assert line.split("=", 1)[1].strip() == ""
