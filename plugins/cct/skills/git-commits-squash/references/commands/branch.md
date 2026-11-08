---
description: Squash all commits on the current feature branch into one local commit
---

The user input is: $ARGUMENTS

Squashes a feature branch locally — analyzes commits, detects inconsistencies, composes a conventional commit message, discusses findings, and squashes via soft reset.

## Instructions

### Phase 0 — Preflight

1. **Detect base branch**: if `$ARGUMENTS` is provided, use it as the base branch. Otherwise detect the repo default:
   ```bash
   git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@'
   ```
   If that fails, fall back to `main`, then `master`.

2. **Verify commits exist**: run `git rev-list $(git merge-base <base> HEAD)..HEAD --count`. If 0, abort: "No commits to squash — this branch has no commits ahead of `<base>`."

3. **Verify clean working tree**: run `git status --porcelain`. If there are uncommitted changes (staged or unstaged), show the list of dirty files and ask the user:
   - **"Commit them"** — analyze the uncommitted changes with `git diff` and `git diff --cached`, compose a meaningful conventional commit message following `../references/message-composition.md`, show it to the user for approval, then stage and commit. The commit will be squashed along with everything else.
   - **"Stash them"** — run `git stash push -m "branch-squash: stashed before squash"`. These changes are unrelated to the branch work and will be restored after the workflow completes (see Phase 7).
   - **"Abort"** — stop and let the user handle the working tree manually.

4. If only 1 commit exists, inform the user: "Only 1 commit on this branch — squashing is not needed, but I can still analyze and rewrite the message if you'd like. Continue?" Wait for confirmation.

### Phase 1 — Gather Data

Run the four gathering scripts. The scripts are in the skill's `scripts/` directory.

**Step 1** — Run these three in parallel (they are independent):
```bash
bash ${CLAUDE_SKILL_DIR}/scripts/gather-branch-info.sh <base>
bash ${CLAUDE_SKILL_DIR}/scripts/gather-file-operations.sh <base>
bash ${CLAUDE_SKILL_DIR}/scripts/gather-ecosystem.sh
```

**Step 2** — Check the output of `gather-branch-info.sh`:

- If `on_protected_branch: true` → **abort**: "You are on `<branch>`. Squashing a protected branch is not allowed. Switch to a feature branch first."
- If `commit_count` > 20 or `files_changed` > 50 → **warn**: "This is a large branch (N commits, M files changed). Consider splitting before squashing. Continue anyway?" Wait for user response.

**Step 3** — Run the full diff separately (kept separate to manage context size):
```bash
bash ${CLAUDE_SKILL_DIR}/scripts/gather-full-diff.sh <base>
```

### Phase 2 — Enrich Ticket Context

From the ticket references in the `gather-branch-info.sh` output:

**Linear tickets found:**
1. Attempt `mcp__claude_ai_Linear__get_issue` for each ticket ID
2. If the MCP call fails or is unavailable → **warn user**: "Linear MCP is unavailable — I cannot fetch full ticket context (title, description, acceptance criteria). Continue without it, or paste the ticket description here?"
3. If succeeds: extract title, description, status, priority, acceptance criteria, type/labels

**GitHub references found:**
1. For each `#N` reference:
   - `gh issue view N --json title,body,state,labels` (try as issue first)
   - If not found: `gh pr view N --json title,body,state` (try as PR)

### Phase 3 — Analyze

Launch **one agent** with all gathered data: branch info, file operations, ecosystem info, full diff, and enriched ticket context.

The agent receives two reference files to guide its work:
- `../references/inconsistency-categories.md` — the 7 detection categories
- `../references/message-composition.md` — multi-commit synthesis rules (which itself references `../../role-conventional-commits/references/format.md` for the canonical format)

The agent performs two tasks **sequentially** (cross-referencing matters — the message should reflect findings):

#### Task A — Inconsistency Detection

Apply all 7 categories from `../references/inconsistency-categories.md`:

1. **Contradictory changes** — use the `-#-#- CONTRADICTIONS -#-#-` (files added then deleted) and `-#-#- NET_ZERO_FILES -#-#-` sections from `gather-file-operations.sh`. Cross-reference with `-#-#- BEGIN PER_COMMIT_OPERATIONS -#-#-`. Flag with commit SHAs and ask why.

2. **Incomplete operations** — from file operations: check renames (`R` entries) for stale references. Grep the full diff for imports/references to deleted or renamed files.

3. **Missing companion changes** — for new files (`A` entries): check if corresponding test files exist. For new dependencies: check version constraints. For new config keys in the diff: check for example/template entries.

4. **Version coherence** — cross-reference: the commit type (from ticket or branch prefix) with version files from ecosystem output. If changes are `feat` type and no version bump is visible, flag it.

5. **Scope drift** — compare branch name and ticket description against the full diff. Flag files/directories that seem unrelated to the stated purpose.

6. **Dead artifacts** — from deletions in the diff: use Grep to search the codebase for remaining references to removed files, symbols, config keys, env vars.

7. **Symmetry violations** — scan the diff for one-sided changes to known paired patterns (setup/teardown, create/delete, up/down, open/close, etc.).

Classify each finding as **Question**, **Concern**, or **Info**.

#### Task B — Compose Message

Using `../references/message-composition.md` rules (which references `../../role-conventional-commits/references/format.md` for canonical type/header/body/footer rules):

1. **Determine type**: from ticket type/labels first, then dominant change pattern. If ambiguous, note both options for user to choose.
2. **Determine scope**: primary module or directory affected.
3. **Compose header**: `<type>(<scope>): <imperative description>` — under 72 chars.
4. **Compose body**: synthesize a coherent narrative from commit messages and ticket context. Explain what changed and why. Do not list individual commits.
5. **Compose footer**: `Refs:` for Linear tickets, `Fixes:`/`Closes:` for GitHub issues, `Co-authored-by:` from gathered data, `BREAKING CHANGE:` if applicable.

The agent returns both the classified findings and the proposed commit message.

### Phase 4 — Present & Discuss

Display to the user:

```
## Branch Summary
- Branch: <branch-name>
- Base: <base-branch>
- Commits: <count>
- Files changed: <count> (+<insertions>, -<deletions>)
- Tickets: <ticket-id> (<title> — <status>) [if found]

## Proposed Squash Message

\`\`\`
<the composed conventional commit message>
\`\`\`

## Findings

### Questions (need your input before squashing)
1. <finding with commit references>

### Concerns (recommend addressing)
1. <finding>

### Info
1. <finding>
```

Then ask: **"Would you like to adjust the message, address any findings, or proceed with squashing?"**

Iterate on the message and findings until the user says to proceed. The user may:
- Edit the message text
- Ask to change the type or scope
- Dismiss a finding
- Ask to fix a concern before squashing

### Phase 5 — Squash

After user approval:

1. **Create backup branch** (flatten slashes to avoid git ref namespace conflicts):
   ```bash
   BACKUP_BRANCH="backup/branch-squash--$(git rev-parse --abbrev-ref HEAD | tr '/' '-')"
   git branch "$BACKUP_BRANCH" HEAD
   ```

2. **Squash via soft reset:**
   ```bash
   git reset --soft $(git merge-base <base> HEAD)
   git commit -m "$(cat <<'EOF'
   <approved message>
   EOF
   )"
   ```

3. **Verify the squash is correct** — compare file trees between backup and squashed HEAD:
   ```bash
   git diff "$BACKUP_BRANCH" HEAD
   ```
   - If the diff is **empty** → squash is correct, trees match perfectly
   - If the diff is **not empty** → something went wrong. Show the diff to the user and ask how to proceed. Do NOT delete the backup.

4. **Delete backup branch** (only after successful verification):
   ```bash
   git branch -D "$BACKUP_BRANCH"
   ```

5. **Show result:**
   ```bash
   git log --oneline -5
   ```

### Phase 6 — Push Decision

If the gathered data showed `push_required: true` (remote tracking branch exists):

Ask the user: **"Remote tracking branch exists (`<upstream>`). Push with `--force-with-lease`? (y/n)"**

- If yes: `git push --force-with-lease`
- If no: "Remember to force-push before merging: `git push --force-with-lease`"

If no remote tracking → skip this phase.

### Phase 7 — Restore Stash

If changes were stashed in Phase 0 step 3:

1. Run `git stash pop`
2. If pop succeeds → inform the user: "Restored stashed changes."
3. If pop fails (conflict) → inform the user: "Stash pop had conflicts. Your stashed changes are still in the stash. Resolve manually with `git stash pop` or `git stash show -p` to review."

If nothing was stashed → skip this phase.

## Error Handling

### No commits on branch
Abort cleanly: "No commits ahead of `<base>`. Nothing to squash."

### Protected branch detected
Abort: "Cannot squash on `<branch>` — it is a protected branch."

### Merge-base detection fails
The base branch may not exist locally. Try `git fetch origin <base>` first, then retry. If still failing, ask the user to specify the correct base branch.

### Linear MCP unavailable
Warn and ask the user whether to continue without ticket context. Do not silently skip — the ticket context is valuable for composing a good message.

### Squash verification fails
Do NOT delete the backup branch. Show the diff between backup and HEAD. Let the user decide:
- Restore from backup: `git reset --hard "$BACKUP_BRANCH"`
- Accept the difference
- Investigate further

### Force push rejected
If `--force-with-lease` is rejected, it means the remote has new commits not in the local branch. Warn the user: "Force push rejected — remote has diverged. You may need to fetch and reconcile."
