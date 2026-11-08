# Information Architecture

## Purpose

Model the objects, routes, words, and navigation moves this change needs.
The routes come from `cct:ux-sitemap-create`, scoped to this change; this activity never
builds its own route tree.

## Inputs

- `<spec>/brief.md`.
- The asks (`intent.md` `## Asks`, or the brief's `## Owner Asks` in standalone mode).
- `docs/ux/setup.md`, especially router, screen goals, glossary, and guidelines paths.
- Route files, such as router config and `app/**/page.tsx`.
- Data schema files, when present.
- the shared `rule-areas.md`.
- the shared `writing.md`.

## Steps

1. Read the glossary, screen goals, router config, and route files.
2. Run `cct:ux-sitemap-create as-built scope:<spec> out:<spec>` for the routes this change
   touches. It cites every route with `file:line` and writes `<spec>/sitemap.md` and
   `<spec>/sitemap.json`.
3. Forage nouns from asks, the brief, UI strings, and schemas.
4. Sort nouns as object, attribute, instance or value, or set aside.
5. Run object tests.
   Check detail view, lifecycle, searchability, independence, and relationships.
6. Flag broken object types.
   Use shapeshifter, frankenobject, ghost, or zombie.
7. Build the nested object matrix.
   Include cardinality and role names.
8. Inventory CTAs across objects.
   Separate primary, secondary, overflow, and contra-CTAs.
9. Rank attributes per list row, card, and detail view.
10. Draw `stateDiagram-v2` for each object whose state changes actions.
11. Map object views to routes: run `cct:ux-sitemap-create proposed scope:<spec> out:<spec>`
    with this file's objects as its input.
12. Run `cct:ux-sitemap-create diff scope:<spec> out:<spec>`: the changes, and an additive
    redirect for every moved address. The whole-app `docs/ux/sitemap.md` is not touched now;
    the PR that builds the change runs `cct:ux-sitemap-create` on the whole app when it ships.
13. Write the screen inventory.
    For each screen: its purpose (from screen goals), the job stories it serves, how you arrive,
    and where you can go next. A screen that serves no job story is a finding.
14. Write one journey per job story: the screens in order, the control used at each step, and
    the number of moves. The most frequent jobs take the fewest moves; say how often each job
    happens (every session, weekly, rarely) and why its path has the length it has.
15. Write the move table.
    Include lateral, forward, up, and back.
    Every move names WHY someone makes it: the job story or ask (A<n>) it serves.
    A move with no why is removed or becomes a question for the owner.
16. Define what Back restores.
    Include scroll, selection, search, playback, and filters.
17. Build the alias table.
    Keep one word per meaning.

## Output Template

Write `<spec>/ia.md`.

~~~markdown
# Information Architecture

## Objects

| Object | Definition | Status | Need |
|---|---|---|---|

## Alias Table

| Canonical | Rejected | Reason |
|---|---|---|

## Nested Object Matrix

| Parent | Child | Cardinality | Role name | Rank |
|---|---|---|---|---|

## CTA Inventory

| Object | Verb | Control | Type | Contra-CTA |
|---|---|---|---|---|

## Attribute Priority

| View | Attribute | Rank | Reason |
|---|---|---|---|

## State Diagrams

```mermaid
stateDiagram-v2
```

## Sitemap

Written by `cct:ux-sitemap-create` into `<spec>/sitemap.md` and `<spec>/sitemap.json`, scoped
to this change: As built, Proposed, Changes from as built, Redirects. Link it here; do not copy
its tables.

## Screen Inventory

| Screen | Route | Purpose | Job stories served | Arrive from | Go next to |
|---|---|---|---|---|---|

## Navigation Tree

<indented tree or mermaid graph of the proposed sitemap: sections, screens, detail views, and
which are reached laterally (rail, tabs) and which forward (open a row)>

## Journeys

| Job story | How often | Path (screen → control → screen …) | Moves | Why this length |
|---|---|---|---|---|

## Move Table

| From | Control | To | Type | Why (job story or ask) | Back target | Restores |
|---|---|---|---|---|---|---|

## Open Questions

| Question | Recommended answer | Why it matters |
|---|---|---|
~~~

## Checks

- Every route exists in a route file or is marked new (the sitemap's `source` or `proposed`).
- Every moved address has a redirect in the sitemap's Redirects table.
- The sitemap's checks SM-1 to SM-12 left no finding unanswered.
- No orphan object remains.
- No operation uses two verbs.
- Every label is in the glossary or proposed in the alias table.
- Up never exits the app.
- Every forward move has a back target.
- Every move has a why; every job story has a journey; every screen serves a job story.
- No dead end: every screen has a way on and a way back.
- A frequent job never takes more moves than a rare one without a written reason.
- Every object traces to a need.
- The file captures only the residue.

## Skip Rule

Skip when the `ia` skip is set (the shared `spec-folder.md`, section 2).
The reason is already recorded; write no file.

## Optional Skills

Used only when installed; the activity runs fully without them.

- `cct:ux-jobs-write`.

Sources: github.com/jamiemill/layers-skills · github.com/s1dd4rth/ooux-skill · developer.android.com/guide/navigation/principles
