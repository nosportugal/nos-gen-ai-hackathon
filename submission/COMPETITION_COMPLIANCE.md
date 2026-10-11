# JunctionX competition compliance review

[Documentation index](00_INDEX.md) | [Technical guide](NOS_Three_Agents/README.md)

Initially reviewed on 2026-10-10 against the user-supplied
NOS - JunctionX Lisbon 2026.pdf, pages 2-5. This review covers repository
structure, local changes, submission artifacts and the documented workflow.
It is not a competition eligibility certification or a live-model evaluation.

Maintenance update, 2026-10-11: 151 offline tests passed, one real-document
check skipped; repository flake8 and whitespace checks passed. The original
upstream main was fetched and matches local main at `c4995b0`. Of its 17
files, 15 remain unchanged; only the required prompt/output contents differ,
recorded in `be5dfcb`. Maintenance changed none of these base files.

## Explicit rules and local evidence

| Requirement | Source | Local evidence / remaining work |
|---|---|---|
| One public team fork; work outside main | p.3 | Current branch: team-portwineoverflow. Remote visibility and collaborator access still need verification. |
| Preserve history; each member commits from their account | p.3 | Team PR merges and maintenance commits are recorded in Git. Verify contributor identities before delivery. |
| Work inside submission/ | p.3 | New rules, privacy code, tests and documentation remain inside submission/. |
| LLM detects sensitive data using context | p.2 | submission/agent implements a Gemini pipeline; tests can use stubs. Live quality has not been established here. |
| One asterisk per anonymized word; preserve layout except empty lines | p.2 | Three-agent text model implements a provisional word/punctuation rule. Verify final candidate against source; privacy detection alone cannot check formatting. |
| Keep supplied filenames and clean generated output | p.4 | submission.txt is nonempty as of 2026-10-11; commit be5dfcb records its addition. Exact model-response provenance remains unverified. |
| Exact prompt that generated the output | p.4 | prompt.txt is nonempty and matches prompts/prompt_v3_2.txt as of 2026-10-11. Verify the exact generating request and output together before delivery. |
| Include development code and setup/usage docs | pp.4-5 | Agent and three-agent workspace exist with READMEs. Optional privacy setup documented separately. |
| Reference open-source packages | pp.2,5 | Individual framework/package references and their roles are documented in NOS_Three_Agents/README.md. |
| Open-source licence | p.5 | Root LICENSE is MIT. Preserve it. |
| Automatic evaluation and flake8 | p.5 | Three organiser workflows exist. Repository flake8 passed locally before these adjustments. Missing files can still produce skipped green checks. |
| Final PR to original repository main | p.4 | Not created by this review. Confirm target repository and include all required artifacts. |
| JunctionX registration with PR link | p.4 | External/manual step, not verified. |
| Pitch at most two minutes | p.5 | Prepare and time the team's pitch. |

## Documentation placement

Rechecked against the [official NOS brief](https://lisbon.hackjunction.com/assets/challenges/NOS%20-%20JunctionX%20Lisbon%202026.pdf),
pages 3-5, on 2026-10-11. Page 3 requires work inside `submission/`;
page 5 requires clear README, usage and setup documentation. It does not
prescribe an index filename or a document count. Keeping
[00_INDEX.md](00_INDEX.md) beside the preserved submission README is our
organisation choice, consistent with those requirements.

Page 4 reserves `submission.txt` for the system output and `prompt.txt`
for its exact prompt. Neither is a documentation destination. The original
READMEs remain unchanged under the team's preservation rule. The index
contains navigation; the project README owns shared setup, interface usage,
design and library references. Component READMEs own their command-specific
behaviour. This review owns delivery checks and unresolved risks. Frozen
policies and experiment reports remain evidence, rather than current setup
instructions.

## Git clarification

The PDF does not ban additional working branches; it explicitly evaluates
branches and merges. The user nevertheless requires this task to remain on
team-portwineoverflow. That preference is recorded in AGENTS.md.

The previous generic rebase recommendation is superseded for this project.
Preserve collaboration history using merge-based integration. Before pulling,
review local changes and save them without discarding work. Never squash or
force-push over the team's history.

## Review findings

- Earlier privacy additions made heavy optional libraries mandatory in the
  base requirements. They are now isolated in requirements-privacy.txt.
- Ordinary tests must not depend on an unfinished competition submission.
  Real-document checking is selected with NOS_PRIVACY_DOCUMENT; an explicit
  empty/missing document remains an error.
- A small NER model can flag harmless header names that the brief's example
  keeps, and can miss sensitive data. Findings require human review and must
  not silently rewrite the submission or determine eligibility.
- The brief does not explicitly resolve multi-prompt pipelines or deterministic
  rendering. The existing evidence table records those uncertainties.
- Root tutorial text is generic and includes older event details. Use the
  supplied JunctionX brief for event-specific requirements; preserve originals.

## Final delivery gate

1. Review only the intended diff, preserve teammate changes, and run relevant
   offline tests plus repository flake8.
2. Generate a real candidate through the selected LLM pipeline; preserve the
   exact prompt and provenance. Check masking, formatting and false findings.
3. Confirm submission/submission.txt and submission/prompt.txt are nonempty,
   contain the required content, and accompany the development code.
4. Confirm public fork, licence, setup instructions and library references.
5. Commit with the actual contributor identity and preserve merge history.
6. After team approval, push, open the PR to the original repository main,
   inspect actual evaluation results, and register the PR link on JunctionX.
7. Prepare a pitch within two minutes.


## Additive security measures and remaining risks

These measures are intentionally separate from teammates' model pipelines.
They do not rewrite generated output, change frozen prompts, or remove
competition evidence. The preflight is an optional review gate, not an
enterprise security certification.

| Finding | Measure / rationale | Remaining limitation |
|---|---|---|
| Secrets can enter a public commit | security_preflight.py scans indexed blobs for selected Google/GitHub token and private-key patterns; reports categories and filenames only. | Untracked files, earlier history and other secret formats are not scanned. Review findings before committing. |
| A local-provider URL may send documents externally | --local-url rejects non-loopback destinations and URLs containing credentials, query or fragment. No DNS/network request is made. | The existing agent does not invoke this check automatically; run it with the exact URL before using a local provider. |
| Candidate validation is not mandatory in the existing agent | --document checks an explicitly selected output using the existing optional privacy checker, plus selected secret patterns. Missing/empty input or setup errors fail. | This tool does not block someone invoking/publishing the agent directly. No findings do not prove anonymity. |
| Validation errors can print sensitive content | Preflight uses a fixed error message and findings contain categories/offsets, not source text. | Existing agent dry-run/error logs still require a separate team-reviewed change. |
| Great Expectations analytics was not explicitly disabled | Our privacy test creates its ephemeral context with analytics_enabled=False. | Provider tracing and other packages are not controlled by this setting. |
| Raw inputs and responses are persisted/versioned | Keep current challenge evidence, which uses fictional data; prohibit reuse with real customer data until storage/access/retention controls are agreed. | No encryption or access-control system is added by this hackathon patch. |
| The detector covers only five PII entity categories | Secret patterns supplement the existing detector without changing its masking policy. Document country/entity coverage and require human review. | National IDs, bank accounts, indirect identifiers and other categories remain incomplete. |
| Prompts may be manipulated by document content | Preserve current structural validators and synthetic injection tests; require adversarial evaluation before real deployment. | Tags and prompt instructions alone are not a security boundary. |
| Production provider, access and retention policies are unverified | Use fictional competition data only; require the team's security/privacy review before any enterprise rollout. | No corporate readiness or regulatory compliance claim is made. |

### Run the optional preflight

Use the [preflight instructions](NOS_Three_Agents/README.md#optional-read-only-preflight)
for commands, scope and exit codes. Findings require review; the tool does
not rewrite output or establish anonymity. Candidate-specific findings
are recorded below.

Validation of additive measures: 122 offline tests passed, one real-document
check skipped unless explicitly selected. The indexed secret scan found no
configured matches. An earlier run hit an existing timestamp-based run-name
collision in Agent C; the repeated suite passed. That intermittent collision
is recorded for team review and was not changed by this patch.

## Current candidate privacy review

Review date: 2026-10-11. Candidate: `submission/submission.txt`.
SHA-256: `945670e3095b497e491cd676dea835afd33255a0285965cfcb65122779c08885`.

The explicitly selected candidate check returns **1 failure and 11 passing
synthetic privacy tests**. The failure is the zero-findings expectation:
the detector returns 16 spans (8 LOCATION, 6 PERSON, 2 ORGANIZATION).
It does not establish that all 16 are leaks.

| Group | Count | Review finding |
|---|---|---|
| Field labels | 11 | Spans lie entirely before their line's colon. The prompt preserves labels; these findings do not identify unmasked field values. |
| Sex value | 1 | ORGANIZATION detection on line 7 overlaps the retained sex value; the prompt explicitly preserves sex. |
| Document title/header | 1 | LOCATION span [0,50) crosses the title/header boundary. Requires contextual review; metadata is retained by the prompt. |
| Values or cross-line spans | 3 | LOCATION [899,917) on line 23, LOCATION [2051,2060) and PERSON [2074,2084) on line 47 remain unresolved. Review against the source and prompt before accepting the candidate. |

Offsets are zero-based, half-open Python character positions after UTF-8
reading with newline translation, matching the existing privacy test.
No detected source fragments are reproduced here.

No detector findings were suppressed, no score threshold was lowered and
neither candidate nor prompt was edited. A model score of 0.85 is not a
calibrated probability of a leak.

The detector covers PERSON, EMAIL_ADDRESS, PHONE_NUMBER, LOCATION and
ORGANIZATION. It does not independently implement the prompt's government,
professional, financial or biometric identifiers, age, ethnicity, religion
or income rules. Therefore even resolving these spans would not prove
complete compliance with the prompt. The prompt also preserves clinical
content; that design choice is not a general anonymity guarantee.

**Status: candidate privacy not approved.** Resolve the four contextual
findings and review uncovered categories before delivery. The freeze is
a separate task and was not modified by this review.

For execution commands, return to the [technical guide](NOS_Three_Agents/README.md)
or choose a task from the [documentation index](00_INDEX.md).
