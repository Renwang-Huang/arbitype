# Examples

These examples show the intended boundary between agent reasoning and
Arbitype's typed decision primitives. The outputs are illustrative fixtures,
not live benchmark results or guarantees.

| Scenario | Recommended tool | Why |
| --- | --- | --- |
| [Support routing](support-routing/) | `route` | Choose one next action without executing it. |
| [PR verification](pr-verification/) | `verify` | Check several named claims independently. |
| [Release review](release-review/) | `review` / `gate` | Review a whole release package and threshold bounded checks. |
| [Agent next step](agent-next-step/) | `route` | Return one bounded follow-up action. |

Every directory contains a sample input and a structured sample output.
