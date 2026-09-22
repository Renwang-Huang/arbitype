# Support routing

Use `route` when an agent must choose one next action from a closed set. The
tool suggests an action; it does not send a message, issue a refund, or modify
the ticket.

Use `input.json` as the `arguments` object in an MCP `tools/call` request
whose tool name is `route`.

The fixture in [output.json](output.json) is illustrative only.
