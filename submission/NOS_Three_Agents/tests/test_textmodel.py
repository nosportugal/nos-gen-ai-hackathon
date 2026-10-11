"""Source model: lines, words, offsets, masking rule, rendering."""
import pytest

from conftest import FIXTURE, GOOD_IDS, GOOD_OUTPUT
from shared.textmodel import split_lines, split_token


def test_blank_lines_removed_with_position_map(doc):
    smap = doc.source_map()
    assert smap["source_line_count"] == 7
    assert smap["retained_line_count"] == 5
    assert smap["removed_source_line_indexes"] == [1, 3]
    for row in smap["retained"]:
        line = doc.retained[row["line"] - 1]
        assert FIXTURE[row["start"]:row["end"]] == line.text
        assert doc.lines[row["source_line_index"]] is line


def test_every_offset_points_at_its_text(doc):
    for tok in doc.tokens:
        assert FIXTURE[tok.start:tok.end] == tok.text
        assert FIXTURE[tok.core_start:tok.core_end] == tok.core


@pytest.mark.parametrize("text,prefix,core,suffix,maskable", [
    ("Sá,", "", "Sá", ",", True),
    ("(João,", "(", "João", ",", True),
    ("123)", "", "123", ")", True),
    ("01/02/1990.", "", "01/02/1990", ".", True),
    ("+351", "", "+351", "", True),
    ("€62.500", "", "€62.500", "", True),
    ("d'Ávila", "", "d'Ávila", "", True),
    ("ana.sa@exemplo.pt", "", "ana.sa@exemplo.pt", "", True),
    ("-", "", "-", "", False),
    ("*", "", "*", "", False),
    ("...", "", "", "...", False),
])
def test_word_core_and_surrounding_punctuation(
    policy, text, prefix, core, suffix, maskable
):
    got = split_token(text, policy.open_p, policy.close_p)
    assert got == (prefix, core, suffix, maskable)


def test_render_masks_one_asterisk_per_word(doc):
    assert doc.render(GOOD_IDS) == GOOD_OUTPUT


def test_render_preserves_spacing_tabs_and_existing_asterisk(doc):
    out = split_lines(doc.render([]))
    assert out[0] == "Relatório  Clínico\t(teste) "
    assert "pediu * desconto." in out[3]
    assert len(out) == 5 and "" not in out


def test_multiword_name_becomes_two_asterisks(policy):
    d = policy.make_doc("Ana Correia\n")
    assert d.render(["L001.T01", "L001.T02"]) == "* *\n"


def test_render_refuses_non_words_and_unknown_ids(policy):
    d = policy.make_doc("a - b\n")
    with pytest.raises(ValueError):
        d.render(["L001.T02"])
    with pytest.raises(ValueError):
        d.render(["L009.T01"])


def test_run_quotes_and_token_view(doc):
    first, last = doc.get(2, 2), doc.get(2, 4)
    quotes = doc.run_quotes(first, last)
    assert quotes[0] == "Ana-Maria d'Ávila Sá"
    assert quotes[1] == "Ana-Maria d'Ávila Sá,"
    view = doc.token_index_view().splitlines()
    assert view[0] == "L001: [1]Relatório [2]Clínico [3](teste)"
    assert len(view) == 5


def test_final_newline_is_not_an_extra_line():
    assert split_lines("a\nb\n") == ["a", "b"]
    assert split_lines("a\n\n") == ["a", ""]
    assert split_lines("") == []
