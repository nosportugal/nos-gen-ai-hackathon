# Benchmark tables - bench-live-20261010T173924Z

- Mode: LIVE. LIVE Gemini run.
- Reference status: PROVISIONAL (AI-drafted, not human-reviewed). Every accuracy figure below is PROVISIONAL.
- Planned trials: 3; statuses: {'CANDIDATE_VALID': 3}.
- N/A marks an undefined value; UNKNOWN marks usage the backend did not report. Neither is zero.

## Per-trial results

| agent | trial | status | structural_pass | pass_ignoring_trailing_ws | alignment_status | tp | fp | fn | precision | recall | f1 | exact_agreement | over_masking_rate | under_masking_rate | ambiguous_hidden_n | char_inserted | char_deleted | char_substituted | exact_reference_match | calls_submitted | prompt_tokens | output_tokens | model_latency_s | pipeline_latency_s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 1 | CANDIDATE_VALID | yes | yes | ALIGNED | 46 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0 | 0 | 0 | 0 | yes | 1 | 1988 | 799 | 27.8134 | 27.817 |
| A | 2 | CANDIDATE_VALID | yes | yes | ALIGNED | 46 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0 | 0 | 0 | 0 | yes | 1 | 1988 | 799 | 154.9656 | 154.9681 |
| A | 3 | CANDIDATE_VALID | yes | yes | ALIGNED | 46 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0 | 0 | 0 | 0 | yes | 1 | 1988 | 799 | 30.9233 | 30.9258 |

## Aggregates per agent

| agent | trials_planned | trials_run | pipeline_failures | candidates_produced | valid_candidates | overall_valid_output_rate | evaluable_outputs | mean_precision_evaluable | mean_recall_evaluable | mean_f1_evaluable | mean_exact_agreement_evaluable | mean_over_masking_evaluable | mean_under_masking_evaluable | calls_submitted_total | http_attempts_total | prompt_tokens_total | output_tokens_total | mean_model_latency_s | mean_pipeline_latency_s | repeat_pairs_compared | max_words_differing_between_repeats |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 3 | 3 | 0 | 3 | 3 | 1.0000 | 3 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 3 | 5 | 5964 | 2397 | 71.2341 | 71.2370 | 3 | 0 |
