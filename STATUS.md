# STATUS.md

Current state of the project. Update this at the end of every session. Read it at the start of every session.

Last updated: 2026-11-18 20:19 Central time (America/Chicago)

## Phase

**Phase 1: core harness.** Scaffolding is done and verified in mock mode on the local machine. Real model runs have not happened yet.

## Model plan

- **Primary model for all development runs: DeepSeek-R1 14B, local via Ollama.** It costs nothing per run, so iteration is free.
- **Claude Sonnet is for comparison runs only.** Use the same emails, prompts, and pipeline. It runs through the API, which is billed separately from Claude Pro.
- Keep the judge on the same model as extraction for the first baseline. Test a Claude judge later as its own experiment.

## Done

- Dataset: Enron ham subset (16,493 emails), in `data/` and git-ignored. Re-download steps are in README.md.
- Harness scaffolding: extract, validate, judge, decide, log.
- Mock mode verified end to end on 5 real emails.
- Grounding check: each extracted `text` must appear in the email body (whitespace and case ignored). Failures go to `rule_issues`, which triggers the retry. Covered by `python -m unittest tests.test_grounding -v`, which needs no model.
- Ollama routing added in `model_client.py`. Not yet run against a live server.
- Vision document (VISION.md).

## Not done yet

- No real model run yet. First run is DeepSeek-R1 14B via `ollama serve`. Sonnet comes after, and needs `ANTHROPIC_API_KEY` with a funded API balance.
- Grounding check only catches invented text. It does not check that the quote supports the stated date or attribution.
- Confidence is still self-reported by the model and the judge. Calibration against real labels comes in Phase 4.
- Judge's per-item confidence is logged but not used in `decide()`.
- Body is truncated at 4,000 characters, so late deadlines get missed.
- Relative dates ("next Tuesday") are not resolved against the email date.
- No hand-labeled ground truth yet.
- Cost per run is not computed.

## Next steps, in order

1. ~~Add the grounding check~~ Done 2026-11-18.
2. ~~Use the judge's per-item confidence in `decide()`~~ Done 2026-11-18. The final confidence is now the lower of the extraction score and the judge score.
3. Run 10 emails on DeepSeek-R1 14B (`HARNESS_EXTRACT_MODEL` and `HARNESS_JUDGE_MODEL` set to `deepseek-r1:14b`). Record tokens, latency, decisions, and JSON parse failures in the log.
4. Run the same 10 emails on Claude Sonnet. Compare decisions, cost, and latency against step 3.
5. Hand-label 30 emails for the first eval set. Save them as `eval/labels.jsonl`.
6. Test a Claude judge with DeepSeek extraction as a separate experiment.

## Open decisions

- Accept threshold (currently 0.75 in config.py). Set it from eval results, not by hand.
- Judge model for the comparison. Keep the same model for both sides in the first baseline. Decide the Claude-judge experiment after step 4.
- DeepSeek output format. If parse failures are frequent, fix the prompt in a new version file, not by editing v1.

## Session log

- 2026-11-16: Added CLAUDE.md and STATUS.md. Project files copied to the local clone. Not yet committed. Waiting for approval to commit.
- 2026-11-18: Mock run passes on the local machine (5 emails). Changed the plan so DeepSeek-R1 14B is the primary development model and Sonnet is for comparison only. Added the grounding check and 6 unit tests. Used the judge's per-item confidence in `decide()`, with 7 more unit tests (13 total). The mock now quotes the real email body, so it passes the check. Not yet committed.
