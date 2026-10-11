"""Synthetic tests for read-only security preflight controls."""
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "security_preflight.py"
SPEC = importlib.util.spec_from_file_location("security_preflight", SCRIPT)
preflight = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preflight)


@pytest.mark.parametrize("url", [
    "http://localhost:8080/v1",
    "http://127.0.0.1:8080/v1",
    "https://[::1]:8080/v1",
])
def test_loopback_url_is_allowed(url):
    preflight.validate_local_url(url)


@pytest.mark.parametrize("url", [
    "http://example.com/v1",
    "http://192.168.1.10/v1",
    "http://localhost.example.com/v1",
    "http://user:password@localhost/v1",
    "http://localhost/v1?key=secret",
    "file:///tmp/server",
    "http://localhost:99999/v1",
])
def test_external_or_unsafe_url_is_rejected(url):
    with pytest.raises(ValueError):
        preflight.validate_local_url(url)


def test_secret_detection_does_not_return_secret_values():
    synthetic_key = "AIza" + "A" * 35
    result = preflight.secret_types(synthetic_key)
    assert result == ["google_api_key"]
    assert synthetic_key not in str(result)


def test_empty_candidate_is_rejected_before_optional_import(tmp_path):
    candidate = tmp_path / "candidate.txt"
    candidate.write_text(" \n", encoding="utf-8")
    with pytest.raises(ValueError, match="Candidate is empty"):
        preflight.document_findings(candidate)


def test_preflight_errors_do_not_print_exception_content(monkeypatch, capsys):
    def fail():
        raise RuntimeError("SENSITIVE_SYNTHETIC_CONTENT")
    monkeypatch.setattr(preflight, "indexed_secret_findings", fail)
    assert preflight.main([]) == 2
    assert "SENSITIVE_SYNTHETIC_CONTENT" not in capsys.readouterr().out
