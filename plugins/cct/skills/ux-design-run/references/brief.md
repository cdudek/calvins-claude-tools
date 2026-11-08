# Brief

## Purpose

Turn the owner's asks into the design brief for this change.
Each ask stays traceable.

## Inputs

- The asks: sdlc mode, the change's `intent.md` `## Asks`; standalone mode, the `## Owner Asks`
  table just collected (the shared `spec-folder.md`, section 4).
- The size and skips (the shared `spec-folder.md`, section 2).
- `docs/ux/setup.md`, especially audience scenes and screen goals.
- The design file named by `decisions.json` `design`, when present.
- the shared `writing.md`.

## Steps

1. Copy each A<n> from the asks exactly.
   Then search for briefs already given about the same screens: the tracker (parked and backlog
   issues), old ticket exports, archived changes and the design files `setup.md` names. Each
   earlier decision found becomes an ask with its source, copied into `<spec>/asks/`. A brief the
   owner gave once is never re-asked and never silently dropped.
2. Read the audience scenes from `setup.md`.
3. Write job stories in this form:
   `When ..., I want to ..., so I can ...`.
4. Tie each job story to one audience scene.
5. Tie each job story to the asks it answers.
6. Set appetite to the size.
7. List no-gos from the asks, setup, guidelines, and hard rules.
8. Define visible success.
   State what the owner sees when the change works.
9. Map every ask.
   If an ask is set aside, give the reason.

## Output Template

Write `<spec>/brief.md`. In standalone mode it opens with the frontmatter and the `## Owner Asks`
table from the shared `spec-folder.md`, section 4, in place of the table below.

```markdown
# Brief

## Owner Asks

| Ask | Source | Words | Answered by |
|---|---|---|---|

## Job Stories

| Job | Audience scene | Asks answered | Visible success |
|---|---|---|---|

## Appetite

Size: <none | S | M | L>

## No-Gos

| No-go | Source | Reason |
|---|---|---|

## Visible Success

<what the owner sees when it works>

## Ask Map

| Ask | Status | Where answered | Reason if set aside |
|---|---|---|---|

## Open Questions

| Question | Recommended answer | Why it matters |
|---|---|---|
```

## Checks

- Every A<n> appears once in the ask map.
- Every job story has one audience scene.
- Every job story uses the `When ..., I want to ..., so I can ...` form.
- Appetite equals the size.
- Set-aside asks have reasons.
- No-gos come from a source.

## Skip Rule

Skip when the `brief` skip is set (the shared `spec-folder.md`, section 2).
The reason is already recorded; write no file. Standalone mode is the exception: the file still
holds the frontmatter, the asks and the ask map (`spec-folder.md`, section 4).

## Optional Skills

Used only when installed; the activity runs fully without them.

- `cct:ux-brief-write`.
- `cct:ux-jobs-write`.
- `cct:ux-copy-write`.

Sources: nngroup.com/articles/wireflows
