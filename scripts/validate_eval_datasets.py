#!/usr/bin/env python3
"""Validate public offline and live-benchmark datasets without calling a model."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_stability_benchmark import load_cases as load_stability_cases  # noqa: E402
from scripts.run_tool_selection_eval import load_cases as load_tool_selection_cases  # noqa: E402


def main() -> int:
    selection = load_tool_selection_cases(ROOT / "evals" / "tool_selection" / "cases.jsonl")
    stability = load_stability_cases(ROOT / "evals" / "stability" / "cases.jsonl")
    print(f"tool-selection dataset: {len(selection)} cases")
    print(f"stability dataset: {len(stability)} cases; live calls not executed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
