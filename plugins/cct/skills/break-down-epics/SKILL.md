---
name: break-down-epics
description: "Split a single oversized epic into shippable user stories using Humanizing Work's nine split patterns (workflow steps, business rules, data variations, etc.). Use when the user names a specific epic that's too big. Triggers on: 'break down this epic', 'split user stories', 'story splitting', 'epic too large', 'vertical slicing'. Skip for: full backlog mapping with narrative flow — use run-story-mapping. Skip for: PRD authoring — use develop-prd."
allowed-tools: "Read Write"
user_invocable: true
metadata:
  version: 1.0.0
  author: Dean Peters
---


## Purpose

Guide product managers through breaking down epics into user stories using Richard Lawrence's Humanizing Work methodology -- a systematic, flowchart-driven approach that applies 9 splitting patterns sequentially. Ensures vertical slicing (end-to-end value) rather than horizontal slicing (technical layers).

This is not arbitrary slicing -- it is a proven, methodical process that starts with validation, walks through patterns in order, and evaluates results strategically.

## Core Principles

A user story is "a description of a change in system behavior from the perspective of a user." Splitting must maintain **vertical slices** -- work that touches multiple architectural layers and delivers observable user value -- not horizontal slices addressing single components.

**Meta-Pattern (applies across all 9 patterns):**
1. Identify the core complexity
2. List all variations
3. Reduce variations to **one complete slice**
4. Make other variations separate stories

## The 9 Splitting Patterns (In Order)

1. **Workflow Steps** -- Thin end-to-end slices, not step-by-step
2. **Operations (CRUD)** -- Create, Read, Update, Delete as separate stories
3. **Business Rule Variations** -- Different rules = different stories
4. **Data Variations** -- Different data types/structures
5. **Data Entry Methods** -- Simple UI first, fancy UI later
6. **Major Effort** -- "Implement one + add remaining"
7. **Simple/Complex** -- Core simplest version first, variations later
8. **Defer Performance** -- "Make it work" before "make it fast"
9. **Break Out a Spike** -- Time-box investigation when uncertainty blocks splitting

For detailed instructions, agent prompts, examples per pattern, and Cynefin domain considerations, see `references/splitting-patterns.md`.

### Facilitation Source of Truth

Use `cct:product-playbook` → `../product-playbook/references/facilitate-workshop.md` as the default interaction protocol. It defines session entry modes, one-question turns, progress labels, and numbered response options.

## Workflow

### Step 0: Gather Epic Context
Collect epic title/ID, description, acceptance criteria, target persona, and rough estimate. See `references/splitting-patterns.md` for the full prompt.

### Step 1: Pre-Split Validation (INVEST Check)
Validate the story satisfies Independent, Negotiable, Valuable, Estimable, and Testable (skip "Small" -- that is what splitting solves). If the story fails "Valuable," STOP and reframe. See `references/splitting-patterns.md` for detailed check questions.

### Step 2: Apply Splitting Patterns Sequentially
Work through the 9 patterns in order. For each, ask "Does this apply?" If yes, generate splits. If no, continue to the next pattern. See `references/splitting-patterns.md` for full pattern details with examples.

### Step 3: Evaluate Split Quality
Check: (1) Does the split reveal low-value work you can deprioritize? (2) Does it produce roughly equal-sized stories? If neither, try a different pattern. See `references/splitting-patterns.md` for evaluation criteria.

### Output
Generate a structured story breakdown using the template in `references/output-template.md`. Include epic context, pattern applied, stories with acceptance criteria, split evaluation, and INVEST validation.

## Anti-Patterns

- **Horizontal slicing:** "Story 1: Build API. Story 2: Build UI." -- neither delivers user value
- **Step-by-step workflow splits:** Each story must cover the full workflow with increasing sophistication
- **Forcing a pattern:** If it does not apply, say NO and continue to the next pattern
- **Not re-splitting:** If stories are still >5 days after splitting, restart at Pattern 1
- **Skipping evaluation:** Always ask "Does this reveal work we can kill or defer?"

See `references/pitfalls.md` for detailed pitfall descriptions with symptoms and fixes.

## Practice & Skill Development

Teams reach fluency in 2.5-3 hours across multiple practice sessions. Start by analyzing recently completed features -- hindsight makes patterns obvious. Walk completed work through the flowchart to build shared vocabulary.

## Examples

See `references/examples.md` for 4 worked examples:
- Pattern 1: Workflow Steps (blog publishing)
- Pattern 2: CRUD Operations (user profiles)
- Pattern 7: Simple/Complex (flight search)
- Iterative splitting with multiple patterns (checkout flow)

## References

### External Frameworks
- Richard Lawrence & Peter Green, *The Humanizing Work Guide to Splitting User Stories* -- Complete methodology
- Bill Wake, *INVEST in Good Stories* (2003) -- Quality criteria
- https://www.humanizingwork.com/the-humanizing-work-guide-to-splitting-user-stories/

---

## Sources

| Source | Author | URL |
|--------|--------|-----|
| Product Manager Skills | Dean Peters | https://github.com/deanpeters/Product-Manager-Skills |
