# Email Harness — Commitment Extraction & Entity Resolution

A small, working proof-of-concept harness for extracting commitments and
deadlines from email, with calibrated confidence and a full audit trail —
built on the public Enron email corpus, independent of any employer's
proprietary systems or data.

## Why this exists

A worked example of the harness pattern underneath modern AI products:
a request goes through extraction, independent review, calibration
(accept / retry / abstain), and a logged decision — rather than a single
prompt producing a silent guess.

## Status

**Phase 1 (in progress):** core harness — extract → validate → judge →
calibrate → decide → log, for commitment/deadline extraction. Runs
end-to-end today in mock mode (no API key required); real model calls
wired and ready, pending a live key.

Planned next: embedding-based cross-thread entity resolution (Phase 2),
tool-calling loop served over MCP (Phase 3), a full LLMOps eval harness —
quality, hallucination rate, latency, cost — scored over 20-30+ cases
(Phase 4), and a public writeup (Phase 5).

## Setup

```bash
pip install -r requirements.txt
```

Dataset: [Enron Spam Dataset](https://github.com/MWiechmann/enron_spam_data)
(public domain; ham/non-spam subset used here as real internal business
email). Download and extract `enron_spam_data.zip` into
`data/enron_spam_data/extracted/enron_spam_data.csv`.

## Run it

No API key needed — verifies the full control flow (accept/retry/abstain)
with deterministic mock responses:

```bash
HARNESS_MOCK_MODE=1 python -m src.run_pipeline --limit 5
```

With a real key:

```bash
export ANTHROPIC_API_KEY=sk-...
python -m src.run_pipeline --limit 5
```

## Architecture

```
Email → [extract] → [validate: structural + rule checks] → [judge]
      → [decide: accept / retry / abstain] → [audit log]
```

- `src/model_client.py` — the only file that calls a model API. Swappable,
  auditable (captures tokens + latency on every call).
- `src/harness.py` — orchestration: the actual control flow deciding what
  gets called, when, and what happens on disagreement.
- `src/rule_checks.py` — deterministic (non-LLM) validation. Substitutes for
  a second model vendor as an independent check, since this project reaches
  only one API — a legitimate, disclosed design choice, not a shortcut
  pretending to be something else.
- `prompts/` — versioned prompt templates. Every logged decision records
  which version produced it.
- `logs/pipeline_runs.jsonl` — append-only audit trail: one record per
  email, with decision, confidence, model/prompt version, token cost.

## A note on methodology

Nothing here touches any employer's proprietary architecture, models, or
customer data. The dataset is public domain, the code is built fresh, and
the eval methodology (independent judging, documented versions, calibrated
abstention) is general practice, applied independently.
