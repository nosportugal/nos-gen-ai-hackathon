"""Build the provisional reference annotations from a reviewable spec.

Usage (workspace root, inside the virtual environment):

    python -I evaluation/build_reference.py

The spec below was drafted by reading the extracted source text. No LLM
API call assisted it. It is PROVISIONAL until a human reviews it; nothing
here is independently verified ground truth.

Each spec row names one run of consecutive words on one line:

    (line, quote, occurrence, decision, category, rationale)

``quote`` is the exact source text from the first word's core to the last
word's core; ``occurrence`` picks the n-th such run on the line. Every
word not covered by a row defaults to KEEP. Positions are zero-based
code-point offsets into the canonical source, half-open [start, end), and
are checked mechanically against the source.

Outputs: evaluation/reference_annotations.json and .csv
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared import artifacts, config  # noqa: E402
from shared.policy import load_policy  # noqa: E402

ANNOTATION_POLICY_VERSION = "1.0"
AUTHOR = (
    "Claude (AI engineering assistant) - drafted by reading the extracted "
    "source; no LLM API assistance"
)
REVIEW_STATUS = "NOT_REVIEWED - no human review has taken place"
OUT_JSON = config.ROOT / "evaluation" / "reference_annotations.json"
OUT_CSV = config.ROOT / "evaluation" / "reference_annotations.csv"

M, A, K = "MASK", "AMBIGUOUS", "KEEP"
BRIEF = "shown unmasked in the brief's sample of a correct output"

SPEC = [
    (1, "Relatório de Admissão - Centro Médico Lisboa", 1, K,
     "DOCUMENT_METADATA", "title and institution; " + BRIEF),
    (2, "15 de abril de 2025", 1, K, "DOCUMENT_METADATA",
     "document date; " + BRIEF),
    (3, "ADM-2025-04-15-089", 1, K, "DOCUMENT_METADATA",
     "document reference; " + BRIEF),
    (5, "Maria Conceição Oliveira Santos", 1, M, "PERSON_NAME",
     "patient full name"),
    (6, "12/03/1978", 1, M, "BIRTH_DATE", "patient date of birth"),
    (7, "Feminino", 1, A, "DEMOGRAPHIC", "sex"),
    (8, "097865413", 1, M, "GOV_ID", "tax number (NIF)"),
    (9, "12345678-9ZX0", 1, M, "GOV_ID", "citizen card number"),
    (10, "Rua das Flores, 123, Apt 45, Sacavém, Lisboa", 1, M, "ADDRESS",
     "patient home address, every word of the value"),
    (11, "+351 912 345 678", 1, M, "PHONE",
     "patient phone, four space-separated groups"),
    (12, "maria.santos@emailpessoal.pt", 1, M, "EMAIL", "patient e-mail"),
    (13, "11223344556", 1, M, "GOV_ID", "social security number"),
    (15, "Maria Santos", 1, M, "PERSON_NAME",
     "patient short name inside a sentence"),
    (15, "mulher", 1, A, "DEMOGRAPHIC", "sex"),
    (15, "caucasiana", 1, A, "DEMOGRAPHIC", "ethnicity"),
    (15, "47", 1, A, "DEMOGRAPHIC", "age"),
    (15, "dores", 1, A, "HEALTH", "symptom, continues on next line"),
    (16, "abdominais intensas", 1, A, "HEALTH", "symptom"),
    (16, "hipertensão", 1, A, "HEALTH", "condition"),
    (16, "diabetes tipo 2", 1, A, "HEALTH", "condition"),
    (16, "5", 1, A, "DATE_OTHER", "years since diagnosis"),
    (17, "HIV positivo", 1, A, "HEALTH", "condition"),
    (17, "2018", 1, A, "DATE_OTHER", "year of a clinical event"),
    (17, "carga viral indetectável", 1, A, "HEALTH", "clinical status"),
    (18, "antirretrovirais", 1, A, "HEALTH", "medication class"),
    (19, "cancro da mama", 1, A, "HEALTH", "family medical history"),
    (19, "52", 1, A, "DEMOGRAPHIC", "relative's age at death"),
    (20, "doença cardíaca", 1, A, "HEALTH", "family medical history"),
    (20, "2022", 1, A, "DATE_OTHER", "year of a clinical event"),
    (21, "predisposição ao cancro de mama", 1, A, "HEALTH",
     "genetic finding"),
    (21, "mutação BRCA1 positiva", 1, A, "HEALTH", "genetic finding"),
    (23, "Divorciada", 1, A, "DEMOGRAPHIC", "marital status"),
    (24, "2", 1, A, "DEMOGRAPHIC", "number of children"),
    (24, "João", 1, M, "PERSON_NAME", "child's first name"),
    (24, "15", 1, A, "DEMOGRAPHIC", "child's age"),
    (24, "Ana", 1, M, "PERSON_NAME", "child's first name"),
    (24, "12", 1, A, "DEMOGRAPHIC", "child's age"),
    (25, "Católica praticante", 1, A, "DEMOGRAPHIC", "religion"),
    (26, "Professora universitária", 1, A, "OCCUPATION", "occupation"),
    (26, "Faculdade de Direito de Lisboa", 1, A, "OCCUPATION", "employer"),
    (27, "Ex-fumante (parou há 3 anos), consome álcool socialmente "
         "(2-3 doses por semana", 1, A, "LIFESTYLE", "habits"),
    (28, "Tratamento para dependência de ansiolíticos em 2019", 1, A,
     "LIFESTYLE", "substance-use history"),
    (30, "Plano Premium Saúde Total", 1, A, "FINANCIAL_ATTRIBUTE",
     "insurance plan name"),
    (30, "987654321", 1, M, "FINANCIAL_ID", "insurance policy number"),
    (31, "4111 2222 3333 4444", 1, M, "FINANCIAL_ID",
     "payment card number, four groups"),
    (31, "09/27", 1, M, "FINANCIAL_ID", "card expiry"),
    (31, "123", 1, M, "FINANCIAL_ID", "card security code"),
    (32, "€62.500", 1, A, "FINANCIAL_ATTRIBUTE", "income"),
    (34, "ID-BIO-12345", 1, M, "BIOMETRIC_ID", "fingerprint record ID"),
    (35, "FACE-ID-78901", 1, M, "BIOMETRIC_ID", "face template ID"),
    (36, "1,68m", 1, A, "HEALTH", "height"),
    (37, "72kg", 1, A, "HEALTH", "weight"),
    (38, "O+", 1, A, "HEALTH", "blood type"),
    (39, "145/90 mmHg", 1, A, "HEALTH", "blood pressure"),
    (41, "ansiosa", 1, A, "HEALTH", "symptom"),
    (42, "cansaço, fadiga", 1, A, "HEALTH", "symptoms"),
    (43, "constante stress", 1, A, "HEALTH", "symptom"),
    (43, "dificuldade em", 1, A, "HEALTH",
     "symptom, continues on next line"),
    (44, "dormir/cumprir as horas indicadas de sono", 1, A, "HEALTH",
     "symptom"),
    (45, "hemograma completo, glicemia em jejum, perfil lipídico, "
         "função hepática e", 1, A, "HEALTH", "requested exams"),
    (46, "renal, ultrassonografia abdominal", 1, A, "HEALTH",
     "requested exams"),
    (47, "Metformina 850mg 2x/dia, Losartana 50mg 1x/dia, "
         "Alprazolam 0,5mg", 1, A, "HEALTH", "medication and doses"),
    (48, "crises de ansiedade", 1, A, "HEALTH", "condition"),
    (50, "António Santos", 1, M, "PERSON_NAME", "emergency contact name"),
    (51, "+351961234567", 1, M, "PHONE", "contact phone, one group"),
    (52, "antonio.santos@emailpessoal.pt", 1, M, "EMAIL",
     "contact e-mail"),
    (53, "Joana Pereira", 1, M, "PERSON_NAME", "emergency contact name"),
    (54, "+351939876543", 1, M, "PHONE", "contact phone, one group"),
    (56, "Carlos Mendes", 1, M, "PERSON_NAME",
     "doctor's name; the title 'Dr.' stays"),
    (57, "12345-PT", 1, M, "PROFESSIONAL_ID", "doctor's licence number"),
    (58, "Medicina Interna", 1, A, "OCCUPATION", "doctor's specialty"),
    (59, "carlos.mendes@centromedicalisboa.pt", 1, M, "EMAIL",
     "doctor's e-mail"),
    (60, "+351213456789", 1, M, "PHONE", "doctor's phone, one group"),
]
DEFAULT_RATIONALE = (
    "default: not in any MASK or AMBIGUOUS category of policy "
    "v{version}"
)


def find_run(doc, line: int, quote: str, occurrence: int):
    toks = doc.line_tokens.get(line, [])
    hits = []
    for i, first in enumerate(toks):
        for last in toks[i:]:
            if doc.run_quotes(first, last)[0] == quote:
                hits.append((first, last))
    if len(hits) < occurrence:
        raise SystemExit(
            f"spec error: L{line} {quote!r} occurrence {occurrence} "
            f"not found ({len(hits)} match(es))"
        )
    first, last = hits[occurrence - 1]
    return toks[first.index - 1:last.index]


def default_category(doc, tok) -> str:
    toks = doc.line_tokens[tok.line]
    labels = [t.index for t in toks if t.text.endswith(":")]
    if labels and tok.index <= labels[0]:
        return "STRUCTURE"
    return "NARRATIVE"


def build(doc, policy) -> dict:
    assigned, entities = {}, []
    for n, (line, quote, occ, decision, category, why) in enumerate(SPEC, 1):
        if policy.decision_of(category) != decision:
            raise SystemExit(f"spec error: {category} is not {decision}")
        comps = [t for t in find_run(doc, line, quote, occ) if t.maskable]
        if not comps:
            raise SystemExit(f"spec error: L{line} {quote!r} has no word")
        entity_id = f"E{n:02d}"
        for tok in comps:
            if tok.comp_id in assigned:
                raise SystemExit(f"spec error: {tok.comp_id} assigned twice")
            assigned[tok.comp_id] = (decision, category, why, entity_id)
        entities.append({
            "entity_id": entity_id, "decision": decision,
            "category": category, "line": line,
            "start": comps[0].core_start, "end": comps[-1].core_end,
            "substring": doc.text[comps[0].core_start:comps[-1].core_end],
            "component_ids": [t.comp_id for t in comps],
            "rationale": why,
        })
    rows = []
    for tok in doc.components:
        if tok.comp_id in assigned:
            decision, category, why, entity_id = assigned[tok.comp_id]
            basis = "explicit"
        else:
            decision, category = K, default_category(doc, tok)
            why = DEFAULT_RATIONALE.format(version=policy.version)
            entity_id, basis = "", "default"
        rows.append({
            "component_id": tok.comp_id, "line": tok.line,
            "token_index": tok.index, "start": tok.core_start,
            "end": tok.core_end, "substring": tok.core,
            "token_text": tok.text, "decision": decision,
            "category": category, "rationale": why,
            "entity_id": entity_id, "basis": basis,
        })
    check(doc, rows, entities)
    counts = {d: sum(1 for r in rows if r["decision"] == d)
              for d in (M, A, K)}
    return {
        "meta": {
            "status": "PROVISIONAL",
            "annotation_policy_version": ANNOTATION_POLICY_VERSION,
            "masking_policy_version": policy.version,
            "masking_policy_sha256": policy.sha256,
            "source_path": config.rel(config.CANONICAL_SOURCE),
            "source_sha256": config.sha256_text(doc.text),
            "author": AUTHOR,
            "reviewer_status": REVIEW_STATUS,
            "created_utc": artifacts.utc_now(),
            "coordinates": "zero-based Python code-point offsets into the "
            "canonical source, half-open [start, end); each interval is "
            "the word's core (surrounding punctuation excluded)",
            "unit": "one row per maskable word (component)",
            "component_counts": counts,
            "entity_count": len(entities),
        },
        "components": rows,
        "entities": entities,
    }


def check(doc, rows, entities) -> None:
    """Mechanical bounds and substring-equality validation."""
    size = len(doc.text)
    for item in list(rows) + list(entities):
        start, end = item["start"], item["end"]
        if not 0 <= start < end <= size:
            raise SystemExit(f"bounds error: {item}")
        if doc.text[start:end] != item["substring"]:
            raise SystemExit(f"substring mismatch: {item}")
    ids = [r["component_id"] for r in rows]
    if len(ids) != len(set(ids)) or len(ids) != len(doc.components):
        raise SystemExit("component coverage error")


def main() -> int:
    policy = load_policy()
    doc = policy.make_doc(config.read_text_exact(config.CANONICAL_SOURCE))
    reference = build(doc, policy)
    if OUT_JSON.exists():
        old = config.load_json(OUT_JSON)
        same = (old["components"] == reference["components"]
                and old["entities"] == reference["entities"])
        if same:
            print("reference unchanged:", config.rel(OUT_JSON))
            print(old["meta"]["component_counts"])
            return 0
        print("NOTE: reference content changed; any comparison computed "
              "against the previous version is invalid.")
    config.dump_json(OUT_JSON, reference)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(reference["components"]
                                                    [0]))
        writer.writeheader()
        writer.writerows(reference["components"])
    print("written:", config.rel(OUT_JSON), config.rel(OUT_CSV))
    print(reference["meta"]["component_counts"],
          "entities:", reference["meta"]["entity_count"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
