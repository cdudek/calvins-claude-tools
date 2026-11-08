# Interaction

## Purpose

Specify the flows, states, keys, feedback, saving, leaving, undo, and errors.
Every pointer action gets keyboard and menu routes.

## Inputs

- `<spec>/brief.md`.
- `<spec>/ia.md`.
- `docs/ux/setup.md`.
- `docs/ux/interaction-guidelines.md`, or the path named in setup.
- the shared `rule-areas.md`.
- the shared `writing.md`.

## Steps

1. Write one wireflow per job story.
2. Start every arrow at the control that triggers it.
3. List every screen in the flow.
4. Write a state table per screen.
5. Include at least default, loading, empty, partial, error, and disabled-with-reason.
6. Add product-specific states from IA state diagrams.
7. Add a mermaid `stateDiagram` for each screen or object with more than three states.
8. Write the elements x interactions matrix: one row per element type on each screen (row,
   tile, card, pad, track, chip, field, header, empty area), one column per gesture: click,
   double-click, drag, drop onto it, hover, right-click or More, keys, selection (single, Shift,
   Command). Every cell gets the outcome or "nothing", and the guideline rule it follows.
   The same element type behaves the same on every screen unless conformance records why not.
9. For every pointer action, write keyboard and menu routes.
10. For every action, define save, leave, and undo behaviour.
11. Cite the guideline rule for each action.
12. Mark feedback as silent, visible, or ask first.
13. Write every error as event, consequence, and action.

## Output Template

Write `<spec>/interaction.md`.

~~~markdown
# Interaction

## Wireflows

### <Job story>

| From control | Action | To screen or state | Notes |
|---|---|---|---|

## State Tables

### <Screen>

| State | Entry or trigger | What the user sees | Words | Actions with key | Exit |
|---|---|---|---|---|---|

## State Diagrams

```mermaid
stateDiagram
```

## Elements x Interactions

| Screen | Element | Click | Double-click | Drag | Drop onto | Hover | Right-click / More | Keys | Selection | Rules |
|---|---|---|---|---|---|---|---|---|---|---|

## Action Behaviour

| Action | Pointer route | Keyboard route | Menu route | Save | Leave | Undo | Guideline |
|---|---|---|---|---|---|---|---|

## Feedback

| Action | Feedback | Reason | Where shown |
|---|---|---|---|

## Errors

| Event | Consequence | Action |
|---|---|---|

## Open Questions

| Question | Recommended answer | Why it matters |
|---|---|---|
~~~

## Checks

- Every job story has one wireflow.
- Every arrow starts at a control.
- Every screen has the required states.
- Every pointer action has keyboard and menu routes.
- Every cell of the elements x interactions matrix is filled, "nothing" included.
- The same element type has the same row on every screen, or the difference is listed for
  conformance.
- Every save, leave, and undo rule cites a guideline.
- Every error uses event, consequence, and action.
- Feedback never hides essential information in a disappearing message.

## Skip Rule

Skip when the `interaction` skip is set (the shared `spec-folder.md`, section 2).
The reason is already recorded; write no file.

## Optional Skills

Used only when installed; the activity runs fully without them.

- `cct:ux-states-design`.
- `cct:ux-copy-write`.
- `cct:design-system-write`.

Sources: nngroup.com/articles/wireflows · github.com/openai/plugins
