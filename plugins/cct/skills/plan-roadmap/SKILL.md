---
name: plan-roadmap
description: "Sequence a strategic roadmap — order epics into a quarterly or release plan with prioritization, stakeholder alignment, and milestones. Use when the user has multiple initiatives and needs them placed on a timeline. Triggers on: 'plan a roadmap', 'build a quarterly roadmap', 'sequence our initiatives', 'create a release plan', 'roadmap for next quarter'. Skip for: choosing a scoring framework — use cct:product-playbook. Skip for: cleaning a feature-request inbox — use cct:product-playbook. Skip for: splitting an epic into stories — use break-down-epics."
allowed-tools: "Read Write"
user_invocable: true
metadata:
  version: 1.0.0
  author: Dean Peters
---


## Purpose
Guide product managers through strategic roadmap planning by orchestrating prioritization, epic definition, stakeholder alignment, and release sequencing into a structured process. Use this to move from disconnected feature requests to a cohesive, outcome-driven roadmap that aligns stakeholders, sequences work logically, and communicates strategic intent.

This is not a Gantt chart — it's a strategic communication tool that shows what you're building, why it matters, and how it ladders up to business outcomes.

## Reference Files

- `references/phase-details.md` — Detailed activities, outputs, participants, and timing for all 5 phases (gather inputs, define epics, prioritize, sequence, communicate)
- `references/pitfalls.md` — 5 common roadmap planning pitfalls with symptoms, consequences, and fixes
- `template.md` — Fill-in roadmap template
- `examples/sample.md` — Full roadmap examples

Read the relevant reference file when executing each phase or when the user asks about specific activities.

## Key Concepts

### Types of Roadmaps

| Type | Structure | Best For |
|------|-----------|----------|
| **Now/Next/Later** | Current quarter (committed) / following quarter (high confidence) / future (low confidence) | Agile teams, uncertainty, continuous discovery |
| **Theme-Based** | Organized by strategic themes (e.g., "Retention," "Enterprise Expansion") | Communicating to execs, showing strategic intent |
| **Timeline (Quarters)** | Q1: Epics A, B; Q2: Epics C, D | Resource planning, stakeholder communication |
| **Feature-Based** (anti-pattern) | Lists features without context | Avoid — no strategic narrative or customer framing |

### Why This Works
- **Outcome-driven:** Ties initiatives to business/customer outcomes
- **Stakeholder alignment:** Transparent process reduces political friction
- **Strategic clarity:** Shows not just "what" but "why"
- **Flexible:** Adapts as you learn from discovery/delivery

### Anti-Patterns
- **Not a commitment:** Roadmaps are strategic plans, not contracts
- **Not a feature list:** Roadmaps frame problems, not just solutions
- **Not waterfall:** Roadmaps evolve quarterly based on learning

### When to Use This
- Annual or quarterly planning cycles
- After product strategy session (translate strategy to roadmap)
- Onboarding new stakeholders (align on direction)
- Reframing existing roadmap (shift from feature-driven to outcome-driven)

### When NOT to Use This
- For tactical sprint planning (use backlog instead)
- When strategy is unclear (run product-strategy-session first)
- When stakeholders expect date commitments (address expectations first)

## Workflow Overview

Use `template.md` for the full fill-in structure. This workflow orchestrates **5 phases** over **1-2 weeks**. See `references/phase-details.md` for detailed activities and outputs per phase.

### Phase 1: Gather Inputs (Day 1-2)
Collect business goals (OKRs), validated customer problems, technical constraints, and stakeholder requests. Output: 3-5 business outcomes, 3-5 customer problems, tech investments list, stakeholder request list.

### Phase 2: Define Initiatives (Day 3-4)
Turn inputs into 10-15 epics with hypotheses, success metrics, and T-shirt effort estimates. Map each epic to a business outcome. Uses `cct:break-down-epics` for epic hypothesis writing.

### Phase 3: Prioritize Initiatives (Day 5)
Choose a prioritization framework (RICE, ICE, Value/Effort), score all epics, adjust for strategic fit. Output: ranked backlog, top 10 epics. Uses `cct:product-playbook` → `../product-playbook/references/advise-prioritization.md` for framework selection and scoring.

### Phase 4: Sequence Roadmap (Day 6-7)
Map dependencies, sequence into quarters (Now/Next/Later or Q1/Q2/Q3), validate with engineering for capacity and feasibility.

### Phase 5: Communicate Roadmap (Week 2)
Create presentation, present to stakeholders with strategic narrative, gather feedback, refine, and publish.

**Total time:** 1 week (fast track) to 2 weeks (typical).

```
Week 1:
├─ Day 1-2: Gather Inputs (goals, problems, constraints, requests)
├─ Day 3-4: Define Initiatives (epic hypotheses, effort, outcome mapping)
├─ Day 5: Prioritize (framework, scoring, strategic adjustments)
└─ Day 6-7: Sequence (dependencies, quarters, engineering validation)

Week 2:
└─ Communicate (presentation, stakeholder review, refine, publish)
```

## References

### Related Skills

- `cct:break-down-epics` — Phase 2: epic hypothesis writing
- `cct:product-playbook` → `../product-playbook/references/advise-prioritization.md` — Phase 3: framework selection and scoring
- `cct:product-playbook` → `../product-playbook/references/run-strategy-session.md` — Run before roadmap planning to establish strategy
- `cct:product-playbook` → `../product-playbook/references/run-discovery-process.md` — Provides customer problem inputs for Phase 1
- `cct:run-story-mapping` — For complex epics requiring release planning

### External Frameworks
- Bruce McCarthy, *Product Roadmaps Relaunched* (2017) — Outcome-driven roadmaps
- C. Todd Lombardo, *Product Roadmaps Relaunched* (2017) — Now/Next/Later framework
- Intercom, "RICE Prioritization" (2016) — Prioritization framework

---

## Sources

| Source | Origin |
|--------|--------|
| [deanpeters/Product-Manager-Skills](https://github.com/deanpeters/Product-Manager-Skills) — skills/roadmap-planning | Original skill |
