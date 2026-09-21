# Arbitype security policy

## Scope

Arbitype is a local MCP adapter and typed decision layer. It forwards the
state and questions supplied by an agent host to TypeSafe AI's API. It is not a sandbox,
authorization layer, prompt-injection firewall, or substitute for human review.

## API keys

Set `TYPESAFE_API_KEY` in the environment of the Arbitype MCP process. Do not put it in
tool arguments, source code, shell history, a checked-in host config, or an
issue. Arbitype never includes the key in MCP output and redacts it from
provider error details.

## Custom endpoints

`TYPESAFE_BASE_URL` must use HTTPS. Plain HTTP is accepted only for loopback
hosts (`localhost`, `127.0.0.1`, or `::1`) so local test doubles can be used
without allowing the bearer credential to cross an unencrypted network.

The STDIO reader bounds each input frame before parsing it, rejects invalid
UTF-8 as a protocol parse error, and validates tool arguments against the
schemas advertised through `tools/list` before creating a provider request.
Provider redirects are disabled; a redirect response is treated as an error
and no bearer-authenticated request is sent to its `Location` target.

## Reporting a vulnerability

Please do not open a public issue for a credential leak or an exploitable
security defect. Contact the repository maintainers privately with a minimal
reproduction and the affected version. Rotate any key used in a reproduction
immediately.
