from anonymizer import detector, gemini_client
from anonymizer.detector import Detection, DetectedSpan
from anonymizer.spans import Category, Span

TEXT = "Nome: Ana Correia\nContacto: Ana Correia, 912 345 678\nFim"


def found(line, text, category=Category.NAME):
    return DetectedSpan(line=line, text=text, category=category, reason="r")


def test_number_lines():
    assert detector.number_lines("a\nb") == "L001| a\nL002| b"


def test_prompt_has_one_placeholder_and_gets_the_document():
    template = detector.PROMPT_PATH.read_text(encoding="utf-8")
    assert template.count(detector.PLACEHOLDER) == 1

    prompt = detector.build_prompt(TEXT)
    assert detector.PLACEHOLDER not in prompt
    assert "L002| Contacto: Ana Correia, 912 345 678" in prompt


def test_detect_fixes_lines_drops_unknown_and_duplicates(monkeypatch):
    answer = Detection(spans=[
        found(1, "Ana Correia"),
        found(1, "Ana Correia"),                       # duplicate
        found(3, "912 345 678", Category.CONTACT),     # wrong line
        found(2, "Rui Tavares"),                       # not in document
        found(1, "  "),                                # empty
    ])
    monkeypatch.setattr(
        gemini_client, "generate_json", lambda prompt, schema: answer,
    )

    assert detector.detect(TEXT) == [
        Span(1, "Ana Correia", Category.NAME, "r"),
        Span(2, "912 345 678", Category.CONTACT, "r"),
    ]


def test_locate_matches_whole_words_only():
    lines = ["Mariana", "Ana"]
    assert detector._locate([found(1, "Ana")], lines) == [
        Span(2, "Ana", Category.NAME, "r"),
    ]


def test_generate_json_uses_cache(monkeypatch, tmp_path):
    calls = []

    def fake_call(model, prompt, schema):
        calls.append(prompt)
        return '{"spans": []}'

    monkeypatch.setattr(gemini_client, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(gemini_client, "_call", fake_call)

    first = gemini_client.generate_json("same prompt", Detection)
    second = gemini_client.generate_json("same prompt", Detection)

    assert first == second == Detection(spans=[])
    assert len(calls) == 1
