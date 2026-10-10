# Anonymisation Pipeline: Design

Team Nova Finance Club, JunctionX Lisbon 2026, NOS Gen AI challenge.

## 1. Goal

Anonymise `raw_data/document_to_anonymize.pdf`, a Portuguese medical
admission report with fictitious personal data, so that:

- each sensitive **word** becomes a single `*` (`Ana Correia` → `* *`);
- everything else, including line breaks, accents and punctuation, is kept
  exactly as it was. The only layout change is that **empty lines are
  removed**;
- context decides what is sensitive. The header date (`Data: 15 de abril de
  2025`) and the reference (`ADM-2025-04-15-089`) stay visible.

## 2. How we are scored, and why it shapes the design

| Artefact | Checked by | Consequence for the design |
|---|---|---|
| `submission/submission.txt` | `evaluation.yml`: diff against a hidden target | Any change other than `*` masks costs points, so LLMs must never rewrite the text |
| `submission/prompt.txt` | `prompt_eval.yml`: a hidden script runs it with `google-genai` | Must work **on its own, in one call** (inferred: the script is secret) |
| Code in `submission/` | Judges (Explainability, Efficiency, GitHub) | Clear modules, few LLM calls, a readable report |

CI never runs our code. It only reads the two text files.

## 3. Design principles

1. **`prompt.txt` is a hand-written input.** It is a complete,
   self-contained set of anonymisation instructions. CI runs it single-shot.
   The pipeline reads the same file and uses it as the shared base of every
   agent prompt.
2. **LLMs only find; Python masks.** Agents return `Finding`s (exact text plus
   category). A deterministic masker applies `*`. If an LLM rewrote the whole
   document, it would tend to alter spacing, accents or line breaks, and each
   alteration is a diff error.
3. **The orchestrator is plain Python.** The flow is fixed, so an LLM
   orchestrator would only add calls, cost and randomness. The agents are the
   LLM calls it dispatches.
4. **The coherence agent adds spans; it never rewrites.** It finds words that
   indirectly reveal an already-masked entity (e.g. "a city known for its
   tram 28" after a masked "Lisbon"), and it can reject false positives.
5. **The taxonomy is data.** The categories live in `categories.json`.
   Regrouping them is an edit to that file, not a code change.

## 4. Architecture

```
prompt.txt --base_prompt--> shared instructions (document section dropped)
PDF --extract--> text (no empty lines)
  -> 5 x detector (parallel)                          -> findings/category
  -> context_checker for each category with findings  -> +spans / -rejects
  -> merge + dedupe -> masking.apply_findings          -> masked v1
  -> reviewer (sees masked v1, flags leaks; 1 pass)   -> extra findings
  -> masking again -> submission.txt ; report.md ; findings.json
```

- **Agent prompt** = shared instructions from `prompt.txt` + the agent's
  focus from `prompts/<agent>.md` (with the category inserted) + the document
  text.
- **Budget:** at most 5 + 5 + 1 = 11 Gemini calls per run, at temperature 0,
  with JSON-structured output (`response_schema` set to a pydantic model).
- **Parallelism:** detectors and context checkers run in a
  `ThreadPoolExecutor`. Rate-limit errors are retried with backoff in
  `llm.py`.

## 5. Directory layout

```
submission/
  prompt.txt            # hand-written; ends with "### DOCUMENTO ###" + doc
  submission.txt        # pipeline output (only the masked document)
  README.md             # organisers' guidelines (not ours to edit)
  validation.py         # DocumentValidator: meaning score, mask counting
  test_validation.py
  run.py                # CLI entry point
  docs/design.md        # this file
  anonymizer/
    config.py           # model ids, temperature, paths, env var names
    llm.py              # LLMClient protocol, GeminiClient (google-genai)
    schemas.py          # pydantic models shared by all agents
    categories.json     # category pseudo-DB
    categories.py       # loader -> list[Category]
    extract.py          # PDF -> text
    masking.py          # findings -> masked text
    base_prompt.py      # prompt.txt -> shared instructions
    orchestrator.py     # run_pipeline()
    report.py           # findings.json + report.md
    agents/
      detector.py
      context_checker.py
      reviewer.py
    prompts/
      detector.md
      context_checker.md
      reviewer.md
  synth/                # synthetic labelled documents
  evaluate/score.py     # precision/recall vs synthetic ground truth
  optimize/search.py    # offline prompt optimisation
  tests/                # unittest, FakeLLMClient (no network)
  outputs/              # findings.json, report.md of the final run
```

Dependencies are listed in the root `requirements.txt`. The API key is read
from the `API_KEY` env var; a local `.env` (gitignored) is loaded with
`python-dotenv`. `MODEL` selects the pipeline model (default
`gemini-2.5-flash`) and `VALIDATION_MODEL` the judge model; without it, the
meaning score is skipped.

## 6. Contracts

These are the interfaces teammates code against. Changing one means telling
the team.

### 6.1 Data models (`schemas.py`)

```python
class Finding(BaseModel):
    text: str        # copied verbatim from the document
    category: str    # an id from categories.json
    reason: str      # one short sentence, shown in the report
    context: str = ""  # the line the finding sits on, copied verbatim

class DetectorResult(BaseModel):
    findings: list[Finding]

class ContextResult(BaseModel):
    additions: list[Finding]   # indirect identifiers to mask too
    rejections: list[str]      # finding texts judged not sensitive

class ReviewResult(BaseModel):
    findings: list[Finding]    # leaks still visible in the masked text

class EntailmentScore(BaseModel):
    score: int = Field(ge=0, le=100)
```

### 6.2 LLM client (`llm.py`)

```python
class LLMClient(Protocol):
    def generate_json(self, prompt: str,
                      schema: type[T]) -> T: ...
    def generate_text(self, prompt: str) -> str: ...
```

`GeminiClient(model, temperature=0.0)` implements it with `google-genai`,
retrying HTTP 429/500/503 with backoff (1 s, 2 s, 4 s). Tests use
`FakeLLMClient` (in `tests/`). It answers through a
`responder(prompt, schema)` function, routing on prompt content rather than
call order (agents run in parallel), and records the prompts it receives.

### 6.3 Agents

```python
detect(text, category, base, client) -> list[Finding]
check_context(text, category, findings, base, client) -> ContextResult
review(masked_text, base, client) -> list[Finding]
```

### 6.4 Pipeline and validation

```python
apply_findings(text, findings) -> MaskResult
    # .masked: str, .unmatched: list[Finding] (not found verbatim)

run_pipeline(text, base, client) -> PipelineResult
    # .masked, .findings, .rejected: list[str], .unmatched

DocumentValidator(client=None)
    .entailment(original, anonymised) -> int    # 0-100
    .check_removed_words(document, expected) -> bool
```

### 6.5 Synthetic data format

One JSON file per document in `synth/data/`:

```json
{"id": "synth-001",
 "text": "Relatório ...",
 "spans": [{"text": "Maria Santos", "category": "identity"}]}
```

Category ids must exist in `categories.json`.

## 7. Masking rule

- A **word** is a token separated by whitespace.
- A token is masked when any part of it overlaps a finding's text. The
  text only matches as whole words (`Ana` never matches inside
  `Anamnese`).
- When a finding has a `context` (its line), only occurrences inside that
  line are masked. Masking every occurrence would also hide the `Lisboa`
  in the title `Centro Médico Lisboa`, which must stay visible. A finding
  with no `context` is masked everywhere.
- Punctuation at the start or end of the token (`, . ; : ( ) ! ?`) is kept,
  and the rest of the token becomes a single `*`.
- Punctuation inside the token (`@ . - / +`) belongs to the word.

| Input | Output |
|---|---|
| `Maria Conceição Oliveira Santos` | `* * * *` |
| `Flores,` | `*,` |
| `(João,` | `(*,` |
| `maria.santos@emailpessoal.pt` | `*` |
| `+351 912 345 678` | `* * * *` |
| `12345678-9ZX0` | `*` |

Line structure is never changed. The rule lives in one function in
`masking.py`. The hidden target may treat the edge cases (emails, `+351`)
differently; check this against the first CI evaluation result.

## 8. Categories (`categories.json`)

| id | Covers |
|---|---|
| `identity` | names of people (patient, relatives, friends, doctor), age |
| `contact_location` | address, phone, email, workplace |
| `gov_financial_ids` | NIF, Cartão de Cidadão, social security no., card number, expiry, CVV, insurance policy no., income, professional licence no. |
| `health` | diagnoses, HIV status, genetics, family medical history, medication, biometrics and biometric IDs |
| `sensitive_social` | religion, ethnicity, marital status, substance use |

Each entry has `id`, `name`, `description`, `examples` and `do_not_mask`. The
exact boundaries (e.g. sex, blood type, the hospital's name) are a team
decision, made by editing this file and `prompt.txt` together. A unit test
checks that every category id is mentioned in `prompt.txt`.

## 9. `prompt.txt` structure

```
<role and task>
<output rules: one * per word, keep layout, drop empty lines>
<categories, with ids, matching categories.json>
<what NOT to mask: header date, reference code, ...>
<one short worked example>
### DOCUMENTO ###
<full document text>
```

The document is included because we can't tell whether the CI script
supplies it. `base_prompt.py` drops everything from the marker onwards, and
the pipeline passes the document to each agent separately.

## 10. Reports and validation

Each run writes `outputs/findings.json` (every finding, its category and
reason, the rejections) and `outputs/report.md` (a readable table plus
`DocumentValidator().entailment()` as the meaning-preservation score). The
report supports the brief's optional manual validation and the
Explainability criterion.

## 11. Offline prompt optimisation

`optimize/search.py` improves `prompt.txt` during development. It is not
part of the pipeline run.

```
N candidate prompts -> single-shot on synthetic train docs -> score.py
   ^                                                            |
   +---- Gemini writes N new prompts from top-k + their errors <-+
best by F1 on held-out synthetic docs -> human review -> prompt.txt
```

- Fitness is `score.py` against ground truth. Gemini only writes the
  candidates; judging its own output without labels would be circular.
- The synthetic docs are split into train and held-out sets. The real PDF is
  never used, because it is the test.
- Cost is capped by flags (default about 4 prompts × 5 docs × 3 rounds ≈ 60
  calls).

## 12. Usage

```
pip install -r requirements.txt
python -m submission.run                 # pipeline -> submission.txt
python -m submission.run --single-shot   # prompt.txt alone, like CI
python -m submission.run --no-validate   # skip the entailment score
python -m unittest discover -s submission -t .
flake8 .
```

To submit: refine `prompt.txt`, run the pipeline, review
`outputs/report.md`, run the tests and `flake8`, then commit on the team
branch and open a PR to upstream `main`.

## 13. Ownership and build order

| Part | Depends on | Owner |
|---|---|---|
| core spine (`llm`, `schemas`, `extract`, `masking`, `orchestrator`, `run.py`) | n/a | João |
| agents + their focus prompts | core | team |
| `prompt.txt` | categories | team |
| `validation.py` | `llm.py` | Rogério |
| `synth/` | contracts §6.5 | Salvador |
| `evaluate/score.py` | `synth/` | tbd |
| `optimize/` | `synth/`, `score.py` | tbd |

## 14. Known risks

- **The hidden CI scripts.** The prompt check and the masking edge cases are
  inferred, not confirmed. The first PR run is the cheapest way to check.
- **PDF line wrapping.** `page.get_text()` keeps the PDF's visual line breaks
  (e.g. `dores` / `abdominais` on separate lines). We keep them, on the
  assumption that the target was made from the same extraction.
- **Free-tier rate limits.** Retries with backoff in `llm.py`, and the call
  budget in §4.
- **Overfitting in prompt optimisation.** Mitigated by the held-out split in
  §11.
