"""Word ids and masked flags, on synthetic text."""
from benchmark.mask_diff import mask_diff
from benchmark.tests.test_mask_syntax_validation import GOOD, SOURCE


def masked_ids(diff):
    return sorted(k for k, w in diff.items() if w["masked"])


def test_ids_point_at_the_source_words():
    diff = mask_diff(SOURCE, GOOD)
    for word in diff.values():
        assert SOURCE[word["start"]:word["end"]] == word["text"]
    # Line numbers are file lines, blank lines included.
    assert diff["L3:W2"]["text"] == "Ana-Maria"
    assert diff["L5:W2"]["text"] == "+351"
    assert diff["L6:W3"]["text"] == "Ana"


def test_masked_flags():
    diff = mask_diff(SOURCE, GOOD)
    assert masked_ids(diff) == [
        "L3:W2", "L3:W3", "L3:W4", "L3:W7",
        "L5:W2", "L5:W3", "L5:W4", "L5:W5", "L5:W6", "L5:W8",
        "L6:W3",
    ]
    assert diff["L1:W1"] == {"text": "Relatório", "start": 0, "end": 9,
                             "masked": False}
    # "*" in the source has nothing to mask, so it has no id.
    assert "L6:W5" not in diff


def test_same_ids_for_every_masked_version():
    copy = "".join(ln + "\n" for ln in SOURCE.split("\n") if ln.strip())
    assert mask_diff(SOURCE, copy).keys() == mask_diff(SOURCE, GOOD).keys()
    assert masked_ids(mask_diff(SOURCE, copy)) == []


def test_leading_spaces_do_not_shift_word_numbers():
    diff = mask_diff("  Nome: Rui\n", "  Nome: *\n")
    assert diff["L1:W2"]["text"] == "Rui" and diff["L1:W2"]["masked"]


def test_rule_breaks_are_unknown_not_guessed():
    changed = GOOD.replace("Nota: a *", "Nota: a Anna")
    assert mask_diff(SOURCE, changed)["L6:W3"]["masked"] is None
    joined = GOOD.replace("*.\nTelefone", "*. Telefone")
    assert mask_diff(SOURCE, joined)["L3:W2"]["masked"] is None


def test_bare_asterisk_counts_as_masked():
    diff = mask_diff("Rua Nova, 12\n", "* *, *\n")
    assert diff["L1:W2"]["masked"] and diff["L1:W3"]["masked"]
    diff = mask_diff("Rua Nova, 12\n", "* * *\n")
    assert diff["L1:W2"]["masked"]


def test_trailing_spaces_do_not_break_alignment():
    diff = mask_diff("Nome: Rui \n", "Nome: *\n")
    assert diff["L1:W2"]["masked"]
