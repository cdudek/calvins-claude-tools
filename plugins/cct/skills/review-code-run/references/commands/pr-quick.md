---
description: Quick diff-only PR review with inline findings
---

The user input is: $ARGUMENTS

Parse the input as: `<pr_number>`

## Step 1: Load PR Context

Follow `../references/pr-context-loading.md` to fetch PR metadata (with `id`, the PR node id), diff, changed files, CI status, and the pending-review probe (`$PENDING_REVIEW`). Store `$PR_NODE_ID` (from `nodeId`) and `$PENDING_REVIEW` — both are required by the posting step.

Extract the owner/repo from `git remote get-url origin`.

## Step 2: Analyze Changes

Review the diff against the **categories** defined in `../../role-code-analysis/references/categories.md` (Security → Correctness → Performance → Testing → Conventions → Project Rules → Completeness), in priority order. Use the dimension names from `../references/dimensions.md` when tagging findings — categories own per-mode priority; dimensions own canonical naming.

For each finding:
- Identify the exact file path and line number
- Verify the claim against the diff context — do not speculate
- Assign a severity: critical, warning, suggestion, or nit
- Assign a confidence score (0-100)
- Write a `failure_scenario`: concrete inputs or state → the wrong output, crash, or leak. Section C posts it as the comment's second sentence, so a finding without one posts a single line. Cannot write one? You do not have a finding.

Skip nitpicks. Don't comment on formatting if a formatter is configured.

Before finalizing, self-filter: deduplicate findings on the same file:line. Tag findings with `confidence < 50` as `unverified: true` rather than dropping them — they render in the "Unvalidated observations" block below.

## Step 3: Present Findings

Format findings per `../references/finding-format.md` — `pr` mode uses **Section B (Review Action Plan table)** only. The detailed **Section A** Findings rendering is for the validated `*-deep` / `*-max` reports, not `pr-quick`.

### PR Summary
Brief description of what the PR does (2-3 sentences max).

### Review Action Plan
Render the action table from Section B of `finding-format.md`. In `pr` mode there is no thread reconciliation, so every finding gets `Action=new` and `Reason=—`. The header reads `Existing threads: —` (pr mode does not fetch threads); the `Pending review:` field is derived from `$PENDING_REVIEW` loaded in Step 1 — show `yes (N comments)` when `$PENDING_REVIEW` is non-empty (using its `comment_count`), `no` otherwise. If no real issues are found, say so clearly instead of rendering an empty table.

### Unvalidated observations — Low-confidence (< 50)
Findings the reviewer flagged but didn't reach the confidence threshold. Clearly labeled as not independently verified, for the reader to triage. Omit the heading if there are none.

## Step 4: Post (on user request only)

**Before posting, mint the two fields the posting scripts require but `pr-quick` never produced.** `pr-deep`/`pr-max` get them from `scripts/posting-findings.sh`, the only minter of `side` (`../../CLAUDE.md` → the `side` type rule); `pr-quick` has no `findings.json` to feed it, so set them by hand on every finding you are about to post: `path` = the finding's file path, and `side: RIGHT` (review findings target added/context lines on the PR head). `../references/review-posting.md` requires `side` on every entry and `scripts/review-add-thread.sh` takes it as a mandatory argument — a null `DiffSide` makes GitHub accept the mutation and silently drop the thread, so the review posts with comments missing and no error.

**Compose every comment per `../references/finding-format.md` → Section C** — emoji, label, decoration, two sentences, `F<id>`, and a ` ```suggestion ` block where the line is in the diff. `pr` mode has no `findings.json`, so number the ids `1..N` as Step 3 already does and render them `F1`, `F2`, … in the comment.

**Two exclusions, the same ones `scripts/posting-findings.sh` applies for the validated modes.** That script needs a `findings.json` and `verdicts.json` that `pr-quick` never writes, so apply them by hand here or they do not happen at all:

- **Drop every `nit`.** `suggestion` is the floor for a thread. Nits stay in the Step 3 report.
- **Findings tagged `unverified: true` get no thread.** They go into the review body as a short table, under a heading saying they were not verified — see `../references/posting-pipeline.md` Phase 3.

When the user asks to post, follow `../references/review-posting.md`. Never post automatically. The state-driven flow uses `$PR_NODE_ID` and `$PENDING_REVIEW` (both loaded in Step 1) to pick between Scenario A (no pending review) and Scenario B (one exists from a prior session). `pr` mode never sets any `matched_thread_id` / `matched_comment_database_id` — every finding goes through as `action: new`.
