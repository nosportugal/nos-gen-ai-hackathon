"""Extract the target PDF and write the canonical source and its manifest.

Usage (workspace root, inside the virtual environment):

    python -I prepare_source.py            # refuses to change frozen files
    python -I prepare_source.py --force    # rewrite derived files

PDF text extraction and canonical-source creation.

Method: PyMuPDF ``page.get_text()`` with default arguments, pages joined
in order with no separator. This is the first step of the organisers'
tutorial (tutorials/pdf__to__txt.ipynb). The tutorial's second step
(``remove_all_special_characters``) is NOT applied: it strips accents,
punctuation and line breaks, which contradicts the brief's own sample of
a correct output.

Canonicalisation is limited to the newline convention (CRLF/CR -> LF).
Accents, punctuation and all spaces, including the space PyMuPDF emits at
the end of each line of this PDF, are left untouched.

The original PDF is only read. Derived files:
    input/raw_extraction.txt
    input/canonical_source.txt
    input/source_manifest.json
"""
from __future__ import annotations

import argparse
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from shared import config  # noqa: E402
from shared.textmodel import SourceDoc  # noqa: E402


def extract_raw(pdf_path) -> dict:
    import fitz

    with fitz.open(str(pdf_path)) as doc:
        pages = [page.get_text() for page in doc]
        meta = dict(doc.metadata or {})
    return {
        "text": "".join(pages),
        "page_count": len(pages),
        "chars_per_page": [len(p) for p in pages],
        "pdf_metadata": meta,
        "pymupdf_version": fitz.VersionBind,
    }


def canonicalize(raw_text: str) -> str:
    """Normalise the newline convention only."""
    return raw_text.replace("\r\n", "\n").replace("\r", "\n")


def write_frozen(path, text: str, force: bool) -> str:
    if path.exists():
        if config.read_text_exact(path) == text:
            return "UNCHANGED"
        if not force:
            raise SystemExit(
                f"{config.rel(path)} exists with different content; "
                "use --force to replace a frozen derived file"
            )
    config.write_text_exact(path, text)
    return "WRITTEN"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if not config.TARGET_PDF.exists():
        raise SystemExit(
            "BLOCKED: target PDF missing at " + config.rel(config.TARGET_PDF)
        )
    extracted = extract_raw(config.TARGET_PDF)
    raw = extracted["text"]
    canonical = canonicalize(raw)
    doc = SourceDoc(canonical)

    status_raw = write_frozen(config.RAW_EXTRACTION, raw, args.force)
    status_can = write_frozen(config.CANONICAL_SOURCE, canonical, args.force)
    lines = doc.lines
    manifest = {
        "target_pdf": {
            "path": config.rel(config.TARGET_PDF),
            "sha256": config.sha256_file(config.TARGET_PDF),
            "pages": extracted["page_count"],
            "pdf_metadata": extracted["pdf_metadata"],
        },
        "extraction": {
            "method": "PyMuPDF page.get_text() default, pages concatenated",
            "pymupdf_version": extracted["pymupdf_version"],
            "official_status": "SUGGESTED by the brief ('PDF to text: "
            "PyMuPDF'), not mandatory; the tutorial's accent/punctuation "
            "cleanup is deliberately not applied",
            "chars_per_page": extracted["chars_per_page"],
        },
        "raw_extraction": {
            "path": config.rel(config.RAW_EXTRACTION),
            "sha256": config.sha256_text(raw),
            "write_status": status_raw,
        },
        "canonical_source": {
            "path": config.rel(config.CANONICAL_SOURCE),
            "sha256": config.sha256_text(canonical),
            "write_status": status_can,
            "encoding": "UTF-8, no BOM",
            "newline": "LF",
            "final_newline": canonical.endswith("\n"),
            "normalisation": "newline convention only (CRLF/CR -> LF)",
            "identical_to_raw": canonical == raw,
            "unicode_nfc": unicodedata.normalize("NFC", canonical)
            == canonical,
            "chars": len(canonical),
            "source_lines": len(lines),
            "blank_lines": sum(1 for ln in lines if not ln.retained_no),
            "retained_lines": len(doc.retained),
            "lines_with_trailing_whitespace": sum(
                1 for ln in doc.retained if ln.text != ln.text.rstrip()
            ),
            "whitespace_tokens": len(doc.tokens),
            "maskable_components": len(doc.components),
            "asterisks_in_source": canonical.count("*"),
        },
        "source_map": doc.source_map(),
    }
    config.dump_json(config.SOURCE_MANIFEST, manifest)
    summary = dict(manifest["canonical_source"])
    summary["pymupdf_version"] = extracted["pymupdf_version"]
    for key, value in summary.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
