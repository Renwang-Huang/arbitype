# Configuration reference

Arbitype reads provider and safety settings from the process environment.
The only required setting is the TypeSafe credential:

~~~bash
export TYPESAFE_API_KEY="your-key"
~~~

Do not put this value in MCP tool arguments or commit it to a host
configuration file. Host setup uses environment forwarding or a password
prompt instead.

## Environment variables

| Variable | Default | Description |
| --- | --- | --- |
| TYPESAFE_API_KEY | none | Required TypeSafe bearer credential. |
| TYPESAFE_BASE_URL | https://api.typesafe.ai | TypeSafe API base URL. |
| TYPESAFE_MODEL | jev-latest | Model alias; retained as a legacy-compatible setting. |
| TYPESAFE_DEFAULT_MODEL | jev-latest | Default model used by the TypeSafe client. |
| TYPESAFE_TIMEOUT_SECONDS | 10 | Timeout for each HTTP attempt. |
| TYPESAFE_MAX_RETRIES | 2 | Retries after the initial request. |
| TYPESAFE_RETRY_BACKOFF_SECONDS | 0.5 | Initial exponential retry backoff. |
| TYPESAFE_MAX_STATE_CHARS | 120000 | Maximum serialized state size. |
| TYPESAFE_MAX_QUESTION_CHARS | 60000 | Maximum serialized question size. |
| TYPESAFE_MAX_REQUEST_BYTES | 512000 | Maximum complete request size. |
| TYPESAFE_MAX_RESPONSE_BYTES | 4194304 | Maximum provider response size. |

Set an explicit model when reproducibility matters:

~~~bash
export TYPESAFE_MODEL="jev-latest"
~~~

The canonical model setting is TYPESAFE_DEFAULT_MODEL. TYPESAFE_MODEL remains
accepted for compatibility with earlier configurations.

## Endpoint and transport rules

The default endpoint is:

~~~text
https://api.typesafe.ai
~~~

Custom endpoints must use HTTPS. Plain HTTP is accepted only for loopback
development endpoints such as localhost, 127.0.0.1, and ::1. Redirects are
not followed for provider requests, so a bearer credential cannot be copied to
a redirect target.

Arbitype validates request limits before sending a paid request and validates
provider responses before returning them to the MCP host.

## Operational guidance

- Keep credentials in the process environment or a host-managed secret
  prompt.
- Do not include the API key in JSON request bodies, tool arguments, issue
  reports, or benchmark reports.
- Use the default endpoint unless a controlled HTTPS endpoint is required.
- Start with local diagnostics:

  ~~~bash
  arbitype doctor --json
  ~~~

- Make a provider request only when live behavior is intended:

  ~~~bash
  TYPESAFE_API_KEY="your-key" arbitype doctor --live
  ~~~

The limits above protect the local adapter and are not a substitute for
provider-side quotas or authorization controls. For the security model, see
[SECURITY.md](../SECURITY.md).
