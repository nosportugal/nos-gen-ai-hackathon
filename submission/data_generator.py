#!/usr/bin/env python3
"""
Generate synthetic medical admission documents and masked versions using Gemini.

Requirements:
    pip install google-genai python-dotenv

.env file:
    GEMINI_API_KEY=your_gemini_api_key_here

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
from typing import Any, Dict, List, Set

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types


DEFAULT_MODEL = "gemini-3.8-flash"


def build_prompt(document_number: int) -> str:
    return f"""
Generate one fully synthetic Portuguese medical admission report.

The document must be similar in style, structure, and level of detail to a hospital or medical admission report from Portugal.

The document must be written in Portuguese from Portugal.

All data must be completely fictitious.
Do not use real people, real patients, real public figures, or real addresses tied to real individuals.
Use realistic but mock data only.

The response must be valid JSON only.

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
"""

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
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Could not parse Gemini response as JSON.\n\nResponse was:\n{cleaned}"
        ) from exc


def validate_payload(payload: Dict[str, Any]) -> None:
    """
    Basic validation to make sure the generated response has the expected shape.
    """
    if not isinstance(payload, dict):
        raise ValueError("Gemini response is not a JSON object.")

    if "document_text" not in payload:
        raise ValueError("Missing field: document_text")

    if "sensitive_items" not in payload:
        raise ValueError("Missing field: sensitive_items")

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

        if item["text"] not in document_text:
            missing_items.append(item["text"])

    if missing_items:
        print(
            "Warning: Some sensitive items were not found exactly in the document text:",
            file=sys.stderr,
        )
        for value in missing_items:
            print(f"  - {value}", file=sys.stderr)


def generate_document(
    client: genai.Client,
    model: str,
    document_number: int,
) -> Dict[str, Any]:
    prompt = build_prompt(document_number)

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
    validate_payload(payload)

    return payload


def write_outputs(
    payload: Dict[str, Any],
    outdir: Path,
    document_number: int,
) -> None:
    """
    Writes:
    - Main synthetic document .txt
    - Sensitive values to mask .txt
    """
    outdir.mkdir(parents=True, exist_ok=True)

    document_path = outdir / f"synthetic_document_{document_number:03d}.txt"
    mask_path = outdir / f"synthetic_document_{document_number:03d}_sensitive_to_mask.txt"

    document_text = payload["document_text"].strip()
    sensitive_items = payload["sensitive_items"]

    with document_path.open("w", encoding="utf-8") as file:
        file.write(document_text)
        file.write("\n")

    seen = set()

    with mask_path.open("w", encoding="utf-8") as file:
        file.write("Sensitive information to mask\n")
        file.write("=============================\n\n")

        for item in sensitive_items:
            category = item["category"].strip()
            text = item["text"].strip()

            if not text:
                continue

            key = (category.lower(), text)

            if key in seen:
                continue

            seen.add(key)
            file.write(f"{category} | {text}\n")

    print(f"Created: {document_path}")
    print(f"Created: {mask_path}")


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
        default="generated_documents",
        help="Output directory where the generated .txt files will be saved.",
    )

    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help=f"Gemini model name. Default: {DEFAULT_MODEL}",
    )

    return parser.parse_args()


def main() -> None:
    # Load variables from .env into environment
    load_dotenv()

    args = parse_args()

    if args.count < 1:
        raise ValueError("--count must be at least 1.")

    api_key = os.getenv("API_KEY")

    if not api_key:
        raise EnvironmentError(
            "Missing GEMINI_API_KEY. Add it to your .env file like this:\n"
            "API_KEY=your_gemini_api_key_here"
        )

    client = genai.Client(api_key=api_key)
    outdir = Path(args.outdir)

    for document_number in range(1, args.count + 1):
        payload = generate_document(
            client=client,
            model=args.model,
            document_number=document_number,
        )

        write_outputs(
            payload=payload,
            outdir=outdir,
            document_number=document_number,
        )


if __name__ == "__main__":
    main()