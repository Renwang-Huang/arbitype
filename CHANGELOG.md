# Changelog

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
