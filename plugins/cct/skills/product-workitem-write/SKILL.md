---
name: product-workitem-write
description: "Writes one canonical work item (feature or user story, discovery or spike) from rough product input, and renders it in the requested `format`: `business` (technology-agnostic WHAT, ready for a GitHub issue) or `agent` (self-contained, spec-driven for a coding agent: EARS requirements, Gherkin acceptance, scope, Always/Ask/Never guardrails, machine-checkable Definition of Done). Use when the user says 'write a work item', 'write a developer ticket', 'agent-ready issue', 'write acceptance criteria', 'discovery ticket', 'schreib ein ticket'. Skip for: splitting an oversized epic into slices - use cct:product-epic-analyze. Skip for: the stakeholder requirements document - use cct:product-prd-write. Skip for: creating or updating the issue in Linear - use cct:linear-manage."
allowed-tools: "Read Write"
user_invocable: true
metadata:
  version: 2.0.0
  author: Maik Kummerfeldt
---

# Write a work item

Turn rough product input (brain-dumps, stakeholder requests, Slack snippets, meeting notes, doc excerpts) into **one canonical work item**: a Feature / User Story or a Discovery / Spike. The content is written once. The `format` decides how it is rendered:

- `business` (default): captures the **WHAT** (the problem and the outcome), stays technology-agnostic and leaves the HOW to developers. For a stakeholder request, a GitHub issue, a backlog item people read.
- `agent`: the same content as a spec a coding agent can finish alone and correctly on the first try. It adds EARS requirements, Gherkin proof, implementation anchors, guardrails and a runnable Definition of Done.

Choose the format from the request. If the item goes to a coding agent unattended (or the user says EARS, Gherkin, spec-driven, agent-ready), use `agent`. If it is unclear, ask in the batched questions. If both audiences need it, write the canonical content once and render both, never two diverging tickets.

Delegation: splitting a large epic into slices is `cct:product-epic-analyze`, which hands each slice back here for authoring. The stakeholder PRD is `cct:product-prd-write`, which links the work items written here. Pushing the finished item into Linear is `cct:linear-manage`.

## Language

- Write the work item itself in English, whatever the input language, unless the repo says otherwise.
- Mirror the user's language in the conversation (questions, explanations, next steps).

## Canonical content (both formats)

Problem, outcome (user story), acceptance (observable behaviours), rules, out of scope, open questions, constraints the user stated. Every fact lives in one place. The two renderings below only differ in shape and depth.

## Core principles

1. **Problem-first.** Lead with the problem and the value, never with a proposed solution.
2. **Observable outcomes.** Acceptance states what is true when done ("the operator can deactivate a feature without engineering support"), not implementation ("add an `is_active` column").
3. **Ask before you write.** When required information is missing, ask focused questions first, then draft. Never fill gaps with assumptions. Never fabricate acceptance criteria: derive them from stated outcomes, or ask.
4. **One item, one concept.** If the input mixes several problems or two personas (operator vs. buyer), say so and propose a split.
5. **Say everything once.** Acceptance criteria (for spikes, the questions to answer) are the scope: never restate them as an "in scope" list. Link inline; do not repeat links in a separate section. `Out of Scope` holds only genuine non-goals a reader might wrongly assume are included.
6. **No local paths in anything a reader outside your machine opens.** A `docs/FOO.md` or `.claude/plans/x.md` resolves to nothing in Linear, Jira or GitHub. Inline the load-bearing constraints, or link a resolvable URL (GitHub permalink pinned to a commit, hosted doc, Linear document).
7. **No vague numbers, no missing unhappy paths** (mandatory in `agent`, good practice in `business`): replace adjectives with numbers ("p95 < 200ms", not "fast") and define empty input, duplicates, permission denied and timeouts.

## Workflow

1. Detect the type (Feature/Story or Discovery/Spike) and the `format`. Ask if unclear.
2. Check for a linked document (design doc, plan, PRD, Outline page, click dummy), unless the input answers it. This decides whether the item gets a `## Rules` section.
3. Gap check against the required fields for the type.
4. Ask only the necessary clarifying questions, batched in one message. Skip anything the input answers. If the input covers the template, go straight to the draft.
5. Draft the item in the template for the chosen format.
6. Developer lens review (below).
7. Cut pass: go sentence by sentence and ask "would a developer act differently without this?". If not, delete. Check the limits for the format. This step makes the item shorter, never longer.
8. Offer next steps: adjust, split, tighten the acceptance, render the other format, hand to `cct:linear-manage`.

### Clarifying-question bank (ask only what is missing)

- **Problem and value:** what problem, who is affected, what it costs today, which initiative or OKR it serves.
- **Persona:** which user or role; operator (internal/admin) or buyer (end customer). Keep them in separate items.
- **Outcome:** how will we know this worked; what can the user do afterwards that they could not before.
- **Scope:** what is explicitly out; which edge cases matter.
- **Business constraints:** legal, multi-entity invoicing, BU-specific rules, deadlines tied to an event.
- **Dependencies:** related issues, docs, designs, click dummies, other teams.
- **Spikes only:** what decision or work does it unblock, is there a timebox, what deliverable (recommendation, ADR, doc, prototype).
- **Agent format only:** verify commands to run, repo and areas of the code, what the agent must never touch, which dependencies need approval.

## Format `business`

### Length and structure

Long items get skimmed, and skimmed items get built wrong. These limits apply to the overview, the part above `## Rules`.

- **Problem:** 2 to 3 sentences: the situation, who it hurts, why it matters. No lead-in sentences.
- **User story:** one sentence.
- **Acceptance criteria:** at most 7. One line, one behaviour each, no nested bullets, no parenthetical lists of conditions. Each states what is true when done, not every rule that makes it true.
- **Overview total:** about 250 words, links excluded.

Exact rules (states, conditions, limits, edge cases, copy) go in one of two places:

- **A linked document exists:** link it in one line, `Exact rules, states and copy: <link>`. Do not copy its rules in. Never write "if this item and the document differ, the document wins": that sentence means the content is duplicated.
- **No linked document exists:** the item is the only specification, so put the rules in `## Rules` below the acceptance criteria, grouped under the same headings as the acceptance criteria. One terse bullet per rule, no prose, no reasons. Use a `<details>` block only for long lists such as copy in several languages.

If acceptance exceeds 7 or `## Rules` passes about 15 bullets, do not compress further. Tell the user and offer two options: split the item, or move the rules into a separate spec document that the item links. The user decides.

### Template: Feature / User Story

Title: imperative and concise (`Allow Sales to toggle seasonal availability without engineering`). Include an optional section only when it has real content; never write a section that says "None".

```markdown
## Problem
<2-3 sentences: the situation today, who it hurts, why it matters. No solution here.>

## User Story
As a <persona>, I want <capability>, so that <outcome / value>.

## Acceptance Criteria
- [ ] <one observable behaviour, one line>
- [ ] <...at most 7>

<One of these two:>
Exact rules, states and copy: <link to design doc / plan / click dummy>

## Rules
**<same heading as a group of acceptance criteria>**
- <one rule, one line>

## Out of Scope            <!-- optional -->
- <only what a reader might reasonably assume is included>

## Open Questions          <!-- optional: only unresolved items -->
- <product or business decision still open>

**Release conditions:** <optional: what must be true before go-live, not before work starts>

## Technical context (provided)   <!-- optional: only what the user stated -->
- <constraint from the user>

---
**Suggested labels:** `type:feature` · `area:<...>`
```

### Template: Discovery / Spike

Title prefixed `Discovery:` or `Spike:` (`Discovery: separate shop-facing pricing tiers from the entitlement model`). Background 2 to 3 sentences, at most 7 questions. The spike is done when the questions are answered and the deliverable is shared, so it has no separate Definition of Done.

```markdown
## Background
<2-3 sentences: what triggered this, and the uncertainty or risk that makes investigation worthwhile.>

## Decision to unblock
<One sentence: the decision or downstream work this discovery enables.>

## Questions to answer
- <the concrete unknown, or a hypothesis to validate or reject>

## Deliverable
<What the spike produces: a written recommendation, an ADR, an Outline doc, a throwaway prototype. Add "Timebox: <n> days." if the user gave one.>

## Out of Scope            <!-- optional -->
- <only what a reader might reasonably assume is being investigated>

## Open Questions          <!-- optional: only unresolved items -->
- <unresolved item>

---
**Suggested labels:** `type:discovery` · `area:<...>`
```

### Guardrails for `business`

- Do not prescribe implementation (schemas, libraries, endpoints, architecture). If the user states a technical detail, capture it under `## Technical context (provided)` as their constraint, never as your invention.
- Do not merge two personas or two problems into one item.
- Do not pad. Omit a section with nothing real in it.
- Do not duplicate: no "Desired Outcome" repeating the user story, no "Dependencies & Links" list repeating inline links, no rules copied from a linked document.
- Do not pack rules into acceptance. A criterion with a list of conditions in parentheses is a rule: move it to `## Rules` or the linked document.

## Format `agent`

An agent implementing the item has no shoulder to tap. It cannot ask what "fast" means or where the spec lives; the item is its whole world. So the item must be self-contained, spec-first (what and why before how), verifiable ("done" is a command that passes and scenarios that go green) and right-sized (one coherent unit of work; recall degrades as context fills, so include the smallest set of high-signal tokens and link the full spec rather than pasting it).

### Hard rules

1. Never reference a local or unhosted document path (rule 6 above). Repo code paths (`src/ui/button.tsx`) are allowed only in the labelled "Implementation anchors (in-repo)" section, as guidance for the agent working in the checkout, never as the sole pointer to required spec context.
2. Never write vague acceptance (rule 7 above).
3. Never omit the unhappy paths.
4. Never tell the agent to modify tests to make them pass, to touch unrelated modules, or to add dependencies without approval.
5. Never use shortcuts the repo bans (for example an arbitrary-value Tailwind ban).

### Template (9 sections, in order)

Keep it tight: favour inlined essentials plus one resolvable link over pasted walls of code. The first-pass `business` content maps in directly: Problem becomes section 1, Rules and acceptance become sections 3 and 4, Out of Scope becomes section 5, Open Questions become section 9.

```markdown
# <Imperative title - "Add Dutch-auction countdown to lead detail">

## 1. Context & Why
2-4 sentences: the user/business outcome and why it matters. What and why, not how.

## 2. Source of Truth (inline first, then resolvable links - NO local paths)
- <Inlined load-bearing constraint 1>
- <Inlined load-bearing constraint 2>
- Full spec -> <GitHub permalink pinned to a commit, or hosted/Linear doc>

## 3. Requirements (EARS - one behaviour per line)
- Ubiquitous: The system shall <response>.
- Event:      When <trigger>, the system shall <response>.
- State:      While <state>, the system shall <response>.
- Optional:   Where <feature present>, the system shall <response>.
- Unwanted:   If <error/condition>, then the system shall <response>.

## 4. Acceptance Criteria (Gherkin - incl. unhappy paths)
Scenario: <name>
  Given <context with concrete data>
  When  <action>
  Then  <observable, numeric outcome>

## 5. Scope & Out-of-Scope
- In:  <bullets>
- Out: <bullets - prevents scope drift and over-building>

## 6. Implementation anchors (in-repo - for the coding agent)
File paths, modules, data models, key constraints. Strong heuristics, not a dictated algorithm.

## 7. Guardrails (Always / Ask / Never)
- Always: <run typecheck/lint/test; follow repo conventions; ...>
- Ask:    <before irreversible/risky steps; before adding deps>
- Never:  <modify tests to pass; touch unrelated modules; reference local doc paths; arbitrary values>

## 8. Definition of Done (machine-checkable)
- [ ] Tests written first (TDD), committed failing, then green, tests unchanged.
- [ ] `<exact verify commands>` pass (e.g. `pnpm typecheck && pnpm lint && pnpm test`).
- [ ] All Gherkin scenarios (incl. unhappy paths) pass.
- [ ] Acceptance criteria in section 4 satisfied.

## 9. Open Questions
- [NEEDS CLARIFICATION: <question>]  <- the agent must NOT guess these; resolve before implementing.
```

### The grammar lives in one file

EARS patterns, the Gherkin pairing, `[NEEDS CLARIFICATION: ...]` and the rule for which document gets which grammar: `references/requirements-grammar.md`. Read it before writing section 3 or 4. It is the single owner: `cct:sdlc-run`, `cct:linear-manage` and this skill all point at the same file. Never copy a pattern table into another skill, and never bolt EARS onto a `business` item: the two shapes answer different questions.

### Altitude, guardrails and Definition of Done

- Aim for specific enough to guide, flexible enough to leave the algorithm to the agent. Avoid both "make it nice" and a dictated line-by-line implementation. Give one or two canonical examples, the relevant data model and an explicit out-of-scope list.
- Behavioural boundaries go in section 7, but anything irreversible or security-relevant must be enforced outside the text (required status checks, protected branches, append-only grants). The item states the boundary; CI enforces it.
- The Definition of Done is observable and runnable. Prefer the TDD loop: tests first, confirm they fail, commit them as a checkpoint, implement to green without editing them. List the exact verify commands.

### Worked example

```markdown
# Build interaction primitives: button state matrix, toasts, global loading bar

## 1. Context & Why
Every surface needs consistent, accessible feedback primitives. Trust is the conversion; honest,
predictable interaction states are load-bearing.

## 2. Source of Truth (inline first)
- Button states: default / hover / active / focus-visible / loading / disabled. Focus = 2px purple
  ring (the only sanctioned ring). Reduced-motion disables transitions.
- Loading bar: 4px, fixed top, full-width, indeterminate; slides DOWN on navigation start, UP on
  completion; under prefers-reduced-motion = opacity fade only, never positional.
- Full spec -> https://github.com/<org>/<repo>/blob/<sha>/FRONTEND-GUIDELINES.md#5

## 3. Requirements (EARS)
- The system shall expose a Button supporting default/hover/active/focus-visible/loading/disabled.
- When a route transition starts, the system shall show a 4px top indeterminate bar sliding down.
- While prefers-reduced-motion is set, the system shall animate the bar by opacity only.

## 4. Acceptance Criteria (Gherkin)
Scenario: Loading bar respects reduced motion
  Given the OS sets prefers-reduced-motion: reduce
  When a navigation starts
  Then the bar appears via opacity only, with no positional slide

## 5. Scope & Out-of-Scope
- In:  Button, Toaster, TopLoadingBar primitives and their states.
- Out: page-level data wiring; skeletons (separate issue).

## 6. Implementation anchors (in-repo)
src/ui/{button,toaster,top-loading-bar}.tsx · tokens via Tailwind v4 @theme.

## 7. Guardrails (Always / Ask / Never)
- Always: token-only styling; respect prefers-reduced-motion; run typecheck/lint/test.
- Ask:    before adding any new dependency.
- Never:  arbitrary Tailwind values; outline:none without a visible replacement.

## 8. Definition of Done
- [ ] TDD: tests written first, committed failing, then green (unchanged).
- [ ] `pnpm typecheck && pnpm lint && pnpm test` pass.
- [ ] All Gherkin scenarios pass.

## 9. Open Questions
- [NEEDS CLARIFICATION: toast stack max and auto-dismiss durations (success vs error)?]
```

### Linear specifics

- Links in Linear must be resolvable URLs; inline the essentials so the item stands alone.
- Use structured labels, project and milestone fields so agents can query work. Assigning an issue to an agent delegates it; a human stays the owner of record.
- Workspace conventions (which repo, how to reference issues in commits and PRs, the review process) go into Linear "Agent Guidance" once, not into every item.
- Creating the issue (create minimal, then update with the full body, retry on 500s) is `cct:linear-manage`.

## Developer lens review (both formats)

Before handing the item over, re-read it as a developer who has never seen the context and ask: could I start work without messaging the PM back? Resolve from the existing context whatever you can, then surface only the gaps that genuinely block a developer and whose answer is a product or business decision. Keep the list short. Do not raise pure implementation questions (libraries, schema, indexing, framework) in `business`; those are the developer's call.

The review finds gaps; it does not add acceptance criteria. Ask the user about each gap. The answer goes into `## Rules` (or the linked document) and becomes an acceptance criterion only if it changes what "done" means. Unanswered gaps go into Open Questions.

- **Edge cases and failure states:** what happens when it fails, is empty, times out, or the user does something unexpected.
- **States and transitions:** the valid states and what moves an object or user between them.
- **Permissions:** who can and cannot do this; what an unauthorized attempt does.
- **Data and source of truth:** where the data comes from; what happens to existing or legacy data.
- **Boundaries:** expected volume, limits, business rules on amounts, dates or quantities.
- **Affected surfaces:** other flows, other BUs, downstream systems (invoicing, entitlements).
- **Testability:** can each criterion be verified objectively; is "done" unambiguous.
- **Non-functional needs:** audit/logging, security, response time. Capture the need, not the implementation.
- **Rollout:** feature-flagged, gradual, who validates once live.
