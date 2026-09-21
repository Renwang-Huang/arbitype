# Testing guide

The project is tested as a Codex STDIO MCP service, not only as a collection of
Python functions.

## Local checks

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q .
python3 -m pip wheel --no-deps . --wheel-dir /tmp/typesafe-codex-mcp-dist
make check
```

The test suite uses standard-library fakes and does not need an API key. It
covers request and response validation, credential redaction, retry behavior,
configuration errors, MCP schemas and annotations, Codex initialization,
subprocess STDIO framing, shutdown, tool failures, and clean wheel contents.

The live verification performed during development sent one MCP `evaluate`
request containing Noul, Choice, and Score questions to `jev-latest`. TypeSafe
returned `jev-1.13.0`, calibrated probabilities/confidence, and `usage`; the
bridge accepted the response after its strict contract validation. Live checks
are deliberately excluded from CI because they are paid and require a secret.

## Codex host check

After registering the server, inspect it without making a provider request:

```bash
codex mcp get typesafe
codex mcp list
TYPESAFE_API_KEY=your-key typesafe-codex-mcp doctor --json
```

The live command is opt-in because it makes a paid TypeSafe request:

```bash
TYPESAFE_API_KEY=your-key typesafe-codex-mcp doctor --live
```

Do not put a real key in fixtures, command history, `config.toml`, or issue
reports. Codex should forward it with `env_vars` in the MCP configuration.

## CI

GitHub Actions runs the test and wheel matrix on Python 3.10–3.13 across
Ubuntu, macOS, and Windows, then installs the wheel in a clean Linux virtual
environment and performs an MCP initialization/shutdown smoke test.
