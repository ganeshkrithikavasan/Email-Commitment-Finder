"""
The ONLY place that talks to a model API. Everything else in the harness
calls call_model() and never touches an SDK directly — that's what makes it
swappable (change provider here, nothing else changes) and auditable (every
call's token usage and latency is captured in one place).
"""
import os
import time
from dataclasses import dataclass

from . import config


@dataclass
class ModelResponse:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_seconds: float


def call_model(prompt: str, model: str) -> ModelResponse:
    """
    Calls the configured model with `prompt`, returns the raw text plus
    token/latency metadata for logging. In mock mode, returns a canned
    response instead so you can test the harness's control flow with no
    API key at all.

    Dispatches to a local Ollama server for local model names (see
    config.is_ollama_model), and to the Anthropic API otherwise. This is
    the one function the rest of the harness never has to know about —
    extract() and judge() just pass a model name, same as always.
    """
    if config.MOCK_MODE:
        return _mock_response(prompt, model)

    if config.is_ollama_model(model):
        return _call_ollama(prompt, model)

    return _call_anthropic(prompt, model)


def _call_anthropic(prompt: str, model: str) -> ModelResponse:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "No ANTHROPIC_API_KEY in environment. Either set it, or run with "
            "HARNESS_MOCK_MODE=1 to test the pipeline logic without a live call."
        )

    import anthropic  # local import: only required when actually calling the API

    client = anthropic.Anthropic(api_key=api_key)
    start = time.monotonic()
    resp = client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    latency = time.monotonic() - start

    return ModelResponse(
        text=resp.content[0].text,
        model=model,
        input_tokens=resp.usage.input_tokens,
        output_tokens=resp.usage.output_tokens,
        latency_seconds=latency,
    )


def _call_ollama(prompt: str, model: str) -> ModelResponse:
    """
    Calls a locally-running Ollama server (default http://localhost:11434).
    This only reaches a server on the same machine the code runs on — it
    will NOT reach your laptop's Ollama from a cloud sandbox. Run this
    script on the machine where Ollama is actually running.

    Reasoning models like deepseek-r1 emit a <think>...</think> block before
    their real answer by default. We strip it here, at the point the model's
    own quirk is known, rather than downstream — harness.parse_json_strict
    also strips it defensively, but fixing it at the source is the honest
    place to do it.
    """
    import json
    import re
    import urllib.request

    start = time.monotonic()
    req_body = json.dumps(
        {"model": model, "prompt": prompt, "stream": False}
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{config.OLLAMA_HOST}/api/generate",
        data=req_body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise RuntimeError(
            f"Could not reach Ollama at {config.OLLAMA_HOST}. Is `ollama serve` "
            f"running on THIS machine, and is '{model}' pulled "
            f"(`ollama pull {model}`)? Underlying error: {e}"
        ) from e
    latency = time.monotonic() - start

    text = body.get("response", "")
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    return ModelResponse(
        text=text,
        model=model,
        # Ollama reports real token counts for both sides of the call —
        # no estimating needed, unlike the mock path.
        input_tokens=body.get("prompt_eval_count", 0),
        output_tokens=body.get("eval_count", 0),
        latency_seconds=latency,
    )


def _mock_response(prompt: str, model: str) -> ModelResponse:
    """
    Deterministic fake response for pipeline testing. Returns a plausible
    extraction JSON regardless of input — good enough to exercise every
    branch of decide() (accept/retry/abstain) before a real key exists.
    """
    import json

    if "Extraction to review" in prompt:
        # This is a judge call
        fake = {
            "items_reviewed": [
                {
                    "item_text": "mock extracted item",
                    "supported_by_email": True,
                    "attribution_correct": True,
                    "date_correct": True,
                    "judge_confidence": 0.8,
                    "note": "",
                }
            ],
            "missed_items": "",
            "overall_agree": True,
        }
    else:
        # This is an extraction call. Quote the start of the real email body,
        # so the mock passes the grounding check the same way a faithful model would.
        body = prompt.split("Email Body:\n", 1)[-1].strip()
        quote = body[:40] or "mock extracted item"
        fake = {
            "has_commitment_or_deadline": True,
            "items": [
                {
                    "type": "deadline",
                    "text": quote,
                    "attributed_to": "mock sender",
                    "date": "1999-12-15",
                    "confidence": 0.8,
                }
            ],
        }
    return ModelResponse(
        text=json.dumps(fake),
        model=f"{model} (mock)",
        input_tokens=len(prompt) // 4,  # rough char->token estimate, mock only
        output_tokens=len(json.dumps(fake)) // 4,
        latency_seconds=0.01,
    )
