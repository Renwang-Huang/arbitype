import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_stability_benchmark import decision_signature, load_cases as load_stability_cases, probabilities  # noqa: E402
from scripts.run_tool_selection_eval import load_cases, score_cases  # noqa: E402


class EvaluationTests(unittest.TestCase):
    def test_tool_selection_dataset_has_120_balanced_cases(self):
        cases = load_cases(ROOT / "evals" / "tool_selection" / "cases.jsonl")
        self.assertEqual(len(cases), 120)
        counts = {}
        for case in cases:
            counts[case["expected_tool"]] = counts.get(case["expected_tool"], 0) + 1
        self.assertEqual(set(counts), {"evaluate", "classify", "score", "check", "verify", "gate", "route", "review"})
        self.assertEqual(set(counts.values()), {15})

    def test_tool_selection_scoring_reports_invalid_and_confusion(self):
        cases = load_cases(ROOT / "evals" / "tool_selection" / "cases.jsonl")[:3]
        predictions = [
            {"selected_tool": cases[0]["expected_tool"], "schema_valid": True},
            {"selected_tool": "not-a-tool", "schema_valid": False},
            {"selected_tool": cases[2]["expected_tool"], "schema_valid": True},
        ]
        report = score_cases(cases, predictions)
        self.assertEqual(report["cases"], 3)
        self.assertAlmostEqual(report["tool_selection_accuracy"], 2 / 3, places=5)
        self.assertAlmostEqual(report["invalid_tool_call_rate"], 1 / 3, places=5)
        self.assertEqual(report["confusion_matrix"][cases[1]["expected_tool"]]["__invalid__"], 1)

    def test_stability_dataset_is_live_only_and_decision_signature_is_bounded(self):
        cases = load_stability_cases(ROOT / "evals" / "stability" / "cases.jsonl")
        self.assertEqual(len(cases), 8)
        result = {"type": "route", "route": "inspect"}
        self.assertEqual(decision_signature("route", result), "inspect")
        self.assertEqual(
            probabilities(
                {"type": "gate", "checks": {"tests": {"probability": 0.9}}}
            ),
            [0.9],
        )

    def test_tool_selection_case_schema_rejects_invalid_case(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.jsonl"
            path.write_text(
                json.dumps(
                    {
                        "id": "bad",
                        "prompt": "Choose a tool",
                        "expected_tool": "not-a-tool",
                        "acceptable_tools": ["not-a-tool"],
                        "reason": "bad",
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_cases(path)


if __name__ == "__main__":
    unittest.main()
