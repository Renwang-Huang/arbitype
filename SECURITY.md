# Security policy

## Scope

This project is a local MCP adapter. It forwards the state and questions
supplied by an agent host to TypeSafe AI's API. It is not a sandbox,
authorization layer, prompt-injection firewall, or substitute for human review.

## API keys

Set `TYPESAFE_API_KEY` in the environment of the MCP process. Do not put it in
tool arguments, source code, shell history, a checked-in host config, or an
issue. The bridge never includes the key in MCP output and redacts it from
provider error details.

## Reporting a vulnerability

Please do not open a public issue for a credential leak or an exploitable
security defect. Contact the repository maintainers privately with a minimal
reproduction and the affected version. Rotate any key used in a reproduction
immediately.
