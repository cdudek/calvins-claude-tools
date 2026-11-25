# Intent template

Copy to `changes/<slug>/intent.md`. It is written from the grilling answers, in plain words a person without code can approve.

```markdown
---
status: draft
author: <name>
---

# Intent: <slug>

## Problem
What hurts today, and for whom. Two or three sentences.

## Outcome
- outcome-1: A signed-in user can save a search and reopen it from the sidebar.
- outcome-2: A saved search keeps its filters.

## Constraints
- constraint-1: No new paid service.
- constraint-2: Works at 320 px wide.

## Appetite
How big it may get, for example 2 milestones. Beyond that, re-scope.

## Out of scope
No-gos and rabbit holes.

## Affected
Systems, and spec files as paths (`specs/2026-12/2026-12-20__saved-searches.md`).

## Open questions
None. (Every question is answered before approval.)

## Success signal
How we will know it worked, in one observable sentence.
```

## Rules
- `status` is `draft` until the approval, then `approved`.
- Outcomes are `outcome-1`, `outcome-2`. Constraints are `constraint-1`, `constraint-2`. Ids are never reused.
- Every requirement in `delta.md` cites at least one id that exists here, like `[outcome-1]` or `[constraint-2]`. The check fails a requirement with none.
- Outside the list items that define them, an id in the prose follows an explainer: "the sidebar keeps saved filters (outcome-2)". The check fails a bare id.
- Holdout scenarios are drawn from the outcomes.
- No `[NEEDS CLARIFICATION` may remain at approval. The check fails it.
- The intent stays in the change folder after the change ships.
- A bug or small feature: Problem and Outcome in one or two sentences each; the other sections can say "none".
