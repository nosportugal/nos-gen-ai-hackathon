"""Agent B: validated ledger first, model rendering second."""
import copy
import json
from pathlib import Path

from agents.B_decision_ledger import agent
from conftest import GOOD_ENTRIES, GOOD_OUTPUT
from shared import config
from shared.gemini_client import (
    GenResponse,
    MockClient,
    ScriptedClient,
    empty_usage,
)

LEDGER = json.dumps({"entries": GOOD_ENTRIES}, ensure_ascii=False)


def run_scripted(make_ctx, *responses):
    holder = {}

    def factory(doc):
        holder["client"] = ScriptedClient(list(responses))
        return holder["client"]

    result = agent.run(make_ctx(factory))
    return result, holder["client"]


def read(result, key):
    return config.read_text_exact(Path(result["artifacts"][key]))


def test_two_stages_produce_a_valid_candidate(make_ctx):
    result, client = run_scripted(make_ctx, LEDGER, GOOD_OUTPUT)
    assert result["status"] == "CANDIDATE_VALID"
    assert [r.stage for r in client.requests] == ["B.ledger", "B.render"]
    assert result["usage"]["calls_submitted"] == 2
    assert read(result, "candidate") == GOOD_OUTPUT
    assert result["validation"]["ledger_agreement_pass"]
    assert result["validation"]["equals_internal_reference_rendering"]
    assert result["competition_eligibility"]["status"] == "UNVERIFIED"


def test_stage_two_receives_source_and_validated_decisions(make_ctx):
    _, client = run_scripted(make_ctx, LEDGER, GOOD_OUTPUT)
    stage1, stage2 = client.requests
    assert stage1.response_schema is not None
    assert "[2]Ana-Maria" in stage1.user_text
    assert stage2.response_schema is None
    assert 'MASK L002 T2 "Ana-Maria"' in stage2.user_text
    assert 'MASK L003 T6 "00"' in stage2.user_text
    assert "Relatório  Clínico\t(teste) \n" in stage2.user_text


def test_invalid_json_stops_before_stage_two(make_ctx):
    result, client = run_scripted(make_ctx, "```json\n" + LEDGER + "\n```")
    assert result["status"] == "PIPELINE_FAILED"
    assert result["failure_reason"].startswith("STAGE1_JSON_INVALID")
    assert len(client.requests) == 1
    assert result["validation"]["stage2"] == "NOT_CALLED"
    assert "candidate" not in result["artifacts"]
    assert "stage1_ledger_raw_text" in result["artifacts"]


def test_unmatched_quote_blocks_rendering(make_ctx):
    entries = copy.deepcopy(GOOD_ENTRIES)
    entries[0]["quote"] = "Ana Maria"
    bad = json.dumps({"entries": entries}, ensure_ascii=False)
    result, client = run_scripted(make_ctx, bad)
    assert result["status"] == "PIPELINE_FAILED"
    assert result["failure_reason"].startswith("STAGE1_LEDGER_INVALID")
    assert len(client.requests) == 1
    errors = result["validation"]["ledger_first_errors"]
    assert errors[0]["code"] == "quote_mismatch"


def test_failed_stage_one_call_stops_the_run(make_ctx):
    truncated = GenResponse(ok=False, status="TRUNCATED", mode="MOCK",
                            text=LEDGER[:40], finish_reason="MAX_TOKENS",
                            usage=empty_usage(), attempts=1, error="cut")
    result, client = run_scripted(make_ctx, truncated)
    assert result["status"] == "PIPELINE_FAILED"
    assert result["failure_reason"].startswith("STAGE1_TRUNCATED")
    assert len(client.requests) == 1


def test_rendering_that_ignores_the_ledger_is_invalid(make_ctx):
    extra = GOOD_OUTPUT.replace("Código: 12345-AB e", "Código: * e")
    result, _ = run_scripted(make_ctx, LEDGER, extra)
    assert result["status"] == "CANDIDATE_INVALID"
    assert "LEDGER_AGREEMENT_FAILED" in result["failure_reason"]
    assert read(result, "candidate") == extra
    assert not result["validation"]["equals_internal_reference_rendering"]


def test_model_rendering_is_never_replaced_by_the_internal_one(make_ctx):
    sloppy = "\n".join(ln.rstrip() for ln in GOOD_OUTPUT.split("\n"))
    result, _ = run_scripted(make_ctx, LEDGER, sloppy)
    assert result["status"] == "CANDIDATE_INVALID"
    assert read(result, "candidate") == sloppy
    assert result["validation"]["ledger_agreement_pass"]


def test_ambiguous_decisions_are_passed_as_keep(make_ctx):
    entries = GOOD_ENTRIES + [{
        "line": 4, "first_token": 6, "last_token": 6, "quote": "desconto",
        "decision": "AMBIGUOUS", "category": "FINANCIAL_ATTRIBUTE",
        "reason": "unclear"}]
    ledger = json.dumps({"entries": entries}, ensure_ascii=False)
    result, client = run_scripted(make_ctx, ledger, GOOD_OUTPUT)
    assert result["status"] == "CANDIDATE_VALID"
    assert 'KEEP L004 T6 "desconto"' in client.requests[1].user_text


def test_mock_backend_runs_both_stages(make_ctx):
    result = agent.run(make_ctx(lambda doc: MockClient(doc)))
    assert result["status"] == "CANDIDATE_VALID"
    assert [s["stage"] for s in result["stages"]] == [
        "stage1_ledger", "stage2_render"]
