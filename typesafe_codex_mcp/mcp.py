"""Dependency-free MCP stdio server and opinionated TypeSafe tools."""

from __future__ import annotations

import json
import sys
from typing import Any

from .core import (
    BridgeError,
    MAX_INPUT_LINE_BYTES,
    SERVER_NAME,
    SERVER_VERSION,
    TypeSafeClient,
    validate_request,
)


STRUCTURED_VALUE_SCHEMA: dict[str, Any] = {
    "anyOf": [
        {"type": "string"},
        {"type": "object"},
        {"type": "array"},
    ]
}
OPTION_DESCRIPTION_SCHEMA: dict[str, Any] = {
    "anyOf": [
        {"type": "string"},
        {"type": "object"},
        {"type": "array"},
        {"type": "null"},
    ]
}
CRITERION_SCHEMA: dict[str, Any] = {
    "anyOf": [
        {"type": "string"},
        {"type": "object"},
        {"type": "array"},
    ]
}
QUESTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "type": {"type": "string", "enum": ["noul", "choice", "score"]},
        "instructions": STRUCTURED_VALUE_SCHEMA,
        "criteria": {},
    },
    "required": ["type", "instructions"],
    "additionalProperties": False,
}

SERVER_INSTRUCTIONS = (
    "TypeSafe Jev returns bounded typed judgments, not generated prose. Use evaluate for "
    "raw questions, or classify/score/check for the common shapes. Use verify and gate as "
    "review signals only: probabilities and confidence are not proof, authorization, or a "
    "security boundary. Keep secrets out of state and batch independent questions. Do not use "
    "Jev for code generation, exact arithmetic, date arithmetic, or open-ended writing."
)


def _tool(
    name: str,
    description: str,
    properties: dict[str, Any],
    required: list[str],
) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "inputSchema": {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        },
    }


TOOLS = [
    _tool(
        "evaluate",
        "Evaluate state with TypeSafe Jev and return the raw typed answers. Use for bounded "
        "noul, choice, or score questions; never for prose, code generation, arithmetic, or dates.",
        {
            "state": {**STRUCTURED_VALUE_SCHEMA, "description": "Text or structured evidence."},
            "questions": {
                "type": "object",
                "description": "Map of question id to a TypeSafe question.",
                "additionalProperties": QUESTION_SCHEMA,
            },
            "model": {"type": "string", "description": "Optional model id or alias."},
        },
        ["state", "questions"],
    ),
    _tool(
        "classify",
        "Choose one label from a closed set and return its probability distribution.",
        {
            "state": STRUCTURED_VALUE_SCHEMA,
            "instructions": STRUCTURED_VALUE_SCHEMA,
            "labels": {"type": "object", "additionalProperties": OPTION_DESCRIPTION_SCHEMA},
            "model": {"type": "string"},
        },
        ["state", "instructions", "labels"],
    ),
    _tool(
        "score",
        "Rate state on an ordered rubric and return the weighted score, probabilities, and confidence.",
        {
            "state": STRUCTURED_VALUE_SCHEMA,
            "instructions": STRUCTURED_VALUE_SCHEMA,
            "levels": {"type": "array", "minItems": 2, "maxItems": 10, "items": STRUCTURED_VALUE_SCHEMA},
            "model": {"type": "string"},
        },
        ["state", "instructions", "levels"],
    ),
    _tool(
        "check",
        "Estimate the probability that a bounded yes/no proposition is true.",
        {
            "state": STRUCTURED_VALUE_SCHEMA,
            "instructions": STRUCTURED_VALUE_SCHEMA,
            "true_criteria": CRITERION_SCHEMA,
            "false_criteria": CRITERION_SCHEMA,
            "model": {"type": "string"},
        },
        ["state", "instructions"],
    ),
    _tool(
        "verify",
        "Check several claims against the supplied evidence in one request. Results are review "
        "signals, not proof of truth.",
        {
            "state": STRUCTURED_VALUE_SCHEMA,
            "claims": {"type": "object", "additionalProperties": STRUCTURED_VALUE_SCHEMA},
            "true_criteria": CRITERION_SCHEMA,
            "false_criteria": CRITERION_SCHEMA,
            "model": {"type": "string"},
        },
        ["state", "claims"],
    ),
    _tool(
        "gate",
        "Evaluate bounded pass checks and turn their probabilities into pass/review/fail. "
        "This is not an authorization or security boundary; keep normal human and policy controls.",
        {
            "state": STRUCTURED_VALUE_SCHEMA,
            "checks": {"type": "object", "additionalProperties": STRUCTURED_VALUE_SCHEMA},
            "pass_at": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.85},
            "review_at": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.60},
            "model": {"type": "string"},
        },
        ["state", "checks"],
    ),
]
TOOL_MAP = {tool["name"]: tool for tool in TOOLS}


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def _require_object(arguments: Any) -> dict[str, Any]:
    if not isinstance(arguments, dict):
        raise BridgeError("arguments must be a JSON object")
    return arguments


def _reject_unknown(arguments: dict[str, Any], allowed: set[str]) -> None:
    unknown = sorted(set(arguments) - allowed)
    if unknown:
        raise BridgeError(f"unsupported argument(s): {', '.join(map(str, unknown))}")


def _require_state(arguments: dict[str, Any]) -> Any:
    if "state" not in arguments:
        raise BridgeError("missing required argument: state")
    return arguments["state"]


def _require_structured(arguments: dict[str, Any], name: str) -> Any:
    if name not in arguments:
        raise BridgeError(f"missing required argument: {name}")
    value = arguments[name]
    if not isinstance(value, (str, dict, list)):
        raise BridgeError(f"{name} must be a string, object, or array")
    return value


def _optional_model(arguments: dict[str, Any]) -> str | None:
    model = arguments.get("model")
    if model is not None and (not isinstance(model, str) or not model.strip()):
        raise BridgeError("model must be a non-empty string when provided")
    return model


def _one_answer(response: dict[str, Any], question_id: str) -> dict[str, Any]:
    answers = response.get("answers")
    if not isinstance(answers, dict) or question_id not in answers:
        raise BridgeError(f"TypeSafe response is missing answer {question_id!r}")
    return {
        "answer": answers[question_id],
        "model": response.get("model"),
        "usage": response.get("usage"),
        "evaluation": response,
    }


def _run_single(
    client: TypeSafeClient,
    *,
    state: Any,
    question_id: str,
    question: dict[str, Any],
    model: str | None,
) -> dict[str, Any]:
    request: dict[str, Any] = {"state": state, "questions": {question_id: question}}
    if model is not None:
        request["model"] = model
    response = client.evaluate(request)
    return _one_answer(response, question_id)


def _call_evaluate(arguments: Any, client: TypeSafeClient) -> dict[str, Any]:
    args = _require_object(arguments)
    payload = validate_request(args, client.settings)
    return client.evaluate(payload)


def _call_classify(arguments: Any, client: TypeSafeClient) -> dict[str, Any]:
    args = _require_object(arguments)
    _reject_unknown(args, {"state", "instructions", "labels", "model"})
    model = _optional_model(args)
    labels = args.get("labels")
    if not isinstance(labels, dict) or not labels:
        raise BridgeError("labels must be a non-empty object")
    result = _run_single(
        client,
        state=_require_state(args),
        question_id="classification",
        question={"type": "choice", "instructions": _require_structured(args, "instructions"), "criteria": labels},
        model=model,
    )
    return {"type": "classification", **result}


def _call_score(arguments: Any, client: TypeSafeClient) -> dict[str, Any]:
    args = _require_object(arguments)
    _reject_unknown(args, {"state", "instructions", "levels", "model"})
    model = _optional_model(args)
    levels = args.get("levels")
    if not isinstance(levels, list) or not levels:
        raise BridgeError("levels must be a non-empty array")
    result = _run_single(
        client,
        state=_require_state(args),
        question_id="score",
        question={"type": "score", "instructions": _require_structured(args, "instructions"), "criteria": levels},
        model=model,
    )
    return {"type": "score", **result}


def _call_check(arguments: Any, client: TypeSafeClient) -> dict[str, Any]:
    args = _require_object(arguments)
    _reject_unknown(args, {"state", "instructions", "true_criteria", "false_criteria", "model"})
    model = _optional_model(args)
    criteria: dict[str, Any] = {}
    if "true_criteria" in args:
        criteria["true"] = args["true_criteria"]
    if "false_criteria" in args:
        criteria["false"] = args["false_criteria"]
    question: dict[str, Any] = {
        "type": "noul",
        "instructions": _require_structured(args, "instructions"),
    }
    if criteria:
        question["criteria"] = criteria
    result = _run_single(
        client,
        state=_require_state(args),
        question_id="check",
        question=question,
        model=model,
    )
    return {"type": "check", **result}


def _claims_question(
    claim: Any,
    true_criteria: Any,
    false_criteria: Any,
) -> dict[str, Any]:
    question: dict[str, Any] = {
        "type": "noul",
        "instructions": {
            "claim": claim,
            "question": "Does the supplied evidence support this claim?",
        },
    }
    criteria: dict[str, Any] = {}
    if true_criteria is not None:
        criteria["true"] = true_criteria
    if false_criteria is not None:
        criteria["false"] = false_criteria
    if criteria:
        question["criteria"] = criteria
    return question


def _call_verify(arguments: Any, client: TypeSafeClient) -> dict[str, Any]:
    args = _require_object(arguments)
    _reject_unknown(args, {"state", "claims", "true_criteria", "false_criteria", "model"})
    claims = args.get("claims")
    if not isinstance(claims, dict) or not claims:
        raise BridgeError("claims must be a non-empty object")
    true_criteria = args.get("true_criteria")
    false_criteria = args.get("false_criteria")
    questions = {
        claim_id: _claims_question(claim, true_criteria, false_criteria)
        for claim_id, claim in claims.items()
    }
    request: dict[str, Any] = {"state": _require_state(args), "questions": questions}
    model = _optional_model(args)
    if model is not None:
        request["model"] = model
    response = client.evaluate(request)
    return {"type": "verification", "evaluation": response, "answers": response["answers"]}


def _threshold(arguments: dict[str, Any], name: str, default: float) -> float:
    value = arguments.get(name, default)
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 <= value <= 1:
        raise BridgeError(f"{name} must be a number between 0 and 1")
    return float(value)


def _call_gate(arguments: Any, client: TypeSafeClient) -> dict[str, Any]:
    args = _require_object(arguments)
    _reject_unknown(args, {"state", "checks", "pass_at", "review_at", "model"})
    checks = args.get("checks")
    if not isinstance(checks, dict) or not checks:
        raise BridgeError("checks must be a non-empty object")
    pass_at = _threshold(args, "pass_at", 0.85)
    review_at = _threshold(args, "review_at", 0.60)
    if review_at > pass_at:
        raise BridgeError("review_at must not be greater than pass_at")

    questions = {
        check_id: {
            "type": "noul",
            "instructions": {
                "check": check,
                "question": "Does this check pass based on the supplied state?",
            },
        }
        for check_id, check in checks.items()
    }
    request: dict[str, Any] = {"state": _require_state(args), "questions": questions}
    model = _optional_model(args)
    if model is not None:
        request["model"] = model
    response = client.evaluate(request)

    normalized_checks: dict[str, Any] = {}
    decision = "pass"
    for check_id, answer in response["answers"].items():
        probability = answer["noul"]
        if probability < review_at:
            check_decision = "fail"
        elif probability < pass_at:
            check_decision = "review"
        else:
            check_decision = "pass"
        if check_decision == "fail":
            decision = "fail"
        elif check_decision == "review" and decision == "pass":
            decision = "review"
        normalized_checks[check_id] = {
            "decision": check_decision,
            "probability": probability,
        }

    return {
        "type": "gate",
        "decision": decision,
        "policy": {"pass_at": pass_at, "review_at": review_at},
        "checks": normalized_checks,
        "evaluation": response,
    }


def call_tool(name: str, arguments: Any) -> dict[str, Any]:
    """Dispatch one MCP tool call."""

    if name not in TOOL_MAP:
        raise BridgeError(f"unknown tool: {name}")
    client = TypeSafeClient()
    dispatch = {
        "evaluate": _call_evaluate,
        "classify": _call_classify,
        "score": _call_score,
        "check": _call_check,
        "verify": _call_verify,
        "gate": _call_gate,
    }
    return dispatch[name](arguments, client)


def _result(request_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _rpc_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def handle_message(message: dict[str, Any]) -> dict[str, Any] | None:
    """Handle one JSON-RPC request. Return ``None`` for notifications."""

    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
        request_id = message.get("id") if isinstance(message, dict) else None
        return _rpc_error(request_id, -32600, "invalid JSON-RPC request")

    method = message.get("method")
    if not isinstance(method, str):
        return _rpc_error(message.get("id"), -32600, "method must be a string")
    request_id = message.get("id")
    is_notification = "id" not in message
    params = message.get("params", {})
    if params is None:
        params = {}
    if not isinstance(params, dict):
        return None if is_notification else _rpc_error(request_id, -32602, "params must be an object")

    if method in {"notifications/initialized", "notifications/cancelled", "notifications/progress"}:
        return None
    if method == "ping":
        return None if is_notification else _result(request_id, {})
    if method == "shutdown":
        return None if is_notification else _result(request_id, {})
    if method == "initialize":
        requested = params.get("protocolVersion")
        supported = {"2025-06-18", "2025-03-26", "2024-11-05", "2024-10-07"}
        protocol_version = requested if isinstance(requested, str) and requested in supported else "2025-06-18"
        return None if is_notification else _result(
            request_id,
            {
                "protocolVersion": protocol_version,
                "capabilities": {
                    "tools": {"listChanged": False},
                    "resources": {"subscribe": False, "listChanged": False},
                    "prompts": {"listChanged": False},
                },
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                "instructions": SERVER_INSTRUCTIONS,
            },
        )
    if method == "tools/list":
        return None if is_notification else _result(request_id, {"tools": TOOLS})
    if method == "resources/list":
        return None if is_notification else _result(request_id, {"resources": []})
    if method == "prompts/list":
        return None if is_notification else _result(request_id, {"prompts": []})
    if method == "logging/setLevel":
        return None if is_notification else _result(request_id, {})
    if method == "tools/call":
        if is_notification:
            return None
        name = params.get("name")
        if not isinstance(name, str) or name not in TOOL_MAP:
            return _rpc_error(request_id, -32602, "unknown tool")
        try:
            result = call_tool(name, params.get("arguments", {}))
            return _result(
                request_id,
                {
                    "content": [{"type": "text", "text": _json_text(result)}],
                    "structuredContent": result,
                },
            )
        except BridgeError as exc:
            return _result(
                request_id,
                {"isError": True, "content": [{"type": "text", "text": str(exc)}]},
            )

    return None if is_notification else _rpc_error(request_id, -32601, f"method not found: {method}")


def main_stdio() -> int:
    """Run the line-delimited JSON-RPC stdio transport."""

    for raw_line in sys.stdin.buffer:
        if len(raw_line) > MAX_INPUT_LINE_BYTES:
            response = _rpc_error(None, -32600, "input message is too large")
        else:
            line = raw_line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
                if not isinstance(message, dict):
                    raise ValueError("message must be an object")
                response = handle_message(message)
            except (json.JSONDecodeError, ValueError) as exc:
                response = _rpc_error(None, -32700, f"invalid JSON-RPC message: {exc}")
            except Exception:
                # Never print tracebacks to stdout: a single malformed request
                # must not corrupt the MCP stream or reveal local details.
                response = _rpc_error(None, -32603, "internal server error")

        if response is not None:
            try:
                sys.stdout.write(_json_text(response) + "\n")
                sys.stdout.flush()
            except BrokenPipeError:
                return 0
    return 0


__all__ = ["TOOLS", "TOOL_MAP", "call_tool", "handle_message", "main_stdio"]
