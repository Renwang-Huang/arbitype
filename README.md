# TypeSafe Codex MCP

![CI](https://github.com/Renwang-Huang/typesafe-codex-mcp/actions/workflows/ci.yml/badge.svg)

Dependency-free, Codex-first STDIO MCP service for [TypeSafe AI](https://typesafe.ai)'s
Jev System One API.

It keeps the API key in the process environment, validates requests and
responses, retries temporary provider failures safely, and exposes typed tools
for Codex routing, review signals, and bounded judgments.

> TypeSafe Codex MCP is an independent community project. It is not an
> official TypeSafe AI or OpenAI product.

## Why this bridge

TypeSafe's official interface is an HTTP API. This project provides the local
STDIO MCP adapter that Codex can start, without third-party runtime dependencies
beyond Python 3.10+ itself.

- No third-party runtime dependencies.
- `evaluate` stays close to the official API: `noul`, `choice`, and `score`.
- `classify`, `score`, and `check` remove repetitive question-map boilerplate.
- `verify` batches claim checks into one request.
- `gate` converts bounded check probabilities into `pass`, `review`, or `fail`.
- `codex_route` selects the next action from a closed set without executing it.
- `codex_review` evaluates a diff, plan, or test report against explicit checks.
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
git clone https://github.com/Renwang-Huang/typesafe-codex-mcp.git
cd typesafe-codex-mcp
export TYPESAFE_API_KEY="your-key"
python3 server.py
```

### Install as a command

```bash
python3 -m pip install .
typesafe-codex-mcp --version
typesafe-codex-mcp doctor --json
```

The package has no runtime dependencies. Once published, an isolated installer
such as `uvx` can run it directly from a pinned Git tag:

```bash
uvx --from 'git+https://github.com/Renwang-Huang/typesafe-codex-mcp@v0.3.0' \
  typesafe-codex-mcp
```

## Codex configuration

For a checkout, add this to `~/.codex/config.toml`:

```toml
[mcp_servers.typesafe]
command = "python3"
args = ["/absolute/path/to/typesafe-codex-mcp/server.py"]
env_vars = ["TYPESAFE_API_KEY"]
startup_timeout_sec = 10
tool_timeout_sec = 60
default_tools_approval_mode = "prompt"
enabled_tools = ["codex_route", "codex_review", "classify", "score", "check", "verify", "gate", "evaluate", "health"]
```

For an installed command:

```toml
[mcp_servers.typesafe]
command = "typesafe-codex-mcp"
env_vars = ["TYPESAFE_API_KEY"]
startup_timeout_sec = 10
tool_timeout_sec = 60
default_tools_approval_mode = "prompt"
```

Keep the key out of `config.toml`; `env_vars` asks Codex to forward the
environment variable without putting its value in the MCP command line.

## Tools

| Tool | Input shape | Output |
| --- | --- | --- |
| `evaluate` | `state` + TypeSafe `questions` map | Raw TypeSafe response |
| `classify` | `state` + `instructions` + `labels` | One Choice answer and distribution |
| `score` | `state` + `instructions` + ordered `levels` | One Score answer and distribution |
| `check` | `state` + yes/no `instructions` | One Noul probability |
| `verify` | `state` + `claims` map | One Noul answer per claim |
| `gate` | `state` + `checks` map + thresholds | `pass`, `review`, or `fail` plus evidence |
| `codex_route` | `state` + `actions` map | Suggested next Codex action; no execution |
| `codex_review` | `state` + `checks` map + thresholds | Codex-oriented review decision and evidence |
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
typesafe-codex-mcp doctor --json
cat request.json | typesafe-codex-mcp evaluate
typesafe-codex-mcp evaluate --input request.json
```

The Python library is intentionally small:

```python
from typesafe_codex_mcp import TypeSafeClient

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
python3 -m pip wheel --no-deps . --wheel-dir /tmp/typesafe-codex-mcp-dist
```

The test suite uses local fakes only; it never needs an API key. A live check
is opt-in and makes one paid request:

```bash
TYPESAFE_API_KEY="your-key" typesafe-codex-mcp doctor --live
```

See [SECURITY.md](SECURITY.md) before using live credentials and
[BENCHMARK.md](BENCHMARK.md) for the comparison against the community
implementations reviewed during development.

## Limitations

Jev is designed for bounded judgments. Use ordinary code for exact math, date
arithmetic, and authorization; use a generative model for prose or code
generation. The bridge sends `state` to TypeSafe, so do not pass secrets or
personal data without checking your data-handling requirements.
