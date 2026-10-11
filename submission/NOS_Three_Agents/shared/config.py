"""Paths, exact text I/O, JSON helpers and hashing."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = ROOT / "input"
RUNS_DIR = ROOT / "runs"
TARGET_PDF = INPUT_DIR / "original" / "document_to_anonymize.pdf"
RAW_EXTRACTION = INPUT_DIR / "raw_extraction.txt"
CANONICAL_SOURCE = INPUT_DIR / "canonical_source.txt"
SOURCE_MANIFEST = INPUT_DIR / "source_manifest.json"
POLICY_PATH = ROOT / "shared" / "policy" / "masking_policy_v1.json"
MODEL_CONFIG_PATH = ROOT / "shared" / "model_config.json"
FREEZE_MANIFEST = ROOT / "evaluation" / "freeze_manifest.json"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_file(path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def read_text_exact(path) -> str:
    """Read UTF-8 text with no newline translation."""
    return Path(path).read_bytes().decode("utf-8")


def write_text_exact(path, text: str) -> None:
    """Write UTF-8 text with no newline translation."""
    Path(path).write_bytes(text.encode("utf-8"))


def load_json(path):
    return json.loads(read_text_exact(path))


def dump_json(path, obj) -> None:
    text = json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
    write_text_exact(path, text)


def rel(path) -> str:
    """Workspace-relative path with forward slashes."""
    try:
        return str(Path(path).resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)
