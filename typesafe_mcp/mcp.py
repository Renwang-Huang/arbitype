"""Dependency-free MCP stdio server and opinionated TypeSafe tools."""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any

from .core import (
    BridgeError,
    ConfigError,
    MAX_INPUT_LINE_BYTES,
    SERVER_NAME,
    SERVER_VERSION,
    Settings,
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
ENTRY_SCHEMA: dict[str, Any] = {
    "anyOf": [
        {"type": "string"},
        {"type": "object"},
        {"type": "array"},
        {"type": "null"},
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
    **ENTRY_SCHEMA,
}
QUESTION_SCHEMA: dict[str, Any] = {
    "oneOf": [
        {
            "type": "object",
            "properties": {
                "type": {"const": "noul"},
                "instructions": ENTRY_SCHEMA,
                "criteria": {
                    "type": "object",
                    "properties": {"true": CRITERION_SCHEMA, "false": CRITERION_SCHEMA},
                    "additionalProperties": False,
                },
            },
            "required": ["type", "instructions"],
            "additionalProperties": False,
        },
        {
            "type": "object",
            "properties": {
                "type": {"const": "choice"},
                "instructions": ENTRY_SCHEMA,
                "criteria": {
                    "type": "object",
                    "minProperties": 1,
                    "maxProperties": 255,
                    "additionalProperties": OPTION_DESCRIPTION_SCHEMA,
                },
            },
            "required": ["type", "instructions", "criteria"],
            "additionalProperties": False,
        },
        {
            "type": "object",
            "properties": {
                "type": {"const": "score"},
                "instructions": ENTRY_SCHEMA,
                "criteria": {"type": "array", "minItems": 2, "maxItems": 10, "items": ENTRY_SCHEMA},
            },
            "required": ["type", "instructions", "criteria"],
            "additionalProperties": False,
        },
    ]
}

SERVER_INSTRUCTIONS = (
    "Host-neutral read-only MCP service for TypeSafe Jev judgments. Use route for the next "
    "action and review for a diff or checklist; use classify/score/check/verify/gate for typed "
    "signals. Tools never edit files, run commands, approve changes, or replace tests/review. "
    "Keep secrets out of state. Probabilities are advisory, not proof or authorization. Use "
    "evaluate for raw noul/choice/score and batch independent questions. Do not use Jev for "
    "code generation, arithmetic, dates, or prose."
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
        "annotations": {
            "title": f"TypeSafe {name.replace('_', ' ').title()}",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
        "outputSchema": {"type": "object"},
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
            "instructions": ENTRY_SCHEMA,
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
            "instructions": ENTRY_SCHEMA,
            "levels": {"type": "array", "minItems": 2, "maxItems": 10, "items": ENTRY_SCHEMA},
            "model": {"type": "string"},
        },
        ["state", "instructions", "levels"],
    ),
    _tool(
        "check",
        "Estimate the probability that a bounded yes/no proposition is true.",
        {
            "state": STRUCTURED_VALUE_SCHEMA,
            "instructions": ENTRY_SCHEMA,
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
            "claims": {"type": "object", "additionalProperties": ENTRY_SCHEMA},
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
            "checks": {"type": "object", "additionalProperties": ENTRY_SCHEMA},
            "pass_at": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.85},
            "review_at": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.60},
            "model": {"type": "string"},
        },
        ["state", "checks"],
    ),
    _tool(
        "route",
        "Choose the next action from a closed set. This suggests an action; it does not execute it.",
        {
            "state": STRUCTURED_VALUE_SCHEMA,
            "instructions": ENTRY_SCHEMA,
            "actions": {
                "type": "object",
                "minProperties": 2,
                "maxProperties": 32,
                "additionalProperties": OPTION_DESCRIPTION_SCHEMA,
            },
            "model": {"type": "string"},
        },
        ["state", "actions"],
    ),
    _tool(
        "review",
        "Evaluate a diff, plan, or test report against checks and return pass/review/fail signals. It never edits files.",
        {
            "state": STRUCTURED_VALUE_SCHEMA,
            "checks": {"type": "object", "minProperties": 1, "additionalProperties": ENTRY_SCHEMA},
            "pass_at": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.85},
            "review_at": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.60},
            "model": {"type": "string"},
        },
        ["state", "checks"],
    ),
    _tool(
        "health",
        "Inspect local MCP configuration without making a network request. Set live=true only for an explicit paid provider check.",
        {
            "live": {"type": "boolean", "default": False},
        },
        [],
    ),
]
TOOL_MAP = {tool["name"]: tool for tool in TOOLS}
# These names were published by versions before the project became
# host-neutral. Keep accepting them for callers that have not migrated yet,
# but do not advertise them in tools/list.
TOOL_ALIASES = {"codex_route": "route", "codex_review": "review"}


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


def _require_structured(arguments: dict[str, Any], name: str, *, allow_null: bool = False) -> Any:
    if name not in arguments:
        raise BridgeError(f"missing required argument: {name}")
    value = arguments[name]
    if not isinstance(value, (str, dict, list)) and not (allow_null and value is None):
        suffix = ", or null" if allow_null else ""
        raise BridgeError(f"{name} must be a string, object, or array{suffix}")
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
        question={
            "type": "choice",
            "instructions": _require_structured(args, "instructions", allow_null=True),
            "criteria": labels,
        },
        model=model,
    )
    return {"type": "classification", **result}


def _call_route(arguments: Any, client: TypeSafeClient) -> dict[str, Any]:
    args = _require_object(arguments)
    _reject_unknown(args, {"state", "instructions", "actions", "model"})
    actions = args.get("actions")
    if not isinstance(actions, dict) or not 2 <= len(actions) <= 32:
        raise BridgeError("actions must be an object with between 2 and 32 options")
    instructions = args.get(
        "instructions",
        "Which next action should the agent take based on the supplied state? Choose only one action.",
    )
    if not _is_structured_argument(instructions, allow_null=True):
        raise BridgeError("instructions must be a string, object, array, or null")
    model = _optional_model(args)
    result = _run_single(
        client,
        state=_require_state(args),
        question_id="next_action",
        question={"type": "choice", "instructions": instructions, "criteria": actions},
        model=model,
    )
    answer = result["answer"]
    return {"type": "route", "route": answer["choice"], **result}


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
        question={
            "type": "score",
            "instructions": _require_structured(args, "instructions", allow_null=True),
            "criteria": levels,
        },
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
        "instructions": _require_structured(args, "instructions", allow_null=True),
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
    for check_id in checks:
        answer = response["answers"][check_id]
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


def _call_review(arguments: Any, client: TypeSafeClient) -> dict[str, Any]:
    result = _call_gate(arguments, client)
    result["type"] = "review"
    return result


def _is_structured_argument(value: Any, *, allow_null: bool = False) -> bool:
    return isinstance(value, (str, dict, list)) or (allow_null and value is None)


def _call_health(arguments: Any) -> dict[str, Any]:
    args = _require_object(arguments)
    _reject_unknown(args, {"live"})
    live = args.get("live", False)
    if not isinstance(live, bool):
        raise BridgeError("live must be a boolean")

    checks: dict[str, Any] = {
        "type": "health",
        "server": SERVER_NAME,
        "version": SERVER_VERSION,
        "api_key_configured": bool(os.getenv("TYPESAFE_API_KEY", "").strip()),
        "live": False,
    }
    try:
        settings = Settings.from_env(require_key=False)
    except ConfigError as exc:
        checks.update({"status": "configuration_error", "message": str(exc)})
        return checks

    checks.update(
        {
            "status": "ok" if checks["api_key_configured"] else "missing_api_key",
            "base_url": settings.base_url,
            "model": settings.model,
            "timeout_seconds": settings.timeout_seconds,
            "max_retries": settings.max_retries,
        }
    )
    if not live:
        return checks
    if not checks["api_key_configured"]:
        return checks

    started = time.monotonic()
    TypeSafeClient(settings).evaluate(
        {
            "state": "MCP health check",
            "questions": {
                "ready": {"type": "noul", "instructions": "Is this health check request ready?"}
            },
        }
    )
    checks.update({"live": True, "latency_ms": round((time.monotonic() - started) * 1000, 1)})
    return checks


def call_tool(name: str, arguments: Any) -> dict[str, Any]:
    """Dispatch one MCP tool call."""

    canonical_name = TOOL_ALIASES.get(name, name)
    if canonical_name not in TOOL_MAP:
        raise BridgeError(f"unknown tool: {name}")
    if canonical_name == "health":
        return _call_health(arguments)
    client = TypeSafeClient()
    dispatch = {
        "evaluate": _call_evaluate,
        "classify": _call_classify,
        "score": _call_score,
        "check": _call_check,
        "verify": _call_verify,
        "gate": _call_gate,
        "route": _call_route,
        "review": _call_review,
    }
    return dispatch[canonical_name](arguments, client)


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
                "capabilities": {"tools": {"listChanged": False}},
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
        if not isinstance(name, str) or (name not in TOOL_MAP and name not in TOOL_ALIASES):
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
        except Exception:
            return _result(
                request_id,
                {
                    "isError": True,
                    "content": [{"type": "text", "text": "internal tool error"}],
                },
            )

    return None if is_notification else _rpc_error(request_id, -32601, f"method not found: {method}")


def main_stdio() -> int:
    """Run the line-delimited JSON-RPC stdio transport."""

    for raw_line in sys.stdin.buffer:
        message: dict[str, Any] | None = None
        should_exit = False
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
                # MCP replies to ``shutdown`` first; the client then sends the
                # ``exit`` notification. Exit only after that notification so
                # the lifecycle remains compatible with strict clients.
                should_exit = message.get("method") == "exit"
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
        if should_exit:
            return 0
    return 0


__all__ = [
    "SERVER_INSTRUCTIONS",
    "TOOLS",
    "TOOL_MAP",
    "TOOL_ALIASES",
    "call_tool",
    "handle_message",
    "main_stdio",
]
