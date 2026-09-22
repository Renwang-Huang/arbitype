#!/usr/bin/env python3
"""Run an opt-in repeated Arbitype decision benchmark against TypeSafe Jev.

This script is intentionally live-only: it refuses to run without ``--live``
and a ``TYPESAFE_API_KEY``. It is not called by CI and never stores or prints
the credential. The report separates selected-decision consistency from the
distribution of model probabilities.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arbitype.mcp import TOOL_MAP, call_tool  # noqa: E402


class StabilityDataError(ValueError):
    """Raised when the fixed stability dataset is invalid."""


def load_cases(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    seen: set[str] = set()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise StabilityDataError(f"cannot read {path}: {exc}") from exc
    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise StabilityDataError(f"{path}:{line_number}: invalid JSON") from exc
        if not isinstance(raw, dict):
            raise StabilityDataError(f"{path}:{line_number}: case must be an object")
        case_id = raw.get("id")
        tool = raw.get("tool")
        arguments = raw.get("arguments")
        if not isinstance(case_id, str) or not case_id or case_id in seen:
            raise StabilityDataError(f"{path}:{line_number}: id must be unique and non-empty")
        if tool not in TOOL_MAP or tool == "health":
            raise StabilityDataError(f"{path}:{line_number}: tool must be a live decision tool")
        if not isinstance(arguments, dict):
            raise StabilityDataError(f"{path}:{line_number}: arguments must be an object")
        seen.add(case_id)
        cases.append({"id": case_id, "tool": tool, "arguments": arguments})
    if not cases:
        raise StabilityDataError(f"{path}: dataset is empty")
    return cases


def _answer_values(result: dict[str, Any]) -> list[dict[str, Any]]:
    answers = result.get("answers")
    if not isinstance(answers, dict):
        answer = result.get("answer")
        answers = {"answer": answer} if isinstance(answer, dict) else {}
    return [answer for answer in answers.values() if isinstance(answer, dict)]


def decision_signature(tool: str, result: dict[str, Any]) -> Any:
    """Extract a comparable decision without pretending probabilities are fixed."""

    if tool in {"gate", "review"}:
        return result.get("decision")
    if tool == "route":
        return result.get("route")
    if tool == "classify":
        answer = result.get("answer", {})
        return answer.get("choice") if isinstance(answer, dict) else None
    if tool == "score":
        answer = result.get("answer", {})
        return answer.get("score") if isinstance(answer, dict) else None
    if tool == "check":
        answer = result.get("answer", {})
        value = answer.get("noul") if isinstance(answer, dict) else None
        return None if not isinstance(value, (int, float)) else value >= 0.5
    if tool in {"verify", "evaluate"}:
        values = {}
        answers = result.get("answers", {})
        if isinstance(answers, dict):
            for key, answer in sorted(answers.items()):
                if isinstance(answer, dict) and isinstance(answer.get("noul"), (int, float)):
                    values[key] = answer["noul"] >= 0.5
                elif isinstance(answer, dict):
                    values[key] = answer.get("choice", answer.get("score"))
        return values
    return None


def probabilities(result: dict[str, Any]) -> list[float]:
    values: list[float] = []
    for answer in _answer_values(result):
        noul = answer.get("noul")
        if isinstance(noul, (int, float)) and not isinstance(noul, bool):
            values.append(float(noul))
        distribution = answer.get("probabilities")
        if isinstance(distribution, dict):
            numeric = [float(value) for value in distribution.values() if isinstance(value, (int, float))]
            if numeric:
                values.append(max(numeric))
    checks = result.get("checks")
    if isinstance(checks, dict):
        values.extend(
            float(check["probability"])
            for check in checks.values()
            if isinstance(check, dict)
            and isinstance(check.get("probability"), (int, float))
            and not isinstance(check.get("probability"), bool)
        )
    return values


def _stats(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"mean": None, "std": None, "min": None, "max": None}
    return {
        "mean": round(statistics.mean(values), 6),
        "std": round(statistics.pstdev(values), 6),
        "min": round(min(values), 6),
        "max": round(max(values), 6),
    }


def _usage(result: dict[str, Any]) -> dict[str, int]:
    usage = result.get("usage")
    if not isinstance(usage, dict):
        evaluation = result.get("evaluation")
        usage = evaluation.get("usage") if isinstance(evaluation, dict) else None
    if not isinstance(usage, dict):
        return {"input_tokens": 0, "output_tokens": 0}
    return {
        "input_tokens": int(usage.get("input_tokens", 0)),
        "output_tokens": int(usage.get("output_tokens", 0)),
    }


def run_case(case: dict[str, Any], repeats: int) -> dict[str, Any]:
    signatures: list[Any] = []
    probability_values: list[float] = []
    latencies: list[float] = []
    usage_total = {"input_tokens": 0, "output_tokens": 0}
    for _ in range(repeats):
        started = time.monotonic()
        result = call_tool(case["tool"], case["arguments"])
        latencies.append(round((time.monotonic() - started) * 1000, 1))
        signatures.append(decision_signature(case["tool"], result))
        probability_values.extend(probabilities(result))
        usage = _usage(result)
        for key in usage_total:
            usage_total[key] += usage[key]
    first = signatures[0]
    consistent = sum(signature == first for signature in signatures)
    return {
        "id": case["id"],
        "tool": case["tool"],
        "repeats": repeats,
        "selected_decision": first,
        "decision_consistency": round(consistent / repeats, 6),
        "probability": _stats(probability_values),
        "latency_ms": _stats(latencies),
        "usage": usage_total,
        "_probability_samples": probability_values,
        "_latency_samples": latencies,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cases",
        type=Path,
        default=Path("evals/stability/cases.jsonl"),
        help="fixed JSONL live benchmark cases",
    )
    parser.add_argument("--repeats", type=int, default=3, help="calls per case (1-10)")
    parser.add_argument("--live", action="store_true", help="explicitly allow paid TypeSafe requests")
    args = parser.parse_args(argv)
    if not args.live:
        print("stability benchmark is opt-in; pass --live to make paid requests", file=sys.stderr)
        return 2
    if not os.getenv("TYPESAFE_API_KEY", "").strip():
        print("stability benchmark requires TYPESAFE_API_KEY in the process environment", file=sys.stderr)
        return 2
    if not 1 <= args.repeats <= 10:
        print("--repeats must be between 1 and 10", file=sys.stderr)
        return 2
    try:
        cases = load_cases(args.cases)
        reports = [run_case(case, args.repeats) for case in cases]
    except StabilityDataError as exc:
        print(f"stability-benchmark: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # provider/network errors should be visible without a traceback
        print(f"stability-benchmark: live request failed: {exc}", file=sys.stderr)
        return 1

    decision_consistency = [report["decision_consistency"] for report in reports]
    all_probabilities = [value for report in reports for value in report.pop("_probability_samples")]
    all_latencies = [value for report in reports for value in report.pop("_latency_samples")]
    usage = {
        key: sum(report["usage"][key] for report in reports)
        for key in ("input_tokens", "output_tokens")
    }
    output = {
        "cases": len(reports),
        "repeats": args.repeats,
        "selected_decision_consistency": round(statistics.mean(decision_consistency), 6),
        "probability": _stats(all_probabilities),
        "latency_ms": _stats(all_latencies),
        "usage": usage,
        "reports": reports,
        "note": "Model probabilities are signals and may vary even when the selected decision is consistent.",
    }
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
