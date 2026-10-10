# Backend

Python pipeline that masks sensitive data in a PDF, one `*` per word.

```
document.pdf ──extract_text()──▶ text (one line per PDF line, no empty lines)
                                   │
          prompt.txt + numbered text ──Gemini──▶ spans.json  {"spans": [{line, text, category, reason}]}
                                   │                │
                                   └──────mask()────┘──▶ masked text: every word of a span becomes "*"
```

The model only *points* at sensitive text; the masking is done in code, so
lines, spacing and every other word stay byte for byte the same.

## Setup

```bash
cd submission/backend
python3 -m venv .venv && source .venv/bin/activate   # Python >= 3.10
pip install -r requirements.txt
cp .env.example .env                                  # add your GEMINI_API_KEY
```

## Usage

```bash
# Mask a document (calls Gemini once; the answer is cached in .cache/)
python -m anonymizer ../../raw_data/document_to_anonymize.pdf -o out.txt

# Same, keeping the model's exact answer and the run details in a folder
python -m anonymizer ../../raw_data/document_to_anonymize.pdf \
    --save-run ../outputs -o ../submission.txt

# Reproduce the output from that folder, without the API
python -m anonymizer ../../raw_data/document_to_anonymize.pdf \
    --from-run ../outputs -o out.txt
```

`--save-run DIR` writes:

| File | Content |
|---|---|
| `spans.json` | the JSON the model returned, exactly as returned |
| `run.json` | model, `prompt.txt` hash, document hash and line count, timestamp |

The final `submission/submission.txt` is produced with `--save-run
submission/outputs`, so the judges can follow document → prompt → model
answer → `*`, and anyone can replay it with `--from-run`.

## Tests

```bash
python -m pytest -q      # no API calls
cd ../.. && flake8 .     # same check as the CI workflow
```
