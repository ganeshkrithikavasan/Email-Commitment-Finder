"""
The orchestration layer — this file IS the "harness" in engineering terms.
It decides what gets called, in what order, and what happens when the
extractor and judge disagree. Every other file here is a building block;
this is the one that wires them into a pipeline.
"""
import json
import time
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path

from . import config, rule_checks
from .model_client import call_model


def load_prompt(name: str) -> str:
    return (config.PROMPTS_DIR / f"{name}.txt").read_text()


def render(template: str, **kwargs) -> str:
    out = template
    for k, v in kwargs.items():
        out = out.replace("{{" + k + "}}", str(v))
    return out


def parse_json_strict(raw_text: str) -> dict:
    """
    Models sometimes wrap JSON in markdown fences, leave in a reasoning
    trace, or add stray text despite instructions. Strip the common cases,
    then parse strictly — a malformed output should fail loudly here, not
    get silently guessed at downstream.
    """
    import re

    text = raw_text.strip()
    # Defensive second pass: model_client already strips <think> blocks at
    # the source for Ollama calls, but any other reasoning model gets the
    # same treatment here rather than silently failing to parse.
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


@dataclass
class PipelineResult:
    record_id: str
    email_subject: str
    extraction: dict
    judge_result: dict | None
    rule_issues: list
    decision: str  # "accept" | "retry_then_accept" | "retry_then_abstain" | "abstain"
    final_confidence: float
    retries_used: int
    total_latency_seconds: float
    total_input_tokens: int
    total_output_tokens: int
    extract_model: str
    judge_model: str
    extract_prompt_version: str
    judge_prompt_version: str


def extract_commitment(subject: str, date: str, body: str) -> tuple[dict, "ModelResponse"]:
    template = load_prompt(config.EXTRACT_PROMPT_VERSION)
    prompt = render(template, subject=subject, date=date, body=body)
    resp = call_model(prompt, config.EXTRACT_MODEL)
    return parse_json_strict(resp.text), resp


def judge_commitment(subject: str, body: str, extraction: dict) -> tuple[dict, "ModelResponse"]:
    template = load_prompt(config.JUDGE_PROMPT_VERSION)
    prompt = render(
        template,
        subject=subject,
        body=body,
        extraction_json=json.dumps(extraction, indent=2),
    )
    resp = call_model(prompt, config.JUDGE_MODEL)
    return parse_json_strict(resp.text), resp


def decide(extraction: dict, judge_result: dict, rule_issues: list) -> tuple[str, float]:
    """
    The actual calibration logic. Returns (decision, confidence).
    This is deliberately simple and readable — tune the thresholds in
    config.py once Phase 4 gives you real eval numbers, don't hand-tune
    this function itself.
    """
    if rule_issues:
        return "needs_retry", 0.0

    if not extraction.get("items"):
        return "accept", 1.0  # confidently "nothing found" is a valid, common outcome

    min_item_confidence = min(item.get("confidence", 0.0) for item in extraction["items"])
    judge_agrees = judge_result.get("overall_agree", False)

    # The judge's own per-item confidence counts too. If the judge reviewed
    # nothing, or gave no score, treat that as no confidence.
    judge_scores = [
        float(review.get("judge_confidence") or 0.0)
        for review in judge_result.get("items_reviewed", [])
    ]
    min_judge_confidence = min(judge_scores) if judge_scores else 0.0

    confidence = min(min_item_confidence, min_judge_confidence)

    if judge_agrees and confidence >= config.ACCEPT_CONFIDENCE_THRESHOLD:
        return "accept", confidence

    return "needs_retry", confidence


def run_email(subject: str, date: str, body: str) -> PipelineResult:
    record_id = str(uuid.uuid4())
    t0 = time.monotonic()
    total_in_tokens = 0
    total_out_tokens = 0
    retries_used = 0

    extraction, extract_resp = extract_commitment(subject, date, body)
    total_in_tokens += extract_resp.input_tokens
    total_out_tokens += extract_resp.output_tokens

    rule_issues = rule_checks.check_extraction(extraction, body)
    judge_result, judge_resp = judge_commitment(subject, body, extraction)
    total_in_tokens += judge_resp.input_tokens
    total_out_tokens += judge_resp.output_tokens

    decision, confidence = decide(extraction, judge_result, rule_issues)

    # One bounded retry: re-extract with the disagreement/issues as context.
    if decision == "needs_retry" and retries_used < config.MAX_RETRIES:
        retries_used += 1
        retry_context = (
            f"\n\nA previous attempt had these problems — fix them: "
            f"{rule_issues or judge_result.get('missed_items', 'low confidence')}"
        )
        template = load_prompt(config.EXTRACT_PROMPT_VERSION)
        prompt = render(template, subject=subject, date=date, body=body) + retry_context
        resp = call_model(prompt, config.EXTRACT_MODEL)
        total_in_tokens += resp.input_tokens
        total_out_tokens += resp.output_tokens
        extraction = parse_json_strict(resp.text)

        rule_issues = rule_checks.check_extraction(extraction, body)
        judge_result, judge_resp = judge_commitment(subject, body, extraction)
        total_in_tokens += judge_resp.input_tokens
        total_out_tokens += judge_resp.output_tokens
        decision, confidence = decide(extraction, judge_result, rule_issues)
        decision = "retry_then_accept" if decision == "accept" else "retry_then_abstain"
    elif decision == "needs_retry":
        decision = "abstain"
    else:
        decision = "accept"

    result = PipelineResult(
        record_id=record_id,
        email_subject=subject,
        extraction=extraction,
        judge_result=judge_result,
        rule_issues=rule_issues,
        decision=decision,
        final_confidence=confidence,
        retries_used=retries_used,
        total_latency_seconds=time.monotonic() - t0,
        total_input_tokens=total_in_tokens,
        total_output_tokens=total_out_tokens,
        extract_model=config.EXTRACT_MODEL,
        judge_model=config.JUDGE_MODEL,
        extract_prompt_version=config.EXTRACT_PROMPT_VERSION,
        judge_prompt_version=config.JUDGE_PROMPT_VERSION,
    )
    log_record(result)
    return result


def log_record(result: PipelineResult) -> None:
    """Append-only audit log — one JSON line per email processed."""
    log_path = config.LOGS_DIR / "pipeline_runs.jsonl"
    with open(log_path, "a") as f:
        f.write(json.dumps(asdict(result)) + "\n")
