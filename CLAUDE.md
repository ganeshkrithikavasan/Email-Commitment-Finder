# CLAUDE.md

Project guide for Claude Code. Read this first, then read STATUS.md for what is in progress right now.

## What this project is

Email Commitment Finder: a small AI harness that reads email, finds commitments and deadlines, assigns a confidence score, and abstains when unsure. It also includes a planned entity-linking step. Data is the public Enron corpus. Nothing here touches any employer's systems or data.

Read VISION.md for the full why. Do not restate it in code comments.

## Architecture

Every email goes through one pipeline:

    extract (model call, versioned prompt)
      -> validate (structural and rule checks, no LLM)
      -> judge (second model call, independent review)
      -> decide (accept / retry once / abstain)
      -> log (append-only JSONL audit record)

Files:

- `src/config.py`: models, prompt versions, thresholds, Ollama routing, mock flag. Thresholds are placeholders until Phase 4 eval numbers exist.
- `src/model_client.py`: the only file that calls a model. Routes to Ollama for local model names, otherwise to the Anthropic API. Mock mode returns canned responses.
- `src/harness.py`: orchestration. The control flow lives here.
- `src/rule_checks.py`: deterministic checks. These are the non-LLM judge.
- `src/run_pipeline.py`: entry point. Loads emails from the dataset and runs them.
- `prompts/`: versioned prompt templates. Never edit a version in place. Create a new version file and bump the constant in config.py.
- `logs/pipeline_runs.jsonl`: audit log. Git-ignored.

## Commands

Mock run, no API key or Ollama needed. Use this to check control flow:

    HARNESS_MOCK_MODE=1 python -m src.run_pipeline --limit 5

Unit tests, no model or API key needed. Run after any change to `rule_checks.py` or `decide()`:

    python -m unittest tests.test_grounding tests.test_decide -v

Local DeepSeek run, the default for development (requires `ollama serve` running on this machine and `ollama pull deepseek-r1:14b`):

    HARNESS_EXTRACT_MODEL=deepseek-r1:14b HARNESS_JUDGE_MODEL=deepseek-r1:14b python -m src.run_pipeline --limit 5

Claude Sonnet run, for comparison only. Costs money per token through the API, which Claude Pro does not cover:

    export ANTHROPIC_API_KEY=...   # never commit or paste this
    python -m src.run_pipeline --limit 5

PowerShell equivalents use `$env:NAME="value"` and `Remove-Item Env:NAME`.

## Rules

- Never commit `data/`, `.env`, API keys, or anything in `logs/`. `.gitignore` covers these. Check `git status` before every commit.
- Never hardcode a key or a model response.
- Prompt versions are immutable. Changing a prompt means a new version file.
- Every logged decision must record model and prompt versions. Do not remove those fields.
- Keep the code plain. No frameworks until a phase needs one.
- Public-facing text (README, VISION.md, writeups): short sentences, no colons in prose, no em dashes, no stock AI phrasing.
- Do not add an agent loop or MCP layer before Phase 3. Phase order is in STATUS.md.

## Working agreement

- One task per session. Use /clear between tasks.
- Commit after every working step, with a message that says what works now.
- Update STATUS.md before ending a session. Put the date and time, with timezone, on its "Last updated" line.
- If a result is surprising, record it in STATUS.md before fixing anything.
