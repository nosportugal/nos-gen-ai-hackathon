"""Freeze manifest: hashes of everything that can change an agent output.

Written once before measured trials (``run_benchmark.py --freeze``) and
verified before every live run. Any difference blocks live runs until the
change is documented and the manifest is rewritten on purpose.
"""
from __future__ import annotations

import platform
from importlib import metadata

from . import artifacts, config
from .gemini_client import load_model_config

FROZEN_GLOBS = (
    "input/canonical_source.txt",
    "shared/policy/*.json",
    "shared/model_config.json",
    "shared/*.py",
    "agents/*.py",
    "agents/*/*.py",
    "agents/*/*.txt",
    "agents/*/*.json",
    "evaluation/reference_annotations.json",
    "requirements.txt",
)


def current_state() -> dict:
    files = {}
    for pattern in FROZEN_GLOBS:
        for path in sorted(config.ROOT.glob(pattern)):
            files[config.rel(path)] = config.sha256_file(path)
    cfg = load_model_config()
    try:
        pymupdf = metadata.version("PyMuPDF")
    except metadata.PackageNotFoundError:
        pymupdf = "NOT_INSTALLED"
    return {
        "files": files,
        "model_id": cfg["model_id"],
        "model_id_source": cfg["model_id_source"],
        "temperature": cfg["temperature"],
        "max_output_tokens": cfg["max_output_tokens"],
        "python": platform.python_version(),
        "pymupdf": pymupdf,
    }


def write_manifest(note: str = "") -> dict:
    manifest = {"frozen_utc": artifacts.utc_now(), "note": note}
    manifest.update(current_state())
    config.dump_json(config.FREEZE_MANIFEST, manifest)
    return manifest


def verify() -> list:
    """Return a list of differences; empty means the freeze holds."""
    if not config.FREEZE_MANIFEST.exists():
        return ["freeze manifest missing: run run_benchmark.py --freeze"]
    frozen = config.load_json(config.FREEZE_MANIFEST)
    now = current_state()
    diffs = []
    for key in ("model_id", "temperature", "max_output_tokens", "python",
                "pymupdf"):
        was = frozen.get(key)
        if was != now[key]:
            diffs.append(f"{key}: frozen {was!r}, now {now[key]!r}")
    for path in sorted(set(frozen["files"]) | set(now["files"])):
        if frozen["files"].get(path) != now["files"].get(path):
            diffs.append(f"changed since freeze: {path}")
    return diffs
