# ADR Template

**Linear object:** Document (attached to a Project or standalone)
**Source:** this file. The Linear workspace held a template of the same name until
2026-09-12; it was deleted, so there is no live version to fetch.

**No EARS, no Gherkin.** An ADR records a decision, not a behaviour. If you find yourself writing
`the system shall`, the content belongs in an RFC or an issue.

## MCP Steps

```
create_document:
  title: "ADR-<NUMBER>: <Decision Title>"
  project: "<project-name>"  # optional
  icon: ":scales:"
```

## Template

```markdown
# ADR-[NUMBER]: [Decision Title]

## Status

[Proposed | Accepted | Deprecated | Superseded]

## Context

> What is the issue we're facing? Include technical constraints, business requirements, and why a
> decision is needed now.

[Describe the situation and the forces at play]

## Decision

> State the decision clearly and directly. Start with "We will".

We will [specific technical decision].

## Consequences

### Positive

- [What gets better or easier]
- [Problems this solves]

### Negative

- [What gets harder]
- [Technical debt incurred]
- [Limitations introduced]

## Alternatives Considered

### Option A: [Alternative name]

- **Approach:** [Brief description]
- **Pros:** [Key benefits]
- **Cons:** [Key drawbacks]
- **Rejected because:** [Specific reason]

### Option B: [Alternative name]

- **Approach:** [Brief description]
- **Pros:** [Key benefits]
- **Cons:** [Key drawbacks]
- **Rejected because:** [Specific reason]

## Related

- [Related ADRs, RFCs, Linear issues, PRs]

---

**Date:** [YYYY-MM-DD]
**Author:** [Name / Team]
**Decision makers:** [@person1, @person2]
**Reviewed by:** [Names]
**Supersedes:** [ADR-XXX if applicable]
**Superseded by:** [ADR-XXX if applicable]
```

## Why this shape

One subsection per alternative, not a table row. "Rejected because" is the sentence a reader comes
back for in a year, and it does not survive being squeezed into a table cell.

`Supersedes` and `Superseded by` are what turn a pile of ADRs into a decision log. Without them
nobody can tell which decision is current, and the whole record stops being trustworthy.
