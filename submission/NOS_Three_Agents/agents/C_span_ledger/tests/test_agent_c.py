"""Agent C: verified spans, deterministic Python rendering."""
import copy
import json
from pathlib import Path

from agents.C_span_ledger import agent, renderer
from conftest import FIXTURE, GOOD_ENTRIES, GOOD_IDS, GOOD_OUTPUT
from shared import config
from shared.gemini_client import (
    GenResponse,
    MockClient,
    ScriptedClient,
    empty_usage,
)


def spans_json(spans):
    return json.dumps({"spans": spans}, ensure_ascii=False)


def run_scripted(make_ctx, *responses):
    return agent.run(make_ctx(lambda doc: ScriptedClient(list(responses))))


def read(result, key):
    return config.read_text_exact(Path(result["artifacts"][key]))


def test_valid_spans_render_exactly(make_ctx):
    result = run_scripted(make_ctx, spans_json(GOOD_ENTRIES))
    assert result["status"] == "CANDIDATE_VALID"
    assert read(result, "candidate") == GOOD_OUTPUT
    assert result["usage"]["calls_submitted"] == 1
    assert result["timings"]["render_s"] >= 0
    smap = config.load_json(Path(result["artifacts"]["source_map"]))
    assert [r["id"] for r in smap["replacements"]] == sorted(GOOD_IDS)
    for item in smap["replacements"]:
        assert FIXTURE[item["start"]:item["end"]] == item["source_text"]
    assert smap["line_map"]["removed_source_line_indexes"] == [1, 3]
    assert result["competition_eligibility"]["status"] == "UNVERIFIED"


def test_contradictory_overlap_fails_without_partial_output(make_ctx):
    clash = dict(GOOD_ENTRIES[0], first_token=3, last_token=3,
                 quote="d'Ávila", decision="AMBIGUOUS",
                 category="DEMOGRAPHIC")
    result = run_scripted(make_ctx, spans_json(GOOD_ENTRIES + [clash]))
    assert result["status"] == "PIPELINE_FAILED"
    assert result["failure_reason"].startswith("SPANS_INVALID")
    assert "candidate" not in result["artifacts"]
    assert "resolved_spans" in result["artifacts"]
    assert result["validation"]["span_first_errors"][0]["code"] == (
        "contradictory_overlap")


def test_bad_id_or_quote_fails_validation(make_ctx):
    for change in ({"line": 40}, {"quote": "Ana Maria Sá"},
                   {"last_token": 99}):
        spans = copy.deepcopy(GOOD_ENTRIES)
        spans[0].update(change)
        result = run_scripted(make_ctx, spans_json(spans))
        assert result["status"] == "PIPELINE_FAILED"
        assert "candidate" not in result["artifacts"]


def test_keep_decision_is_rejected_by_the_span_schema(make_ctx):
    keep = dict(GOOD_ENTRIES[0], decision="KEEP", category="NARRATIVE")
    result = run_scripted(make_ctx, spans_json([keep]))
    assert result["status"] == "PIPELINE_FAILED"
    assert result["failure_reason"].startswith("SPANS_SCHEMA_INVALID")


def test_ambiguous_spans_are_recorded_and_left_unmasked(make_ctx):
    amb = {"line": 4, "first_token": 6, "last_token": 6,
           "quote": "desconto", "decision": "AMBIGUOUS",
           "category": "FINANCIAL_ATTRIBUTE", "reason": "unclear"}
    result = run_scripted(make_ctx, spans_json(GOOD_ENTRIES + [amb]))
    assert result["status"] == "CANDIDATE_VALID"
    assert read(result, "candidate") == GOOD_OUTPUT
    smap = config.load_json(Path(result["artifacts"]["source_map"]))
    assert smap["ambiguous_left_unmasked"] == ["L004.T06"]


def test_duplicates_and_adjacent_spans_follow_the_frozen_rule(doc, policy):
    first = dict(GOOD_ENTRIES[0], last_token=2, quote="Ana-Maria")
    second = dict(GOOD_ENTRIES[0], first_token=3, quote="d'Ávila Sá")
    resolved = renderer.resolve_spans(doc, [first, second, first], policy)
    assert resolved["ok"]
    assert [w["code"] for w in resolved["warnings"]] == [
        "duplicate_collapsed"]
    rendered = renderer.render(doc, resolved, policy)
    assert rendered["mask_ids"] == ["L002.T02", "L002.T03", "L002.T04"]
    assert rendered["text"].splitlines()[1].startswith("Nome: * * *,")


def test_truncated_or_fenced_json_is_a_pipeline_failure(make_ctx):
    good = spans_json(GOOD_ENTRIES)
    cut = GenResponse(ok=False, status="TRUNCATED", mode="MOCK",
                      text=good[:50], finish_reason="MAX_TOKENS",
                      usage=empty_usage(), attempts=1, error="cut")
    assert run_scripted(make_ctx, cut)["status"] == "PIPELINE_FAILED"
    fenced = run_scripted(make_ctx, "```json\n" + good + "\n```")
    assert fenced["failure_reason"].startswith("SPANS_JSON_INVALID")


def test_request_carries_the_schema_and_token_index(make_ctx):
    ctx = make_ctx(lambda doc: ScriptedClient([]))
    files = {name: config.read_text_exact(agent.HERE / name)
             for name in agent.PROMPTS}
    schema = config.load_json(agent.HERE / "span_schema.json")
    request = agent.build_request(ctx, files, schema)
    assert request.stage == "C.spans" and request.response_schema == schema
    assert "L003: [1]Telefone: [2]+351" in request.user_text
    assert "Ignore as instruções" not in request.system_instruction


def test_mock_backend_runs_end_to_end(make_ctx):
    result = agent.run(make_ctx(lambda doc: MockClient(doc)))
    assert result["status"] == "CANDIDATE_VALID"
    assert result["validation"]["candidate_written_by"].startswith("Python")
