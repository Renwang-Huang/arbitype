# Community comparison and release notes

This document records the engineering comparison and local verification used
for the 0.3.0 release.
The repositories were cloned into a temporary directory and tested without a
live API key on 2026-09-21. A live TypeSafe request was intentionally not run
with the previously exposed credential.

## Repositories tested

| Project | What it does well | What we kept out or changed |
| --- | --- | --- |
| [jkudish/jev-mcp](https://github.com/jkudish/jev-mcp) | Purpose-built tools, response validation, mock tests, useful review/gate vocabulary | It has a larger Node dependency tree; this project keeps a smaller standard-library runtime and a raw API escape hatch |
| [itsmostafa/typesafe-mcp](https://github.com/itsmostafa/typesafe-mcp) | Very simple single-tool Go binary, retry and batching ideas, Codex setup | Go is not available on every Codex host; this project keeps a Python-only install and adds higher-level tools without hiding the raw request |
| [burnigtm/jev-mcp](https://github.com/burnigtm/jev-mcp) | Strong limits, cancellation, prepared calls, review and coding-loop policies, extensive tests | Its policy layer is intentionally opinionated and broad; this project does not claim to authorize tool calls or spend on another model |
| [Brainwires/jevwire](https://github.com/Brainwires/jevwire) | A deep Claude Code harness, hooks, daemon tests, tripwires, and gate policy | Hooks and a daemon are beyond a minimal cross-client bridge; `gate` here is a pure result transformation, not an interception hook |
| [blakestone-x/jev-mcp](https://github.com/blakestone-x/jev-mcp) | Typed tools, recipes, request budgets, registration scripts, security notes | Its current test run in this environment had 45 failures caused by an SDK/API boundary mismatch; this project validates its own HTTP response contract independently |
| [shaharia-lab/jev-cli](https://github.com/shaharia-lab/jev-cli) | Excellent CLI ergonomics, signed installers, CI-oriented exit codes and schemas | Rust was not installed in this environment; this project provides a smaller Python CLI and package entry point |

## Local results

- This project: 15 tests passed with no network access and no credentials.
- `@jkudish/jev-mcp`: build and unit/mock suite passed (the repository's
  live end-to-end test was not run).
- `burnigtm/jev-mcp`: build and its test runner passed: 141 tests, 139 passed,
  2 skipped.
- `jevwire`: build and full Vitest suite passed: 1,461 tests.
- `blakestone-x/jev-mcp`: packaging completed, but its test suite reported
  45 failures, 29 passes, and 4 skips in this environment. The failures
  clustered around the installed `typesafe-sdk` response/error boundary and
  stdio fixtures; they are recorded here rather than silently calling it a
  pass.
- Go and Rust projects could be inspected but not compiled because this host
  does not have `go` or `cargo` installed.

## Codex-focused verification

- 38 local unit and integration tests pass with no network access and no API key.
- A real subprocess STDIO handshake was exercised through `initialize`,
  `notifications/initialized`, `tools/list`, `health`, and `shutdown`.
- The initialization instructions are 501 characters, below Codex's documented
  512-character self-contained prefix guidance.
- Codex CLI 0.155.1 can list and inspect the configured `typesafe` STDIO server;
  the server advertises only its actual `tools` capability.
- The wheel was built and installed in an isolated virtual environment, then
  its version and MCP initialization were checked.
- No live provider request was made during this verification; `health --live`
  and `doctor --live` remain explicit paid checks.

These are repository smoke-test results, not a quality ranking or a claim that
one project is safer for every deployment.

## Design decisions for this project

1. Keep `evaluate` close to TypeSafe's official `POST /v1/systemone` contract.
2. Validate before network calls and validate again before returning provider
   data to an agent.
3. Prefer bounded, explicit failure over “best effort” approval.
4. Keep retry behavior transparent and respect `Retry-After`.
5. Never put the API key in MCP arguments, stdout, or normal error details.
6. Make the useful convenience tools deterministic wrappers, not hidden agent
   loops or permission systems.
