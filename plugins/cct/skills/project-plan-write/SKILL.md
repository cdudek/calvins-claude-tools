---
name: project-plan-write
description: "Authors the execution plan for a project or initiative: goal, non-goal, scope, success metrics, milestones, owners and dependencies, definition of done. Text only; creating it in Linear is separate. Use when the user says 'write a project plan', 'plan the milestones', 'draft the initiative', 'assign owners and dependencies'. Skip for: the technical approach inside a milestone (use cct:arch-plan-write), progress reports (use cct:project-report-write), saving it in Linear (use cct:linear-manage)."
allowed-tools: "Read Grep Glob Write"
user_invocable: true
metadata:
  version: 1.0.0
  author: calvindudek
---

# Write a project or initiative plan

Authors the plan that frames coordinated work: what is delivered, in what milestones, by whom,
and what blocks what. It does not describe implementation detail and does not create anything in
a tracker.

## Pick the level

- **Initiative**: a strategic goal. Use `${CLAUDE_PLUGIN_ROOT}/skills/linear-manage/references/initiative-template.md`. Goal, key results with
  baseline and target, context (why now, what if we do not), scope in and out. No implementation
  detail, no dates unless the user gave them, no project table (the tracker lists child
  projects).
- **Project**: coordinated work that needs more than one issue. Use
  `${CLAUDE_PLUGIN_ROOT}/skills/linear-manage/references/project-template.md`. Goal, Non-Goal (an outcome deliberately not chased, which is
  different from out-of-scope work), why this project, scope, success metrics, approach, definition
  of done (must, should, could, won't), key decisions, resources.

## Add the execution parts

The templates frame the work. Also write, in the project plan:

1. **Milestones.** Each is a deliverable with a checkable exit condition, not a phase name. Order
   them. Phases belong in tracker milestones, not in prose that goes stale.
2. **Ownership.** One named owner per milestone and per key result. If the user did not name one,
   write `owner: unassigned` and list it under open questions; do not invent a person.
3. **Dependencies.** For each milestone, `needs: <milestone or external item>`. Independent
   milestones say so, since independent work merges on its own.
4. **Risks** that threaten a milestone, with the mitigation.

## Rules

- Key results are measurable: "reduce p95 latency from 800 ms to 200 ms", not "improve
  performance".
- Link decisions and documents (PRD, RFC, ADRs) instead of pasting them.
- Technical approach for a milestone is `cct:arch-plan-write`; a decision record is
  `cct:arch-decision-log`.
- To create the project or initiative in Linear, hand the finished text to `cct:linear-manage`.
  The templates carry the Linear steps (create minimal first, then add the description).
