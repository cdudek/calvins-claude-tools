# RFC Template

**Linear objects:** Project + Document
**Base:** this kit's version. Two sections adopted from the Linear workspace template "RFC
Template" — the Summary instruction and Goals / Non-Goals — and `Migration Plan` folded in from the
generic developer template. Linear's nine numbered sections, four appendices and review checklist
are deliberately **not** adopted; see the note at the end.

**No EARS, no Gherkin.** An RFC proposes an approach. It has Goals instead, and the behaviour is
specified in the PRD or the issues that follow it.

## MCP Steps

```
save_project:
  name: "<project>"
  team: "<team>"

create_document:
  title: "RFC: <Title>"
  project: "<project>"
  icon: ":memo:"
```

Then `update_document` with the body.

## Template

```markdown
## Summary

> Two or three sentences an executive can read on their own: the problem or opportunity, the
> proposed approach, the expected impact, and the biggest risk.

[Summary]

## Problem

What is broken or missing? Include data, user feedback, or incident links.

**Business context:** [Why this matters now. Scale, cost, the metric that improves.]
**Technical context:** [What we learned about the current system and why existing options do not work.]

## Goals and Non-Goals

### Goals

> Specific, measurable, testable. These are what the RFC is judged against.

- [ ] [Goal]
- [ ] [Goal]

### Non-Goals

> Things a reader might reasonably expect here but which are out of scope. This is the section
> that prevents the scope argument in week three.

- [Non-goal]
- [Non-goal]

## Proposed Solution

### Architecture

[Components and how they fit. A simple diagram a non-specialist can follow.]

### Data Flow

[How data moves through the system.]

### API Changes

| Endpoint | Method | Change |
|---|---|---|
|  |  |  |

### Schema Changes

| Table | Column | Type | Change |
|---|---|---|---|
|  |  |  |  |

## Alternatives Considered

### Option A: [Name]

- **Approach:** [Brief description]
- **Pros:** [Key benefits]
- **Cons:** [Key drawbacks]
- **Rejected because:** [Specific reason]

### Option B: [Name]

- **Approach:** [Brief description]
- **Pros:** [Key benefits]
- **Cons:** [Key drawbacks]
- **Rejected because:** [Specific reason]

## Implementation Plan

Create the phases as Linear milestones (`save_milestone`), not as text here. A phase list in prose
goes stale the day after it is written.

## Migration Plan

> Only when something already running has to change. How do we get from the current state to the
> proposed one without an outage or a data loss window?

- [Step, and what is reversible about it]
- **Rollback:** [How we undo this if it goes wrong]

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
|  |  |  |  |

## Success Metrics

**North star:** [The one metric that says this worked]
**Supporting:** [Two or three, each with how it is measured]

## Open Questions

- [ ] [NEEDS CLARIFICATION: <question>] — resolve before implementation starts

## Decision Log

| Date | Decision | Rationale | Decided by |
|---|---|---|---|
|  |  |  |  |

---

**Status:** [Draft | Proposal | Under review | Approved | Rejected]
**Author:** [Name / Team]
**Reviewers:** [Names and their roles]
**Date:** [YYYY-MM-DD]
```

## Why the Linear version was not adopted wholesale

The workspace RFC template has nine numbered sections, appendices A to D including a glossary, and
an eight-item review checklist. It is roughly three times this one. Nobody fills appendix D for a
real RFC, and a template whose unfilled sections outnumber its filled ones teaches people that
templates are decoration.

What was worth taking was taken: the Summary instruction, which is the best-written prompt in
either library, and Goals / Non-Goals, which this kit was missing entirely.

If an RFC genuinely needs a glossary or a performance appendix, add one. The template does not
need to ask every author for it in advance.
