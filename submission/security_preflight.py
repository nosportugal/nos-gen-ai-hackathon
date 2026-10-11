"""Read-only preflight for a hackathon candidate; not a security guarantee."""
import argparse
import ipaddress
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
PATTERNS = {
    "google_api_key": re.compile(r"AIza[0-9A-Za-z_-]{35}"),
    "github_token": re.compile(r"ghp_[A-Za-z0-9]{36}"),
    "private_key": re.compile(
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
    ),
}


def secret_types(text):
    """Report categories only; never return secret values."""
    return [name for name, pattern in PATTERNS.items() if pattern.search(text)]


def validate_local_url(value):
    """Keep the local provider on loopback without making DNS requests."""
    parsed = urlsplit(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Local URL contains credentials or parameters.")
    # Accessing port validates malformed and out-of-range port values.
    parsed.port
    if parsed.hostname == "localhost":
        return
    try:
        address = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        raise ValueError("Local URL must use loopback.") from None
    if not address.is_loopback:
        raise ValueError("Local provider must use a loopback address.")


def indexed_secret_findings():
    """Inspect Git's index, which is what the next commit will contain."""
    listing = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, check=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    findings = []
    for filename in listing.stdout.split(b"\0"):
        if not filename:
            continue
        name = filename.decode("utf-8", errors="surrogateescape")
        blob = subprocess.run(
            ["git", "show", ":" + name], cwd=ROOT, check=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        categories = secret_types(blob.stdout.decode("utf-8", errors="ignore"))
        if categories:
            findings.append({"file": name, "categories": categories})
    return findings


def document_findings(path):
    """Inspect an explicitly selected candidate without rewriting it."""
    text = Path(path).read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError("Candidate is empty.")
    findings = [{"entity": name} for name in secret_types(text)]
    # Import our optional checker only when a candidate is requested.
    workspace = Path(__file__).resolve().parent / "NOS_Three_Agents"
    sys.path.insert(0, str(workspace))
    from shared.privacy import find_privacy_leaks
    findings.extend(
        {"entity": result.entity_type,
         "start": result.start, "end": result.end}
        for result in find_privacy_leaks(text)
    )
    return findings


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--document", type=Path)
    parser.add_argument("--local-url")
    args = parser.parse_args(argv)
    try:
        if args.local_url:
            validate_local_url(args.local_url)
        findings = indexed_secret_findings()
        if args.document:
            findings.extend(document_findings(args.document))
    except (
        OSError, ValueError, RuntimeError, ImportError,
        subprocess.CalledProcessError,
    ):
        # Third-party exceptions can contain documents, URLs or credentials.
        print("Preflight incomplete; check setup, input and local URL.")
        return 2
    print(json.dumps({"findings": findings}, ensure_ascii=True))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
