## Purpose
Guide product managers through the MITRE Problem Framing Canvas process by asking structured questions across three phases: Look Inward (examine your own assumptions and biases), Look Outward (understand who experiences the problem and who doesn't), and Reframe (synthesize insights into an actionable problem statement and "How Might We" question). Use this to ensure you're solving the right problem before jumping to solutions—avoiding confirmation bias, overlooked stakeholders, and solution-first thinking.

This is not a solution brainstorm—it's a problem framing tool that broadens perspective, challenges assumptions, and produces a clear, equity-driven problem statement.

## Prerequisites

Read `references/reframe-problem/references/canvas-framework.md` for full MITRE canvas structure, when/when-not guidance, and anti-patterns.

### Facilitation Source of Truth

Use `${CLAUDE_SKILL_DIR}/../product-playbook/references/facilitate-workshop.md` as the default interaction protocol for this skill.

It defines:
- session heads-up + entry mode (Guided, Context dump, Best guess)
- one-question turns with plain-language prompts
- progress labels (for example, Context Qx/8 and Scoring Qx/5)
- interruption handling and pause/resume behavior
- numbered recommendations at decision points
- quick-select numbered response options for regular questions (include `Other (specify)` when useful)

This file defines the domain-specific assessment content. If there is a conflict, follow this file's domain logic.

## Application

Use `references/reframe-problem/template.md` for the full fill-in structure.

This interactive skill follows a **three-phase process**, asking **adaptive questions** in each phase. Read `references/reframe-problem/references/question-guide.md` for full question text, enumerated options, and examples.

## Workflow

1. **Gather context** — Collect problem statement, symptoms, stakeholder context (Step 0)
2. **Phase 1: Look Inward**
   - Q1: What is the problem? (Describe symptoms — 4 options)
   - Q2: Why haven't we solved it? (6 options, multi-select)
   - Q3: How are we part of the problem? (Assumptions & biases — 4 options)
3. **Phase 2: Look Outward**
   - Q4: Who experiences it? When, where, consequences?
   - Q5: Who else has it? Who doesn't?
   - Q6: Who's been left out? Who benefits from the status quo?
4. **Phase 3: Reframe**
   - Q7: Generate refined problem statement from Phase 1-2 insights
   - Q8: Create "How Might We" statement
5. **Output canvas** — Produce final artifact per `references/reframe-problem/references/output-template.md`

## Key Rules

- Never skip "Look Inward" — examining biases before outward analysis is the canvas's core value
- Always ask "Who benefits when the problem exists?" — surfaces political dynamics and resistance
- Problem statement must be specific: who, what, when, consequence, root cause
- HMW statement must be broad enough to allow multiple solution directions
- This is a team exercise — solo completion misses the point (diverse perspectives challenge groupthink)
- Problem statement template: "[Who] struggles to [what] because [root cause], leading to [consequence]"
- HMW template: "How might we [action] as we aim to [objective]?"

## References

### Reference Files
- `references/reframe-problem/references/canvas-framework.md` — MITRE canvas structure, when/when-not guidance, anti-patterns
- `references/reframe-problem/references/question-guide.md` — Full question text, options, and examples for all 8 questions
- `references/reframe-problem/references/output-template.md` — Final canvas output format
- `references/reframe-problem/references/examples-and-pitfalls.md` — Example excerpts and 5 common pitfalls
- `references/reframe-problem/template.md` — Fill-in template for the canvas
- `references/reframe-problem/examples/sample.md` — Full problem framing example

### Related Skills
- `references/reframe-problem/references/frame-problem.md` — converts the reframed problem into a formal problem statement
- `cct:product-playbook` — opportunity-tree method for generating solution options from the HMW statement
- `cct:product-discovery-run` — validates the reframed problem with customers

### External Frameworks
- MITRE Innovation Toolkit, "Problem Framing Canvas v3" (2021) — Origin of canvas, equity-driven design thinking
- Stanford d.school, "How Might We" statements — Actionable problem framing

## Sources

| Origin | Author | License |
|--------|--------|---------|
| [deanpeters/Product-Manager-Skills](https://github.com/deanpeters/Product-Manager-Skills) — `skills/problem-framing-canvas` | Dean Peters | MIT |
