# Pull-request verification

Use `verify` when the agent has multiple named claims and needs one signal per
claim. Use `review` instead when the question is about the overall quality or
risk of the pull request.

Use `input.json` as the `arguments` object in an MCP `tools/call` request
whose tool name is `verify`.

The fixture in [output.json](output.json) is illustrative only. Probabilities
are model signals, not proof that a claim is true.
