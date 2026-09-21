# Contributing

Small, reviewable pull requests are welcome.

Before opening a pull request, run:

```bash
python3 -m pip install "ruff>=0.8,<1"
python3 -m ruff check typesafe_mcp typesafe_codex_mcp server.py smoke_test.py scripts tests
python3 -m unittest discover -s tests -v
python3 -m compileall -q .
python3 -m pip wheel --no-deps . --wheel-dir /tmp/typesafe-mcp-dist
```

`typesafe_mcp/` is the canonical implementation package. The
`typesafe_codex_mcp/` directory is a compatibility shim; do not add new
implementation code there.

Do not add API keys, live request payloads, or provider responses containing
private data to fixtures. Prefer local HTTP fakes and deterministic tests. New
tools should preserve the raw `evaluate` escape hatch, document whether their
decision is advisory, and fail closed when a provider response is malformed.
