"""Expected masking of the real document under the proposed policy v3.4.

Principle: mask who the person is and when things happened to them;
keep what happened. Compared with prompt v3.2 the reference in
benchmark/real_document/ also masks marital status, number of children,
occupation, insurance plan name, ages of relatives, and the years or
durations of events in a person's life. Diseases, habits and treatments
stay readable.

It is the team's proposal, not the NOS hidden reference. No model is
called here: these tests only pin the target a prompt must reach.
"""
from pathlib import Path

from benchmark.mask_diff import mask_diff
from benchmark.mask_syntax_validation import read, validate
from benchmark.scorer import score

SUBMISSION = Path(__file__).resolve().parents[2]
DATA = SUBMISSION / "benchmark" / "real_document"
SOURCE = read(DATA / "input" / "admission_report.txt")
TRUTH = read(DATA / "ground_truth" / "admission_report.txt")
LINES = [line.rstrip() for line in TRUTH.split("\n")]
MASKED_WORDS = 72

# Line numbers as in the source file (1-based).
WHO_AND_WHEN_ARE_MASKED = {
    16: "abdominais intensas. Tem histórico de hipertensão e diabetes "
        "tipo 2, diagnosticada há * anos. É",
    17: "HIV positivo desde *, atualmente com carga viral indetectável "
        "graças ao tratamento com",
    19: "A paciente relatou que sua família tem histórico de cancro da "
        "mama (mãe falecida aos * anos)",
    20: "e doença cardíaca (pai e avô paterno). Exames genéticos "
        "realizados em * indicaram",
    23: "Estado civil: *",
    24: "Filhos: * (*, * anos e *, * anos)",
    26: "Ocupação: * * na * * * * *",
    27: "Hábitos: Ex-fumante (parou há * anos), consome álcool "
        "socialmente (2-3 doses por semana)",
    28: "Histórico de uso de substâncias: Tratamento para dependência "
        "de ansiolíticos em *",
    30: "Seguro de saúde: * * * *, apólice nº *",
}
# The brief shows these four lines unmasked in a correct output.
HEADER = [
    "Relatório de Admissão - Centro Médico Lisboa",
    "Data: 15 de abril de 2025",
    "Referência: ADM-2025-04-15-089",
    "Informações do Paciente:",
]
# What happened stays readable: these lines are not changed at all.
UNCHANGED = (18, 21, 36, 37, 38, 39, 45, 46, 47, 48)
CONTENT_KEPT = (
    "hipertensão", "diabetes tipo 2", "HIV positivo", "cancro da mama",
    "doença cardíaca", "Ex-fumante", "consome álcool socialmente",
    "(2-3 doses por semana)", "dependência de ansiolíticos",
    "Metformina 850mg 2x/dia",
)


def test_input_is_the_real_document():
    raw = read(SUBMISSION / "raw_uncensored_document.txt")
    assert SOURCE == raw.replace("\r\n", "\n")
    assert "\r" not in SOURCE and "\r" not in TRUTH


def test_reference_follows_the_masking_syntax():
    assert validate(SOURCE, TRUTH) == {"valid": True, "problems": []}
    assert len(LINES) == 61 and LINES[-1] == ""  # 60 lines + final newline


def test_who_and_when_are_masked():
    for number, expected in WHO_AND_WHEN_ARE_MASKED.items():
        assert LINES[number - 1] == expected, number


def test_header_lines_stay_unmasked():
    assert LINES[:4] == HEADER


def test_what_happened_is_kept():
    source = [line.rstrip() for line in SOURCE.split("\n")]
    for number in UNCHANGED:
        assert LINES[number - 1] == source[number - 1], number
    for phrase in CONTENT_KEPT:
        assert phrase in TRUTH, phrase


def test_reference_word_count():
    words = mask_diff(SOURCE, TRUTH)
    assert all(word["masked"] is not None for word in words.values())
    assert sum(word["masked"] for word in words.values()) == MASKED_WORDS


def test_scorer_rewards_the_reference_and_catches_misses():
    perfect = score(SOURCE, TRUTH, TRUTH)["counts"]
    assert (perfect["tp"], perfect["fp"], perfect["fn"]) == (
        MASKED_WORDS, 0, 0)
    unmasked = score(SOURCE, SOURCE, TRUTH)
    assert unmasked["counts"]["fn"] == MASKED_WORDS
    assert unmasked["metrics"]["recall"] == 0
