"""Privacy validation with one small multilingual model."""
import os
from pathlib import Path

import pytest

gx = pytest.importorskip("great_expectations")
pd = pytest.importorskip("pandas")
pytest.importorskip("presidio_analyzer")
spacy = pytest.importorskip("spacy")
if not spacy.util.is_package("xx_ent_wiki_sm"):
    pytest.skip(
        "Install requirements-privacy.txt to run privacy checks.",
        allow_module_level=True,
    )

from great_expectations.data_context.types.base import (  # noqa: E402
    DataContextConfig,
    InMemoryStoreBackendDefaults,
)

from shared.privacy import (  # noqa: E402
    build_privacy_analyzer,
    find_privacy_leaks,
)


@pytest.mark.parametrize("language", ["en", "pt", "es"])
def test_contact_detection_in_each_language(language):
    text = "Email: ana@example.com; +351 912 345 678."
    entities = {
        result.entity_type
        for result in find_privacy_leaks(text, language=language)
    }
    assert {"EMAIL_ADDRESS", "PHONE_NUMBER"} <= entities


def test_model_is_shared_between_languages():
    engine = build_privacy_analyzer().nlp_engine
    assert engine.nlp["en"] is engine.nlp["pt"] is engine.nlp["es"]


def test_mixed_language_findings_are_deduplicated():
    results = find_privacy_leaks("Email: ana@example.com")
    emails = [r for r in results if r.entity_type == "EMAIL_ADDRESS"]
    assert len(emails) == 1


def test_unsupported_language_is_rejected():
    with pytest.raises(ValueError, match="Unsupported language"):
        find_privacy_leaks("Synthetic text", language="zz")


def validate_findings(dataframe):
    # Disable usage telemetry before context creation for private validation.
    context = gx.get_context(
        mode="ephemeral",
        project_config=DataContextConfig(
            analytics_enabled=False,
            store_backend_defaults=InMemoryStoreBackendDefaults(),
        ),
    )
    source = context.data_sources.add_pandas(name="privacy")
    asset = source.add_dataframe_asset(name="findings")
    definition = asset.add_batch_definition_whole_dataframe("all_findings")
    batch = definition.get_batch(batch_parameters={"dataframe": dataframe})
    return batch.validate(
        gx.expectations.ExpectTableRowCountToEqual(value=0)
    )


@pytest.mark.parametrize("row_count", [0, 1])
def test_privacy_expectation_rejects_findings(row_count):
    dataframe = pd.DataFrame({"entity": ["PERSON"] * row_count})
    assert validate_findings(dataframe).success == (row_count == 0)


@pytest.mark.parametrize("language", ["en", "pt", "es"])
def test_named_entity_detection(language):
    findings = find_privacy_leaks("Barack Obama visited London.", language)
    entities = {result.entity_type for result in findings}
    assert {"PERSON", "LOCATION"} <= entities


def test_document_has_no_detected_privacy_leaks():
    document_path = os.environ.get("NOS_PRIVACY_DOCUMENT")
    if not document_path:
        pytest.skip("Set NOS_PRIVACY_DOCUMENT to validate a real document.")
    submission_path = Path(document_path).expanduser().resolve()
    assert submission_path.is_file(), f"Missing file: {submission_path}"
    text = submission_path.read_text(encoding="utf-8")
    assert text.strip(), "Document is empty; cannot validate anonymity."

    findings = find_privacy_leaks(text)
    # Report positions, not the potentially sensitive source text.
    dataframe = pd.DataFrame(
        [
            {
                "entity": result.entity_type,
                "start": result.start,
                "end": result.end,
                "score": result.score,
            }
            for result in findings
        ],
        columns=["entity", "start", "end", "score"],
    )
    validation = validate_findings(dataframe)
    assert validation.success, (
        "Possible privacy leaks detected:\n" + dataframe.to_string(index=False)
    )
