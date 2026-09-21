# Contributing

Small, reviewable pull requests are welcome.

Before opening a pull request, run:

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q .
python3 -m pip wheel --no-deps . --wheel-dir /tmp/typesafe-codex-mcp-dist
```

Do not add API keys, live request payloads, or provider responses containing
private data to fixtures. Prefer local HTTP fakes and deterministic tests. New
tools should preserve the raw `evaluate` escape hatch, document whether their
decision is advisory, and fail closed when a provider response is malformed.
