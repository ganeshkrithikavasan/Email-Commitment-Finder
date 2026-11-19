"""
Grounding tests. No model calls, no API key, no Ollama needed.
Run with: python -m unittest tests.test_grounding -v
"""
import unittest

from src import rule_checks

BODY = (
    "gary , production from the high island larger block a - 1 # 2 commenced on\n"
    "saturday at 2 : 00 p . m . at about 6 , 500 gross . carlos expects between 9 , 500 and\n"
    "10 , 000 gross for the week . please send the nomination by friday ."
)


def item(text, **overrides):
    base = {"type": "commitment", "text": text, "attributed_to": "gary",
            "date": None, "confidence": 0.9}
    base.update(overrides)
    return base


class GroundingTests(unittest.TestCase):

    def test_exact_quote_passes(self):
        issues = rule_checks.check_extraction(
            {"items": [item("please send the nomination by friday")]}, BODY)
        self.assertEqual(issues, [])

    def test_spacing_difference_passes(self):
        # Model writes "6,500"; email has "6 , 500"
        issues = rule_checks.check_extraction(
            {"items": [item("about 6,500 gross")]}, BODY)
        self.assertEqual(issues, [])

    def test_case_difference_passes(self):
        issues = rule_checks.check_extraction(
            {"items": [item("PLEASE SEND THE NOMINATION BY FRIDAY")]}, BODY)
        self.assertEqual(issues, [])

    def test_invented_text_is_flagged(self):
        issues = rule_checks.check_extraction(
            {"items": [item("I will deliver the final report on Monday")]}, BODY)
        self.assertEqual(len(issues), 1)
        self.assertIn("not found in email body", issues[0])

    def test_changed_number_is_flagged(self):
        # A wrong number is the dangerous case. It must not pass as grounded.
        issues = rule_checks.check_extraction(
            {"items": [item("expects between 9 , 500 and 11 , 000 gross")]}, BODY)
        self.assertEqual(len(issues), 1)

    def test_empty_items_no_grounding_issue(self):
        self.assertEqual(rule_checks.check_extraction({"items": []}, BODY), [])


if __name__ == "__main__":
    unittest.main()
