## Purpose
Guide product managers through creating a customer journey map by asking adaptive questions about the actor (persona), scenario/goal, journey phases, actions/emotions, and opportunities for improvement. Use this to visualize the end-to-end customer experience, identify pain points, and create a shared mental model across teams—avoiding surface-level feature lists and ensuring discovery work focuses on real customer problems, not assumed solutions.

This is not a feature roadmap—it's a discovery and alignment tool that uncovers where the experience breaks down and where improvements will have the greatest impact.

## Prerequisites

Read `references/run-journey-workshop/references/journey-map-framework.md` for full NNGroup framework details, canvas structure, when/when-not guidance, and anti-patterns.

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

This interactive skill asks **up to 5 adaptive questions**, offering **3-4 enumerated options** at each step.

Interaction pattern: Pair with `facilitate-workshop` when you want a one-step-at-a-time flow with numbered recommendations at decision points and quick-select options for regular questions. If the user asks for a single-shot output, skip the multi-turn facilitation.

## Workflow

Read `references/run-journey-workshop/references/question-guide.md` for full question text, enumerated options, and adaptation notes for each step.

1. **Gather context** — Collect customer research, product context, personas (Step 0)
2. **Identify actor** — Select or describe the persona anchoring this map (Q1)
3. **Define scenario + goal** — What is the actor trying to accomplish? (Q2)
4. **Identify journey phases** — Generate 4-6 phases, confirm with user (Q3)
5. **Map actions, thoughts, emotions** — Fill in each phase with behaviors, thoughts, feelings, pain points (Q4)
6. **Identify opportunities** — Generate 5-7 improvement opportunities ranked by impact (Q5)
7. **Output journey map** — Produce final artifact per `references/run-journey-workshop/references/output-template.md`

## Key Rules

- One map per persona — never combine multiple personas in a single map
- Map from customer perspective, not internal process
- Every phase must include emotions and pain points, not just actions
- Opportunities must be ranked by impact (HIGH/MEDIUM/LOW) with evidence
- Get specific — vague actions ("uses product") and emotions ("happy") are anti-patterns
- Include real customer quotes where available

## References

### Reference Files
- `references/run-journey-workshop/references/journey-map-framework.md` — NNGroup framework, canvas structure, when/when-not guidance
- `references/run-journey-workshop/references/question-guide.md` — Full question text and enumerated options for each step
- `references/run-journey-workshop/references/output-template.md` — Final journey map output format
- `references/run-journey-workshop/references/examples-and-pitfalls.md` — Good/bad examples and 5 common pitfalls

### Related Skills
- `references/run-journey-workshop/references/map-customer-journey.md` — journey map template and stage framework
- `cct:product-problem-write` — converts opportunities into problem statements
- `cct:product-discovery-run` — gathers research input for mapping
- `cct:product-playbook` — opportunity-tree method for designing solutions to journey opportunities

### External Frameworks
- Nielsen Norman Group, "Journey Mapping 101" (2016) — Definitive guide to journey mapping
- Adaptive Path, "Guide to Experience Mapping" (2013) — Experience vs. journey maps

## Sources

| Origin | Author | License |
|--------|--------|---------|
| [deanpeters/Product-Manager-Skills](https://github.com/deanpeters/Product-Manager-Skills) — `skills/customer-journey-mapping-workshop` | Dean Peters | MIT |
