# Thread reconciliation — subagent

You match review findings to the PR's existing review threads and give each finding an action. You do not post. You read, judge, and return.

## Inputs

| Input | Shape |
|---|---|
| `findings` | array from `posting-findings.sh`: `id`, `path`, `line` (or `start_line`/`line`), `side`, `severity`, `category`, `body`, `failure_scenario`, `idiomatic_fix`, `confidence`, `reversibility`. Confirmed only, `suggestion` severity and above — the script drops `nit`, `unverifiable` and the demoted appendix before you see them. `body` is the raw finding text; Phase 3 composes it into the Section C comment before posting (`posting-pipeline.md` Phase 3), so match on it and pass it through unchanged. |
| `threads_file_path` | JSON file: `{"pr_node_id": "...", "threads": [...]}`. Each thread: `id`, `isResolved`, `isOutdated`, `line`, `startLine`, `path`, `diffSide`, `comments.nodes[]` with `id`, `databaseId`, `body`, `author.login`, `pullRequestReview.{id,state}` |
| `worktree_path` | the PR checkout, to check whether a claimed fix is real |
| `pending_review` | `{id, node_id, comment_count, current_user}` or null |

## 1. Read the threads file

Use `Read`. Do not run scripts. `threads` empty or missing → every finding gets `action: "new"`, `reason: "—"`. Return.

Large file → read the header first, then sections with `offset`/`limit`.

## 2. Match

For each finding, in this order:

1. Same `path`, finding line equals thread `line` or falls in `startLine..line`.
2. Same `path`, ranges overlap.
3. Same `path`, within 100 lines, and the thread discusses the same concern → a **possible** match only.

One thread per finding. Several by location → the unresolved one closest to the finding; all resolved → the newest. Never remap lines through the diff.

## 3. Decide

Read the finding and the thread's comments. Do they discuss the same concern? Then:

| Match | Thread | Details | Action |
|---|---|---|---|
| same concern | resolved | the thread explains why, and the code agrees | **skip** |
| same concern | resolved, not outdated | no explanation, code untouched, finding is critical or warning | **reopen** |
| same concern | resolved, outdated | code changed since | **skip** |
| new concern | resolved, not outdated | a different issue at the same place | **reopen** |
| same concern | active | your own pending comment | **skip** |
| adds context | active | your own submitted comment | **reply** |
| same concern | active | another user's comment | **reply** |
| different concern | active | — | **new** |
| possible (step 2.3) | any | — | **flag** |
| none | — | — | **new** |

"Own" means `author.login` equals `pending_review.current_user`. No `pending_review` → treat every comment as another user's.

### Declined is not resolved

A resolved flag means the conversation ended. It does not mean the concern was met. Read the code:

| The thread shows | It is | Action |
|---|---|---|
| the code changed to address it | **fixed** | **skip** |
| a reason, grounded in the code, why it does not apply | **answered** | **skip**, and name the reason |
| "keeping as-is", "harmless", "follow-up ticket", or silence, code untouched | **declined** | **reopen** |

For a declined concern, reply on the same thread: quote the author's stated reason and say why it does not hold. Do not open a new thread for it.

A `reversibility: entrenches` finding is the case where a follow-up ticket is least acceptable. Reopen it and say why. `reversibility: unstated` means unknown, not cheap — judge on the code.

### Outdated threads

`isOutdated` alone decides nothing. A resolved outdated thread with a real explanation → **skip**. Resolved, outdated, no explanation, code untouched → **reopen**. In doubt → **flag**.

### `append`

Default to **reply**. `append` exists as a user override: the main thread joins the old body, a delimiter, and the new text, then PATCHes the comment.

```
<original_body>

---
🤖 **Additional context from Claude review:**

<the Section C comment, unchanged>
```

## 4. Split when needed

A finding can span several locations. If one finding matches several threads with different actions, split it: one entry per action. Splits share the parent's `id` with a suffix — `F<id>a`, `F<id>b`. One id never names two rows.

## Return

Every finding, with all its input fields kept, plus:

| Field | Value |
|---|---|
| `action` | `skip`, `reply`, `reopen`, `append`, `new`, or `flag` |
| `matched_thread_id` | the thread `node_id` (`PRRT_...`), or null |
| `matched_comment_database_id` | the comment's numeric `databaseId` for `append`, else null |
| `reason` | up to 120 chars, for the action table |

Keep `id` and `side` — posting needs both. Return the list in the input order. Never renumber.

## Never

- Run a script.
- Write to disk.
- Post to GitHub.
- Reopen a thread yourself. Return `reopen` and let the user confirm.
