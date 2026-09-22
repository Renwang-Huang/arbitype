import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_stability_benchmark import (  # noqa: E402
    decision_signature,
    load_cases as load_stability_cases,
    probabilities,
    probability_metrics,
)
from scripts.run_tool_selection_live import fixture_arguments  # noqa: E402
from scripts.run_tool_selection_eval import load_cases, score_cases  # noqa: E402
from arbitype.mcp import TOOL_MAP, _matches_json_schema  # noqa: E402


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

    def test_stability_metrics_are_computed_per_case_not_across_cases(self):
        metrics = probability_metrics([[0.2, 0.8], [0.4, 0.6], [0.3, 0.7]])
        self.assertEqual(metrics["probability_mean"], 0.5)
        self.assertEqual(metrics["probability_std"], 0.0)
        self.assertEqual(metrics["probability_range"], 0.0)
        self.assertEqual(metrics["mean_absolute_delta"], 0.0)
        self.assertEqual(metrics["probability_sample_count"], 6)

        uneven = probability_metrics([[0.2], [0.6], [0.4]])
        self.assertEqual(uneven["probability_mean"], 0.4)
        self.assertAlmostEqual(uneven["probability_std"], 0.163299, places=6)
        self.assertEqual(uneven["probability_range"], 0.4)
        self.assertEqual(uneven["mean_absolute_delta"], 0.3)

    def test_stability_report_names_global_distribution_explicitly(self):
        metrics = probability_metrics([[0.1], [0.9]])
        self.assertIn("probability_std", metrics)
        self.assertNotIn("global_probability_distribution", metrics)

    def test_live_adapter_fixtures_match_advertised_tool_schemas(self):
        for tool in TOOL_MAP:
            with self.subTest(tool=tool):
                arguments = fixture_arguments(tool, "A bounded benchmark task.")
                self.assertTrue(_matches_json_schema(arguments, TOOL_MAP[tool]["inputSchema"]))

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
