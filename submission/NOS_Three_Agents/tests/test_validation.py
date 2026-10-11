"""Structural checks and the monotonic alignment for A and B outputs."""
from conftest import FIXTURE, GOOD_IDS, GOOD_OUTPUT
from shared import config
from shared.validation import (
    align,
    masked_ids,
    strict_check,
    validate_candidate,
)


def lines(text):
    return text.split("\n")


def test_exact_output_passes_and_aligns(doc, policy):
    report = validate_candidate(doc, GOOD_OUTPUT, policy)
    assert report["structural_pass"]
    assert report["alignment"]["status"] == "ALIGNED"
    states = list(report["alignment_states"])
    assert masked_ids(doc, states) == set(GOOD_IDS)


def test_final_newline_is_optional(doc):
    assert strict_check(doc, GOOD_OUTPUT.rstrip("\n"))["pass"]


def test_dropped_trailing_space_fails_strict_only(doc, policy):
    out = GOOD_OUTPUT.replace("(teste) \n", "(teste)\n")
    report = validate_candidate(doc, out, policy)
    assert not report["structural_pass"]
    counts = report["strict"]["violation_counts"]
    assert counts == {"trailing_whitespace_mismatch": 1}
    assert report["pass_ignoring_trailing_whitespace"]
    assert report["alignment"]["evaluable"]


def test_collapsed_double_space_is_a_whitespace_violation(doc):
    out = GOOD_OUTPUT.replace("Relatório  Clínico", "Relatório Clínico")
    counts = strict_check(doc, out)["violation_counts"]
    assert counts == {"whitespace_mismatch": 1}


def test_added_fence_and_preamble_are_rejected(doc, policy):
    out = "Aqui está:\n```\n" + GOOD_OUTPUT + "```\n"
    report = validate_candidate(doc, out, policy)
    assert not report["structural_pass"]
    assert report["markdown_fences"]["added"]
    assert report["alignment"]["status"] == "ALIGNED_WITH_GAPS"
    assert not report["alignment"]["evaluable"]
    assert len(report["alignment"]["inserted"]) == 4


def test_joined_lines_fail_structure_but_words_still_align(doc):
    out = GOOD_OUTPUT.replace("(teste) \nNome:", "(teste) Nome:")
    strict = strict_check(doc, out)
    assert "line_count_mismatch" in strict["violation_counts"]
    assert align(doc, out)["status"] == "ALIGNED"


def test_wrong_asterisk_count_is_unalignable(doc):
    out = GOOD_OUTPUT.replace("* * * * *; email", "* * *; email")
    result = align(doc, out)
    assert result["status"] == "UNALIGNABLE"
    assert result["states"] is None and not result["evaluable"]
    assert "word_count_mismatch" in strict_check(doc, out)["violation_counts"]


def test_corrected_typo_is_an_unauthorised_change(doc):
    out = GOOD_OUTPUT.replace("desconto.", "descontos.")
    result = align(doc, out)
    assert result["status"] == "ALIGNED_WITH_ALTERED"
    assert result["states"].count("A") == 1 and result["evaluable"]
    assert strict_check(doc, out)["violation_counts"] == {"word_altered": 1}


def test_swallowed_punctuation_is_a_nonconforming_mask(doc):
    out = GOOD_OUTPUT.replace("* * *, nascida", "* * * nascida")
    result = align(doc, out)
    assert result["states"].count("N") == 1
    counts = strict_check(doc, out)["violation_counts"]
    assert counts == {"nonconforming_mask": 1}


def test_partial_mask_counts_as_not_hidden(doc):
    out = GOOD_OUTPUT.replace("email: *", "email: *@exemplo.pt")
    result = align(doc, out)
    assert result["states"][doc.tokens.index(doc.get(3, 8))] == "A"
    assert strict_check(doc, out)["violation_counts"] == {"partial_mask": 1}


def test_blank_line_and_carriage_return_are_flagged(doc):
    counts = strict_check(doc, GOOD_OUTPUT.replace("\n", "\n\n", 1))[
        "violation_counts"]
    assert "blank_line_present" in counts
    counts = strict_check(doc, GOOD_OUTPUT.replace("\n", "\r\n"))[
        "violation_counts"]
    assert "carriage_return_present" in counts


def test_structural_validity_is_not_semantic_completeness(doc, policy):
    """A model that obeys the embedded instruction returns the original.

    That output is structurally valid (nothing unauthorised changed), so
    only the reference-based metrics can show that nothing was masked.
    """
    unmasked = "\n".join(ln.text for ln in doc.retained) + "\n"
    report = validate_candidate(doc, unmasked, policy)
    assert report["structural_pass"]
    assert masked_ids(doc, list(report["alignment_states"])) == set()


def test_brief_anchor_lines_apply_to_the_real_source_only(doc, policy):
    assert validate_candidate(doc, GOOD_OUTPUT, policy)[
        "brief_anchor_lines"] == {"applicable": False, "pass": None}
    real = policy.make_doc(config.read_text_exact(config.CANONICAL_SOURCE))
    ok = validate_candidate(real, real.render([]), policy)
    assert ok["brief_anchor_lines"]["pass"] is True
    bad = validate_candidate(real, real.render(["L001.T05"]), policy)
    assert bad["brief_anchor_lines"]["pass"] is False
    assert not bad["structural_pass"]


def test_fixture_matches_declared_shape():
    assert FIXTURE.count("\n") == 7 and "*" in FIXTURE
