#!/usr/bin/env python3
"""
Generate synthetic medical admission documents and masked versions using Gemini.

Requirements:
    pip install google-genai python-dotenv

.env file:
    Either of these is accepted:
        GEMINI_API_KEY=your_gemini_api_key_here
    or:
        API_KEY=your_gemini_api_key_here

Examples:
    python data_generator.py --count 2
    python data_generator.py --count 5 --outdir generated_documents
    python data_generator.py --count 2 --max-retries 6
    python data_generator.py --count 2 --write-items-file
"""

import argparse
import json
import os
import random
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from dotenv import load_dotenv
from google import genai
from google.genai import types


DEFAULT_MODEL = "gemini-3.8-flash"
DEFAULT_OUTDIR = "generated_documents"

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

# Matches words/numbers while preserving punctuation around them.
# Examples:
#   Ana Correia -> * *
#   12/03/1978 -> */*/*
#   +351 912 345 678 -> +* * * *
#   ana.correia@email.pt -> *.*@*.*
MASKABLE_TOKEN_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9]+")


def build_prompt(document_number: int) -> str:
    return f"""
Generate one fully synthetic Portuguese medical admission report.

The document must be similar in style, structure, and level of detail to a hospital or medical admission report from Portugal.

The document must be written in Portuguese from Portugal.

All data must be completely fictitious.
Do not use real people, real patients, real public figures, or real addresses tied to real individuals.
Use realistic but mock data only.

The response must be valid JSON only.
Do not include markdown.
Do not include explanations outside the JSON.

Return exactly this JSON structure:

{{
  "document_text": "Full synthetic report text here",
  "sensitive_items": [
    {{
      "category": "Name",
      "text": "Exact sensitive text span appearing in document_text"
    }}
  ]
}}

The generated document should include realistic sections such as:
- Relatório de Admissão
- Data
- Referência
- Informações do Paciente
- Histórico Médico
- Informações Sociais e Comportamentais
- Informações Financeiras
- Dados Biométricos
- Contactos de Emergência
- Assinatura Digital

Sensitive information that MUST be included in sensitive_items:
- Patient full name and partial names when repeated in the text
- Family member names
- Emergency contact names
- Companion names
- Doctor, nurse, or staff names if tied to personal identification
- NIF
- Cartão de Cidadão
- Número de Utente do SNS
- Número de Segurança Social or NISS
- Passport numbers, if present
- Phone numbers
- Email addresses
- Residential addresses
- Door numbers
- Postal codes
- Specific neighbourhood names if they are part of the personal address
- Date of birth
- Exact patient age
- Marital status
- Profession
- Employer
- Nationality
- Religion
- Political affiliation, if present
- Patient hospital file numbers
- Patient-specific admission IDs
- Insurance policy numbers
- IBAN
- Bank account numbers
- Credit card numbers
- Credit card expiry dates
- CVV
- Biometric identifiers
- Fingerprint IDs
- Face recognition IDs
- Professional licence numbers tied to a named doctor or nurse, such as CRM or Ordem number

Information that MUST NOT be included in sensitive_items:
- Document labels, such as "Nome:", "Data de Nascimento:", "Morada:", "Contacto:"
- Section headers, such as "Informações do Paciente:"
- Hospital, clinic, or institution names
- Document creation dates, such as "Data: 15 de abril de 2025"
- General administrative document references, such as "Referência: ADM-2025-04-15-089"
- Generic medical terms
- Symptoms
- Diagnosis names
- Medication names
- Procedure names
- Department names
- Generic clinical values such as height, weight, blood type, and blood pressure, unless they are part of a unique biometric identifier

Rules for sensitive_items:
- Include only exact substrings that appear in document_text.
- Include minimal spans that should be masked while preserving the sentence context.
- Do not include full sentences unless the entire sentence is sensitive.
- Do not include labels or punctuation that can safely remain visible.
- If a full name appears once and a partial name appears elsewhere, include both exact spans.
- Avoid standalone city names like "Lisboa" unless they are inside a full residential address span.
- Avoid duplicates.
- Be comprehensive.

Masking examples:
- "Ana Correia" should be listed as "Ana Correia"
- "Rua das Flores, 123, 2.º Esq., 1000-001 Lisboa" should be listed as that exact address
- "ana.correia@example.invalid" should be listed as that exact email

Document number: {document_number}
"""


def remove_empty_lines(text: str) -> str:
    """
    Remove empty lines while preserving all non-empty line content exactly.
    """
    lines = text.splitlines()
    non_empty_lines = [line for line in lines if line.strip() != ""]
    return "\n".join(non_empty_lines)


def extract_json(text: str) -> Dict[str, Any]:
    """
    Parse Gemini's JSON response.

    If the model accidentally wraps JSON in markdown fences, remove them.
    """
    cleaned = text.strip()

    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()

    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Could not parse Gemini response as JSON.\n\nResponse was:\n{cleaned}"
        ) from exc

    if not isinstance(payload, dict):
        raise ValueError("Gemini response is not a JSON object.")

    return payload


def normalize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Clean document_text and sensitive_items.
    """
    document_text = payload.get("document_text", "")
    sensitive_items = payload.get("sensitive_items", [])

    if isinstance(document_text, str):
        payload["document_text"] = remove_empty_lines(document_text.strip())

    if isinstance(sensitive_items, list):
        cleaned_items = []

        for item in sensitive_items:
            if not isinstance(item, dict):
                continue

            category = str(item.get("category", "")).strip()
            text = str(item.get("text", "")).strip()

            if not category or not text:
                continue

            cleaned_items.append(
                {
                    "category": category,
                    "text": text,
                }
            )

        payload["sensitive_items"] = cleaned_items

    return payload


def validate_payload(payload: Dict[str, Any]) -> None:
    """
    Basic validation to make sure the generated response has the expected shape.
    """
    if not isinstance(payload, dict):
        raise ValueError("Gemini response is not a JSON object.")

    if "document_text" not in payload:
        raise ValueError("Missing field: document_text.")

    if "sensitive_items" not in payload:
        raise ValueError("Missing field: sensitive_items.")

    if not isinstance(payload["document_text"], str):
        raise ValueError("document_text must be a string.")

    if not isinstance(payload["sensitive_items"], list):
        raise ValueError("sensitive_items must be a list.")

    document_text = payload["document_text"]
    missing_items: List[str] = []

    for item in payload["sensitive_items"]:
        if not isinstance(item, dict):
            raise ValueError("Each sensitive item must be an object.")

        if "category" not in item or "text" not in item:
            raise ValueError("Each sensitive item must contain category and text.")

        if not isinstance(item["category"], str):
            raise ValueError("Sensitive item category must be a string.")

        if not isinstance(item["text"], str):
            raise ValueError("Sensitive item text must be a string.")

        text = item["text"].strip()

        if text and text not in document_text:
            missing_items.append(text)

    if missing_items:
        print(
            "Warning: Some sensitive items were not found exactly in the document text:",
            file=sys.stderr,
        )
        for value in missing_items:
            print(f"  - {value}", file=sys.stderr)


def get_status_code_from_exception(exc: Exception) -> Optional[int]:
    """
    Try to extract an HTTP status code from google-genai exceptions.
    """
    status_code = getattr(exc, "status_code", None)

    if isinstance(status_code, int):
        return status_code

    match = re.search(r"\b(429|500|502|503|504)\b", str(exc))

    if match:
        return int(match.group(1))

    return None


def is_retryable_error(exc: Exception) -> bool:
    """
    Return True for temporary API errors worth retrying.
    """
    status_code = get_status_code_from_exception(exc)

    if status_code in RETRYABLE_STATUS_CODES:
        return True

    text = str(exc).lower()

    retryable_markers = [
        "unavailable",
        "high demand",
        "overloaded",
        "rate limit",
        "quota",
        "temporarily",
        "timeout",
        "connection",
    ]

    return any(marker in text for marker in retryable_markers)


def generate_document(
    client: genai.Client,
    model: str,
    document_number: int,
    max_retries: int,
) -> Dict[str, Any]:
    """
    Generate one document with retries for temporary Gemini/API failures.
    """
    prompt = build_prompt(document_number)
    last_error: Optional[Exception] = None

    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.9,
                    top_p=0.95,
                    response_mime_type="application/json",
                ),
            )

            if not response.text:
                raise RuntimeError("Gemini returned an empty response.")

            payload = extract_json(response.text)
            payload = normalize_payload(payload)
            validate_payload(payload)

            return payload

        except Exception as exc:
            last_error = exc

            if not is_retryable_error(exc):
                raise

            if attempt >= max_retries:
                break

            backoff_seconds = min(
                30.0,
                float(2 ** (attempt - 1)) + random.uniform(0.25, 1.25),
            )

            print(
                f"Temporary Gemini/API error while generating document {document_number}. "
                f"Attempt {attempt}/{max_retries}. "
                f"Reason: {exc}",
                file=sys.stderr,
            )

            time.sleep(backoff_seconds)

    raise RuntimeError(
        f"Failed to generate document {document_number} after {max_retries} attempts. "
        f"Last error: {last_error}"
    )


def mask_sensitive_value(value: str) -> str:
    """
    Replace each word/number token with a single asterisk.

    Preserves punctuation and spacing inside the value.

    Examples:
        Ana Correia -> * *
        12/03/1978 -> */*/*
        +351 912 345 678 -> +* * * *
        ana.correia@example.invalid -> *.*@*.*
        12345678-9ZX0 -> *-*
    """
    return MASKABLE_TOKEN_RE.sub("*", value)


def build_unique_sensitive_items(
    sensitive_items: List[Dict[str, str]],
) -> List[Dict[str, str]]:
    """
    Remove duplicate sensitive items and sort longest first.

    Sorting longest first avoids problems like masking "Ana" before "Ana Correia".
    """
    seen: Set[Tuple[str, str]] = set()
    unique_items: List[Dict[str, str]] = []

    for item in sensitive_items:
        category = item.get("category", "").strip()
        text = item.get("text", "").strip()

        if not category or not text:
            continue

        key = (category.lower(), text)

        if key in seen:
            continue

        seen.add(key)
        unique_items.append(
            {
                "category": category,
                "text": text,
            }
        )

    unique_items.sort(key=lambda item: len(item["text"]), reverse=True)

    return unique_items


def mask_document(
    document_text: str,
    sensitive_items: List[Dict[str, str]],
) -> str:
    """
    Mask the sensitive items in the document.

    Keeps:
    - labels
    - punctuation
    - colons
    - non-empty line breaks
    - overall structure

    Removes:
    - empty lines
    """
    masked_text = remove_empty_lines(document_text)
    unique_items = build_unique_sensitive_items(sensitive_items)

    for item in unique_items:
        sensitive_text = item["text"]

        if not sensitive_text:
            continue

        if sensitive_text not in masked_text:
            continue

        replacement = mask_sensitive_value(sensitive_text)
        masked_text = masked_text.replace(sensitive_text, replacement)

    return remove_empty_lines(masked_text)


def write_outputs(
    payload: Dict[str, Any],
    outdir: Path,
    document_number: int,
    write_items_file: bool,
) -> None:
    """
    Writes:
    - Main synthetic document .txt
    - Masked synthetic document .txt
    - Optional sensitive items list .txt
    """
    outdir.mkdir(parents=True, exist_ok=True)

    document_path = outdir / f"synthetic_document_{document_number:03d}.txt"
    masked_path = outdir / f"synthetic_document_{document_number:03d}_masked.txt"
    items_path = outdir / f"synthetic_document_{document_number:03d}_sensitive_to_mask.txt"

    document_text = remove_empty_lines(payload["document_text"].strip())
    sensitive_items = build_unique_sensitive_items(payload["sensitive_items"])
    masked_text = mask_document(document_text, sensitive_items)

    with document_path.open("w", encoding="utf-8", newline="\n") as file:
        file.write(document_text)
        file.write("\n")

    with masked_path.open("w", encoding="utf-8", newline="\n") as file:
        file.write(masked_text)
        file.write("\n")

    print(f"Created: {document_path}")
    print(f"Created: {masked_path}")

    if write_items_file:
        with items_path.open("w", encoding="utf-8", newline="\n") as file:
            file.write("Sensitive information to mask\n")
            file.write("=============================\n")

            for item in sensitive_items:
                file.write(f"{item['category']} | {item['text']}\n")

        print(f"Created: {items_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate synthetic sensitive documents using Google Gemini."
    )

    parser.add_argument(
        "--count",
        type=int,
        required=True,
        help="Number of synthetic documents to generate.",
    )

    parser.add_argument(
        "--outdir",
        type=str,
        default=DEFAULT_OUTDIR,
        help=f"Output directory where the generated .txt files will be saved. Default: {DEFAULT_OUTDIR}",
    )

    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help=f"Gemini model name. Default: {DEFAULT_MODEL}",
    )

    parser.add_argument(
        "--max-retries",
        type=int,
        default=5,
        help="Maximum retry attempts per document for temporary API errors. Default: 5",
    )

    parser.add_argument(
        "--write-items-file",
        action="store_true",
        help="Also write a .txt file listing the sensitive spans used for masking.",
    )

    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop the whole script if one document fails. By default, failed documents are skipped.",
    )

    return parser.parse_args()


def get_api_key() -> str:
    """
    Read Gemini API key from environment.

    Accepts both GEMINI_API_KEY and API_KEY so your current .env keeps working.
    """
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("API_KEY")

    if not api_key:
        raise EnvironmentError(
            "Missing API key. Add one of these to your .env file:\n"
            "GEMINI_API_KEY=your_gemini_api_key_here\n"
            "or\n"
            "API_KEY=your_gemini_api_key_here"
        )

    return api_key


def main() -> None:
    load_dotenv()

    args = parse_args()

    if args.count < 1:
        raise ValueError("--count must be at least 1.")

    if args.max_retries < 1:
        raise ValueError("--max-retries must be at least 1.")

    api_key = get_api_key()
    client = genai.Client(api_key=api_key)
    outdir = Path(args.outdir)

    successful = 0
    failed = 0

    for document_number in range(1, args.count + 1):
        try:
            payload = generate_document(
                client=client,
                model=args.model,
                document_number=document_number,
                max_retries=args.max_retries,
            )

            write_outputs(
                payload=payload,
                outdir=outdir,
                document_number=document_number,
                write_items_file=args.write_items_file,
            )

            successful += 1

        except Exception as exc:
            failed += 1

            print(
                f"Error: failed to generate document {document_number}. {exc}",
                file=sys.stderr,
            )

            if args.fail_fast:
                raise

    print()
    print("Generation summary")
    print("==================")
    print(f"Requested documents: {args.count}")
    print(f"Successfully generated: {successful}")
    print(f"Failed: {failed}")
    print(f"Output directory: {outdir}")


if __name__ == "__main__":
    main()