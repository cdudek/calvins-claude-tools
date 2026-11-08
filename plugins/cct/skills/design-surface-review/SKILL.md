---
name: design-surface-review
description: "Reviews an authored visual plan or an already-changed UI surface before or at build time, rating it 0 to 10 per design dimension, calibrated against the repo's design system (DESIGN.md or token files), and listing the design issues to fix. Use when the user says 'review this UI plan', 'rate the design plan', 'design review before building', 'critique this changed screen's design'. Skip for: WCAG verdicts (cct:ux-accessibility-audit); Laws of UX verdicts (cct:ux-usability-audit); whole-app or PR UX assessment (cct:ux-assessment-run); authoring the design (cct:design-frontend-write)."
allowed-tools: "Read Grep Glob Write Skill"
user_invocable: true
metadata:
  version: 1.0.0
  author: Garry Tan
effort: high
---

# Designer's Eye Plan Review

Rate UI implementation plans 0-10 BEFORE any code is written. Catch design problems in the plan stage where fixing is free.

**Calibrate against the repo's design system.** Before judging a planned UI change, read the repo's `DESIGN.md` or token files (if none exists, say so and judge against the plan's own tokens). Check the plan against it — flag any planned raw CSS, primitive colors, non-`txt-*` typography, arbitrary spacing/radius, or raw z-index.

## When to Use

- Before implementing a UI feature
- When reviewing a plan that includes UI changes
- When a plan mentions "create a page", "add a component", "build a dashboard"

## Review Process

### 1. Read the Plan

Read the full plan. Identify every UI touchpoint — pages, components, layouts, interactions.

### 2. Design Hard Rules Check

**Classifier:** Is this MARKETING/LANDING, APP UI, or HYBRID?

**Hard rejection criteria** (instant-fail, flag if ANY apply):
1. Generic SaaS card grid as first impression
2. Beautiful image with weak brand
3. Strong headline with no clear action
4. Busy imagery behind text
5. Sections repeating same mood statement
6. Carousel with no narrative purpose
7. App UI made of stacked cards instead of layout

### 3. Litmus Checks (YES/NO)

Answer each for the planned design:
1. Brand/product unmistakable in first screen?
2. One strong visual anchor present?
3. Page understandable by scanning headlines only?
4. Each section has one job?
5. Are cards actually necessary?
6. Does motion improve hierarchy or atmosphere?
7. Would design feel premium with all decorative shadows removed?

### 4. AI Slop Scan

Check the plan for any of these anti-patterns:
1. Purple gradient backgrounds
2. 3-column icon-in-circle feature grids
3. Centered everything with uniform bubbly radius
4. Decorative blobs and wavy dividers
5. Generic hero copy
6. Cookie-cutter section rhythm

### 5. Score (0-10)

| Score | Meaning |
|-------|---------|
| 9-10 | Ship it — design is intentional, polished, distinctive |
| 7-8 | Good foundation — minor suggestions, proceed with notes |
| 5-6 | Needs work — structural issues that should be fixed before building |
| 3-4 | Significant redesign needed — multiple hard rule violations |
| 0-2 | Start over — the approach is fundamentally flawed |

### 6. Output

```
DESIGN PLAN REVIEW: [score]/10

HARD REJECTIONS: [list or "none"]
LITMUS SCORECARD: [7 YES/NO answers]
AI SLOP FLAGS: [list or "clean"]

FINDINGS:
- [severity] [finding] → [specific suggestion]

VERDICT: [one sentence — proceed / revise / redesign]
```

## Key Principle

It's cheaper to fix a bad design in a plan than in code. Be direct. A 4/10 score with clear suggestions is more valuable than a polite 7/10 that lets problems through.

## Sources

| Origin | Author | License |
|--------|--------|---------|
| [garrytan/gstack](https://github.com/garrytan/gstack) — `design-surface-review` | Garry Tan | MIT |
