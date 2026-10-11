# Project working rules

[Documentation index](00_INDEX.md)

These instructions apply to all work under submission/. The reviewed source
is NOS - JunctionX Lisbon 2026.pdf, pages 2-5, supplied by the user.

## Collaboration and Git

- Continue on team-portwineoverflow, as explicitly requested by the user.
  Do not create or switch branches without a new user instruction.
- Never develop directly on main.
- Preserve files inherited from the original main. Refactoring must only edit
  team-added files. Do not edit prompt.txt or submission.txt during maintenance;
  changes to delivery contents require a specific generation/delivery task.
- Inspect git status and the relevant diff before editing or integrating.
  Preserve existing local changes and teammates' work.
- Keep changes focused and reviewable. Stage only files belonging to the task.
- Preserve team history: no squash, force-push, history rewriting, or destructive
  reset/restore. Synchronize using a normal merge after reviewing local state.
- Each member must commit under their own identity. Never change Git identity
  or attribute assistant work to another teammate.
- Keep the team's fork public. Check visibility before final submission.
- Code, comments, docstrings, commit messages and new documentation must be in
  English. Portuguese document content and prompt examples may retain the
  source language.

## Competition requirements

- Develop inside submission/. Preserve organisers' raw_data/, tutorials/,
  workflow files and existing history.
- Use an LLM and contextual prompt engineering for sensitive-data detection.
- Replace each anonymized word with one asterisk. Preserve meaning and
  formatting; remove empty lines. The exact word/punctuation edge cases are
  not specified by the brief: document assumptions rather than invent rules.
- Preserve the supplied filenames submission.txt and prompt.txt.
- submission.txt must contain only the actual model/API-generated output as
  returned by the system, without team information, explanations or wrappers.
  Never populate it with fabricated output or synthetic test fixtures.
- prompt.txt must contain the exact prompt used for that output. Preserve
  provenance; do not claim an example prompt generated an unrelated output.
- Include the development code, setup/usage documentation, open-source licence
  and references to open-source libraries.
- Do not equate a privacy heuristic, mock result, or green workflow with a
  valid competition score. Missing files can make workflows skip successfully.
- Final delivery requires a PR to main in nosportugal/nos-gen-ai-hackathon
  and registration on JunctionX using that PR link. The pitch is at most
  two minutes. Do not publish or register without user authorization.
- The brief does not expressly ban additional branches, require Gemini, or
  define every sensitive-data category. Distinguish explicit rules from
  assumptions. Unclear final eligibility decisions belong to the team/mentors.

## Validation and dependencies

- Keep ordinary tests offline and synthetic. Never call a paid/live model
  merely to run checks.
- Keep optional privacy/evaluation dependencies separate from agent runtime.
  Pin tested versions and document installation.
- Real-document validation must be explicitly selected, fail for missing or
  empty input, and avoid printing sensitive source text.
- Run relevant tests and repository flake8 before proposing integration.
  Report skips, failures and missing dependencies accurately.
- Never modify frozen sources, hashes, prompts or benchmark artifacts merely
  to make tests pass.

[Documentation index](00_INDEX.md)
