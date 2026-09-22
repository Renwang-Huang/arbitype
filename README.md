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
</p>

<p>
  <a href="https://registry.modelcontextprotocol.io/?q=io.github.Renwang-Huang%2Farbitype"><img src="https://img.shields.io/badge/MCP%20Registry-listed-2ea44f" alt="Arbitype listed in the MCP Registry"></a>
  <a href="https://glama.ai/mcp/servers/Renwang-Huang/arbitype"><img src="https://img.shields.io/badge/Glama-listed-2ea44f" alt="Arbitype listed on Glama"></a>
</p>

<p>
  <a href="#quick-start">Quick start</a> ·
  <a href="#why-arbitype">Why Arbitype?</a> ·
  <a href="#tools">Tools</a> ·
  <a href="#host-setup">Host setup</a> ·
  <a href="#configuration">Configuration</a> ·
  <a href="https://pypi.org/project/arbitype/">PyPI</a> ·
  <a href="https://registry.modelcontextprotocol.io/?q=io.github.Renwang-Huang%2Farbitype">MCP Registry</a> ·
  <a href="https://glama.ai/mcp/servers/Renwang-Huang/arbitype">Glama</a> ·
  <a href="BENCHMARK.md">Engineering benchmark</a>
</p>

</div>

Arbitype is an MCP-native typed decision layer for AI agents, powered by
[TypeSafe Jev](https://typesafe.ai). It turns probabilistic judgments into
structured decision primitives that an agent or program can consume directly.

> [!NOTE]
> Arbitype is an independent open-source project. It is not an official
> TypeSafe AI product or an official integration for any particular agent host.

<!-- mcp-name: io.github.Renwang-Huang/arbitype -->

## Quick start

The fastest way to connect an MCP host is a local STDIO server launched by
`uvx`:

```bash
export TYPESAFE_API_KEY="your-key"
uvx arbitype
```

The API key stays in the process environment. It is not an MCP argument and
is never printed to standard output.

For a pinned, reproducible launch:

```bash
uvx --from 'arbitype==0.6.0' arbitype
```

Or install the package into the current environment:

```bash
python -m pip install arbitype
arbitype
```

Connect a supported MCP host with a reviewed, repeatable setup plan:

```bash
arbitype setup --detect --dry-run
arbitype setup codex
# non-interactive: arbitype setup codex --yes
```

Use `claude`, `cursor`, or `vscode` instead of `codex` for another host. A
write first prints a unified diff and asks for `[y/N]` confirmation. Use
`--yes` only when applying a reviewed plan non-interactively. The setup command
creates a timestamped backup before editing an existing file, is idempotent,
and never writes the API key. Remove only an entry managed by Arbitype with:

```bash
arbitype setup codex --remove
```

After setup, verify the local process configuration:

```bash
arbitype doctor --json
```

Or run the repository checkout:

```bash
git clone https://github.com/Renwang-Huang/arbitype.git
cd arbitype
export TYPESAFE_API_KEY="your-key"
python3 server.py
```

## Why Arbitype?

Generative models are excellent at prose, code, and open-ended generation.
Agent workflows also need bounded decisions that software can branch on:

```text
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
```

Arbitype provides that decision layer over MCP. It exposes short, host-neutral
primitives for classification, scoring, verification, routing, review, and
fail-closed gate signals. The result is structured data, not a paragraph that
an agent must interpret again.

## Real use cases

Start with one of the small, runnable fixtures:

| Scenario | Tool | What it demonstrates |
| --- | --- | --- |
| [Support routing](examples/support-routing/) | `route` | Choose one next action without executing it. |
| [PR verification](examples/pr-verification/) | `verify` | Check several claims independently. |
| [Release review](examples/release-review/) | `review` / `gate` | Separate holistic review from thresholded checks. |
| [Agent next step](examples/agent-next-step/) | `route` | Keep the next workflow action bounded. |

The example outputs are illustrative fixtures. They are not live model results,
accuracy claims, or authorization decisions.

## Architecture

```mermaid
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
```

The public product is Arbitype; TypeSafe Jev is the current provider. Provider
configuration intentionally keeps the `TYPESAFE_*` names because the
credential and endpoint belong to TypeSafe.

## Tools

Arbitype advertises nine read-only, idempotent MCP tools:

| Tool | Input shape | Output |
| --- | --- | --- |
| `evaluate` | `state` + TypeSafe `questions` map | Raw typed Jev response |
| `classify` | `state` + `instructions` + `labels` | Choice and probability distribution |
| `score` | `state` + `instructions` + ordered `levels` | Weighted score and distribution |
| `check` | `state` + yes/no criteria | Noul (yes/no) probability |
| `verify` | `state` + `claims` map | Noul answer per claim |
| `gate` | `state` + `checks` + thresholds | `pass`, `review`, or `fail` signal |
| `route` | `state` + `actions` map | One suggested next action; no execution |
| `review` | `state` + `checks` + thresholds | Review decision and evidence |
| `health` | Optional `live` boolean | Local configuration; live request only when explicit |

### Tool selection guide

| Need | Use | Avoid confusing it with |
| --- | --- | --- |
| One unordered label | `classify` | `route`, which selects an action |
| One ordered rating | `score` | `classify`, which has no order |
| One bounded proposition | `check` | `verify`, which handles multiple claims |
| Several named claims | `verify` | `review`, which assesses a whole object |
| Checks plus thresholds | `gate` | `review`, which is a holistic assessment |
| One next action | `route` | `classify`, which returns a category |
| Whole diff, plan, release, or report | `review` | `verify`, which answers claim by claim |

Every advertised description also states its `USE WHEN` and `DO NOT USE WHEN`
boundary so an MCP host can select the primitive without relying on hidden
prompt conventions.

For raw Noul questions, provide non-empty `instructions` or at least one
non-empty `true`/`false` criterion. Score levels must be non-null structured
values. These provider-level constraints are validated locally before a paid
request.

Probabilities and confidence are model signals, not proof. `gate` and `review`
are advisory decision transformations, not authorization systems, security
boundaries, or approval engines.

## Host setup

Arbitype uses standard MCP STDIO. For a host that accepts this command-style
configuration:

```toml
[mcp_servers.arbitype]
command = "arbitype"
env_vars = ["TYPESAFE_API_KEY"]
startup_timeout_sec = 10
tool_timeout_sec = 60
default_tools_approval_mode = "prompt"
```

For a checkout:

```toml
[mcp_servers.arbitype]
command = "python3"
args = ["/absolute/path/to/arbitype/server.py"]
env_vars = ["TYPESAFE_API_KEY"]
startup_timeout_sec = 10
tool_timeout_sec = 60
```

Translate the same `command`, arguments, and environment forwarding fields to
the native configuration format of Claude, Cursor, VS Code, Codex, or another
MCP host. Keep the key out of host configuration files whenever possible; use
the host's environment forwarding mechanism.

For supported hosts, the safer automated path is:

```bash
arbitype setup --detect --dry-run  # inspect detected hosts first
arbitype setup claude               # Claude Code user config
arbitype setup cursor               # ~/.cursor/mcp.json
arbitype setup vscode               # VS Code user mcp.json
```

`setup` preserves unknown keys and existing servers, refuses ambiguous
`arbitype` entries, and uses host-native secret references: Codex
`env_vars`, Claude `${TYPESAFE_API_KEY}`, Cursor `${env:TYPESAFE_API_KEY}`, or
a password prompt input in VS Code. It never serializes the value of
`TYPESAFE_API_KEY`.

## CLI and Python

The canonical CLI and package are `arbitype`:

```bash
arbitype --version
arbitype doctor --json
cat request.json | arbitype evaluate
arbitype evaluate --input request.json
```

The Python API is intentionally small:

```python
from arbitype import TypeSafeClient

client = TypeSafeClient()
result = client.evaluate({
    "state": "A payment failed twice.",
    "questions": {
        "urgent": {
            "type": "noul",
            "instructions": "Does this require urgent handling?",
        }
    },
})
```

### Package and import compatibility

The canonical wheel contains the one implementation plus the legacy import
shims. The old PyPI project is not deleted, yanked, or released under a new
identity.

| Surface | Name | Status |
| --- | --- | --- |
| PyPI | `arbitype` | Canonical distribution |
| Python | `arbitype` | Canonical import |
| Python | `typesafe_mcp` | Legacy compatibility shim |
| Python | `typesafe_codex_mcp` | Legacy compatibility shim |

### CLI compatibility

| Command | Status |
| --- | --- |
| `arbitype` | Canonical CLI |
| `typesafe-mcp` | Legacy CLI alias |
| `typesafe-codex-mcp` | Legacy CLI alias |

### Tool compatibility

| Tool | Status |
| --- | --- |
| `route` | Canonical |
| `review` | Canonical |
| `codex_route` | Legacy alias |
| `codex_review` | Legacy alias |

The historical `typesafe-mcp` PyPI project remains intact. A metadata-only
replacement with the same distribution name was tested and rejected because
pip can remove legacy console-script files while replacing the old
distribution. Therefore no `typesafe-mcp==0.6.0` migration package will be
published.

Existing users should use this explicit, safe migration:

```bash
python -m pip uninstall typesafe-mcp
python -m pip install arbitype
```

New installations should use `arbitype` directly. This leaves one
distribution owning the canonical implementation, compatibility shims, and
all three CLI entry points.

## Discovery and Registry

Arbitype `0.6.0` is available through the main discovery surfaces:

| Surface | Canonical entry |
| --- | --- |
| PyPI | [`arbitype`](https://pypi.org/project/arbitype/) |
| MCP Registry | [`io.github.Renwang-Huang/arbitype`](https://registry.modelcontextprotocol.io/?q=io.github.Renwang-Huang%2Farbitype) |
| Glama | [`Renwang-Huang/arbitype`](https://glama.ai/mcp/servers/Renwang-Huang/arbitype) |

The canonical MCP Registry identity is:

```text
io.github.Renwang-Huang/arbitype
```

The package entry used by the Registry is:

```text
uvx arbitype
```

Release ordering and the legacy Registry migration procedure are documented in
[docs/REGISTRY_MIGRATION.md](docs/REGISTRY_MIGRATION.md). The Registry entry
uses PyPI and starts the server with `uvx`, so hosts do not need a repository
checkout.

The former identity `io.github.Renwang-Huang/typesafe-mcp` is a legacy
identity. It must remain available for existing users and should be marked
deprecated through the Registry publisher when that mutation is supported.
New installations should use the Arbitype identity.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `TYPESAFE_API_KEY` | — | Required TypeSafe bearer credential |
| `TYPESAFE_BASE_URL` | `https://api.typesafe.ai` | API base URL |
| `TYPESAFE_MODEL` | `jev-latest` | Model alias; legacy name supported |
| `TYPESAFE_DEFAULT_MODEL` | `jev-latest` | Official SDK-compatible model name |
| `TYPESAFE_TIMEOUT_SECONDS` | `10` | Per HTTP attempt timeout |
| `TYPESAFE_MAX_RETRIES` | `2` | Retries after the initial request |
| `TYPESAFE_RETRY_BACKOFF_SECONDS` | `0.5` | Initial exponential backoff |
| `TYPESAFE_MAX_STATE_CHARS` | `120000` | Serialized state limit |
| `TYPESAFE_MAX_QUESTION_CHARS` | `60000` | Serialized question limit |
| `TYPESAFE_MAX_REQUEST_BYTES` | `512000` | Whole request limit |
| `TYPESAFE_MAX_RESPONSE_BYTES` | `4194304` | Provider response limit |

Custom provider endpoints must use HTTPS. Plain HTTP is accepted only for
loopback hosts such as `localhost`, `127.0.0.1`, and `::1`. Redirects are
disabled so a bearer credential is never forwarded to a redirect target.

## Security boundaries

Arbitype is a local MCP adapter and typed decision layer. It is not:

- a sandbox for untrusted code;
- an authorization or identity system;
- a prompt-injection firewall;
- a security approval boundary; or
- an official TypeSafe AI product.

It does not execute actions suggested by `route`, edit files, run shell
commands, or treat model probabilities as proof. Read [SECURITY.md](SECURITY.md)
before using live credentials.

## Development

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q .
python3 -m pip wheel --no-deps . --wheel-dir /tmp/arbitype-dist
```

The test suite uses local fakes and does not need an API key. The official MCP
Python SDK interoperability smoke test is in
[`scripts/official_sdk_smoke.py`](scripts/official_sdk_smoke.py). A live Jev
check is opt-in and paid:

```bash
TYPESAFE_API_KEY="your-key" arbitype doctor --live
```

See [TESTING.md](TESTING.md), [CONTRIBUTING.md](CONTRIBUTING.md), and
[BENCHMARK.md](BENCHMARK.md) for the full engineering checks and comparison.
Maintainer migration details are in
[`docs/REGISTRY_MIGRATION.md`](docs/REGISTRY_MIGRATION.md).

## Benchmarks

Arbitype keeps two different questions separate:

1. **Tool selection:** can an agent choose `verify` instead of `review`, or
   `route` instead of `classify`? The public 120-case dataset and scoring
   runner are in [`evals/tool_selection/`](evals/tool_selection/). Validate it
   without inventing a score:

   ```bash
   python scripts/run_tool_selection_eval.py --dry-run
   ```

   A real host/model adapter can produce predictions for the runner. Results
   are only meaningful when generated by that adapter and are not committed as
   synthetic benchmark numbers. The repository's opt-in local STDIO + Jev
   adapter can be run with:

   ```bash
   TYPESAFE_API_KEY="your-key" \
     python scripts/run_tool_selection_live.py \
       --output evals/reports/tool-selection-YYYY-MM-DD.json
   ```

   The report records the host, model, date, dataset commit, and scoring
   result, but never the API key or raw provider response.

2. **Decision stability:** repeated Jev calls report selected-decision
   consistency separately from probability mean, standard deviation, range,
   latency, and usage. This benchmark is opt-in and paid:

   ```bash
   TYPESAFE_API_KEY="your-key" \
     python scripts/run_stability_benchmark.py --live --repeats 3
   ```

   It never runs in normal CI. Probabilities may vary even when the selected
   decision remains consistent. Per-case probability statistics are the
   stability metrics; `global_probability_distribution` is only a descriptive
   pooled distribution across cases. The observability boundary for future
   metadata is documented in [`docs/OBSERVABILITY.md`](docs/OBSERVABILITY.md).

## Release identity

Arbitype is currently released as `0.6.0` because it remains Beta while its
canonical public identity moves to the new package, CLI, and Registry name.
The old package history remains intact; the brand migration does not rewrite
Git history or delete the former PyPI project.
