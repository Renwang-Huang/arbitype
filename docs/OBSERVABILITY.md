# Decision observability proposal

## Decision for 0.7.0

Arbitype will not add a new `_meta` object to typed tool results in 0.7.0.
The current output contract already carries `model` and `usage` alongside the
decision payload, and `health` exposes local configuration and opt-in live
latency. Adding a second telemetry envelope would duplicate fields and could
make consumers incorrectly treat telemetry as part of the business decision.

The existing fields remain backward compatible:

```json
{
  "type": "classification",
  "answer": {"choice": "billing", "probabilities": {"billing": 0.8}},
  "model": "jev-1.13.0",
  "usage": {"input_tokens": 10, "output_tokens": 2}
}
```

## Future design

If a future release needs a uniform envelope, it should be additive and keep
decision fields separate from telemetry:

```json
{
  "_meta": {
    "provider": "typesafe",
    "model": "jev-1.13.0",
    "latency_ms": 1234,
    "usage": {"input_tokens": 10, "output_tokens": 2}
  }
}
```

Before implementation, define whether latency is client wall-clock time or
provider time, whether usage is complete, and which metadata is safe to expose
to an MCP host. Credentials, request bodies, state, claims, and provider error
details must never enter telemetry.
