"""
Central config for the harness. Nothing here is secret — the actual API key
is read from the environment at call time (see src/model_client.py), never
hardcoded or logged.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = ROOT / "prompts"
LOGS_DIR = ROOT / "logs"
DATA_DIR = ROOT / "data"

LOGS_DIR.mkdir(exist_ok=True)

# Model + prompt versions used for this run. Every log record stamps these,
# so later you can answer "which prompt/model produced this output" exactly —
# this is the whole point of the governance/audit framing from the deck.
EXTRACT_MODEL = os.environ.get("HARNESS_EXTRACT_MODEL", "claude-sonnet-5")
JUDGE_MODEL = os.environ.get("HARNESS_JUDGE_MODEL", "claude-sonnet-5")
EXTRACT_PROMPT_VERSION = "extract_commitment_v1"
JUDGE_PROMPT_VERSION = "judge_commitment_v1"

# Calibration thresholds — the actual "does it abstain when unsure" logic.
# Tune these once you have real eval numbers in Phase 4; these are a
# reasonable starting point, not tuned yet.
ACCEPT_CONFIDENCE_THRESHOLD = 0.75
MAX_RETRIES = 1

# Set HARNESS_MOCK_MODE=1 to run the full pipeline with fake model responses —
# lets you verify all the control flow (accept/retry/abstain) before you have
# an API key wired up at all.
MOCK_MODE = os.environ.get("HARNESS_MOCK_MODE", "0") == "1"

# Any model name starting with one of these prefixes is routed to a local
# Ollama server instead of the Anthropic API — see model_client.py. This is
# how the Sonnet-vs-DeepSeek tokenomics comparison is wired: same harness,
# same prompts, the only thing that changes is which model name you pass.
OLLAMA_MODEL_PREFIXES = ("deepseek-r1", "deepseek", "llama", "qwen", "mistral")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")


def is_ollama_model(model: str) -> bool:
    return any(model.lower().startswith(p) for p in OLLAMA_MODEL_PREFIXES)
