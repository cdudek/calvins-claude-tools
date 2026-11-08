# Protect Tests

Tests encode expected behavior — they are sacrosanct.

## Rules

- **Never modify a test to make broken code pass.** If the test fails, the code is wrong until proven otherwise.
- **Change tests only when they encode wrong assumptions** — e.g., the test asserts outdated behavior that was intentionally changed.
- **If you must change a test**, do it in a separate step with explicit justification. Never silently modify a test as part of a code fix.
- **If test and code disagree**, investigate which one is correct before changing either.

## Why

Tests are the contract. Weakening tests to make code pass hides bugs instead of fixing them. The test suite should get stricter over time, not more lenient.
