# Simple Task Template

**Linear object:** Issue
**Canonical source:** Linear workspace template "Simple Task Template". Adopted as-is; this kit had
no equivalent.

**No EARS, no Gherkin. On purpose.** This is the escape hatch. Over-specifying small work is the
best-documented failure of spec-driven development, and a template with no escape hatch produces
four user stories and sixteen acceptance criteria for a CSS fix.

## When to use this instead of the agent-ready issue

Use it when **you could describe the change in one sentence** and that sentence leaves nothing open:
a copy change, a dependency bump, a known CSS bug, a config value, a renamed field.

Use `references/issue-template.md` instead the moment any of these is true:

- the change has a branch, a state, or an unhappy path worth naming
- more than one file of behaviour changes
- a person would have to ask a question before starting
- it is going to an agent that cannot ask

The test is not size, it is ambiguity. A one-line change with an unclear correct answer is not a
simple task.

## MCP Steps

```
save_issue:
  title: "[Verb] [what] [where]"
  team: "team-name"
  priority: 3
```

## Template

```markdown
## Task

[What needs to be done and why it is needed. One paragraph.]

## Acceptance Criteria

- [ ] [Specific, checkable completion requirement]
- [ ] [What "done" looks like]

## Technical Notes

[Implementation approach, constraint, or dependency — only if there is one]

## Testing

- [ ] [Unit test, manual check, or edge case to verify — only if there is one]

## Related Work

**Parent project:** [Link, if any]
**Related issues:** LIN-XXX
**Depends on:** [What must land first]
```

## Examples that belong here

- Add an industry filter dropdown to the review search page, using the existing design-system component
- Fix the CSS bug where review stars overflow on iPhone 12 and smaller
- Update the privacy policy copy for the new GDPR requirement
- Bump `pg` from 8.11 to 8.13

## Examples that do not

- "Improve review search performance" — no number, so no way to know when it is done
- "Handle duplicate vendor submissions" — an unhappy path with an undecided answer
- Anything a coding agent picks up unattended
