# Agent

[Documentation index](../00_INDEX.md) | [Project setup](../NOS_Three_Agents/README.md#shared-setup-for-windows-and-linux)

The agent asks one model call to return the document with personal data masked.
It checks the finish reason, but does not verify masking or formatting. The
answer is written exactly as returned, by default to `submission.txt`. The
model is Gemini, or any local OpenAI-compatible server for testing.

```
PDF -> raw_uncensored_document.txt -> prompt -> LLM -> answer file
```

The agent does not validate or score its answer content or save API run records.
Use the benchmark validators to inspect saved answers; its scorer executes
new model calls and records their results.

## Setup

For first-time installation on Windows or Linux, follow the
[shared setup](../NOS_Three_Agents/README.md#shared-setup-for-windows-and-linux).
Run the commands below from `submission/` with that environment's interpreter.
The examples use `python` as shorthand: in the PowerShell setup, replace
`python` with `& $py`; on Linux, use `.venv/bin/python`.
Then configure [the model](#models), check [the prompt](#prompt), and
[run the agent](#run).

## Models

| `--provider` | Default `--model` | Needs |
|---|---|---|
| `gemini` (default) | `gemini-3.6-flash` | `GEMINI_API_KEY` in the environment or `submission/.env` |
| `local` | `local` | An OpenAI-compatible server at `--base-url` (default `http://localhost:8080/v1`) |

For example with llama.cpp:

```
llama-server -m model.gguf --port 8080
python -m agent --provider local --out local_answer.txt
```

`LLM_PROVIDER` and `LOCAL_LLM_URL` set the defaults of `--provider` and
`--base-url`. Gemini uses temperature 0.0; local models use their
own default. `--timeout` sets the seconds allowed per
model call (default 300); raise it for a slow local model.

## Prompt

The prompt is the instruction text sent as the system message. The
document is sent separately, as the user message between `<document>` tags.

By default the agent reads `submission/prompt.txt`. If that file is empty
it stops and says so. Other prompts are in `submission/prompts/`; pass one
with `--prompt`.

## Run

```
python -m agent --dry-run                  # show the prompt, no API call
python -m agent                            # call Gemini, write submission.txt
python -m agent --prompt "path/to/reviewed_prompt.txt" --out candidate_review.txt
python -m agent --pdf other.pdf --out answer.txt
```

`--pdf` defaults to `raw_data/document_to_anonymize.pdf`, `--out` to
`submission/submission.txt`. Every run, including `--dry-run`, first extracts the PDF to
`submission/raw_uncensored_document.txt`.

When the answer goes to `submission.txt` and you passed a different
`--prompt`, that prompt is also copied into `prompt.txt` to record the
instruction. Verify the generating request and response before final delivery.

No new answer file is written when the model call fails (it is not
retried) or the answer is cut off (its `finish_reason` is not `STOP`). PDF
extraction happens before the model call and may already have written raw text.

The response and prompt are written sequentially, not atomically: an I/O
failure after writing the response can leave the prompt unchanged.
`--dry-run` writes the extracted text and prints the prompt plus the first
200 characters of the document message; it makes no model call.

Exit codes: `0` answer written, `1` model failure, `2` not run (empty prompt
or no API key). File-read, extraction and write failures are not all caught
by these handlers and can produce a traceback.

## Evaluate an answer

```
python -B security_preflight.py --document candidate_review.txt
python -m benchmark.mask_syntax_validation raw_uncensored_document.txt submission.txt
python -m benchmark.mask_diff raw_uncensored_document.txt submission.txt
```

To score a model + prompt over the whole benchmark dataset, see the
[benchmark scorer documentation](../benchmark/README.md#scorer).

## Files

| File | Job |
|---|---|
| `__main__.py` | Arguments and the LangChain chain that links the steps |
| `extraction.py` | PDF to text (PyMuPDF), exact spaces and accents kept |
| `prompt.py` | Loads the prompt file, builds the system and user messages |
| `llm.py` | Chat model per provider, API key, reading the answer |
| `tests/` | Offline tests: model replaced by a stub, plus a fake local server |

## Tests

```
python -m pytest agent/tests benchmark/tests NOS_Three_Agents -ra -o addopts="-p no:cacheprovider"
```

The locally verified interpreter is Python 3.12.7. Use one virtual environment
and the same interpreter for pip and execution. The full project setup,
optional privacy requirements, recorded checks and competition delivery
instructions are in [the project README](../NOS_Three_Agents/README.md).
Replace example prompt paths with actual reviewed files. The preflight is
optional and does not establish anonymity or validate document formatting.

After generation, follow [answer validation](#evaluate-an-answer), then
[inspect the saved comparison](../NOS_Three_Agents/README.md#view-the-saved-output).
Return to the [documentation index](../00_INDEX.md) for other tasks.
