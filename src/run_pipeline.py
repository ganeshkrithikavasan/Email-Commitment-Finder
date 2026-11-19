"""
Entry point. Loads N real emails from the Enron corpus and runs each through
the harness. Works right now with HARNESS_MOCK_MODE=1 (no API key needed) to
verify the control flow end to end. Once ANTHROPIC_API_KEY is set, drop the
mock flag and it runs for real, unchanged.

Usage:
    HARNESS_MOCK_MODE=1 python -m src.run_pipeline --limit 5
    python -m src.run_pipeline --limit 5          # real run, needs ANTHROPIC_API_KEY
"""
import argparse
import csv
import sys
from pathlib import Path

from . import config, harness

CSV_PATH = config.DATA_DIR / "enron_spam_data" / "extracted" / "enron_spam_data.csv"


def load_emails(limit: int):
    csv.field_size_limit(10**7)
    emails = []
    with open(CSV_PATH, encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["Spam/Ham"] != "ham":
                continue
            if not row["Message"]:
                continue
            emails.append(row)
            if len(emails) >= limit:
                break
    return emails


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    if not CSV_PATH.exists():
        print(f"Dataset not found at {CSV_PATH}. See README for setup.", file=sys.stderr)
        sys.exit(1)

    emails = load_emails(args.limit)
    print(f"Loaded {len(emails)} emails. Mock mode: {config.MOCK_MODE}\n")

    decisions = {}
    for email in emails:
        result = harness.run_email(
            subject=email["Subject"] or "(no subject)",
            date=email["Date"] or "unknown",
            body=email["Message"][:4000],  # cap body length for prompt size
        )
        decisions[result.decision] = decisions.get(result.decision, 0) + 1
        print(
            f"[{result.decision:>18}] conf={result.final_confidence:.2f} "
            f"retries={result.retries_used} "
            f"tokens={result.total_input_tokens + result.total_output_tokens} "
            f"latency={result.total_latency_seconds:.2f}s "
            f"-- {result.email_subject[:60]}"
        )

    print(f"\nDecision breakdown: {decisions}")
    print(f"Full audit log: {config.LOGS_DIR / 'pipeline_runs.jsonl'}")


if __name__ == "__main__":
    main()
