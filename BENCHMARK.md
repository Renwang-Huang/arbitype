# Arbitype engineering comparison and verification

This document records the engineering comparison and local verification used
for the 0.7.0 development review. The currently published package remains
0.6.0; no 0.7.0 artifact is implied by this document.
The repositories were inspected through their public source, documentation,
and test layouts on 2026-09-21. GitHub star counts are only a snapshot, not a
quality ranking. This project was also exercised against the real TypeSafe API
with short, controlled Jev requests; the credential was never printed or
committed.

## Professional MCP baselines

| Project | Production practice observed | Decision for Arbitype |
| --- | --- | --- |
| [modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk) | Official Python SDK (24k stars at review time), typed protocol surface, 2026-07-28 plus earlier revisions, stdio/Streamable HTTP/SSE, discovery, and a real `Client` | Keep the runtime dependency-free; implement dual-era STDIO negotiation, precise schemas, and run the official SDK v2 against this server in CI. HTTP remains an explicit gap |
| [PrefectHQ/fastmcp](https://github.com/PrefectHQ/fastmcp) | Mature Python framework (27k stars), server/client/app abstractions, generated schemas, auth/transports, async fixtures, typing and broad tests | Do not introduce a framework dependency for Arbitype's narrow service; adopt its contract-first schemas, bounded async/interoperability tests, and documentation discipline |
| [modelcontextprotocol/inspector](https://github.com/modelcontextprotocol/inspector) | Official web/CLI/TUI inspector (10k stars), composable test servers, smoke tests, packaging guards, and CI quality gates | Keep this repository focused on Jev; add a scriptable official-SDK smoke test that can also be driven by Inspector/MCPJam |
| [MCPJam/inspector](https://github.com/MCPJam/inspector) | Cross-client/model evals, OAuth debugging, traces, conformance checks, and CI regression gates | Arbitype exposes stable tools/output schemas for inspection, but does not pretend to replace cross-client eval or OAuth tooling |
| [snyk/agent-scan](https://github.com/snyk/agent-scan) | Explicit consent before executing discovered STDIO commands, agent config discovery, prompt-injection and secret-risk scanning, signed release artifacts | Treat this adapter as read-only and secret-conscious, but do not claim to be a supply-chain scanner; users should scan untrusted MCP configs separately |

The main trade-off is intentional: the official SDK and FastMCP provide a
broader protocol surface and stronger reusable abstractions, while Arbitype
keeps a zero-runtime-dependency footprint, a small auditable codebase, and a
focused TypeSafe tool contract. That makes it easy to start on a constrained
agent host, but means new MCP protocol features must be tracked and implemented
here instead of inherited from an SDK.

## Capability gap matrix

| Area | Arbitype 0.7.0 development | Professional baseline | Assessment |
| --- | --- | --- | --- |
| MCP protocol | 2026-07-28 modern STDIO metadata plus legacy initialize revisions; `server/discover`; version errors | Official SDK supports the current revision and earlier revisions | Strong for local STDIO; verified with the official SDK v2 |
| Transports | Newline-delimited STDIO only | Official SDK/FastMCP/Inspector support Streamable HTTP and often SSE | Deliberate limitation; remote deployment needs a separate transport layer |
| Server features | Tools only; resources/prompts are not advertised | Frameworks commonly expose tools, resources, prompts, subscriptions, elicitation | Correctly narrow for Jev; do not add unused surface just for parity |
| Schemas | Strict input validation and per-tool output schemas | Generated or typed schemas plus runtime validation | Competitive for this fixed contract |
| Reliability | Bounded retries, `Retry-After`, size limits, redaction, fail-closed provider validation | Mature projects add async cancellation, tracing, and broader fault injection | Good local reliability; cancellation/telemetry remain next steps |
| Testing | 76 offline tests, subprocess lifecycle tests, a 120-case tool-selection dataset, opt-in stability benchmark, and official SDK v2 smoke in CI | Large projects add conformance suites, cross-client evals, coverage gates | Stronger contract/evaluation surface; no synthetic accuracy claim and not a replacement for cross-client evaluation |
| Security | Environment-only secret, read-only annotations, no file/command execution, bounded diagnostics | HTTP servers add OAuth, token audience checks, sandboxing and scanners | Safe for local STDIO; not an authenticated remote service |
| Release engineering | Matrix CI, wheel inspection, clean install, compatibility aliases | Mature projects add signed artifacts, automated publishing, dependency/update gates | Solid foundation; signed releases and registry publishing remain |

## Jev-specific community projects previously reviewed

| Project | What it does well | What we kept out or changed |
| --- | --- | --- |
| [jkudish/jev-mcp](https://github.com/jkudish/jev-mcp) | Purpose-built tools, response validation, mock tests, useful review/gate vocabulary | It has a larger Node dependency tree; Arbitype keeps a smaller standard-library runtime and a raw API escape hatch |
| [itsmostafa/typesafe-mcp](https://github.com/itsmostafa/typesafe-mcp) | Very simple single-tool Go binary, retry and batching ideas, straightforward host setup | Go is not available on every host; Arbitype keeps a Python-only install and adds higher-level tools without hiding the raw request |
| [burnigtm/jev-mcp](https://github.com/burnigtm/jev-mcp) | Strong limits, cancellation, prepared calls, review and coding-loop policies, extensive tests | Its policy layer is intentionally opinionated and broad; Arbitype does not claim to authorize tool calls or spend on another model |
| [Brainwires/jevwire](https://github.com/Brainwires/jevwire) | A deep Claude Code harness, hooks, daemon tests, tripwires, and gate policy | Hooks and a daemon are beyond Arbitype's minimal cross-client service; `gate` here is a pure result transformation, not an interception hook |
| [blakestone-x/jev-mcp](https://github.com/blakestone-x/jev-mcp) | Typed tools, recipes, request budgets, registration scripts, security notes | Its current test run in this environment had 45 failures caused by an SDK/API boundary mismatch; Arbitype validates its own HTTP response contract independently |
| [shaharia-lab/jev-cli](https://github.com/shaharia-lab/jev-cli) | Excellent CLI ergonomics, signed installers, CI-oriented exit codes and schemas | Rust was not installed in this environment; Arbitype provides a smaller Python CLI and package entry point |

## Local results

- Arbitype: 76 offline tests passed, followed by real Jev requests through
  the MCP STDIO process. The live response returned `jev-1.13.0`, all three
  question types, and token usage; response validation accepted it.
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

## Host and protocol verification

- 76 local unit and integration tests pass with no network access and no API key.
- The public tool-selection corpus contains 120 balanced cases (15 per
  advertised decision path). Dataset validation and scoring run offline; no
  accuracy number is reported until a real host/model adapter supplies
  predictions.
- The decision-stability corpus contains 8 fixed live cases. It is opt-in,
  requires `TYPESAFE_API_KEY`, and reports selected-decision consistency,
  probability statistics, latency, and usage without running in CI.
- A real subprocess STDIO handshake was exercised through `initialize`,
  `notifications/initialized`, `tools/list`, `health`, and `shutdown`.
- A modern `server/discover` request and per-request `2026-07-28` metadata path
  were exercised, including `resultType`, cache metadata, and unsupported-version
  errors.
- The official MCP Python SDK v2 connected to the server, negotiated
  `2026-07-28`, listed all 9 tools, and called `health` successfully.
- The initialization instructions are 484 characters, below the 512-character
  self-contained prefix limit used by the Codex integration.
- Codex CLI 0.155.1 can list and inspect the configured `arbitype` STDIO server;
  the server advertises only its actual `tools` capability. The wire contract
  itself is host-neutral and uses standard MCP STDIO messages.
- The wheel was built and installed in an isolated virtual environment, then
  its version, canonical/legacy import identity, and MCP initialization were
  checked.
- The PEP 517 build path was exercised after removing the source-tree import
  assumption from `setup.py`; clean isolated builds no longer depend on the
  checkout being importable.
- The default HTTP attempt timeout is 10 seconds, matching the official
  TypeSafe Python SDK and leaving room for bounded retry behavior under common
  MCP host tool timeouts.
- Live checks remain explicit paid operations; CI continues to use local fakes
  and never receives a provider credential.

## Remaining priorities

1. Add an optional Streamable HTTP deployment package with MCP OAuth discovery;
   keep it separate from the zero-dependency STDIO core.
2. Add Inspector/MCPJam-compatible cross-client smoke fixtures and a small
   non-paid evaluation corpus for tool-selection regressions.
3. Add structured cancellation and tracing if Jev requests become concurrent or
   long-running; the current synchronous STDIO loop intentionally keeps the
   failure surface small.

These are repository smoke-test results, not a quality ranking or a claim that
one project is safer for every deployment.

## Arbitype design decisions

1. Keep `evaluate` close to TypeSafe's official `POST /v1/systemone` contract.
2. Validate before network calls and validate again before returning provider
   data to an agent.
3. Prefer bounded, explicit failure over “best effort” approval.
4. Keep retry behavior transparent and respect `Retry-After`.
5. Never put the API key in MCP arguments, stdout, or normal error details.
6. Make the useful convenience tools deterministic wrappers, not hidden agent
   loops or permission systems.
7. Keep real-provider tests manual and opt-in; never put a paid live call in CI.
