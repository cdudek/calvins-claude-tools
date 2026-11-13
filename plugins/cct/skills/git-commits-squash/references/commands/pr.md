---
description: Compose a clean commit message from a GitHub PR's context and squash-merge it server-side via gh
---

Verification and every push follow the [local-first contract](../../../sdlc-run/references/local-first.md); read it before running checks or preparing a push.

The user input is: $ARGUMENTS

Squash-merges a GitHub pull request — gathers PR context, enriches with ticket data, composes a conventional commit message, optionally refreshes the PR title/body, then squash-merges via `gh pr merge --squash`.

## Instructions

### Phase 0 — Resolve PR

Parse `$ARGUMENTS`:

- If a number (e.g., `123`) → that's the PR number.
- If a GitHub PR URL (e.g., `https://github.com/owner/repo/pull/123`) → extract the trailing number as the PR number.
- If empty → resolve from the current branch:
  ```bash
  gh pr view --json number --jq '.number'
  ```
  If that fails (no PR for the current branch), abort: "No PR found for the current branch. Pass a PR number explicitly: `/cct:git-commits-squash pr <number>`."

Set `PR=<number>` for downstream phases.

### Phase 1 — Gather

Run the shared scripts from `github-manage` sequentially:

```bash
bash ${CLAUDE_SKILL_DIR}/../github-manage/scripts/pr-merge-policy.sh
bash ${CLAUDE_SKILL_DIR}/../github-manage/scripts/pr-context.sh "$PR"
```

`${CLAUDE_SKILL_DIR}` resolves to the squash skill root, so `${CLAUDE_SKILL_DIR}/../github-manage/...` reaches the sibling skill.

Outputs use the `-#-#- SECTION -#-#-` delimiter convention (see CLAUDE.md scripts rule). Parse by anchoring on the section markers.

Check the policy output:
- Look at the `-#-#- REPO_MERGE_POLICY -#-#-` section.
- If `squash_allowed: false` → **abort**: "This repo does not allow squash merging. Use `/cct:git-commits-squash branch` to squash locally, or use a different merge strategy."

Parse the `-#-#- PR -#-#-` section of pr-context.sh output:
- If `state != OPEN` → **abort**: "PR #$PR is not open (state: <state>). Cannot merge."
- Extract: title (from this section), body (from the `-#-#- BEGIN PR_BODY -#-#-` ... `-#-#- END PR_BODY -#-#-` block), commits (from `-#-#- COMMITS -#-#-`, each commit terminated by `-#-#- END COMMIT -#-#-`), linked issues (from `-#-#- LINKED_ISSUES -#-#-`), reviews summary (from `-#-#- REVIEWS -#-#-`). Keep for Phase 3.

### Phase 2 — Enrich Ticket Context

From the `-#-#- LINKED_ISSUES -#-#-` section of pr-context.sh output:

**Linear tickets found** (the `linear:` row, comma-separated):
1. Attempt `mcp__claude_ai_Linear__get_issue` for each ticket ID.
2. If the MCP call fails or is unavailable → **warn**: "Linear MCP is unavailable — proceeding without ticket context. The composed message may be less precise. Continue?"
3. If succeeds: extract title, description, status, priority, acceptance criteria, type/labels.

**GitHub references found** (the `github:` row, comma-separated):
1. For each `#N`:
   - `gh issue view N --json title,body,state,labels` (try as issue first)
   - If not found: `gh pr view N --json title,body,state` (try as PR)

### Phase 3 — Compose

Apply `../references/message-composition.md` (which references `../../role-conventional-commits/references/format.md` for canonical format) against:

- The PR's source commits (`-#-#- COMMITS -#-#-` section, each ended by `-#-#- END COMMIT -#-#-`).
- The PR body (between `-#-#- BEGIN PR_BODY -#-#-` and `-#-#- END PR_BODY -#-#-`).
- The enriched ticket context from Phase 2.
- The existing reviews summary (`-#-#- REVIEWS -#-#-`) — useful for understanding what reviewers cared about.

Apply the PR-mode synthesis specifics from `message-composition.md`:
- If the PR body is already a coherent narrative matching the format, lift it with minimal edits.
- If the PR body describes scope that's not in the diff (e.g., scope cut during review), strip those parts.

Output: **subject** (one line, conventional commit header) and **body** (multi-line, may be empty).

### Phase 4 — Present + Decide

#### Step A: Stale PR title/body?

When updating the PR body, retain the repository template and its Decision4 section ([advisory](../../../sdlc-run/references/decision4-pr.md)), refreshing it if scope changed. The composed squash message is
commit text; it does not replace the PR template.

Compare composed subject/body to the PR's current title/body (from `-#-#- PR -#-#-` and the `BEGIN PR_BODY`/`END` block):

- Compute approximate Levenshtein-style divergence on title (rough word-overlap is fine).
- Flag as "significant divergence" when:
  - The title's conventional-commit *type* differs (e.g., PR says `chore:` but composed says `feat:`), OR
  - The title diverges by more than ~25% of characters, OR
  - The body covers scope not in the PR body, or references scope no longer in the diff.

Display to the user:

```
## Proposed Squash Message

Subject: <composed subject>

Body:
<composed body>

## PR Current Record
Title: <PR title>
Body: <first ~5 lines of PR body, truncated marker if longer>
```

If significant divergence is detected, ask:

> The composed message diverges significantly from the PR title/body. Update the PR record before merging? (y/N)

- `y` → run:
  ```bash
  gh pr edit "$PR" --title "<composed subject>" --body-file - <<'BODY'
  <composed body>
  BODY
  ```
- `n` (or Enter) → skip; the squash commit message still uses the composed subject/body via `-t`/`-F -`. Continue to Step B.

If no significant divergence → skip Step A entirely, go to Step B.

#### Step B: Readiness + merge prompt

Run the readiness script:

```bash
bash ${CLAUDE_SKILL_DIR}/../github-manage/scripts/pr-readiness.sh "$PR"
```

Display the readiness output verbatim, then prompt:

```
Merge action:
  y     — squash-merge now
  auto  — queue with --auto; GitHub merges when blockers clear
  n     — abort
```

- `y` → proceed to Phase 5 without `--auto`.
- `auto` → proceed to Phase 5 with `--auto`.
- `n` → stop; print the composed message so the user can use it later.

Do **not** gate on readiness — show the state and let the user pick. If `y` is chosen on a not-ready PR, `gh pr merge` will fail with a clear reason; the user can rerun with `auto`.

### Phase 5 — Execute

Invoke the squash-merge script with subject as arg and body via heredoc stdin:

```bash
bash ${CLAUDE_SKILL_DIR}/../github-manage/scripts/pr-squash-merge.sh "$PR" "<composed subject>" [--auto] <<'BODY'
<composed body>
BODY
```

- Use `<<'BODY'` (quoted delimiter) so body content is passed verbatim without shell expansion.
- Pass `--auto` only when the user picked `auto` in Step B.

After the script returns:
- On success: print the merge commit URL or sha from gh's output, and a one-line summary ("Squash-merged PR #$PR with subject `<subject>`.").
- On failure: surface gh's error message directly. Common cases — required checks pending, conflicts, missing reviews — all imply the user should rerun with `auto` or fix the blocker first.

## Error Handling

### PR not found / wrong number
Abort with the error from gh. Do not silently fall back.

### `squash_allowed: false`
Already handled in Phase 1.

### Linear MCP unavailable
Warn loudly; ask the user whether to continue without ticket context.

### `gh pr merge` fails with "checks required"
Tell the user: "Required checks have not passed. Rerun and choose `auto` to queue the merge, or wait until checks pass and rerun."

### `gh pr merge` fails with conflict
Tell the user: "PR has merge conflicts. Resolve via rebase against the base branch, push, then rerun."

### Commitlint rejects the message after merge
This happens at the PR-checks layer, not in the script. If a post-merge check rejects, the user sees the failure on GitHub and can address it there. The script does not validate commit-message style — that is by design (see `../../role-conventional-commits/SKILL.md` and the CLAUDE.md scripts rule).
