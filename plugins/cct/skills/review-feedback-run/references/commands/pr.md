---
description: Pick up an existing PR end-to-end — gather feedback + CI + staleness, enter worktree, run the shared execution tail, finalize, then propose + apply per-thread resolve/comment actions
---

The user input is: $ARGUMENTS

Parse the input as: `<pr_number>` (a number, or a PR URL — extract the number).

## Step 1: Gather PR State

Follow `references/pr-gather.md` to run the 5 gather scripts, classify CI failures, and parse all sections.

If there are no review comments, no issue comments, and no failing checks, AND the branch is up to date (not behind base), report "nothing to address" and stop. If the branch is behind base but there are otherwise no findings, continue — the merge is handled in Step 3's execute.

## Step 2: Enter Worktree

Follow `references/pr-worktree.md` to check or enter the PR's worktree.

## Step 3: Investigate, triage, execute, verify, report (the tail, steps 1–5)

Run `references/execution-tail.md` with `GATE=interactive`.

Layer PR-specific handling onto its first three steps (Investigate, Triage, Execute) as below; the tail's Verify and Report steps run as-is. The tail's own Report is the in-loop summary; the PR-level finalize, thread actions, and final summary table happen in Steps 4-7 after the tail returns. When the tail's step 5 (Report) returns, continue to Step 4 below.

- **Investigate** — beyond the review/issue comments, fold in:
  - CI failures: category `CI failure`, action from the flaky check (`FIX` / `INVESTIGATE` / `FLAKY → Linear`).
  - Staleness: category `Staleness`, action `MERGE` if behind base (existing PR — merge commit, not rebase).
- **Triage** — header the table with PR context, and include the PR-specific actions (`FLAKY → Linear`, `MERGE`) alongside the universal ones:
  ```
  ## PR #{number}: {title}
  Branch: {head} → {base}
  ```
- **Execute** — bracket the tail's code execution as pre-step → inner → post-step (the three sub-items below are *not* a flat sequence):
  1. **Before the tail's Execute — merge base** (if `MERGE` selected) — follow `references/pr-finalize.md` → *Merge base*. On conflicts, stop and surface them; do not force-resolve.
  2. **Code changes via execute-phases.md (Phase RED/GREEN)** — the tail's Execute step runs `references/execute-phases.md`. `MERGE` is a PR-only verb handled by sub-item 1 here, not by execute-phases.md.
  3. **After the tail's Execute and before the tail's Verify — flaky tickets** — for each `FLAKY → Linear` item, follow `references/create-linear-ticket.md` (Title: `Flaky test: {test_name}`; Description: failure log snippet + CI context). If ticket creation fails for all retries (Linear MCP unavailable and the `gh issue create` fallback also fails), surface the failure to the user before handing back to the tail. The tail then continues into its Verify step (step 4) and Report step (5).

## Step 4: Propose Thread Actions

Follow `references/pr-resolve-threads.md` → *Propose thread actions*: build the proposal table from the gathered `REVIEW_THREADS`, the triage actions, and the files/lines modified during the tail's Execute step (Phase GREEN); present it; confirm with the user (with override). No GitHub mutations run here — the SHA needed for "comment+resolve" replies isn't pushed until Step 5.

## Step 5: Finalize (push + body)

Follow `references/pr-finalize.md` → *Finalize (push + body)* (update PR body + push + capture HEAD SHA). Re-request review intentionally moves to Step 7 so the reviewer arrives to a fully-annotated state.

## Step 6: Apply Thread Actions

Follow `references/pr-resolve-threads.md` → *Apply thread actions* against the confirmed plan from Step 4, using the SHA captured in Step 5 for `comment+resolve` reply bodies.

## Step 7: Re-request Review (optional)

Now that the PR has been pushed and threads annotated/resolved, ask the user:

```
Re-request review from existing reviewers? (yes/no)
```

If `yes` → follow `references/pr-finalize.md` → *Re-request review*.
If `no` (or empty) → skip.

Then report the final summary table (counts per action verb + any errors from Step 6).

## Error Handling

**PR not found** — verify the PR number and check `gh auth status`; ensure the token has `repo` scope.

Merge conflicts, Linear unavailability, and per-thread mutation failures are handled per `references/policies.md` → Error handling. Abort an in-progress merge with `git merge --abort`.

## Example

"address feedback on PR 47" / "continue PR 47": gather PR state + CI + staleness (Step 1) → enter worktree (Step 2) → the tail presents a table (e.g. 2 review comments `ADD TEST`, 1 lint failure `FIX`, 1 flaky test `FLAKY`, 1 behind-base `MERGE`); user selects; merge base → Phase RED/GREEN → flaky ticket → verify (tail step 4) → report (tail step 5) → propose thread actions (outer Step 4) → push + body (outer Step 5) → apply resolves/replies (outer Step 6) → re-request (outer Step 7).
