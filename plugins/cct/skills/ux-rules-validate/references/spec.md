# Spec Conformance

## Purpose

Check the design spec before facts and build.
Write the gaps, departures, and missing rules.

## Inputs

- `docs/ux/setup.md`.
- The skips for the mode (the shared `spec-folder.md`, section 2).
- The documents table from step 0 of the skill (found or missing, with paths).
- `<spec>/brief.md`.
- `<spec>/ia.md`.
- `<spec>/interaction.md`.
- `<spec>/screens.md`.
- `<spec>/prototype/index.md`, when present.
- Interaction guidelines from setup.
- Glossary from setup.
- Design system from setup.
- Component location and catalogue from setup.
- Screen goals from setup.
- the shared `rule-areas.md`.
- the shared `writing.md`.

## Steps

1. Read every spec file that exists.
2. Read the skip reasons (the shared `spec-folder.md`, section 2).
   If a source document is missing (no guidelines, glossary, design system or screen goals),
   say so at the top of the section it feeds, check against what exists, and propose the
   missing document as the first row of "Missing guidelines". Never invent its rules.
3. Check the interaction model against accepted rules.
   When the guidelines are a router (a page that sends each topic to its document), read the
   router first, then every page it names for each screen and state in the spec. Cite rule ids.
   Check every cell of the elements x interactions matrix against the rules. Then compare
   each element type with the same element on every other screen of the product (read the
   code and the existing specs): a difference is fixed in the spec or listed as a deliberate
   inconsistency for the owner.
   Check navigation: every move in `<spec>/ia.md` against the Back and place rules, every
   journey for dead ends and for its length against how often the job happens.
4. Check design system use against tokens, type, spacing, surfaces, colour meanings, and density.
   Every component the spec names is the design system's shared component, not a hand-built
   copy, and every value is a token, not a literal.
5. Build the component inventory from `<spec>/screens.md`.
6. For each component, search the code for current callers.
7. Count callers and list files.
8. State the implication for other screens.
9. Check every string against the glossary and writing rules.
10. Check screen goals, audience scenes, and object taxonomy.
11. List deliberate inconsistencies for the owner.
12. Propose missing guidelines and their home document.

## Output Template

Write `<spec>/conformance.md`.

```markdown
# Conformance

## Interaction model

| Screen or state | Rule | Result | Change or proposed rule |
|---|---|---|---|

## Design system

| Area | Departure | Impact | Fix |
|---|---|---|---|

## Component inventory

| Component | Status | Where the spec uses it | Callers today | Implication for other screens | Variant or new spec |
|---|---|---|---|---|---|

## Words

| String | Where | Result | Proposed word |
|---|---|---|---|

## Screen goals, audience, taxonomy

| Screen | Goal | Audience scene | Object or control home | Result |
|---|---|---|---|---|

## Deliberate inconsistencies

| Rule | Where | Why | Owner decision needed |
|---|---|---|---|

## Missing guidelines

| Proposed rule | Home document | Why needed |
|---|---|---|
```

## Checks

- The seven headings appear exactly and in order.
- Component callers include count and files.
- Every proposed new component names props and states.
- Every missing guideline names its home document.
- Deliberate inconsistencies stay undecided until the owner decides.

Sources: github.com/openai/plugins · github.com/ratacat/claude-skills
