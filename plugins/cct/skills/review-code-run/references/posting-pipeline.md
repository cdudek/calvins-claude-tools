# Posting pipeline

For `pr-deep` and `pr-max`. Matches findings to the PR's existing review threads, shows an action plan, and — **only when the user asks** — posts.

## Inputs

| Input | From |
|---|---|
| `findings` | `posting-findings.sh` — each has `id`, `path`, `line`, `side`, `severity`, `category`, `body`, `failure_scenario`, `idiomatic_fix`, `confidence`, `reversibility`. **Confirmed only, `suggestion` severity and above.** Not the demoted appendix, not `unverifiable`, not `nit` — the script owns all three exclusions and states why. |
| `$OWNER`, `$REPO`, `$PR_NUMBER`, `$PR_NODE_ID`, `$PENDING_REVIEW` | `pr-context-loading.md` |
| `$ROOT` | the PR checkout |

`id` must reach Phase 2. The action plan renders it as `F<id>`.

## Phase 1 — Match against existing threads

The main thread runs four steps:

1. Fetch threads to a file. Only the path enters your context.
   ```bash
   THREADS_FILE="${TMPDIR:-/tmp}/reviewer-threads-${PR_NUMBER}-${CLAUDE_CODE_SESSION_ID:-$$}.json"
   bash "${CLAUDE_SKILL_DIR}/scripts/review-threads.sh" "$OWNER" "$REPO" "$PR_NUMBER" "$THREADS_FILE"
   ```
2. Get the header counts.
   ```bash
   eval "$(bash "${CLAUDE_SKILL_DIR}/scripts/review-threads-counts.sh" "$THREADS_FILE" "${PENDING_REVIEW:-}")"
   # sets THREADS_TOTAL THREADS_RESOLVED THREADS_OWN_ACTIVE THREADS_OTHERS_ACTIVE
   ```
3. `$THREADS_TOTAL` > 0 → spawn one `Agent` (model: sonnet) per `reconcile-threads.md`. Pass `findings`, `threads_file_path=$THREADS_FILE`, `worktree_path=$ROOT`, `pending_review`. Pass the **path**, never the JSON. It returns each finding with `action`, `matched_thread_id`, `matched_comment_database_id`, `reason`.
   `$THREADS_TOTAL` = 0 → every finding gets `action: new`, `reason: —`.
4. Clean up. No `trap`.
   ```bash
   bash "${CLAUDE_SKILL_DIR}/scripts/review-threads-cleanup.sh" "$THREADS_FILE"
   ```

## Phase 2 — Show the action plan

Render Section B of `finding-format.md`. Header: `Existing threads: <total> (<resolved> resolved, <own> active from you, <others> from others)` and `Pending review: yes (N comments)` or `no`.

A finding whose `path:line` is not in the diff cannot be a thread. Send it to the review body in Phase 3 and say so in its row.

Any row with `action: flag` → show the finding and the candidate thread, and ask the user to pick `skip` / `reply` / `reopen` / `new` / `append` before posting.

## Phase 3 — Post

Only when the user asks.

First compose each surviving finding into its comment per `finding-format.md` → Section C. That is the `body` every script in `review-posting.md` posts byte-exact; nothing downstream reformats it.

Then follow `review-posting.md`.

The review body carries three things, in this order:

1. The verdict line and why, as in `report-sections.md` → Verdict.
2. Off-diff findings — GitHub takes no thread on a line outside the diff.
3. **Unverified findings**, as a short table (`ID`, `Location`, `Claim`) under a heading that says a validator could not confirm them. They get no thread, so this is the only place the author sees them. Take the unverifiable `id`s from `verdicts.json`, then their `Location` and `Claim` from `findings.json`; `posting-findings.sh` already dropped them from the postable set.

`review-submit.sh` appends the co-review footer. Do not write one.
