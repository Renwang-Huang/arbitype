#!/usr/bin/env python3
"""Validate and score Arbitype tool-selection predictions.

This runner deliberately does not call a model by itself. Use ``--predictions``
with a JSONL adapter output or ``--command`` with an external model/host
adapter. ``--dry-run`` validates the public dataset without producing model
results, so normal CI never claims an evaluation score it did not measure.
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arbitype.mcp import TOOL_MAP  # noqa: E402


TOOL_NAMES = tuple(TOOL_MAP)
INVALID_TOOL = "__invalid__"


class EvalDataError(ValueError):
    """Raised when a case or prediction does not match the runner contract."""


def _read_jsonl(path: Path) -> Iterable[tuple[int, Any]]:
    try:
        stream = path.open(encoding="utf-8")
    except OSError as exc:
        raise EvalDataError(f"cannot read {path}: {exc}") from exc
    with stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                yield line_number, json.loads(line)
            except json.JSONDecodeError as exc:
                raise EvalDataError(f"{path}:{line_number}: invalid JSON: {exc.msg}") from exc


def load_cases(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, (line_number, raw) in enumerate(_read_jsonl(path), 1):
        if not isinstance(raw, dict):
            raise EvalDataError(f"{path}:{line_number}: case must be an object")
        case_id = raw.get("id", f"case-{index:03d}")
        prompt = raw.get("prompt")
        expected = raw.get("expected_tool")
        acceptable = raw.get("acceptable_tools")
        reason = raw.get("reason")
        if not isinstance(case_id, str) or not case_id.strip():
            raise EvalDataError(f"{path}:{line_number}: id must be a non-empty string")
        if case_id in seen:
            raise EvalDataError(f"{path}:{line_number}: duplicate case id {case_id!r}")
        if not isinstance(prompt, str) or not prompt.strip():
            raise EvalDataError(f"{path}:{line_number}: prompt must be a non-empty string")
        if expected not in TOOL_NAMES:
            raise EvalDataError(
                f"{path}:{line_number}: expected_tool must be one of {', '.join(TOOL_NAMES)}"
            )
        if not isinstance(acceptable, list) or not acceptable or any(
            tool not in TOOL_NAMES for tool in acceptable
        ):
            raise EvalDataError(f"{path}:{line_number}: acceptable_tools contains an unknown tool")
        if expected not in acceptable:
            raise EvalDataError(f"{path}:{line_number}: expected_tool must be acceptable")
        if not isinstance(reason, str) or not reason.strip():
            raise EvalDataError(f"{path}:{line_number}: reason must be a non-empty string")
        seen.add(case_id)
        cases.append(
            {
                "id": case_id,
                "prompt": prompt,
                "expected_tool": expected,
                "acceptable_tools": acceptable,
                "reason": reason,
            }
        )
    if not cases:
        raise EvalDataError(f"{path}: dataset is empty")
    return cases


def _normalize_prediction(raw: Any, *, case_id: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {"id": case_id, "selected_tool": None, "schema_valid": False}
    selected = raw.get("selected_tool", raw.get("tool"))
    return {
        "id": raw.get("id", case_id),
        "selected_tool": selected if isinstance(selected, str) else None,
        "schema_valid": bool(raw.get("schema_valid", False)),
    }


def load_predictions(path: Path, cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for line_number, raw in _read_jsonl(path):
        prediction = _normalize_prediction(raw, case_id=f"line-{line_number}")
        case_id = prediction["id"]
        if case_id in by_id:
            raise EvalDataError(f"{path}:{line_number}: duplicate prediction id {case_id!r}")
        by_id[case_id] = prediction
    return [by_id.get(case["id"], _normalize_prediction({}, case_id=case["id"])) for case in cases]


def run_adapter(command: str, cases: list[dict[str, Any]], timeout: float) -> list[dict[str, Any]]:
    argv = shlex.split(command)
    if not argv:
        raise EvalDataError("--command must not be empty")
    predictions: list[dict[str, Any]] = []
    for case in cases:
        request = json.dumps({"id": case["id"], "prompt": case["prompt"]}, ensure_ascii=False)
        try:
            completed = subprocess.run(
                argv,
                input=request + "\n",
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            predictions.append(_normalize_prediction({}, case_id=case["id"]))
            print(f"adapter failed for {case['id']}: {exc}", file=sys.stderr)
            continue
        if completed.returncode != 0:
            print(
                f"adapter exited {completed.returncode} for {case['id']}: "
                f"{completed.stderr.strip()[:240]}",
                file=sys.stderr,
            )
            predictions.append(_normalize_prediction({}, case_id=case["id"]))
            continue
        try:
            raw = json.loads(completed.stdout)
        except json.JSONDecodeError:
            print(f"adapter returned invalid JSON for {case['id']}", file=sys.stderr)
            raw = {}
        predictions.append(_normalize_prediction(raw, case_id=case["id"]))
    return predictions


def score_cases(cases: list[dict[str, Any]], predictions: list[dict[str, Any]]) -> dict[str, Any]:
    if len(cases) != len(predictions):
        raise EvalDataError("case and prediction counts differ")
    total = len(cases)
    correct = 0
    invalid = 0
    schema_valid = 0
    per_tool = Counter(case["expected_tool"] for case in cases)
    per_tool_correct = Counter()
    confusion: dict[str, Counter[str]] = defaultdict(Counter)
    for case, prediction in zip(cases, predictions):
        selected = prediction.get("selected_tool")
        valid_tool = selected in TOOL_NAMES
        if not valid_tool:
            invalid += 1
            selected = INVALID_TOOL
        else:
            if selected in case["acceptable_tools"]:
                correct += 1
                per_tool_correct[case["expected_tool"]] += 1
            if prediction.get("schema_valid"):
                schema_valid += 1
        confusion[case["expected_tool"]][selected] += 1

    def ratio(numerator: int, denominator: int) -> float:
        return round(numerator / denominator, 6) if denominator else 0.0

    return {
        "cases": total,
        "tool_selection_accuracy": ratio(correct, total),
        "per_tool_accuracy": {
            tool: {
                "correct": per_tool_correct[tool],
                "total": per_tool[tool],
                "accuracy": ratio(per_tool_correct[tool], per_tool[tool]),
            }
            for tool in TOOL_NAMES
            if per_tool[tool]
        },
        "confusion_matrix": {
            expected: dict(sorted(counts.items())) for expected, counts in sorted(confusion.items())
        },
        "invalid_tool_call_rate": ratio(invalid, total),
        "schema_valid_call_rate": ratio(schema_valid, total),
        "definition": {
            "acceptable_tools": "A prediction is correct when selected_tool is in the case's acceptable_tools.",
            "invalid_tool_call_rate": "Fraction of cases with no advertised tool selected.",
            "schema_valid_call_rate": "Fraction of valid tool selections explicitly marked schema_valid=true by the adapter.",
        },
    }


def _print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("evals/tool_selection/cases.jsonl"),
        help="JSONL case dataset",
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--predictions", type=Path, help="JSONL predictions from a model adapter")
    source.add_argument("--command", help="adapter command; receives one case JSON on stdin")
    parser.add_argument("--timeout", type=float, default=60.0, help="per-case adapter timeout")
    parser.add_argument("--dry-run", action="store_true", help="validate and summarize the dataset only")
    args = parser.parse_args(argv)

    try:
        cases = load_cases(args.dataset)
        counts = Counter(case["expected_tool"] for case in cases)
        if args.dry_run:
            _print_json({"dataset": str(args.dataset), "cases": len(cases), "cases_by_expected_tool": dict(counts)})
            return 0
        if not args.predictions and not args.command:
            parser.error("one of --predictions or --command is required unless --dry-run is used")
        predictions = (
            load_predictions(args.predictions, cases)
            if args.predictions
            else run_adapter(args.command, cases, args.timeout)
        )
        _print_json(score_cases(cases, predictions))
        return 0
    except EvalDataError as exc:
        print(f"tool-selection-eval: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
