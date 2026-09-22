# Tool-selection evaluation

This dataset measures whether an agent chooses the right Arbitype primitive
before it sends a tool call. It is deliberately separate from model quality:
the cases test tool boundaries, not whether TypeSafe Jev answers the case
correctly.

`cases.jsonl` contains 120 hand-written cases covering the eight callable
decision paths (`evaluate`, `classify`, `score`, `check`, `verify`, `gate`,
`route`, and `review`). The set intentionally includes near-confusions such as
`check` vs `verify`, `verify` vs `review`, `gate` vs `review`, and `route` vs
`classify`.

## Case contract

Each line contains:

```json
{
  "id": "verify-001",
  "prompt": "Verify the claims in this evidence.",
  "expected_tool": "verify",
  "acceptable_tools": ["verify"],
  "reason": "The task asks for one result per named claim."
}
```

`acceptable_tools` allows a future case to document a genuinely equivalent
choice without changing the expected tool used for per-tool reporting.

## Validate without running a model

```bash
python scripts/run_tool_selection_eval.py --dry-run
```

This only validates the dataset and prints its case counts. It does not invent
an accuracy number.

## Score an adapter

An adapter can emit one JSON object per case:

```json
{"id":"verify-001","selected_tool":"verify","schema_valid":true}
```

Then run:

```bash
python scripts/run_tool_selection_eval.py \
  --predictions /path/to/predictions.jsonl
```

For a live host or model adapter, the runner can invoke a command once per
case. The command receives `{"id", "prompt"}` on stdin and must return one
prediction object on stdout:

```bash
python scripts/run_tool_selection_eval.py \
  --command 'python /path/to/adapter.py'
```

The report includes:

- tool-selection accuracy using `acceptable_tools`;
- per-tool accuracy;
- an expected-tool × selected-tool confusion matrix;
- invalid tool-call rate; and
- schema-valid-call rate, based on the adapter's explicit `schema_valid` flag.

No live adapter is part of normal CI. Store real prediction files outside the
repository when they contain private prompts or provider output.

## Reproducible local host + Jev run

The repository includes an opt-in adapter that starts the checked-out Arbitype
STDIO server, reads its real `tools/list` catalog, and uses TypeSafe Jev for
each selection:

```bash
TYPESAFE_API_KEY="..." \
  python scripts/run_tool_selection_live.py \
    --output evals/reports/tool-selection-YYYY-MM-DD.json
```

The report records the host, protocol, resolved model, dataset commit, UTC
timestamp, and aggregate scores. It does not record the API key or raw model
responses. Because the dataset contains prompts but not generated arguments,
`schema_valid_call_rate` checks deterministic fixture arguments against the
actual `tools/list` input schemas; it is not a claim about model-generated
argument quality.
