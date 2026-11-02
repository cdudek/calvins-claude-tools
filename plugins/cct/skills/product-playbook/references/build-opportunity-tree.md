## Purpose
Guide product managers through creating an Opportunity Solution Tree (OST) by extracting target outcomes from stakeholder requests, generating opportunity options (problems to solve), mapping potential solutions, and selecting the best proof-of-concept (POC) based on feasibility, impact, and market fit. Use this to move from vague product requests to structured discovery, ensuring teams solve the right problems before jumping to solutions—avoiding "feature factory" syndrome and premature convergence on ideas.

This is not a roadmap generator—it's a structured discovery process that outputs validated opportunities with testable solution hypotheses.

## Prerequisites

Read `references/ost-framework.md` for full OST structure, when/when-not guidance, and anti-patterns.

### Facilitation Source of Truth

Use `facilitate-workshop` as the default interaction protocol for this skill.

It defines:
- session heads-up + entry mode (Guided, Context dump, Best guess)
- one-question turns with plain-language prompts
- progress labels (for example, Context Qx/8 and Scoring Qx/5)
- interruption handling and pause/resume behavior
- numbered recommendations at decision points
- quick-select numbered response options for regular questions (include `Other (specify)` when useful)

This file defines the domain-specific assessment content. If there is a conflict, follow this file's domain logic.

## Application

Use `template.md` for the full fill-in structure.

This interactive skill follows a **two-phase process**:

- **Phase 1:** Generate OST (extract outcome, identify opportunities, map solutions)
- **Phase 2:** Select POC (evaluate solutions, recommend best starting point)

Read `references/question-guide.md` for full question text, enumerated options, and examples.

## Workflow

1. **Gather context** — Collect stakeholder request, product context, existing research (Step 0)
2. **Extract desired outcome** — What business/product metric are you moving? (Q1 — 4 options)
3. **Identify opportunities** — Generate 3 customer problems that could drive the outcome (Q2)
4. **Generate solutions** — Create 3 solutions for the selected opportunity (Q3)
5. **Evaluate solutions** — Score on Feasibility, Impact, Market Fit per `references/scoring-criteria.md` (Q4)
6. **Define experiment** — Choose experiment type: A/B test, prototype, or concierge (Q5 — 3 options)
7. **Output OST + POC plan** — Produce final artifact per `references/output-template.md`

## Key Rules

- Opportunities are customer problems, never solutions ("mobile-first users can't access product" not "we need a mobile app")
- Always generate at least 3 opportunities and 3 solutions per opportunity — force divergence before convergence
- Outcomes must be measurable ("Increase NPS from 30 to 50" not "Improve user experience")
- Every solution must map to an experiment — no experiments means no OST
- Limit scope: 3 opportunities, 3 solutions each (9 total max) to prevent analysis paralysis
- POC selection uses three-axis scoring: Feasibility (1-5), Impact (1-5), Market Fit (1-5)

## References

### Reference Files
- `references/ost-framework.md` — OST structure, when/when-not guidance, anti-patterns
- `references/question-guide.md` — Full question text, options, and examples for all 5 questions
- `references/scoring-criteria.md` — POC evaluation dimensions and scoring rubric
- `references/output-template.md` — Final OST + POC plan output format
- `references/examples-and-pitfalls.md` — Example excerpts and 5 common pitfalls
- `template.md` — Fill-in template for the OST
- `examples/sample.md` — Full OST example

### Related Skills
- `frame-problem` — Frames opportunities as customer problems
- `prep-discovery-interview` — Validates opportunities through customer interviews
- `run-journey-workshop` — Maps customer journey to find opportunities

### External Frameworks
- Teresa Torres, *Continuous Discovery Habits* (2021) — Origin of Opportunity Solution Tree
- Jeff Patton, *User Story Mapping* (2014) — Outcome-driven product planning
- Ash Maurya, *Running Lean* (2012) — Hypothesis-driven experimentation

## Sources

| Origin | Author | License |
|--------|--------|---------|
| [deanpeters/Product-Manager-Skills](https://github.com/deanpeters/Product-Manager-Skills) — `skills/opportunity-solution-tree` | Dean Peters | MIT |
