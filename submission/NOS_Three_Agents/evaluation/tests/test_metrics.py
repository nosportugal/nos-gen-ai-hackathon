"""Metrics, the reference file, and benchmark-leakage guards."""
from conftest import GOOD_IDS, GOOD_OUTPUT
from evaluation import metrics
from shared import config
from shared.policy import load_policy
from shared.validation import align

REFERENCE = config.ROOT / "evaluation" / "reference_annotations.json"
AMBIGUOUS_ID = "L004.T06"


def synthetic_reference(doc):
    rows = []
    for tok in doc.components:
        decision = "KEEP"
        if tok.comp_id in GOOD_IDS:
            decision = "MASK"
        elif tok.comp_id == AMBIGUOUS_ID:
            decision = "AMBIGUOUS"
        rows.append({"component_id": tok.comp_id, "decision": decision})
    entities = [
        {"decision": "MASK",
         "component_ids": ["L002.T02", "L002.T03", "L002.T04"]},
        {"decision": "MASK", "component_ids": ["L004.T03"]},
    ]
    return {"components": rows, "entities": entities}


def test_perfect_output_scores_one(doc):
    ref = synthetic_reference(doc)
    acc = metrics.accuracy(doc, ref, align(doc, GOOD_OUTPUT)["states"])
    assert (acc["tp"], acc["fp"], acc["fn"]) == (len(GOOD_IDS), 0, 0)
    assert acc["precision"] == acc["recall"] == acc["f1"] == 1.0
    assert acc["exact_agreement"] == 1.0
    assert acc["ref_ambiguous_n_excluded"] == 1
    assert acc["entity_full_mask_rate"] == 1.0
    assert metrics.reference_agreement(doc, ref, GOOD_OUTPUT)[
        "exact_reference_match"]


def test_misses_extras_and_ambiguous_are_counted_separately(doc):
    ref = synthetic_reference(doc)
    out = GOOD_OUTPUT.replace("Nota: a * pediu", "Nota: a Ana pediu")
    out = out.replace("Código: 12345-AB e", "Código: * e")
    out = out.replace("* desconto.", "* *.")
    acc = metrics.accuracy(doc, ref, align(doc, out)["states"])
    assert (acc["fn"], acc["fp"]) == (1, 1)
    assert acc["ambiguous_hidden_n"] == 1
    assert acc["recall"] == (len(GOOD_IDS) - 1) / len(GOOD_IDS)
    assert acc["over_masking_rate"] == 1 / acc["ref_keep_n"]
    assert acc["under_masking_rate"] == 1 / len(GOOD_IDS)
    assert acc["entity_full_mask_rate"] == 0.5
    assert not metrics.reference_agreement(doc, ref, out)[
        "exact_reference_match"]


def test_undefined_ratios_are_none_not_zero(doc):
    ref = synthetic_reference(doc)
    for row in ref["components"]:
        row["decision"] = "KEEP"
    ref["entities"] = []
    unmasked = doc.render([])
    acc = metrics.accuracy(doc, ref, align(doc, unmasked)["states"])
    assert acc["precision"] is None and acc["recall"] is None
    assert acc["f1"] is None and acc["under_masking_rate"] is None
    assert acc["entity_full_mask_rate"] is None
    assert acc["over_masking_rate"] == 0.0
    assert set(metrics.empty_accuracy().values()) == {None}


def test_fidelity_counts_unauthorised_characters(doc):
    states = align(doc, GOOD_OUTPUT)["states"]
    assert metrics.fidelity(doc, GOOD_OUTPUT, states) == {
        "char_inserted": 0, "char_deleted": 0, "char_substituted": 0}
    changed = GOOD_OUTPUT.replace("(teste) \n", "(teste)\n").replace(
        "desconto.", "descontos.")
    edits = metrics.fidelity(doc, changed, align(doc, changed)["states"])
    assert edits["char_deleted"] == 1 and edits["char_inserted"] == 1
    assert metrics.fidelity(doc, "x", None)["char_inserted"] is None


def test_disagreement_between_repeated_runs(doc):
    same = align(doc, GOOD_OUTPUT)["states"]
    other = align(doc, doc.render(GOOD_IDS[:-2]))["states"]
    result = metrics.disagreement([same, same, other])
    assert result["pairs_compared"] == 3
    assert result["max_words_differing"] == 2
    assert metrics.disagreement([same])["max_words_differing"] is None


def test_reference_positions_match_the_frozen_source():
    reference = config.load_json(REFERENCE)
    source = config.read_text_exact(config.CANONICAL_SOURCE)
    meta = reference["meta"]
    assert meta["source_sha256"] == config.sha256_text(source)
    assert meta["status"] == "PROVISIONAL"
    assert meta["reviewer_status"].startswith("NOT_REVIEWED")
    doc = load_policy().make_doc(source)
    rows = reference["components"]
    assert len(rows) == len(doc.components)
    for item in rows + reference["entities"]:
        assert 0 <= item["start"] < item["end"] <= len(source)
        assert source[item["start"]:item["end"]] == item["substring"]
    decisions = {r["decision"] for r in rows}
    assert decisions == {"MASK", "AMBIGUOUS", "KEEP"}
    # The brief shows these three lines unmasked: none may be MASK.
    assert all(r["decision"] == "KEEP" for r in rows if r["line"] <= 3)


def test_agents_cannot_see_the_reference():
    """No agent or runtime module reads evaluation data."""
    runtime = list((config.ROOT / "agents").rglob("*.py"))
    runtime += list((config.ROOT / "agents").rglob("*.txt"))
    runtime += [p for p in (config.ROOT / "shared").glob("*.py")
                if p.name != "freeze.py"]  # freeze only hashes the file
    runtime = [p for p in runtime if "tests" not in p.parts]
    assert len(runtime) > 15
    for path in runtime:
        text = path.read_text(encoding="utf-8")
        assert "reference_annotations" not in text, path
        assert "import evaluation" not in text, path
        assert "from evaluation" not in text, path


def test_prompts_contain_no_text_from_the_real_document():
    """Prompt examples are synthetic: no real value leaks into them."""
    reference = config.load_json(REFERENCE)
    secrets = {e["substring"] for e in reference["entities"]
               if e["decision"] == "MASK" and len(e["substring"]) > 3}
    for path in (config.ROOT / "agents").rglob("*.txt"):
        text = path.read_text(encoding="utf-8")
        for value in secrets:
            assert value not in text, (path.name, value)
