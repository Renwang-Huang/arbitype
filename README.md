<div align="center">

# Arbitype

<p><strong>Typed decision tools for AI agents.</strong></p>

<p>Classify · Score · Verify · Gate · Route · Review</p>

<p><strong>MCP-native · Powered by TypeSafe Jev</strong></p>

<p>
  <a href="https://github.com/Renwang-Huang/arbitype/actions/workflows/ci.yml"><img src="https://github.com/Renwang-Huang/arbitype/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/Renwang-Huang/arbitype/releases"><img src="https://img.shields.io/github/v/release/Renwang-Huang/arbitype?display_name=tag&sort=semver" alt="Latest release"></a>
  <a href="https://pypi.org/project/arbitype/"><img src="https://img.shields.io/pypi/v/arbitype?logo=pypi&logoColor=white" alt="Arbitype on PyPI"></a>
  <a href="https://github.com/Renwang-Huang/arbitype/blob/main/LICENSE"><img src="https://img.shields.io/github/license/Renwang-Huang/arbitype" alt="MIT license"></a>
  <img src="https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python 3.10 or newer">
  <a href="https://github.com/modelcontextprotocol/modelcontextprotocol/tree/main/docs/specification/2026-07-28"><img src="https://img.shields.io/badge/MCP-2026--07--28-6F42C1" alt="MCP 2026-07-28"></a>
  <a href="https://registry.modelcontextprotocol.io/?q=io.github.Renwang-Huang%2Farbitype"><img src="https://img.shields.io/badge/MCP%20Registry-listed-2ea44f" alt="Arbitype listed in the MCP Registry"></a>
</p>

<p>
  <a href="#quick-start">Quick start</a> ·
  <a href="#why-arbitype">Why Arbitype?</a> ·
  <a href="#tools">Tools</a> ·
  <a href="#benchmark-snapshot">Benchmarks</a> ·
  <a href="#documentation">Documentation</a>
</p>

</div>

## What is Arbitype?

Arbitype is an MCP-native typed decision layer for AI agents, powered by
[TypeSafe Jev](https://typesafe.ai). It turns probabilistic judgments into
structured decision primitives that an agent or program can consume directly.

Arbitype 0.7.0 is released on PyPI and the official MCP Registry.

> [!NOTE]
> Arbitype is an independent open-source project. It is not an official
> TypeSafe AI product or an official integration for any particular agent host.

<!-- mcp-name: io.github.Renwang-Huang/arbitype -->

## Quick Start

The fastest way to connect an MCP host is a local STDIO server launched by
uvx:

~~~bash
export TYPESAFE_API_KEY="your-key"
uvx arbitype
~~~

For a pinned, reproducible launch:

~~~bash
uvx --from 'arbitype==0.7.0' arbitype
~~~

Or install the package into the current environment:

~~~bash
python -m pip install arbitype
arbitype
~~~

The API key stays in the process environment. It is not an MCP argument and
is never printed to standard output.

### Host setup

Inspect detected hosts before writing anything:

~~~bash
arbitype setup --detect --dry-run
~~~

Then apply a reviewed plan:

~~~bash
arbitype setup codex
arbitype doctor --json
~~~

The setup flow is plan → unified diff → confirmation → backup → apply.
Use claude, cursor, or vscode in place of codex. Detailed host formats,
secret forwarding, --yes, --remove, ownership, and non-interactive behavior
are documented in [docs/HOST_SETUP.md](docs/HOST_SETUP.md).

### Configuration

At minimum, set TYPESAFE_API_KEY. To select a model explicitly:

~~~bash
export TYPESAFE_API_KEY="your-key"
export TYPESAFE_MODEL="jev-latest"
~~~

See the [full configuration reference](docs/CONFIGURATION.md) for endpoints,
timeouts, retries, and request/response limits.

### Compatibility

arbitype is the canonical distribution, Python package, and CLI. Existing
TypeSafe MCP users should migrate to Arbitype; see
[docs/REGISTRY_MIGRATION.md](docs/REGISTRY_MIGRATION.md).

For the safe migration from the historical distribution:

~~~bash
python -m pip uninstall typesafe-mcp
python -m pip install arbitype
~~~

| Surface | Canonical | Legacy compatibility |
| --- | --- | --- |
| PyPI / CLI | arbitype | typesafe-mcp, typesafe-codex-mcp |
| Python imports | arbitype | typesafe_mcp, typesafe_codex_mcp |
| MCP tools | route, review | codex_route, codex_review |

## Why Arbitype?

Arbitype is designed around contracts and bounded decisions rather than
free-form prose:

| Principle | What it means |
| --- | --- |
| **Contract-first** | Requests and provider responses are validated before they reach the agent. |
| **Safe by default** | Credentials stay out of MCP tool arguments and generated host configuration. |
| **Agent-oriented** | Purpose-built classify, verify, gate, route, review, and score primitives. |
| **Portable** | Zero third-party runtime dependencies and standard MCP STDIO. |
| **Measured** | Public tool-selection and decision-stability evaluation assets. |

The decision flow is:

~~~text
free-form state
      ↓
  TypeSafe Jev
      ↓
probabilistic judgment
      ↓
    Arbitype
      ↓
typed decision + probability
      ↓
agent / code branch
~~~

## Real Use Cases

Start with one of the small, runnable fixtures:

| Scenario | Tool | What it demonstrates |
| --- | --- | --- |
| [Support routing](examples/support-routing/) | route | Choose one next action without executing it. |
| [PR verification](examples/pr-verification/) | verify | Check several claims independently. |
| [Release review](examples/release-review/) | review / gate | Separate holistic review from thresholded checks. |
| [Agent next step](examples/agent-next-step/) | route | Keep the next workflow action bounded. |

The example outputs are illustrative fixtures. They are not live model results,
accuracy claims, or authorization decisions.

## Tools

Arbitype advertises nine read-only, idempotent MCP tools:

| Tool | Use when | Result |
| --- | --- | --- |
| evaluate | You need a custom typed Jev question set. | Raw typed Jev response. |
| classify | You need one choice from unordered labels. | Choice and probability distribution. |
| score | You need one ordered rating or level. | Weighted score and distribution. |
| check | You need a probability for one bounded criterion. | Noul yes/no probability. |
| verify | You need several named claims checked independently. | Noul answer per claim. |
| gate | You need checks and thresholds transformed into a signal. | pass, review, or fail. |
| route | You need one suggested next action. | One action; no action execution. |
| review | You need a holistic quality or risk assessment. | Review decision and evidence. |
| health | You need local diagnostics or an explicit live check. | Configuration and optional provider health. |

### Tool Selection Guide

| Need | Use | Do not substitute |
| --- | --- | --- |
| One unordered label | classify | route, which selects an action |
| One ordered rating | score | classify, which has no order |
| One bounded proposition | check | verify, which handles multiple claims |
| Several named claims | verify | review, which assesses a whole object |
| Checks plus thresholds | gate | review, which is holistic |
| One next action | route | classify, which returns a category |
| Whole diff, plan, release, or report | review | verify, which answers claim by claim |

Tool descriptions also state USE WHEN and DO NOT USE WHEN boundaries so hosts
can select a primitive without hidden prompt conventions.

Probabilities and confidence are model signals, not proof. gate and review
are advisory decision transformations, not authorization systems, security
boundaries, or approval engines.

## Architecture

~~~mermaid
flowchart LR
    host["AI Agent / MCP Host<br/>Codex · Claude · Cursor · VS Code"]
    arbitype["Arbitype<br/>Typed decision tools"]
    jev["TypeSafe Jev<br/>System One Model"]
    env["TYPESAFE_API_KEY<br/>process environment"]

    host -->|MCP| arbitype
    arbitype -->|validated HTTPS| jev
    jev -->|typed probabilistic judgment| arbitype
    arbitype -->|structured decision| host
    env -. credential .-> arbitype
~~~

The public product is Arbitype; TypeSafe Jev is the current provider. Provider
configuration intentionally keeps the TYPESAFE_* names because the credential
and endpoint belong to TypeSafe.

## Benchmark Snapshot

Recorded on the public 120-case Jev-mediated tool-selection evaluation:

| Metric | Result |
| --- | ---: |
| Tool-selection accuracy | **96.67%** |
| Invalid-tool rate | **0%** |
| Schema-valid rate | **100%** |

This is a Jev-mediated evaluation over Arbitype's advertised MCP tool catalog.
It is not a Codex, Claude, or Cursor host benchmark and is not a general
model-performance guarantee.

Details and reproducible assets:

- [Benchmark methodology](BENCHMARK.md)
- [Tool-selection dataset](evals/tool_selection/)
- [Recorded reports](evals/reports/)

## Security Boundaries

Arbitype is a local MCP adapter and typed decision layer. It is not:

- a sandbox for untrusted code;
- an authorization or identity system;
- a prompt-injection firewall;
- a security approval boundary; or
- an official TypeSafe AI product.

It does not execute actions suggested by route, edit files, run shell
commands, or treat model probabilities as proof. Read [SECURITY.md](SECURITY.md)
before using live credentials.

## Documentation

- [Host setup](docs/HOST_SETUP.md)
- [Configuration reference](docs/CONFIGURATION.md)
- [MCP Registry migration](docs/REGISTRY_MIGRATION.md)
- [Supply-chain posture](docs/SUPPLY_CHAIN.md)
- [Observability proposal](docs/OBSERVABILITY.md)
- [Testing](TESTING.md)
- [Benchmarks](BENCHMARK.md)
- [Contributing](CONTRIBUTING.md)
- [Security](SECURITY.md)
- [Official MCP Registry entry](https://registry.modelcontextprotocol.io/?q=io.github.Renwang-Huang%2Farbitype)
- [Glama listing](https://glama.ai/mcp/servers/Renwang-Huang/arbitype) (indexing and metadata refresh may lag publication)

## Development

The test suite uses local fakes and does not need an API key:

~~~bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q .
make check
make release-check
~~~

The official MCP Python SDK interoperability smoke test is in
[scripts/official_sdk_smoke.py](scripts/official_sdk_smoke.py). A live Jev
check is opt-in and paid:

~~~bash
TYPESAFE_API_KEY="your-key" arbitype doctor --live
~~~

Normal CI does not call the provider or run paid benchmarks.
