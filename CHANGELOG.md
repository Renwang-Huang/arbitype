# Changelog

## 0.5.0 — 2026-09-21

- Added MCP 2026-07-28 STDIO discovery and per-request metadata support while
  retaining the legacy initialize handshake.
- Added protocol version negotiation errors, modern `resultType` responses, and
  cache metadata for list operations.
- Replaced generic tool output objects with precise output schemas.
- Added malformed JSON-RPC/id boundary tests and an official MCP Python SDK v2
  interoperability smoke test in CI.

## 0.4.0 — 2026-09-21

- Rebranded the public project as TypeSafe MCP and renamed the distribution and
  primary CLI to `typesafe-mcp`.
- Added the neutral `typesafe_mcp` import path and retained the old package and
  command as compatibility aliases.
- Renamed the advertised `route` and `review` tools so the protocol contract is
  not tied to one agent host; the old `codex_route` and `codex_review` calls are
  accepted as migration aliases.
- Reworked the documentation and host guidance for Codex, Claude, Cursor, VS
  Code, and other MCP-capable clients without adding host-specific runtime code.

## 0.3.0 — 2026-09-21

- Narrowed the product contract to a Codex-first stdio MCP service.
- Added Codex-oriented `codex_route`, `codex_review`, and non-network `health` tools.
- Added read-only/idempotent MCP tool annotations and a Codex-focused initialization guide.
- Removed unsupported resource and prompt capabilities and implemented the MCP shutdown/exit lifecycle.
- Added safer handling for unexpected tool failures.
- Aligned request/response validation with the official API, including structured null entries,
  required model/usage fields, probability-weighted Score validation, and a 10-second default timeout.

## 0.2.0 — 2026-09-21

- Added a reusable standard-library TypeSafe client with bounded retries,
  `Retry-After` support, response validation, request limits, and redacted
  diagnostics.
- Added `classify`, `score`, `check`, `verify`, and deterministic `gate` MCP
  tools while keeping the raw `evaluate` tool compatible.
- Added a package entry point, `doctor`, standalone JSON evaluation mode, CI,
  release metadata, and an expanded test suite.

## 0.1.0

- Initial dependency-free stdio MCP bridge exposing `evaluate`.
