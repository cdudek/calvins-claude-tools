# Evaluate Approaches

For non-trivial fixes, outline 2-3 options with trade-offs before implementing.

## When to evaluate

- The root cause has multiple valid fixes
- The fix touches shared code or public APIs
- You're unsure which approach is simplest

## When to skip

- Mechanical fixes: typos, missing imports, obvious one-liners
- The root cause points to exactly one fix
- The fix is isolated to a single function or test

## How to evaluate

For each option, note:
- What changes
- What it affects (blast radius)
- Complexity and risk

Prefer the simplest viable approach. Start with it — iterate only if it fails.
