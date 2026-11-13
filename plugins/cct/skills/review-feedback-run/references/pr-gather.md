---
description: Gather PR state — metadata, diff, CI checks, mergeability/staleness, review feedback
---

# PR Gather

Run the bundled scripts (one Bash call per script — never combine with `&&` or `;`):

```bash
# PR metadata, commits, body, linked issues, reviews
bash ${CLAUDE_SKILL_DIR}/../github-manage/scripts/pr-context.sh {number}

# Full PR diff (separate because diffs can be large)
bash ${CLAUDE_SKILL_DIR}/../github-manage/scripts/pr-diff.sh {number}

# CI check details (JSONL — name, state, bucket, link, description, workflow)
bash ${CLAUDE_SKILL_DIR}/../github-manage/scripts/pr-checks.sh {number}

# Mergeability + ahead/behind staleness (one informational panel)
bash ${CLAUDE_SKILL_DIR}/../github-manage/scripts/pr-readiness.sh {number}

# Review feedback (line comments, review bodies, issue comments)
bash ${CLAUDE_SKILL_DIR}/scripts/gather-pr-feedback.sh {number}
```

## Parsing

Parse outputs by `-#-#- SECTION -#-#-` markers (see CLAUDE.md scripts rule). Sections you'll consume:

- From `pr-context.sh`: `-#-#- PR -#-#-` (metadata), `-#-#- BEGIN PR_BODY -#-#-`/`END`, `-#-#- LINKED_ISSUES -#-#-`, `-#-#- REVIEWS -#-#-`.
- From `pr-diff.sh`: `-#-#- BEGIN PR_DIFF -#-#-`/`END`.
- From `pr-checks.sh`: `-#-#- BEGIN CI_CHECKS -#-#-`/`END` containing JSONL (one JSON object per line with `name`, `state`, `bucket`, `link`, `description`, `workflow`).
- From `pr-readiness.sh`: `-#-#- MERGEABLE -#-#-` (key-value: `is_draft`, `state`, `mergeable`, `merge_state` — note `is_draft` and `state` are used by the READY blockers logic), `-#-#- CHECKS -#-#-` (summary), `-#-#- CHECKS_FAILING -#-#-` (conditional; per-check name list when any checks are failing), `-#-#- CHECKS_PENDING -#-#-` (conditional; per-check name list when any checks are pending), `-#-#- STALENESS -#-#-` (`behind_base: true/false` — derived from GitHub's `mergeStateStatus`; `true` when the head is behind base), `-#-#- REVIEW_DECISION -#-#-` (key-value: `decision` — one of APPROVED, REVIEW_REQUIRED, CHANGES_REQUESTED, NONE), `-#-#- READY -#-#-` (`ready_to_merge` bool, `blockers` list — blockers include `is_draft`, `not_open`, `conflicts`, `checks_failing`, `checks_pending`, `reviews_required`, `changes_requested`, `behind_base`, `blocked`, `dirty`, `unstable`).
- From `gather-pr-feedback.sh`:
  - `-#-#- BEGIN REVIEW_THREADS -#-#-`/`END` — JSONL, one thread per line. Each thread object has `id` (GraphQL node ID — pass to `resolve-thread.sh`), `isResolved`, `isOutdated`, `viewerCanResolve`, `pr_author` (login of the PR author — used by guardrails in `pr-resolve-threads.md`), `comments_truncated` (bool — `true` when this thread had more than 100 comments and the rest were dropped; the script also writes a stderr warning listing truncated thread IDs), and a `comments` array. Each comment has `comment_id` (REST databaseId — pass to `reply-thread.sh`), `body`, `path`, `line`, `author`, `created_at`.
  - `-#-#- BEGIN PR_REVIEWS -#-#-`/`END` — JSONL with `id`, `author`, `state`, `body`, `submitted_at` per review.
  - `-#-#- BEGIN ISSUE_COMMENTS -#-#-`/`END` — JSONL with `id`, `author`, `body`, `created_at`, `updated_at`, `url` per general PR comment.

Treat `ISSUE_COMMENTS` (general PR discussion comments) the same as a single thread for triage purposes — categorize each as `Discussion comment` and assign an action using the universal verbs (FIX, ADD TEST, INVESTIGATE, REFACTOR, DISCUSS, DEFER → Linear, SKIP). Instruction-style directives from the PR author ("waiting for X", "should be unified", etc.) must not be dropped. Note: ISSUE_COMMENTS are not part of `REVIEW_THREADS` (GitHub treats them as PR-level conversation, not file-level review threads) — they have no `thread_id` and cannot be resolved.

## CI Failure Logs

For each **failed check**, extract the run ID from the `link` field (format: `https://github.com/{owner}/{repo}/actions/runs/{run_id}/...`) and fetch logs:

```bash
gh run view {run_id} --log-failed
```

## CI Failure Classification

```bash
# Check if a failed check also fails on base (returns FLAKY / NOT_FLAKY / NO_DATA)
bash ${CLAUDE_SKILL_DIR}/scripts/check-flaky.sh {base_branch} {check_name}
```

- `FLAKY` → pre-tag as `FLAKY → Linear`
- Lint/format failures → `FIX`
- Ambiguous failures → `INVESTIGATE`

When investigating in the triage step, add these to the findings:

- CI failures: category `CI failure`, action based on flaky check result
- Staleness: category `Staleness`, action `MERGE` if behind base (existing PR — merge commit, not rebase)
