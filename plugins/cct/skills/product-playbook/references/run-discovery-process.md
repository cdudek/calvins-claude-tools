## Purpose
Guide product managers through a complete discovery cycle—from initial problem hypothesis to validated solution—by orchestrating problem framing, customer interviews, synthesis, and experimentation skills into a structured process. Use this to systematically explore problem spaces, validate assumptions, and build confidence before committing to full development—avoiding "build it and they will come" syndrome and ensuring you're solving real customer problems.

This is not a one-time research project—it's a continuous discovery practice that runs in parallel with delivery, typically 1-2 discovery cycles per quarter.

## Prerequisites

- Familiarity with discovery concepts (Teresa Torres, Marty Cagan)
- Access to customers for interviews (5-10 per cycle)
- Cross-functional participation (PM, design, engineering lead)

### Facilitation Source of Truth

When running this workflow as a guided conversation, use `facilitate-workshop` as the interaction protocol.

It defines:
- session heads-up + entry mode (Guided, Context dump, Best guess)
- one-question turns with plain-language prompts
- progress labels (for example, Context Qx/8 and Scoring Qx/5)
- interruption handling and pause/resume behavior
- numbered recommendations at decision points
- quick-select numbered response options for regular questions (include `Other (specify)` when useful)

This file defines the workflow sequence and domain-specific outputs. If there is a conflict, follow this file's workflow logic.

## Application

Use `template.md` for the full fill-in structure.

This workflow orchestrates **6 phases** over **2-4 weeks**, using multiple component and interactive skills. Read `references/phase-details.md` for complete activity descriptions, participants, durations, and outputs per phase.

## Workflow

| Phase | Timing | Key Activity | Skills Used |
|-------|--------|-------------|-------------|
| 1. Frame the Problem | Day 1-2 | Problem framing canvas + formal statement | `reframe-problem`, `frame-problem` |
| 2. Research Planning | Day 3 | Interview prep, recruitment, scheduling | `prep-discovery-interview` |
| 3. Conduct Research | Week 1-2 | 5-10 customer interviews + analytics review | Interview methodology from Phase 2 |
| 4. Synthesize Insights | End of Week 2 | Affinity mapping, pain point prioritization | `run-journey-workshop` (optional), `frame-problem` |
| 5. Generate & Validate | Week 3 | OST creation, experiment design + execution | `build-opportunity-tree` |
| 6. Decide & Document | Week 3-4 | GO/PIVOT/KILL decision, PRD, stakeholder readout | — |

See `references/workflow-timeline.md` for the full week-by-week visual timeline and time investment estimates.

### Decision Points

- **After Phase 1:** Do we have enough context to start research? If NO, gather existing data (+2-3 days)
- **After Phase 3:** Have we reached saturation? (same pain points across 3+ interviews) If NO, schedule more interviews (+1 week)
- **After Phase 5:** Did experiments validate solution? If NO, pivot to next solution option (+1-2 weeks)

## Key Rules

- Always interview 5-10 customers per cycle — never rely on analytics alone
- Use Mom Test questions (focus on past behavior, not hypotheticals)
- Continue interviews until saturation (same patterns across 3+ customers)
- Time-box discovery to 3-4 weeks — avoid analysis paralysis
- Discovery is continuous, not one-time — aim for 1 customer interview per week ongoing
- Every solution must map to an experiment before committing to build

## References

### Reference Files
- `references/phase-details.md` — Complete activity descriptions, participants, durations, outputs for all 6 phases
- `references/workflow-timeline.md` — Week-by-week visual timeline and time estimates
- `references/examples-and-pitfalls.md` — Example excerpts and 5 common pitfalls
- `template.md` — Fill-in template for the discovery process
- `examples/sample.md` — Full discovery process example

### Related Skills (Orchestrated by This Workflow)
- **Phase 1:** `reframe-problem` (interactive), `frame-problem` (component)
- **Phase 2:** `prep-discovery-interview` (interactive)
- **Phase 4:** `run-journey-workshop` (interactive, optional)
- **Phase 5:** `build-opportunity-tree` (interactive)

### External Frameworks
- Teresa Torres, *Continuous Discovery Habits* (2021) — Weekly customer touchpoints, OST framework
- Rob Fitzpatrick, *The Mom Test* (2013) — How to ask good interview questions
- Marty Cagan, *Inspired* (2017) — Product discovery principles

## Sources

| Origin | Author | License |
|--------|--------|---------|
| [deanpeters/Product-Manager-Skills](https://github.com/deanpeters/Product-Manager-Skills) — `skills/discovery-process` | Dean Peters | MIT |
