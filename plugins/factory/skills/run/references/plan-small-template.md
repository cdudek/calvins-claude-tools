# Plan: 2026-11-25-fix-saved-search-reload

A bug or a small feature is a plan with `kind`, one milestone and one task. Copy this file to `changes/<slug>/plan.md`. It passes `check-plan.py` as written, once `delta.md` and `intent.md` exist next to it.

The other files are short too:
- `intent.md`: Problem and Outcome in one or two sentences ([intent-template.md](intent-template.md)).
- `delta.md`: one to three requirements, each citing an intent id, each a line like `- req-<n>: When the page reloads, the system shall show the saved search with its filters. [outcome-<n>]`
- One holdout scenario outside the repo, with `milestone: M1`.

## Outcome
After a reload the saved search opens with its filters. Covers the reload rule (req-4).

## Inputs
- **Delta:** `changes/2026-11-25-fix-saved-search-reload/delta.md`, revision 1.
- **Base branch:** `main`.
- **Fast checks:** `npm run lint`, `npm run typecheck`, `npm test`.
- **Deploy:** on merge to `main`.

## Not in scope
- Any change to how searches are saved.

## Milestones
### M1 backend: reload keeps the filters
- **Result:** the failing test passes and nothing else changes.
- **Validation:** `npm test -- saved-search-reload` prints 1 passed.
- **Recovery:** revert the PR.
- **T1:** one builder. Covers the reload rule (req-4). Owns `src/api/saved-search.ts`, `src/api/saved-search.test.ts`.

## Bug flow (`kind: bug`)
1. The builder's first commit holds only the failing test.
2. The coordinator shows it fails on `main` and records that commit SHA.
3. The fix pass runs `test-integrity.sh` with `--pin <that sha>`, so the test cannot change.

## Risks
- **Riskiest step:** the fix touches the filter parser that three screens share. We notice in the verifier's two neighbouring flows.
- **Rejected:** rewriting the parser (too big for this appetite); patching only the reload path was chosen.

## Turns
- **Per milestone session:** 8 goal turns.

```json factory
{"change": "2026-11-25-fix-saved-search-reload", "base": "main", "goalTurns": 8, "kind": "bug",
 "requirements": ["req-4"],
 "milestones": [
   {"id": "M1", "layer": "backend", "covers": ["req-4"],
    "tasks": [
      {"id": "T1", "covers": ["req-4"], "files": ["src/api/saved-search.ts", "src/api/saved-search.test.ts"], "check": "npm test -- saved-search-reload", "needs": []}]}]}
```

## Progress log
<!-- coordinator only; one entry per stop -->
