"""Confusion counts, metrics and a whole sweep with a stub model."""
import json

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from benchmark import scorer

SOURCE = "Nome: Ana Lima\n\nData: hoje\n"
TRUTH = "Nome: * *\nData: hoje\n"


def test_score_counts_and_lists_the_errors():
    result = scorer.score(SOURCE, "Nome: * Lima\nData: *\n", TRUTH)
    assert result["counts"] == {"tp": 1, "fp": 1, "fn": 1, "tn": 2}
    assert result["false_negatives"] == [{"id": "L1:W3", "text": "Lima"}]
    assert result["false_positives"] == [{"id": "L3:W2", "text": "hoje"}]
    assert result["metrics"]["f1"] == 0.5
    assert result["metrics"]["accuracy"] == 0.6


def test_broken_line_counts_as_not_masked():
    result = scorer.score(SOURCE, "Nome: *\nData: hoje\n", TRUTH)
    assert result["counts"] == {"tp": 0, "fp": 0, "fn": 2, "tn": 3}
    assert len(result["unaligned"]) == 3  # every word of line 1


def test_metrics_without_positives_are_null():
    m = scorer.metrics({"tp": 0, "fp": 0, "fn": 0, "tn": 3})
    assert m["precision"] is None and m["recall"] is None
    assert m["accuracy"] == 1 and m["fpr"] == 0


def test_sweep_writes_one_json_per_document(tmp_path, monkeypatch):
    for sub, text in (("input", SOURCE), ("ground_truth", TRUTH)):
        (tmp_path / "data" / sub).mkdir(parents=True)
        (tmp_path / "data" / sub / "doc_001.txt").write_text(text)
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("Mask personal data.\n")
    reply = AIMessage(content=TRUTH,
                      response_metadata={"finish_reason": "STOP"})
    monkeypatch.setattr(scorer, "get_llm",
                        lambda *a: RunnableLambda(lambda messages: reply))
    code = scorer.main(["--prompt", str(prompt), "--dataset",
                        str(tmp_path / "data"), "--runs",
                        str(tmp_path / "runs")])
    assert code == 0
    [sweep] = (tmp_path / "runs").iterdir()
    run = json.loads((sweep / "doc_001.json").read_text())
    assert (sweep / "doc_001.txt").read_text() == TRUTH
    assert run["syntax"]["valid"] and run["metrics"]["f1"] == 1
    assert run["false_positives"] == run["false_negatives"] == []
    summary = json.loads((sweep / "summary.json").read_text())
    assert summary["counts"] == {"tp": 2, "fp": 0, "fn": 0, "tn": 3}
