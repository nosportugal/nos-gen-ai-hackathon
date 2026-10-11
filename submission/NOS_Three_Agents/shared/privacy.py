"""Lightweight, offline privacy checks for English, Portuguese and Spanish."""
from functools import lru_cache

import spacy
import tldextract
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import NerModelConfiguration, SpacyNlpEngine
from presidio_analyzer.predefined_recognizers import (
    EmailRecognizer,
    PhoneRecognizer,
    SpacyRecognizer,
)

LANGUAGES = ("en", "pt", "es")
MODEL = "xx_ent_wiki_sm"
ENTITIES = (
    "PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "LOCATION", "ORGANIZATION",
)


class OfflineEmailRecognizer(EmailRecognizer):
    """Validate domains using bundled rules without network requests."""

    domain_rules = tldextract.TLDExtract(suffix_list_urls=(), cache_dir=None)

    def validate_result(self, pattern_text):
        return bool(self.domain_rules(pattern_text).fqdn)


@lru_cache(maxsize=1)
def build_privacy_analyzer():
    """Load one shared NER pipeline; never download models during a test."""
    try:
        pipeline = spacy.load(MODEL)
    except OSError as exc:
        raise RuntimeError(
            "Missing multilingual model. Run: "
            "python -m spacy download xx_ent_wiki_sm"
        ) from exc

    engine = SpacyNlpEngine(
        models=[
            {"lang_code": language, "model_name": MODEL}
            for language in LANGUAGES
        ],
        ner_model_configuration=NerModelConfiguration(
            labels_to_ignore=["MISC"],
            model_to_presidio_entity_mapping={
                "PER": "PERSON", "LOC": "LOCATION", "ORG": "ORGANIZATION",
            },
        ),
    )
    # Presidio's default load() would load the same model three times.
    engine.nlp = dict.fromkeys(LANGUAGES, pipeline)
    registry = RecognizerRegistry(supported_languages=list(LANGUAGES))
    for language in LANGUAGES:
        registry.add_recognizer(SpacyRecognizer(
            supported_language=language,
            supported_entities=["PERSON", "LOCATION", "ORGANIZATION"],
        ))
        registry.add_recognizer(OfflineEmailRecognizer(
            supported_language=language,
        ))
        registry.add_recognizer(PhoneRecognizer(
            supported_language=language,
            supported_regions=["PT", "ES", "US", "GB", "BR"],
        ))
    return AnalyzerEngine(
        nlp_engine=engine,
        registry=registry,
        supported_languages=list(LANGUAGES),
    )


def find_privacy_leaks(text, language=None):
    """Scan one language, or all three for mixed/unknown-language documents.

    The small NER model is heuristic: no findings do not prove anonymity.
    Scores of 0.4 include phone matches even without nearby context words.
    """
    if language is not None and language not in LANGUAGES:
        raise ValueError(f"Unsupported language: {language}")
    analyzer = build_privacy_analyzer()
    findings = {}
    for code in (LANGUAGES if language is None else (language,)):
        for result in analyzer.analyze(
            text=text, entities=list(ENTITIES), language=code,
            score_threshold=0.4,
        ):
            key = (result.start, result.end, result.entity_type)
            if key not in findings or result.score > findings[key].score:
                findings[key] = result
    return sorted(
        findings.values(),
        key=lambda result: (result.start, result.end, result.entity_type),
    )
