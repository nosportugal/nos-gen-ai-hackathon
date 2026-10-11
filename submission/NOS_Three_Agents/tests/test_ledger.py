"""Ledger/span validation, schemas and JSON parsing (agents B and C)."""
import copy
import json

from conftest import FIXTURE, GOOD_ENTRIES, GOOD_IDS, GOOD_OUTPUT
from shared import config, schema
from shared.ledger import (
    ledger_agreement,
    parse_ledger,
    render_ids,
    validate_entries,
)
from shared.validation import align

ALL = ("MASK", "AMBIGUOUS", "KEEP")
AGENTS = config.ROOT / "agents"
B_SCHEMA = config.load_json(AGENTS / "B_decision_ledger/ledger_schema.json")
C_SCHEMA = config.load_json(AGENTS / "C_span_ledger/span_schema.json")


def entry(**changes):
    base = copy.deepcopy(GOOD_ENTRIES[0])
    base.update(changes)
    return base


def codes(result):
    return [e["code"] for e in result["errors"]]


def test_valid_ledger_resolves_to_verified_offsets(doc, policy):
    result = validate_entries(doc, GOOD_ENTRIES, policy, ALL)
    assert result["ok"] and result["mask_ids"] == sorted(GOOD_IDS)
    for item in result["resolved"]:
        for comp in item["components"]:
            assert FIXTURE[comp["start"]:comp["end"]] == comp["text"]
    assert doc.render(render_ids(result, policy)) == GOOD_OUTPUT


def test_quote_mismatch_blocks_rendering(doc, policy):
    result = validate_entries(doc, [entry(quote="Ana Maria Sá")], policy, ALL)
    assert codes(result) == ["quote_mismatch"]
    assert not result["ok"] and result["mask_ids"] == []
    try:
        render_ids(result, policy)
    except ValueError:
        return
    raise AssertionError("an invalid ledger must not render")


def test_invalid_ids_are_errors(doc, policy):
    bad = [entry(line=99), entry(first_token=0),
           entry(first_token=4, last_token=2, quote="x"),
           entry(line="2")]
    result = validate_entries(doc, bad, policy, ALL)
    assert codes(result) == ["invalid_location", "invalid_location",
                             "reversed_range", "invalid_location"]


def test_contradictory_overlap_is_an_error(doc, policy):
    keep = entry(first_token=3, last_token=3, quote="d'Ávila",
                 decision="KEEP", category="NARRATIVE")
    result = validate_entries(doc, [GOOD_ENTRIES[0], keep], policy, ALL)
    assert codes(result) == ["contradictory_overlap"] and not result["ok"]


def test_duplicates_and_same_decision_overlaps_are_warnings(doc, policy):
    inner = entry(first_token=3, last_token=4, quote="d'Ávila Sá")
    result = validate_entries(
        doc, [GOOD_ENTRIES[0], GOOD_ENTRIES[0], inner], policy, ALL)
    assert result["ok"]
    assert [w["code"] for w in result["warnings"]] == [
        "duplicate_collapsed", "overlap_same_decision_merged"]
    assert result["mask_ids"] == ["L002.T02", "L002.T03", "L002.T04"]


def test_category_must_belong_to_the_decision(doc, policy):
    result = validate_entries(doc, [entry(category="HEALTH")], policy, ALL)
    assert codes(result) == ["category_contradicts_decision"]


def test_repeated_text_needs_an_explicit_location(doc, policy):
    """Masking one occurrence never masks the other by assumption."""
    first = {"line": 5, "first_token": 2, "last_token": 2,
             "quote": "12345-AB", "decision": "MASK",
             "category": "GOV_ID", "reason": "first occurrence only"}
    result = validate_entries(doc, [first], policy, ALL)
    assert result["mask_ids"] == ["L005.T02"]
    rendered = doc.render(render_ids(result, policy)).splitlines()[-1]
    assert rendered == "Código: * e 12345-AB (repetido)."


def test_ambiguous_entries_are_recorded_and_left_unmasked(doc, policy):
    amb = {"line": 4, "first_token": 6, "last_token": 6,
           "quote": "desconto", "decision": "AMBIGUOUS",
           "category": "FINANCIAL_ATTRIBUTE", "reason": "unclear"}
    result = validate_entries(doc, GOOD_ENTRIES + [amb], policy, ALL)
    assert result["ok"] and result["ambiguous_ids"] == ["L004.T06"]
    assert "L004.T06" not in render_ids(result, policy)


def test_spans_may_not_carry_keep_decisions(doc, policy):
    keep = entry(decision="KEEP", category="NARRATIVE")
    result = validate_entries(doc, [keep], policy, ("MASK", "AMBIGUOUS"))
    assert codes(result) == ["decision_not_allowed"]


def test_punctuation_only_run_and_long_reason_are_errors(doc, policy):
    star = entry(line=4, first_token=5, last_token=5, quote="*")
    wordy = entry(reason="x" * 301)
    result = validate_entries(doc, [star, wordy], policy, ALL)
    assert codes(result) == ["no_maskable_word", "reason_too_long"]


def test_ledger_agreement_detects_missing_and_extra_masks(doc):
    states = align(doc, GOOD_OUTPUT)["states"]
    assert ledger_agreement(doc, states, GOOD_IDS)["pass"]
    fewer = ledger_agreement(doc, states, GOOD_IDS[:-1])
    assert not fewer["pass"]
    assert fewer["masked_but_not_approved"] == ["L004.T03"]
    assert not ledger_agreement(doc, None, GOOD_IDS)["pass"]


def test_malformed_ledgers_fail_schema_validation():
    assert schema.validate({"entries": GOOD_ENTRIES}, B_SCHEMA) == []
    missing = copy.deepcopy(GOOD_ENTRIES[0])
    del missing["quote"]
    wrong = dict(GOOD_ENTRIES[0], line="2", decision="HIDE", extra=1)
    for bad in ({"entries": [missing]}, {"entries": [wrong]},
                {"spans": []}, {"entries": "none"}, []):
        assert schema.validate(bad, B_SCHEMA)
    assert schema.validate({"entries": [dict(GOOD_ENTRIES[0], line=True)]},
                           B_SCHEMA)


def test_schema_enums_match_the_policy(policy):
    b_items = B_SCHEMA["properties"]["entries"]["items"]["properties"]
    c_items = C_SCHEMA["properties"]["spans"]["items"]["properties"]
    assert b_items["category"]["enum"] == policy.category_ids()
    assert c_items["category"]["enum"] == policy.category_ids(
        ("MASK", "AMBIGUOUS"))
    assert c_items["decision"]["enum"] == ["MASK", "AMBIGUOUS"]


def test_gemini_schema_drops_unsupported_keywords():
    converted = schema.to_gemini_schema(B_SCHEMA)
    text = json.dumps(converted)
    assert converted["type"] == "OBJECT"
    assert "additionalProperties" not in text and "maxLength" not in text
    assert converted["properties"]["entries"]["maxItems"] == 400


def test_model_json_is_parsed_as_returned_never_repaired():
    good = json.dumps({"entries": GOOD_ENTRIES})
    assert parse_ledger(good, B_SCHEMA, "entries")[1] is None
    fenced = "```json\n" + good + "\n```"
    assert parse_ledger(fenced, B_SCHEMA, "entries")[1].startswith(
        "JSON_INVALID")
    truncated = good[: len(good) // 2]
    assert parse_ledger(truncated, B_SCHEMA, "entries")[0] is None
    assert parse_ledger("{}", B_SCHEMA, "entries")[1].startswith(
        "SCHEMA_INVALID")
