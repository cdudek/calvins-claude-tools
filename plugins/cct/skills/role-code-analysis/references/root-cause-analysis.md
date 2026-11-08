# Root Cause Analysis

Identify why the defect was possible, not just what the defect is.

## Approach

- **Distinguish root cause from trigger:** the error message is a symptom, the cause is the system gap that allowed it
- **Match depth to impact:** a production bug warrants deep analysis; a missing import does not
- **Dig at least one level deeper:** ask "why was this possible?" after finding the immediate cause
- **Fix the system that allowed the bug:** missing types? missing tests? unclear API contract? race condition in shared state?

## Examples

| Trigger | Root cause |
|---------|-----------|
| `TypeError: undefined is not a function` | Missing null check on optional API response field — no type narrowing |
| Test passes alone, fails in suite | Shared mutable state between tests — missing teardown |
| Wrong query results after deploy | Migration assumed column exists — no schema validation in pipeline |

Focus on the system gap. The specific error is just how you found it.
