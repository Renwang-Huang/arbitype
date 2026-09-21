# Changelog

## 0.6.0 — 2026-09-22

### Renamed to Arbitype

The project formerly known as TypeSafe MCP is now Arbitype. Arbitype is
positioned as a typed decision layer for AI agents rather than a
TypeSafe-specific MCP bridge.

Canonical identities:

- GitHub: `Renwang-Huang/arbitype`
- PyPI: `arbitype`
- CLI: `arbitype`
- Python: `arbitype`
- MCP Registry: `io.github.Renwang-Huang/arbitype`

Legacy names remain available as compatibility aliases where practical. The
former `typesafe-mcp` PyPI project and Registry identity are not deleted or
overwritten by this source migration.

- Moved the implementation to the canonical `arbitype` package and retained
  module-level identity shims for `typesafe_mcp` and `typesafe_codex_mcp`.
- Added the `arbitype` CLI and PyPI metadata while retaining both legacy CLI
  aliases.
- Updated MCP Registry, README, CI, release, and ecosystem-check metadata to
  the Arbitype identity.

## 0.5.3 — 2026-09-22

- Bound STDIO frame reads to 16 MiB and discard oversized lines without
  allocating the complete input; invalid UTF-8 now returns JSON-RPC parse
  error `-32700` without terminating the server.
- Enforced modern per-request MCP metadata, integer-only JSON-RPC request IDs,
  and invalid explicit `params: null` handling while retaining legacy
  handshake compatibility.
- Added runtime validation for every advertised tool input and restricted
  custom HTTP API endpoints to loopback hosts; remote endpoints must use
  HTTPS.
- Added provider-semantic preflight checks for Noul content and non-null Score
  levels, preventing known TypeSafe 400/422 responses after a paid request.
- Disabled automatic HTTP redirects so bearer credentials are never forwarded
  to a redirect target.
- Converted deeply nested or otherwise invalid JSON input into JSON-RPC parse
  error `-32700` without terminating the STDIO server.

## 0.5.2 — 2026-09-21

- Published the `typesafe-mcp` distribution to PyPI for direct `uvx` installs.
- Added official MCP Registry metadata and PyPI ownership verification.

## 0.5.1 — 2026-09-21

- Made the canonical-versus-legacy package layout explicit in the README and
  compatibility module docstrings; `typesafe_mcp` remains the only
  implementation package.
- Centralized the package version and strengthened the official SDK smoke test
  so it checks all 9 advertised tools, including `score`.
- Fixed isolated PEP 517 wheel builds so packaging does not import the source
  package before it has been installed.

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
