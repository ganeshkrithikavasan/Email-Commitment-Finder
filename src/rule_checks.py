"""
Deterministic (non-LLM) checks. This is the "second independent judge" we
substitute for a second model vendor, since this environment can only reach
one API. A rule-based check and an LLM judge catch different kinds of
mistakes, which is a legitimate, defensible form of independence — worth
stating plainly in the writeup rather than pretending it's cross-vendor.
"""
import re
from datetime import datetime


def check_extraction(extraction: dict, body: str) -> list[str]:
    """Returns a list of problems found, empty list if none.

    `body` must be the same text the model saw (after truncation), so that
    a quote is only "grounded" if the model could have copied it from there.
    """
    problems = []

    if "items" not in extraction:
        problems.append("missing 'items' key entirely")
        return problems

    for i, item in enumerate(extraction["items"]):
        date_str = item.get("date")
        if date_str:
            if not _is_valid_date(date_str):
                problems.append(f"item {i}: date '{date_str}' is not a valid YYYY-MM-DD date")

        conf = item.get("confidence")
        if conf is None or not (0.0 <= conf <= 1.0):
            problems.append(f"item {i}: confidence '{conf}' missing or out of 0-1 range")

        text = item.get("text", "")
        if len(text.strip()) == 0:
            problems.append(f"item {i}: empty extracted text")
        elif not _is_grounded(text, body):
            # Grounding: the prompt asks for an exact quote, so the text must
            # occur in the email. Anything else is a likely invention.
            problems.append(f"item {i}: extracted text not found in email body (possible invention)")

        # Vague-urgency check: catches the exact failure mode the prompt warns against
        if date_str is None and re.search(r"\b(soon|asap|shortly)\b", text, re.IGNORECASE):
            if item.get("type") in ("deadline", "both"):
                problems.append(
                    f"item {i}: flagged as deadline but text only has vague urgency language, no date"
                )

    return problems


def _squash(s: str) -> str:
    """Lowercase and drop all whitespace, so '6 , 500' matches '6,500'."""
    return re.sub(r"\s+", "", s).lower()


def _is_grounded(text: str, body: str) -> bool:
    return _squash(text) in _squash(body)


def _is_valid_date(date_str: str) -> bool:
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except (ValueError, TypeError):
        return False
