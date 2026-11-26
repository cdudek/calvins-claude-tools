# Plan: 2026-11-24-saved-searches

Copy this file to `changes/<slug>/plan.md` and replace the example. It passes `check-plan.py` as written, once `intent.md` and a `delta.md` that lists the three requirements (req-1 to req-3, each citing an intent id) sit next to it. Every milestone is detailed with tasks, so it also passes `check-plan.py <plan.md> --all` and runs under `--all`; a milestone without tasks cannot. A broken copy is your edit. For a bug or small feature use `plan-small-template.md`.

## Outcome
A signed-in user saves a search and reopens it from the sidebar with the same filters. Covers saving a search (req-1), reopening it (req-2) and keeping it private (req-3).

## Inputs
- **Intent and delta:** `changes/2026-11-24-saved-searches/intent.md` and `delta.md`, revision 2, approved at one SHA (written in the first progress entry).
- **Design boards:** the Claude Design link for "Saved searches", boards 1 to 4, approved with the plan.
- **Base branch:** `main`.
- **Run:** `npm run dev` on port 3000; each worktree uses its own port.
- **Setup and preflight:** `npm ci` in every new worktree; `command -v npm` proves the tool exists.
- **Fast checks:** `npm run lint`, `npm run typecheck`, `npm test`.
- **Deploy:** on merge to `main`, ready when `/readyz` answers at the serving SHA. (Or: deploy is disabled, SHIPPED is merge plus CI.) `deployOnMerge` is false here.
- **Merge and branches:** `merge` is `auto`; no `integration` branch (add `"integration": "integration/<name>"` to the block to route milestone PRs there and release once into `main`). No `hold`; add one when an owner action is known in advance.

## Not in scope
- Sharing a saved search with another user.
- Renaming the existing "Recent searches" list.

## Milestones
### M1 components: SavedSearchChip and SaveButton
- **Result:** both components render on `/preview/saved-search` with sample data, at 375 and 1280 px.
- **Validation:** `npm test -- SavedSearch` prints 6 passed; the preview page shows both states.
- **Recovery:** revert the PR; nothing else imports the components yet.
- **Tasks (parallel):**
  - **T1:** `SavedSearchChip` with default, hover, selected, long-name states. Covers reopening a search (req-2). Owns `src/ui/SavedSearchChip.tsx`, `src/ui/SavedSearchChip.test.tsx`.
  - **T2:** `SaveButton` with idle, saving, saved, error states. Covers saving a search (req-1). Owns `src/ui/SaveButton.tsx`, `src/ui/SaveButton.test.tsx`. Edits the existing `src/ui/Button.test.tsx` (its `allowTestEdits`).
  - **T3:** the preview page with sample data. Covers saving and reopening (req-1, req-2). Owns `src/app/preview/saved-search/page.tsx`.

### M2 backend: table, create and list endpoints
- **Result:** a signed-in user creates and lists only their own saved searches through the API.
- **Validation:** `npm test -- saved-searches` prints 5 passed.
- **Recovery:** revert the PR, or a forward fix migration where the repo is forward-only (a down step only where the repo allows it).
- **Tasks:**
  - **T4:** table `saved_searches`, one migration, create and list endpoints. Covers storing and privacy (req-1, req-3). Owns `db/migrations/0042_saved_searches.sql`, `src/api/saved-searches.ts`, `src/api/saved-searches.test.ts`.
- Risky (data): its `surface` lists the list endpoint and the digest mail, and its `deferred` item carries a probe.

### M3 screens: sidebar list and save flow
- **Result:** the sidebar lists saved searches; the save button on the search screen stores one and reopens it with the same filters.
- **Validation:** `npm test -- SearchScreen` prints 4 passed; the verifier runs the saved-searches journey.
- **Recovery:** revert the PR; the API from M2 stays unused.
- **Tasks:**
  - **T5:** sidebar list and the save flow. Covers reopening and privacy (req-2, req-3). Owns `src/app/search/Sidebar.tsx`, `src/app/search/SearchScreen.tsx`, `src/app/search/SearchScreen.test.tsx`.

## Risks
- **Riskiest step:** the M2 migration on a large table. We notice in the migration dry run; the recovery touches only the new table.
- **Options rejected:** storing searches in local storage (lost on a new device, breaks the privacy rule (req-3)); a JSON column on the user row (cannot list or limit cheaply).
- **Users:** saved filters that no longer exist after a schema change. The verifier runs a scenario with a removed filter.

## Owner decisions
1. **Limit per user:** decided, 20 saved searches. Over the limit the save button shows an error and stores nothing.

## Turns
- **Per milestone session:** 12 goal turns.
- **Critical path:** M1, M2, M3 in order.

```json factory
{"change": "2026-11-24-saved-searches", "base": "main", "goalTurns": 12,
 "setup": "npm ci", "preflight": ["command -v npm"], "deployOnMerge": false,
 "requirements": ["req-1", "req-2", "req-3"],
 "milestones": [
   {"id": "M1", "layer": "components", "covers": ["req-1", "req-2"],
    "tasks": [
      {"id": "T1", "covers": ["req-2"], "files": ["src/ui/SavedSearchChip.tsx", "src/ui/SavedSearchChip.test.tsx"], "check": "npm test -- SavedSearchChip", "needs": []},
      {"id": "T2", "covers": ["req-1"], "files": ["src/ui/SaveButton.tsx", "src/ui/SaveButton.test.tsx"], "check": "npm test -- SaveButton", "needs": [], "allowTestEdits": ["src/ui/Button.test.tsx"]},
      {"id": "T3", "covers": ["req-1", "req-2"], "files": ["src/app/preview/saved-search/page.tsx"], "check": "npm run typecheck", "needs": []}]},
   {"id": "M2", "layer": "backend", "covers": ["req-1", "req-3"], "risky": true,
    "surface": [
      {"exposure": "GET /api/saved-searches lists only the caller's rows", "requirement": "req-3", "scenario": "scenario-2 another user sees none"},
      {"exposure": "weekly digest mail", "requirement": "req-3", "deferred": {"reason": "no digest mail exists yet", "probe": "rg -n digest src/ shows no match"}}],
    "deferred": [{"item": "sharing a saved search", "reason": "out of appetite", "probe": "rg -n share src/app shows no sharing route"}],
    "tasks": [
      {"id": "T4", "covers": ["req-1", "req-3"], "files": ["db/migrations/0042_saved_searches.sql", "src/api/saved-searches.ts", "src/api/saved-searches.test.ts"], "check": "npm test -- saved-searches", "needs": []}]},
   {"id": "M3", "layer": "screens", "covers": ["req-2", "req-3"],
    "tasks": [
      {"id": "T5", "covers": ["req-2", "req-3"], "files": ["src/app/search/Sidebar.tsx", "src/app/search/SearchScreen.tsx", "src/app/search/SearchScreen.test.tsx"], "check": "npm test -- SearchScreen", "needs": ["T4"]}]}]}
```

## Progress log
<!-- coordinator only; one entry per stop. The first entry records `approved: <sha>`. Each entry adds firstPass, planRevisionsAfterApproval, diffMatchesPlan. -->
