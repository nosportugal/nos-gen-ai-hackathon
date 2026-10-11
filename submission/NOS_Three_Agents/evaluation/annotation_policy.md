# Annotation policy

Version 1.0, frozen 2026-10-10. Applies to
`evaluation/reference_annotations.json` and `.csv`.

## Status

**PROVISIONAL.** The reference was drafted by an AI engineering assistant
(Claude) by reading the extracted source text. No LLM API call assisted
it. **No human has reviewed it.** It is not independently verified ground
truth, and no measurement against it shows agreement with the organisers'
hidden reference.

Review record:

| Field | Value |
|---|---|
| Author | Claude (AI engineering assistant) |
| Method | Source inspection, encoded in `evaluation/build_reference.py` |
| Reviewer | none yet |
| Review status | NOT_REVIEWED |
| Source | `input/canonical_source.txt`, SHA-256 in the JSON `meta` |
| Masking policy | `shared/policy/masking_policy_v1.json`, version 1.0 |

When a team member reviews it, record their name, the date and every
changed row here, and rebuild the file.

## Unit and coordinates

- One row per maskable word (component): a maximal run of non-whitespace
  characters that contains a letter or digit.
- `start` and `end` are zero-based Python code-point offsets into the
  canonical source, half-open `[start, end)`. They cover the word's core:
  opening punctuation at its start and closing punctuation at its end are
  outside the interval.
- `substring` must equal `source[start:end]`. `build_reference.py` and a
  test check every row mechanically.
- Repeated and context-dependent occurrences have their own rows. Nothing
  is annotated by "all occurrences of this string".

## Decisions

| Decision | Meaning | Use in metrics |
|---|---|---|
| MASK | The word belongs to a value in a MASK category of the policy | Primary denominator |
| KEEP | The word is not personal data under the policy | Primary denominator |
| AMBIGUOUS | The word belongs to a special-category or quasi-identifying value whose treatment the organisers have not defined | Excluded from precision, recall, F1 and agreement; counted and reported separately |

Counts in version 1.0: 46 MASK, 193 KEEP, 115 AMBIGUOUS words; 73
annotated runs (entities).

An AMBIGUOUS row is not a guess at ground truth. It marks a word the team
cannot classify without an answer from the organisers. An agent that masks
it is neither rewarded nor penalised in the primary figures; the number of
ambiguous words each output hides is reported next to them.

## Rules applied

1. Lines 1 to 3 (title with institution, document date, reference number)
   are KEEP. The challenge brief shows them unmasked in a correct output.
2. Names of natural persons are MASK at every occurrence, including the
   short form inside a sentence and the two children's first names. The
   title "Dr." and relationship words such as "irmão" are KEEP.
3. Date of birth, tax number, citizen card, social security number,
   address (every word of the value), phones, e-mails, card number, card
   expiry, security code, insurance policy number, biometric record IDs
   and the doctor's licence number are MASK.
4. Health information, sex, ethnicity, ages, marital status, religion,
   number of children, occupation, employer, specialty, income, insurance
   plan name, habits, and years or durations of clinical events are
   AMBIGUOUS.
5. Everything else, including field labels, headings, units and
   connecting text, is KEEP by default.

## Changing the reference

Do not change annotations after looking at agent outputs without recording
the change here. Any comparison computed against the earlier version is
then invalid and must be recomputed. `build_reference.py` prints a notice
when the content changes, and the freeze manifest stops live runs until it
is rewritten on purpose.

## Leakage guard

The reference and the output it implies are evaluation data. No agent
prompt, schema or runtime module reads them; a test
(`evaluation/tests/test_metrics.py`) fails if one does, and another fails
if a real masked value appears in a prompt file.
