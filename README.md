# TypeSafe MCP

![CI](https://github.com/Renwang-Huang/typesafe-mcp/actions/workflows/ci.yml/badge.svg)

Dependency-free, host-neutral STDIO MCP service for [TypeSafe AI](https://typesafe.ai)'s
Jev System One API.

It keeps the API key in the process environment, validates requests and
responses, retries temporary provider failures safely, and exposes typed tools
for agent routing, review signals, and bounded judgments.

> TypeSafe MCP is an independent community project. It is not an official
> TypeSafe AI product or an official integration for any particular agent host.

## Why this bridge

TypeSafe's official interface is an HTTP API. This project provides a local
STDIO MCP adapter that any compatible agent host can start, without third-party
runtime dependencies beyond Python 3.10+ itself.

- No third-party runtime dependencies.
- `evaluate` stays close to the official API: `noul`, `choice`, and `score`.
- `classify`, `score`, and `check` remove repetitive question-map boilerplate.
- `verify` batches claim checks into one request.
- `gate` converts bounded check probabilities into `pass`, `review`, or `fail`.
- `route` selects the next action from a closed set without executing it.
- `review` evaluates a diff, plan, or test report against explicit checks.
- `health` diagnoses local configuration without a network request by default.
- API responses are checked for missing answers, invalid probabilities, unknown
  choices, malformed scores, and inconsistent distributions.
- 408, 429, 500, 502, 503, 504, and 529 receive bounded exponential backoff;
  `Retry-After` is honored.
- Provider error details are bounded and credentials are redacted.
- Request and response size limits protect the MCP process from accidental
  context explosions.

Probabilities and confidence are model signals, not proof. `verify` and
`gate` are deliberately not security boundaries or authorization systems.

## Install

### Run from a checkout

```bash
git clone https://github.com/Renwang-Huang/typesafe-mcp.git
cd typesafe-mcp
export TYPESAFE_API_KEY="your-key"
python3 server.py
```

### Install as a command

```bash
python3 -m pip install .
typesafe-mcp --version
typesafe-mcp doctor --json
```

The package has no runtime dependencies. Once published, an isolated installer
such as `uvx` can run it directly from a pinned Git tag:

```bash
uvx --from 'git+https://github.com/Renwang-Huang/typesafe-mcp@v0.4.0' \
  typesafe-mcp
```

## MCP host configuration

The service uses the standard MCP STDIO transport. Every host has its own
configuration syntax, but the process and environment contract are the same.
For example, a checkout can be registered in a Codex `config.toml` like this:

```toml
[mcp_servers.typesafe]
command = "python3"
args = ["/absolute/path/to/typesafe-mcp/server.py"]
env_vars = ["TYPESAFE_API_KEY"]
startup_timeout_sec = 10
tool_timeout_sec = 60
default_tools_approval_mode = "prompt"
enabled_tools = ["route", "review", "classify", "score", "check", "verify", "gate", "evaluate", "health"]
```

For an installed command:

```toml
[mcp_servers.typesafe]
command = "typesafe-mcp"
env_vars = ["TYPESAFE_API_KEY"]
startup_timeout_sec = 10
tool_timeout_sec = 60
default_tools_approval_mode = "prompt"
```

Keep the key out of host configuration files; `env_vars` asks the host to
forward the environment variable without putting its value in the command
line. The same STDIO process can be registered by Claude, Cursor, VS Code, or
another MCP host using that host's native configuration format.

The old `typesafe-codex-mcp` command and `typesafe_codex_mcp` Python import are
kept as migration aliases. Calls to `codex_route` and `codex_review` are also
accepted, but new configurations should use `route` and `review`.

## Tools

| Tool | Input shape | Output |
| --- | --- | --- |
| `evaluate` | `state` + TypeSafe `questions` map | Raw TypeSafe response |
| `classify` | `state` + `instructions` + `labels` | One Choice answer and distribution |
| `score` | `state` + `instructions` + ordered `levels` | One Score answer and distribution |
| `check` | `state` + yes/no `instructions` | One Noul probability |
| `verify` | `state` + `claims` map | One Noul answer per claim |
| `gate` | `state` + `checks` map + thresholds | `pass`, `review`, or `fail` plus evidence |
| `route` | `state` + `actions` map | Suggested next action; no execution |
| `review` | `state` + `checks` map + thresholds | Review decision and evidence |
| `health` | Optional `live` boolean | Local configuration; live request only when explicit |

Example `classify` call:

```json
{
  "state": "The payment was charged twice.",
  "instructions": "Which team should own this ticket?",
  "labels": {
    "billing": "Payments, invoices, refunds, or duplicate charges",
    "technical": "Bugs, outages, or integration failures",
    "other": "Anything that does not fit the first two labels"
  }
}
```

## CLI and library mode

The MCP process is the default command. The same package can be used in CI:

```bash
typesafe-mcp doctor --json
cat request.json | typesafe-mcp evaluate
typesafe-mcp evaluate --input request.json
```

The Python library is intentionally small:

```python
from typesafe_mcp import TypeSafeClient

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

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `TYPESAFE_API_KEY` | — | Required bearer credential |
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

## Development

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q .
python3 -m pip wheel --no-deps . --wheel-dir /tmp/typesafe-mcp-dist
```

The test suite uses local fakes only; it never needs an API key. A live check
is opt-in and makes one paid request:

```bash
TYPESAFE_API_KEY="your-key" typesafe-mcp doctor --live
```

See [SECURITY.md](SECURITY.md) before using live credentials and
[BENCHMARK.md](BENCHMARK.md) for the comparison against the community
implementations reviewed during development.

## Limitations

Jev is designed for bounded judgments. Use ordinary code for exact math, date
arithmetic, and authorization; use a generative model for prose or code
generation. The bridge sends `state` to TypeSafe, so do not pass secrets or
personal data without checking your data-handling requirements.
