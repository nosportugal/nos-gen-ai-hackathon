# NOS — Synthetic Anonymization Benchmark (50 documents)

[Documentation index](../00_INDEX.md) | [Agent usage](../agent/README.md)

- `input/`: 50 original UTF-8 `.txt` documents (40 pt-PT, 10 English).
- `ground_truth/`: corresponding reference documents with one `*` per whitespace-delimited sensitive token; whitespace-only lines removed.
- `annotations.json`: sensitive source spans with Python character offsets `[start,end)` and category labels.
- All personal identifiers are fictional/test values; names and institution names may resemble real entities by coincidence.

For the separate v3.4 proposal on the challenge document, use
[its dataset guide](real_document/README.md). It has a different reference
policy; do not combine its results with this 50-document dataset.

## Policy used for the reference
Names of individuals (including staff and relatives), individual names repeated in shorter form, contact addresses, telephone numbers, personal email addresses, tax identifiers, social media handles and IBANs are masked. Institutional names, generic city mentions, political party names without a personal identifier, occupations, medical diagnoses, ordinary processing dates, monetary amounts, case references and quoted instructions are preserved. Explicit membership-person links are broken by masking the person's name, not the party. This is a **benchmark-specific policy**, not a verified interpretation of the NOS hidden reference.

The repository includes reference texts and annotations, but this component
does not include a dataset-generation script that establishes how they were produced. **Manually review the originals and ground truths before using them as authoritative labels**, especially contextual references and ambiguous identifiers. Token masking counts whitespace-delimited components. All documents are 50–500 words.

## Validation
`annotations.json` spans refer to the *original* text; ground truths have empty/whitespace-only lines removed. Compare output with ground truth only after verifying the agent's formatting contract.

Check one answer file (run from `submission/`):

```
python -m benchmark.mask_syntax_validation benchmark/input/doc_001.txt answer.txt
python -m benchmark.mask_diff benchmark/input/doc_001.txt answer.txt
```

## Scorer
`scorer.py` runs a model + prompt over `input/` and compares each
answer with `ground_truth/`, word by word (word ids from
`mask_diff.py`). Run from `submission/`:

```
python -m benchmark.scorer --prompt prompts/prompt_v3_2.txt            # Gemini
python -m benchmark.scorer --provider local --prompt prompts/prompt_v3_2.txt
python -m benchmark.scorer --docs doc_001 doc_041 --limit 1
```

`--provider`, `--model`, `--base-url` and `--timeout` work as in
`python -m agent`.
Each call writes `runs/<time>_<model>_<prompt>/`:

- `doc_XXX.json`, one per document: model, prompt path and SHA-256,
  seconds, token usage, error (if the call failed), `syntax` (from
  `mask_syntax_validation.py`), `counts` (tp/fp/fn/tn), `metrics`
  (precision, recall, f1, accuracy, specificity, fpr, fnr), and the word
  id and text of every false positive and false negative.
- `doc_XXX.txt`, the model's answer exactly as returned (none when the
  call failed). Check it by hand with `mask_syntax_validation.py` or
  `mask_diff.py` against `input/doc_XXX.txt`.
- `summary.json`: counts added over all documents, and metrics from those
  totals.

A positive is a word the ground truth masks. A word the answer breaks
the rules at is counted as not masked and listed under `unaligned`.

A masked word keeps its punctuation (`República,` -> `*,`), but reference syntax must be checked in the actual checkout. An answer that writes a
bare `*` instead still counts as masked in `mask_diff.py`, so detection is
scored separately, but it fails the syntax check.


The scorer makes model calls and writes run artifacts; it is not an offline
validation command. It returns 1 for failed model calls and 2 for handled
setup/no-document cases. Syntax failures are recorded but do not by themselves
make the command return a nonzero exit code. File and directory errors may
raise exceptions. A successful command exit is not a quality threshold.

The benchmark policy differs from the v3.2 prompt, notably for contextual
attributes such as age and employer names. Scores measure agreement with
this dataset's reference, not agreement with that prompt or the NOS judges.


## Review required: benchmark line endings

<!-- Review the scorer's exact-read contract before interpreting syntax results. -->
<p style="color: #c62828;"><strong>🔴 CRLF/LF mismatch requires review.</strong></p>

The inspected Windows checkout contains 50 reference files with CRLF.
The scorer preserves those bytes; the validator rejects carriage returns.
All 50 fail the exact-byte check and pass after CRLF-to-LF translation.
Input documents contain 174-258 whitespace-delimited words.

Review whether normalisation belongs at the scorer boundary or whether
checkout configuration should preserve LF. Reference data remains unchanged;
this discrepancy does not establish a model-quality failure.

After reviewing validation results, use the
[delivery checklist](../COMPETITION_COMPLIANCE.md#final-delivery-gate).
Return to the [documentation index](../00_INDEX.md) for other tasks.
