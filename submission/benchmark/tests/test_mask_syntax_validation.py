"""Masking rules, on synthetic text."""
from benchmark.mask_syntax_validation import main, mask, validate

SOURCE = (
    "Relatório  Clínico\t(teste) \n"
    "\n"
    "Nome: Ana-Maria d'Ávila Sá, nascida a 01/02/1990.\n"
    "   \n"
    "Telefone: +351 91 000 00 00; email: ana.sa@exemplo.pt\n"
    "Nota: a Ana pediu * desconto.\n"
)
GOOD = (
    "Relatório  Clínico\t(teste) \n"
    "Nome: * * *, nascida a *.\n"
    "Telefone: * * * * *; email: *\n"
    "Nota: a * pediu * desconto.\n"
)


def test_mask_keeps_surrounding_punctuation():
    assert mask("Sá,") == "*,"
    assert mask("(João,") == "(*,"
    assert mask("01/02/1990.") == "*."
    assert mask("ana.sa@exemplo.pt") == "*"
    assert mask("-") is None and mask("*") is None


def test_correct_masking_is_valid():
    assert validate(SOURCE, GOOD) == {"valid": True, "problems": []}
    assert validate(SOURCE, GOOD.rstrip("\n"))["valid"]  # final newline


def test_which_words_are_masked_does_not_matter():
    copy = "".join(ln + "\n" for ln in SOURCE.split("\n") if ln.strip())
    assert validate(SOURCE, copy)["valid"]  # nothing masked
    over = GOOD.replace("Relatório  Clínico", "*  *")
    assert validate(SOURCE, over)["valid"]  # too much masked


def test_trailing_spaces_are_ignored():
    stripped = GOOD.replace("(teste) \n", "(teste)\n")
    assert validate(SOURCE, stripped)["valid"]
    added = GOOD.replace("desconto.\n", "desconto.  \n")
    assert validate(SOURCE, added)["valid"]


def test_rule_violations():
    bad = {
        "typo fixed": GOOD.replace("Relatório", "Relatorio"),
        "spacing": GOOD.replace("Relatório  ", "Relatório "),
        "joined": GOOD.replace("*.\nTelefone", "*. Telefone"),
        "blank kept": GOOD.replace("\nNome", "\n\nNome"),
        "fence": "```\n" + GOOD + "```\n",
        "two asterisks": GOOD.replace("Nome: * * *", "Nome: ** * *"),
        "punctuation lost": GOOD.replace("* * *,", "* * *"),
        "crlf": GOOD.replace("\n", "\r\n"),
    }
    for name, masked in bad.items():
        assert not validate(SOURCE, masked)["valid"], name


def test_command_line(tmp_path, capsys):
    src, out = tmp_path / "file.txt", tmp_path / "file_masked.txt"
    src.write_bytes(SOURCE.encode("utf-8"))
    out.write_bytes(GOOD.encode("utf-8"))
    assert main([str(src), str(out)]) == 0
    assert '"valid": true' in capsys.readouterr().out
    out.write_bytes(GOOD.replace("Nota", "Note").encode("utf-8"))
    assert main([str(src), str(out)]) == 1


def test_word_counts_remain_distinct_from_syntax(capsys):
    from benchmark.mask_syntax_validation import compare_word_counts

    source = "Nome: Ana\r\n\r\nIdade: 20\r\n"
    changed = "Nome: outra\n   \nIdade: 99\n"
    assert compare_word_counts(source, changed) == 0
    assert not validate(source.replace("\r\n", "\n"), changed)["valid"]
    assert compare_word_counts(source, "Nome: * extra\nIdade: 20") == 1
    assert "line 1: 2 words -> 3" in capsys.readouterr().out
    assert compare_word_counts(source, "") == 1
    assert "submission.txt is empty" in capsys.readouterr().out
    assert compare_word_counts(source, "Nome: *") == 1
    assert "line count differs: 2 vs 1" in capsys.readouterr().out
