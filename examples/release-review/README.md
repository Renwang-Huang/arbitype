# Release review and gate

Use `review` for a holistic assessment of a release candidate. Use `gate` when
the agent already has bounded checks that must be converted into a
pass/review/fail signal. Neither tool is an authorization system.

Use `input.json` as the `arguments` object in an MCP `tools/call` request
whose tool name is `review` (or adapt the checks for `gate`).

The fixture in [output.json](output.json) is illustrative only.
