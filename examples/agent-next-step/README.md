# Agent next step

Use `route` to keep an agent's next step bounded. Arbitype returns the selected
action and probability distribution; the host remains responsible for
approval and execution.

Use `input.json` as the `arguments` object in an MCP `tools/call` request
whose tool name is `route`.

The fixture in [output.json](output.json) is illustrative only.
