---
description: Thread-resolution recipes — propose thread actions (build table, confirm, no GitHub mutations), then apply thread actions (run the confirmed plan). Each H2 is dispatched by name from references/commands/pr.md.
---

# PR Resolve Threads

Two named recipes, dispatched from `references/commands/pr.md`. Run only the block named by the active step:

- **Propose thread actions** — build the proposal table, confirm with the user. No GitHub mutations.
- **Apply thread actions** — run the confirmed plan against GitHub.

GitHub convention is that **the reviewer** resolves their own threads. Auto-resolve by the PR author is acceptable for mechanical fixes (typo, lint, exact line match) but risky when the fix is broader or interpretive — a wrongly-resolved thread hides a still-valid concern. The proposal table surfaces the decision so the user can override per thread.

## Propose thread actions

> Do NOT call any GitHub mutation here. All resolve/reply operations run in *Apply thread actions* (after the push completes and the new HEAD SHA is captured).

### Inputs

Build a per-thread record from:

- `REVIEW_THREADS` section of `gather-pr-feedback.sh` (see `pr-gather.md`) — gives `id`, `isResolved`, `isOutdated`, `viewerCanResolve`, `pr_author`, `comments_truncated`, and per-comment `path`, `line`, `body`, `author`
- The triage action assigned per comment (from the execution tail's triage)
- The list of files modified by the review-fix-implementer agents (from the tail's execute) and the modified hunks/lines

Filter the actionable table by:

- **Omit entirely** (not in any output): `isResolved: true`
- **Move to Informational section** (not actionable, but listed for awareness): `viewerCanResolve: false`

### Confidence algorithm

Compute `confidence` (0–100) per thread:

| Conditions | Confidence |
|---|---|
| action ∈ {FIX} AND path matches a modified file AND line within 5 of a modified hunk AND body ≤ 200 chars AND comment has no `?` | **90** |
| action ∈ {FIX, ADD TEST} AND path matches a modified file AND line within 5 of a modified hunk | **80** |
| action ∈ {FIX, ADD TEST} AND path matches a modified file (line drift larger) | **65** |
| action = REFACTOR AND path matches a modified file | **50** |
| action = INVESTIGATE | **35** |
| action ∈ {DISCUSS, DEFER, SKIP} | **20** |
| no action assigned (thread not addressed) | **0** |

### Proposal mapping

Default action from confidence:

| Confidence | Proposed action |
|---|---|
| ≥ 80 | `resolve` (silent — no reply) |
| 50–79 | `comment+resolve` — reply `"- **Addressed:** {sha}"` then resolve |
| 20–49 | `comment-only` — reply with one-line note; do **not** resolve |
| < 20 | `leave` — no GitHub action |

### Hard guardrails

These OVERRIDE the proposal mapping above. Apply in order:

1. `action = SKIP` → propose `leave`. Reviewer's concern wasn't addressed; thread stays open.
2. `action = DEFER` → propose `comment-only` with body `"- **Deferred:** Tracked as Linear ticket {ticket_id}; remains outside this PR."`; never resolve.
3. `action = DISCUSS` → propose `comment-only` with the DISCUSS reasoning; never resolve.
4. Thread's first comment `author == pr_author` (PR author commented on their own PR) → propose `leave` (these are notes, not review requests).
5. `viewerCanResolve = false` → propose `leave` (no permission; show as informational).
6. `isOutdated: true` → cap proposed action at `comment-only`. The diff context shifted since the thread was created — silently resolving may hide a concern that now applies to a different line, and the reviewer should re-anchor it.
7. Comment path is NOT in modified files AND action was supposed to FIX it → cap proposed action at `comment-only`; the fix may not have reached the right place.

### Presenting the proposal table

```
## Thread Resolution Proposals (PR #{number})

| T# | Thread (file:line) | First comment (60 chars) | Action  | Conf | Proposal        | Why |
|----|---------------------|-------------------------|---------|------|-----------------|-----|
| T1 | pr.md:42           | "use Math.PI not 3.14"  | FIX     | 90   | resolve         | mechanical, file+line match, fix committed |
| T2 | lib.ts:10          | "this could leak"        | INVEST. | 35   | comment-only    | broader concern, investigation only |
| T3 | y.ts:99            | "what about case X?"     | DISCUSS | 20   | comment-only    | DISCUSS — reviewer should decide |
| T4 | z.ts:5             | "rename Foo"             | FIX     | 80   | resolve         | file+line match, fix committed |
| T5 | (other) old.ts:1   | "consider tests"         | DEFER   | 20   | comment-only    | filed as ENG-123 |
```

Threads already resolved (`isResolved: true`) and threads with `viewerCanResolve: false` are listed in a separate "Informational" section below the actionable table, NOT in the main table.

### Override prompt

After the table, prompt:

```
Confirm thread actions (enter = accept proposed, or override):

  all-resolve         — silently resolve every actionable thread
  all-comment+resolve — comment + resolve every actionable thread
  all-comment-only    — comment all, do not resolve any
  all-leave           — do nothing (skip thread step entirely)
  T1=resolve T2=leave — per-thread overrides (space-separated)
  edit                — open the table for inline edits in $EDITOR
  abort               — skip thread resolution; PR is already pushed
```

Verbs must exactly match the canonical verbs from the Proposal mapping table: `resolve`, `comment+resolve`, `comment-only`, `leave`.

Parse the response:

- Empty / `enter` → apply each thread's proposed action
- `all-<verb>` → override every actionable row to that verb (resolve / comment+resolve / comment-only / leave)
- `T<N>=<verb>` tokens → per-thread overrides, applied on top of the `all-<verb>` base (if given) or the proposed actions
- `edit` → write the table to a temp file, open in `$EDITOR`, parse back
- `abort` → stop, report "thread actions skipped — resolve manually in GitHub UI"

Capture the confirmed plan (thread_id → action) for *Apply thread actions*.

## Apply thread actions

Use the SHA captured during *Finalize (push + body)* for `comment+resolve` reply bodies.

### Scannable replies

Use a short bold-labelled bullet for a one-line reply. Longer review comments use What,
Why and Proof lists under the [body rules](../../sdlc-run/references/pr-body.md); name the
check and result, and link the label or result. Never claim a deferred concern is fixed.

### Execution recipes

Run sequentially per thread (one Bash call each). Resolve actions are idempotent (resolving an already-resolved thread is a no-op).

**resolve** (silent):
```bash
bash ${CLAUDE_SKILL_DIR}/scripts/resolve-thread.sh "{thread_id}"
```

**comment-only**:
```bash
bash ${CLAUDE_SKILL_DIR}/scripts/reply-thread.sh "{pr_number}" "{first_comment_id}" "{reply_body}"
```

**comment+resolve** — run reply, then resolve:
```bash
bash ${CLAUDE_SKILL_DIR}/scripts/reply-thread.sh "{pr_number}" "{first_comment_id}" "- **Addressed:** {sha}"
```
```bash
bash ${CLAUDE_SKILL_DIR}/scripts/resolve-thread.sh "{thread_id}"
```

**leave** — no action.

### Final report

After all thread actions complete, print:

```
Threads processed: {N}
  resolved silently:    {a}
  comment + resolved:   {b}
  comment-only:         {c}
  left open:            {d}
  errors:               {e}  (list with reasons)
```

Threads where the resolve mutation failed (e.g., `viewerCanResolve` was stale, or the thread became outdated mid-flight) are reported as errors, not silently swallowed.
