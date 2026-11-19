"""
Decision tests. Pure logic, no model calls.
Run with: python -m unittest tests.test_decide -v
"""
import unittest

from src import config, harness

T = config.ACCEPT_CONFIDENCE_THRESHOLD
ITEM = {"type": "deadline", "text": "x", "attributed_to": "a", "date": None, "confidence": 0.9}


def judge(agree=True, *scores):
    return {
        "overall_agree": agree,
        "items_reviewed": [{"judge_confidence": s} for s in scores],
        "missed_items": "",
    }


class DecideTests(unittest.TestCase):

    def test_high_confidence_on_both_sides_accepts(self):
        d, c = harness.decide({"items": [ITEM]}, judge(True, 0.9), [])
        self.assertEqual(d, "accept")
        self.assertEqual(c, 0.9)

    def test_low_judge_score_forces_retry_even_if_judge_agrees(self):
        d, c = harness.decide({"items": [ITEM]}, judge(True, T - 0.2), [])
        self.assertEqual(d, "needs_retry")
        self.assertAlmostEqual(c, T - 0.2)

    def test_judge_disagreement_forces_retry(self):
        d, _ = harness.decide({"items": [ITEM]}, judge(False, 0.95), [])
        self.assertEqual(d, "needs_retry")

    def test_judge_reviewed_nothing_is_no_confidence(self):
        d, c = harness.decide({"items": [ITEM]}, judge(True), [])
        self.assertEqual(d, "needs_retry")
        self.assertEqual(c, 0.0)

    def test_lowest_judge_score_counts_when_several_items(self):
        d, c = harness.decide({"items": [ITEM, ITEM]}, judge(True, 0.95, 0.4), [])
        self.assertEqual(d, "needs_retry")
        self.assertEqual(c, 0.4)

    def test_rule_issue_forces_retry(self):
        d, c = harness.decide({"items": [ITEM]}, judge(True, 0.95), ["item 0: bad date"])
        self.assertEqual((d, c), ("needs_retry", 0.0))

    def test_nothing_found_accepts_without_judge_scores(self):
        d, c = harness.decide({"items": []}, judge(True), [])
        self.assertEqual((d, c), ("accept", 1.0))


if __name__ == "__main__":
    unittest.main()
