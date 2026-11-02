# PRD Template

**Linear object:** Document (attached to a Project)
**Source:** this file. The Linear workspace held a template of the same name until 2026-09-12; it was deleted,
so there is no live version to fetch.
The Requirements section carries the EARS grammar, which the deleted Linear version never had.

**Requirements are EARS with `F`/`N` numbers, inside the MoSCoW buckets.** Gherkin is optional and
usually belongs in the issues this PRD spawns, not here. Grammar:
`../sdlc-run/references/requirements-grammar.md`.

## MCP Steps

```
save_project:         # ensure the project exists first
  name: "<project>"
  team: "<team>"

create_document:
  title: "PRD: <Product / Feature Name>"
  project: "<project>"
  icon: ":page_facing_up:"
```

Then `update_document` with the body. Create minimal first, update second — long bodies on create
are the most common source of Linear 500s.

---

## The shape, and why it is in this order

Sections run from the least likely to change to the most (Nan Yu, Linear). **Page one** is the
problem, who it is for, the success metric and the non-goals: no solution on it (Intercom). A PRD
stays on page one until the problem is agreed, then grows one section per product review:
solution, requirements, launch, impact. Match the detail to the risk: a two-day fix never leaves
page one; a two-month project fills every section.

Every section added loses readers. Add a section when it answers a question somebody has asked,
and edit the document down every time it is touched.

## Template

```markdown
# PRD: [Product / Feature Name]

**Owner:** [one name] · **Status:** [Page one | Draft | Approved | Shipped | Measured] · **Last updated:** [YYYY-MM-DD]
**RACI:** R [who builds] · A [the owner] · C [design, eng, support, legal, marketing, as needed] · I [who gets the update]
**Links:** [research] · [designs] · [RFC / ADR] · [tracker epic] · [analytics dashboard]

> One link should answer any question about this work. If it is not linked here, link it.

<!-- Page one: problem, who, metric, non-goals. No solution above the line. Stays one page until the problem is agreed. -->

## Problem

[Who has the problem, what happens, what it costs them. In their words where possible.]

**Evidence:**

- [Data point, with source and date]
- [Customer quote or support theme, with count]
- [Usage metric showing the pain]

**Why now:** [what changed that makes this the quarter]

**Cost of not solving:** [what happens if we do nothing: churn, competitive, regulatory]

## Who it is for

| Segment | Size | Current pain | What they will do with this |
|---|---|---|---|
| [A segment, never "users"] | [count or share, with source] | [problem] | [use] |

## Success metric

| Metric | Current | Target | How measured | When measured |
|---|---|---|---|---|
| [The one metric this must move] | [baseline] | [goal] | [method] | [cadence] |
| [Guardrail: must not get worse] | [baseline] | [floor] | [method] | [cadence] |

## Non-goals

- [What this will not do, and why not now]
- [The adjacent request this is not]

---

## Solution

[What we are building, in two or three paragraphs. The shape, not the pixels: design owns the UI.]

**User flows:** [link to the flow or wireframe, a Figma URL, never a local path]

**Guiding principles:**

- [e.g. "Ship weekly iterations over one big release"]

## Requirements

> One EARS sentence per line, each with a number. The number is the handle the issues, the tests
> and the Definition of Done all use. Replace every adjective with a number.
> Mark anything unresolved as [NEEDS CLARIFICATION: <question>] — never guess it.

### Must have (required for launch)

- [ ] **F1** When [trigger], the system shall [response].
- [ ] **F2** If [error condition], then the system shall [response].
- [ ] **N1** The system shall [non-functional property with a number, e.g. answer in under 200 ms at p95].

### Should have (important)

- [ ] **F3** While [state], the system shall [response].

### Could have (if time allows)

- [ ] **F4** Where [feature is included], the system shall [response].

### Won't have (not this version)

- [Explicitly excluded, so the boundary is on the record]
- [Future consideration]

## Decisions

> Every call that changed this document. Appended, never rewritten, so nobody reopens a question
> that has an answer. Anything that blocks a requirement is inline as [NEEDS CLARIFICATION: ...]
> next to the requirement, not here.

| Date | Question | Call | Who | Rejected, and why |
|---|---|---|---|---|
| [YYYY-MM-DD] | [the question] | [the answer] | [name] | [option]: [one clause] |

**Open questions:**

- [ ] [Question, owner, date needed by]

## Launch

**Target:** [date, or the quarter with the decision point that fixes it]
**MVP scope:** [what must be in v1]

**Dependencies:**

- [ ] [Team or system]: [what we need from them, by when]

**Risks:**

| Risk | Probability | Impact | Mitigation | Owner |
|---|---|---|---|---|
| [Risk] | H/M/L | H/M/L | [Plan] | [Who] |

**Readiness:** launch is cross-functional. Each line has a name or is struck through as not needed.

- [ ] Support: macro, help article, who answers escalations
- [ ] Legal and privacy: terms, consent, data retention
- [ ] Marketing: announcement, changelog, who is told first
- [ ] FAQ: the five questions customers will ask on day one, answered
- [ ] Rollout: flag, cohort, rollback

## Impact

> Filled after launch, on the date the success-metric table names. The section almost no
> template asks for, and the only one that says whether this was worth it.

| Metric | Baseline | Target | Observed | Verdict |
|---|---|---|---|---|
| [from Success metric] | [baseline] | [goal] | [measured, with date and source] | [moved / did not / too early] |

**What we learned:** [one paragraph. What to do differently next time.]
```

## Optional sections

> Add only when the product needs them. Each one loses readers.

### Press release and FAQ (big launches)

Written **before** page one is agreed, as a one-page press release dated launch day plus the FAQ
(Amazon PR/FAQ). If the press release is not exciting, stop here. Keep it at the top of the
document until launch, then move it to the Links line.

### Jobs to be done

**[Scenario name]**: **When** [situation or trigger], **I need to** [goal], **so I can** [outcome].

### Strategic context

**Business goal:** [the OKR this serves] · **Market:** [TAM / SAM / SOM with a source] ·
**Competitive landscape:** [who else solves this, and how]

### Phasing

**Phase 1: [Name]** — **Goal:** [what we learn or prove] · **Scope:** [what we build] · **Success:** [metric target]

## Why MoSCoW and EARS together

MoSCoW answers "does this ship in v1"; EARS answers "what exactly must be true". They are different
questions and a template that only asks one of them produces either a prioritised list of vague
wishes, or a precise specification with no launch boundary.

The `Won't have` bucket and the Non-goals section are not filler. An explicitly excluded item is
the cheapest scope control there is: it is the one an engineer can point at six weeks later.

## Where the grammar is enforced

This PRD is where `F1`, `F2`, `N1` are born. Every issue this PRD spawns cites those numbers, and
the Definition of Done in each issue checks its own. That chain is the only traceability in the kit,
and it breaks the moment someone writes a requirement without a number.
