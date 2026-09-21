#!/usr/bin/env python3
"""Run one small live request without printing the API key or request state."""

import json
import sys

from arbitype.core import post_to_typesafe


def main() -> int:
    try:
        response = post_to_typesafe(
            {
                "model": "jev-latest",
                "state": "A customer says the payment failed and asks for urgent help.",
                "questions": {
                    "urgent": {
                        "type": "noul",
                        "instructions": "Does this message express urgency?",
                    }
                },
            }
        )
    except Exception as exc:
        print(f"live request failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    answer = response.get("answers", {}).get("urgent", {})
    print(
        json.dumps(
            {
                "ok": True,
                "model": response.get("model"),
                "answer": answer,
                "usage": response.get("usage"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
