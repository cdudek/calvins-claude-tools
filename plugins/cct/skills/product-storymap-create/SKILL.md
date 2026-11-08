---
name: product-storymap-create
description: "Creates a Jeff Patton user story map from supplied stories: narrative flow of activities and steps on top, story details below, a walking skeleton, and release slices that each deliver an end-to-end outcome. Runs as a facilitated workshop. Use when the user says 'story mapping', 'user story map', 'walking skeleton', 'release slices', 'map the backlog as a story map'. Skip for: splitting a single epic into vertical slices - use cct:product-epic-analyze. Skip for: the all-touchpoint customer journey - use cct:ux-journey-create. Skip for: writing the stories themselves - use cct:product-workitem-write."
allowed-tools: "Read Write"
user_invocable: true
metadata:
  version: 1.0.0
  author: Dean Peters
---

## Purpose

Guide product managers through creating a user story map by asking adaptive questions about the system, users, workflow, and priorities — then generating a two-dimensional map with backbone (activities), user tasks, and release slices. Moves flat backlogs to visual story maps that communicate the big picture, identify gaps, and enable meaningful release planning.

This is not a backlog generator — it's a visual communication framework that organizes work by user workflow (horizontal) and priority (vertical).

## Key Concepts

A story map (Jeff Patton) organizes user stories in two dimensions:

- **Horizontal (left to right):** Activities in narrative/workflow order
- **Vertical (top to bottom):** Priority within each activity (must-have at top)

**Structure:** Backbone (activities) → User Tasks (by priority) → Details/Acceptance Criteria

**Walking Skeleton:** The highest-priority tasks across ALL activities — the minimal end-to-end functionality.

### When to Use
- Starting a new product or major feature
- Reframing an existing flat backlog
- Aligning stakeholders on scope and priorities
- Planning MVP or incremental releases

### When NOT to Use
- Single-feature projects (overkill)
- Backlog already well-understood and prioritized
- Technical refactoring with no user workflow to map

### Anti-Patterns
- Not a Gantt chart (priority, not time estimates)
- Not technical architecture (user workflow, not system layers)
- Not a project plan (discovery tool, not schedule)

## Facilitation

Use `cct:product-playbook` → `../product-playbook/references/facilitate-workshop.md` as the interaction protocol. If the user asks for single-shot output, skip multi-turn facilitation.

Use `template.md` for the facilitation agenda and outputs checklist.

## Workflow

5 adaptive questions, each with 3-4 enumerated options:

| Step | Question | Output |
|------|---------|--------|
| 0 | Gather context | Product scope, personas, existing materials |
| 1 | Define scope | Entire product / Feature area / Journey / Redesign |
| 2 | Identify users | Personas, workflow patterns |
| 3 | Generate backbone | 5-8 activities in narrative order |
| 4 | Generate tasks | 3-5 tasks per activity, prioritized vertically |
| 5 | Define release slices | Walking Skeleton + Release 2 + Release 3 |

> See `references/question-flow.md` for the full question text with enumerated options and examples.

> See `references/output-format.md` for the story map output template.

> See `references/examples-and-pitfalls.md` for worked examples (good and bad) and 5 common pitfalls.

## Key Principles

1. **Build across, not down** — Walking skeleton delivers thin slice across ALL activities, not one activity fully
2. **User narrative, not tech layers** — Backbone follows what users do, not system architecture
3. **Information radiator** — Maps should be visible/posted, not hidden in a tool
4. **Progressive detail** — Start with backbone + high-level tasks, refine later

## References

### External Frameworks
- Jeff Patton, *User Story Mapping* (2014) — Origin of story mapping framework
- Jeff Patton, "The New User Story Backlog is a Map" (blog) — Explains backbone concept

## Sources

| Source | Author | URL |
|--------|--------|-----|
| Product Manager Skills | Dean Peters | https://github.com/deanpeters/Product-Manager-Skills |
