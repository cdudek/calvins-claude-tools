# Initiative Template

**Linear object:** Initiative

Initiatives are strategic goals. Keep them tight — the child projects carry the execution detail. The initiative just answers "where are we going and how do we know we got there?"

## MCP Steps

```
save_initiative:
  name: "[Strategic Goal]"
  status: "Planned"
  icon: ":dart:"
```

Then update with description.

## Template

```markdown
## Goal
One sentence: what we want to achieve and why it matters.

## Key Results
1. [Measurable outcome] — baseline: X, target: Y
2. [Measurable outcome] — baseline: X, target: Y

## Context
- Why now? What changed?
- What happens if we don't do this?

## Scope
- **In:** [which areas/teams this covers]
- **Out:** [what's explicitly not part of this]
```

## Guidelines

1. **No implementation detail** — that belongs in projects and issues.
2. **Measurable key results** — "improve performance" is useless. "Reduce p95 latency from 800ms to 200ms" is actionable.
3. **No dates** — only add dates if the user explicitly provides them.
4. **No project table** — Linear auto-tracks child projects. Don't duplicate it in the description.
