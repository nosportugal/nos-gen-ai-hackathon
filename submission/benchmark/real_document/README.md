# Real document — expected answer under proposed policy v3.4

[Documentation index](../../00_INDEX.md) | [Benchmark guide](../README.md)

One-document dataset in the scorer's layout:

- `input/admission_report.txt`: the official challenge document with fictional personal data, identical to
  `submission/raw_uncensored_document.txt`.
- `ground_truth/admission_report.txt`: the answer we expect from a prompt
  that follows policy v3.4. It has 72 masked words: the 58 that prompt
  v3.2 already masks, plus 14 new ones.

**This is the team's proposal, not the NOS hidden reference.** It was
written by hand from the principle below and checked with
`mask_syntax_validation`.

A separate [saved v3.4 answer](answer_prompt_v3_4_gemini-3.8-flash.txt)
was added alongside the [prompt](../../prompts/prompt_v3_4.txt).
Its filename identifies a model; it is separate from `submission.txt`.
Reference agreement does not establish privacy or agreement with NOS's
hidden evaluation.

## Principle

Mask **who** the person is and **when** things happened to them; keep
**what** happened. The medical and personal story stays readable. The
aim is to reduce links to a person. This is a policy goal, not a verified
anonymity guarantee.

## What v3.4 adds to v3.2

| Group | Example in the document | Rule |
|---|---|---|
| Marital status | `Estado civil: Divorciada` | mask the value |
| Number of children | `Filhos: 2` | mask the number |
| Occupation | `Professora universitária` | mask every word; keep `na` |
| Insurance plan name | `Plano Premium Saúde Total` | mask every word |
| Age of a relative | `falecida aos 52 anos` | mask the number |
| When an event happened | `há 5 anos`, `desde 2018`, `em 2022`, `há 3 anos`, `em 2019` | mask the year or the number only |

Kept on purpose: every diagnosis, the family diseases (`cancro da mama`,
`doença cardíaca`), habits (`Ex-fumante`, `consome álcool socialmente`,
`2-3 doses por semana`), dependence treatment, medication, doses, exams
and measurements, sex, and the document's own date.

The event-time rule is applied everywhere, so it also covers the
patient's own timeline (`há 5 anos`, `desde 2018`, `em 2022`). Drop
those three if the team wants to mask times only in the social history.

## Use

From `submission/`:

```
python -m pytest benchmark/tests/test_real_document_policy.py
python -m benchmark.scorer --dataset benchmark/real_document --prompt prompts/prompt_v3_4.txt
python -m benchmark.mask_diff benchmark/real_document/input/admission_report.txt answer.txt
```

The tests call no model. The scorer does.

The 50-document synthetic benchmark is not changed.

Use the [scorer guide](../README.md#scorer) to locate run artifacts and interpret
its metrics and exit codes. For delivery checks, use the
[competition review](../../COMPETITION_COMPLIANCE.md#final-delivery-gate).
Return to the [documentation index](../../00_INDEX.md) for other tasks.
