"""Download and verify the official reference materials.

Usage (from the workspace root, inside the virtual environment):

    python -I references/fetch_references.py

Existing files are never overwritten. The script records, for each file,
its source, download status, type, size, SHA-256 and page count, plus the
commit of the reference checkout, in references/evidence_manifest.json.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OFFICIAL = HERE / "official"
CLONE = HERE / "nos-gen-ai-hackathon"
TARGET_IN_REPO = CLONE / "raw_data" / "document_to_anonymize.pdf"
TARGET_COPY = ROOT / "input" / "original" / "document_to_anonymize.pdf"
SITE = "https://lisbon.hackjunction.com/assets/"
REPO_URL = "https://github.com/nosportugal/nos-gen-ai-hackathon"

DOWNLOADS = [
    {
        "role": "event challenge brief (NOT the document to anonymize)",
        "name": "NOS - JunctionX Lisbon 2026.pdf",
        "url": SITE + "challenges/"
        + urllib.parse.quote("NOS - JunctionX Lisbon 2026.pdf"),
    },
    {
        "role": "event regulations",
        "name": "JunctionX Lisbon 2026 - Official Regulations.pdf",
        "url": SITE
        + urllib.parse.quote(
            "JunctionX Lisbon 2026 - Official Regulations.pdf"
        ),
    },
]


def describe(path: Path) -> dict:
    data = path.read_bytes()
    info = {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "size_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "is_pdf": data[:5] == b"%PDF-",
    }
    if info["is_pdf"]:
        import fitz

        with fitz.open(stream=data, filetype="pdf") as doc:
            info["pages"] = doc.page_count
            meta = doc.metadata or {}
            info["pdf_title"] = meta.get("title", "")
            info["pdf_author"] = meta.get("author", "")
            info["pdf_creator"] = meta.get("creator", "")
            info["pdf_created"] = meta.get("creationDate", "")
    return info


def download(item: dict) -> dict:
    dest = OFFICIAL / item["name"]
    record = {"role": item["role"], "url": item["url"]}
    if dest.exists():
        record["download_status"] = "ALREADY_PRESENT"
    else:
        try:
            req = urllib.request.Request(
                item["url"], headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read()
                record["http_status"] = resp.status
                record["last_modified"] = resp.headers.get("Last-Modified")
            dest.write_bytes(data)
            record["download_status"] = "DOWNLOADED"
        except Exception as exc:  # recorded, never substituted
            record["download_status"] = "BLOCKED"
            record["error"] = type(exc).__name__ + ": " + str(exc)[:200]
            return record
    record.update(describe(dest))
    return record


def git(*args: str) -> str:
    out = subprocess.run(
        ["git", "-C", str(CLONE), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    return out.stdout.strip()


def repo_record() -> dict:
    if not (CLONE / ".git").exists():
        return {"url": REPO_URL, "status": "MISSING_CHECKOUT"}
    return {
        "url": REPO_URL,
        "status": "CLONED",
        "checked_out_branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "head_commit": git("rev-parse", "HEAD"),
        "head_commit_date": git("log", "-1", "--format=%cI"),
        "origin_main": git("rev-parse", "origin/main"),
        "origin_junctionx_branch": git(
            "rev-parse", "origin/junctionx-lisbon-readme"
        ),
        "working_tree_dirty_files": len(
            [x for x in git("status", "--short").splitlines() if x]
        ),
        "note": "main is the default branch teams fork; the JunctionX "
        "edits live on the unmerged branch junctionx-lisbon-readme "
        "(pull request 36).",
    }


def target_record() -> dict:
    record = {
        "role": "document to anonymize (the actual target)",
        "source": REPO_URL + " raw_data/document_to_anonymize.pdf",
    }
    if not TARGET_IN_REPO.exists():
        record["status"] = "MISSING_IN_CHECKOUT"
        return record
    if not TARGET_COPY.exists():
        TARGET_COPY.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(TARGET_IN_REPO, TARGET_COPY)
        record["status"] = "COPIED_FROM_CHECKOUT"
    else:
        record["status"] = "ALREADY_PRESENT"
    record.update(describe(TARGET_COPY))
    record["identical_to_checkout_file"] = (
        TARGET_COPY.read_bytes() == TARGET_IN_REPO.read_bytes()
    )
    record["git_blob_main"] = git(
        "rev-parse", "origin/main:raw_data/document_to_anonymize.pdf"
    )
    record["git_blob_junctionx_branch"] = git(
        "rev-parse",
        "origin/junctionx-lisbon-readme:raw_data/document_to_anonymize.pdf",
    )
    return record


def main() -> int:
    OFFICIAL.mkdir(parents=True, exist_ok=True)
    manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        ),
        "official_downloads": [download(item) for item in DOWNLOADS],
        "repository": repo_record(),
        "target_document": target_record(),
    }
    out = HERE / "evidence_manifest.json"
    out.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
