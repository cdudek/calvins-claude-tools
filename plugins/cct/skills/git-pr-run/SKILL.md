---
name: git-pr-run
description: "Coordinates opening a GitHub pull request from local changes: branch creation per repo conventions, staging without secrets, lint and syntax checks, documentation freshness check (delegated to cct:docs-audit), commit, draft PR publication and CI monitoring. It always opens a draft; only the author marks it ready. Use when someone says 'create a PR', 'open a pull request', 'submit this as a PR', 'push this as a PR', 'send this for review'. Skip for: reviewing an existing PR, owned by cct:review-code-run; acting on feedback of an open PR, owned by cct:review-feedback-run."
allowed-tools: "Bash(scripts/ci-local *) Bash(gh *) Bash(git *) Bash(npx *) Bash(npm *) Bash(yarn *) Bash(pnpm *) Bash(bundle *) Bash(rubocop *) Bash(uv *) Bash(ruff *) Bash(make *) Bash(cargo *) Read Glob Grep Agent"
user_invocable: true
metadata:
  version: 1.1.0
  author: fuko-fabio
effort: low
---

# PR Creator

Verification and every push follow the [local-first contract](../sdlc-run/references/local-first.md); read it before running checks or preparing a push.

Creates a GitHub pull request from local changes through a complete workflow: branch creation, syntax checking, commit, PR submission, and CI monitoring. Each step respects repo-specific conventions when they exist, falling back to widely-adopted defaults.

## Scannable PR text (required)

- **Order:** `## What` → `## Why` → `## Proof` → `## Before merge` (only while something is open) → the repo's Decision4 section (only with `boundary-map.yaml`) → `## Decision record` (at Repair/Migrate/Answer).
- **Bullets:** Every section is a list; start each bullet with a bold label (`- **Source plan:** 0 adds, 8 updates, 38 destroys.`). Keep one idea per bullet, at most two lines, and no paragraph longer than two sentences. Keep checklist syntax and bold-label the item.
- **Proof:** Name the check and result (`- **Unit tests:** 1,320 passed.`). Put links on the label or result, never a bare URL in prose. Preserve claims and human checklist attestations when restructuring an existing body.
- **Decision4:** When the repo has a boundary map, read it and copy the exact readable section from its PR template. Select its highest applicable class in bold with one colour circle and a sentence explaining recovery; use bold-labelled Recovery steps (numbered for multiple steps), optional Work preserved, Responsible for recovery (a named person at Answer), and Classification change. Keep the Recovery levels legend collapsed. Never author old plain `Decision-Class:` lines.
- **Decision record:** Follow the shared Decision4 PR writing reference: Repair choice story; Migrate options or forced constraint; Answer labelled evidence and challenges with no recommendation. Omit at Undo.
- **Milestone and review text:** The same layout covers milestone-close PRs, issue bodies and PR comments. Put addressed feedback under What, its rationale under Why and its check results under Proof. A short thread reply can be one bold-labelled bullet; include only applicable sections.
- **Validation:** Validate the proposed body before pushing and the actual body after creation or edits through the repo's Decision4 gate when installed. Use `--body-file`; scannable formatting applies even without Decision4.

Read the full [body example](../sdlc-run/references/pr-body.md) before writing a PR, milestone-close body, issue or review reply.

## Core Principles

- **Repo conventions first** — always check for project-specific configuration before falling back to defaults
- **Fail fast on lint** — catch syntax errors before they reach CI
- **One clean commit** — unless the branch already has a meaningful commit history
- **Monitor and fix** — don't just create the PR and walk away; watch CI and attempt fixes

## Workflow

### Step 1: Assess the Situation

Before doing anything, understand what you're working with:

```bash
# What branch are we on?
git branch --show-current

# What's the default branch?
gh repo view --json defaultBranchRef -q .defaultBranchRef.name

# Are there uncommitted changes?
git status --short

# Are there unpushed commits?
git log @{upstream}..HEAD --oneline 2>/dev/null || echo "No upstream set"

# What's the remote?
git remote get-url origin
```

Determine the state:
- **On default branch with uncommitted changes** — need to create a new branch, stage, lint, commit, push, create PR
- **On feature branch with uncommitted changes** — need to stage, lint, commit, push, create or update PR
- **On feature branch with unpushed commits** — need to push, create or update PR
- **PR already exists for this branch** — check with `gh pr view --json number 2>/dev/null`; if so, push and update the PR description

### Step 2: Create a Branch (if needed)

Only create a branch if you're on the default branch. If the user is already on a feature branch, skip this step.

**Check for repo branch naming conventions first:**

```bash
# Look for branch naming docs or config
cat .github/BRANCH_CONVENTION.md 2>/dev/null || \
cat .github/branching.md 2>/dev/null || \
cat CONTRIBUTING.md 2>/dev/null | head -100
```

If no repo-specific convention exists, follow Conventional Branch naming (see `references/conventional-branches.md`):

```
<type>/<short-description>
```

Where type is one of: `feat`, `fix`, `hotfix`, `chore`, `release`

Examples:
- `feat/add-user-authentication`
- `fix/resolve-login-timeout`
- `chore/update-dependencies`

Include a ticket number if one was mentioned: `feat/issue-123-add-user-auth`

```bash
git checkout -b <branch-name>
```

### Step 3: Stage Changes

```bash
# Review what's changed
git status
git diff --stat

# Stage specific files — avoid staging secrets or generated files
# Never stage: .env, .env.*, credentials.json, *.key, *.pem
git add <specific-files>
```

If there are no changes to stage (everything is already committed), skip to Step 5.

### Step 4: Run Local Checks

Before committing, run the repo's format, lint, typecheck and relevant tests. Before pushing, run `scripts/ci-local` or the full local suite under the linked contract; syntax checks alone are insufficient. Detect the project's language and run the appropriate linter. See `references/lint-commands.md` for the full lookup table.

**Detection order:**
1. Check for a `Makefile` with a `lint` target — if it exists, run `make lint`
2. Check `package.json` for a `lint` script — if it exists, run the project's package manager lint command
3. Check for language-specific config files (`.rubocop.yml`, `pyproject.toml`, `Cargo.toml`, etc.)
4. Fall back to common linter commands for the detected language

If linting fails:
- **Auto-fixable issues** (formatting, import order): run the auto-fix command (e.g., `npx eslint --fix`, `ruff check --fix`), then re-stage the fixed files
- **Actual errors** (syntax errors, type errors): report them to the user and stop — don't commit broken code
- **No linter available**: warn the user but proceed (not every project has linting set up)

### Step 4.5: Documentation freshness check

Before committing, check whether the staged changes will make any repo documentation stale. This step delegates to the `docs-audit` skill's diff-mode workflow (`cct` plugin → `../docs-audit/references/commands/diff.md`).

**Trigger condition:** any staged file matches the *crucial-file* patterns defined for this repo in `../docs-audit/references/file-mappings.md`. If no staged file matches, skip this step.

**Procedure:**

1. Read the section for the current repo in `../docs-audit/references/file-mappings.md` (plus the generic-rules section that applies to every repo).
2. If any staged file matches a `Changed pattern` in those tables, invoke the diff-mode audit on the `staged` scope.
3. Apply findings per severity:
   - **Critical** — auto-fix the docs (the doc states something demonstrably false; correcting it is safe). Re-stage the fixed doc files so they fold into the upcoming commit. Add a one-line note to the commit body: `Doc updates: <N> file(s)`.
   - **Warning / Info** — list them to the user and ask: "Apply N? Reply `apply <ids>`, `apply all`, `skip`, or `defer` (mention in PR description)."
4. If the user picks `defer`, continue to Step 5 but list the unapplied findings as bold-labelled bullets under `## Before merge` in the PR description (Step 6).
5. If the user picks `skip`, continue with no further action.

This step is **not** a hard gate — if the audit cannot run (e.g. `git diff` is empty, or no patterns match), proceed silently to Step 5.

### Step 5: Create a Commit

**Check for repo commit conventions first:**

```bash
cat .github/COMMIT_CONVENTION.md 2>/dev/null
```

If no repo-specific convention exists, follow Conventional Commits (see `../role-conventional-commits/references/format.md`):

```
<type>(<optional-scope>): <description>

[optional body]

[optional footer(s)]
```

Analyze the staged changes to determine the appropriate type:
- New files or features → `feat`
- Bug fixes → `fix`
- Dependency updates → `chore`
- Documentation → `docs`
- Refactoring → `refactor`
- Tests → `test`

Write the commit message using a HEREDOC for proper formatting:

```bash
git commit -m "$(cat <<'EOF'
feat(auth): add JWT-based authentication

Implement token generation and validation middleware
for protected API routes.
EOF
)"
```

If the branch already has commits with a clear history, create an additional commit rather than amending. The goal is a clean, reviewable history — not necessarily a single commit.

### Step 6: Push and Create the PR

Prepare the body and validate Decision4 as described below before invoking the local gate.
Run `scripts/ci-local` (or the full local suite if it is not installed) on the final head,
including when the branch already has commits. The script owns the push and exact-SHA
statuses; a raw `git push -u origin <branch>` is only for repositories still migrating,
after their full local suite and proposed-body validation pass.

**Check for a PR template.** GitHub accepts it in the repo root, `.github/` or `docs/`, `.md` or `.txt`, in any case, plus a `PULL_REQUEST_TEMPLATE/` directory of them under each. List the candidates first, then read the one you will use:

```bash
{ find . .github docs -maxdepth 1 -type f \
    \( -iname 'pull_request_template.md' -o -iname 'pull_request_template.txt' \) 2>/dev/null
  find . .github docs -maxdepth 2 -type f -ipath '*/pull_request_template/*' 2>/dev/null
} | sort -u
```

Nothing back means no template. One path back is the template — `cat` it. Several means the repo offers a choice: GitHub applies exactly one per PR, so pick the one that fits this change and `cat` that. Never `cat` two together — concatenating them makes a body the repo never intended, with two of every heading.

**Write Decision4 before pushing.** Follow [Decision4 PR writing and validation](../sdlc-run/references/decision4-pr.md): read the template's writing-rules HTML comment and the repo's boundary map, compute the highest changed-path floor, and fill the readable section. Validate the proposed body locally before the push; after creation validate the actual body before the gate publishes success. Use a body file. If there is no template but a boundary map exists, copy the readable section from `../sdlc-run/templates/github/PULL_REQUEST_TEMPLATE.md` and fill it under those same rules.

**Always create PRs as drafts** (`gh pr create --draft`). A draft can't be merged and signals "not yet ready for review". The author must self-review the PR and then mark it ready (`gh pr ready` or the "Ready for review" button) themselves — that human gate is the whole point of opening as a draft. Never mark a PR ready on the user's behalf, and never skip `--draft` unless the user explicitly asks for a non-draft PR.

Documented, not enforced by a hook: the `pr-draft-gate` PreToolUse hook that used to turn a missing `--draft` into a confirmation prompt was removed on 2026-09-07 — it kept prompting the developer in sdlc-run repos, where PRs open READY on purpose. Pass `--draft` here; the developer's `gh pr ready` stays out of the allow-list (architecture guide).

**If a template exists, the template IS the body.** Start from it verbatim and fill it in: replace placeholder sections with content from the diff and commit history, keep every heading and every checklist item, and don't leave sections empty — fill them or strike them through. Never write a description of your own shape and drop the template, and never pass `--fill` in a repo that has one. A body that replaced the template is the single most common way an unverified PR reaches a reviewer: the last 30 PRs per repo had no self-review line at all in 7 (eventmanager), 11 (reviews-frontend) and 18 (reviews-api) of them. The morning PR bot reads that box, and `pr-task-check@v4` fails the required check when the item its template ships is missing from the body.

**Human-only checklist items:** if the template contains a checklist item asserting human review — e.g. "Self-reviewed PR", "I have reviewed my own changes", "self-review" — leave it **unchecked** (`- [ ]`). That box certifies a human looked at the diff; an AI tool must never tick it. The same applies to any item that asserts a human action the AI didn't actually perform. Fill in descriptive sections freely, but only check boxes for steps that were genuinely completed (and never the self-review attestation).

**If no template exists**, generate a structured description:

```bash
# Gather context for the description
git log $(gh repo view --json defaultBranchRef -q .defaultBranchRef.name)..HEAD --oneline
git diff $(gh repo view --json defaultBranchRef -q .defaultBranchRef.name)..HEAD --stat
```

Then create the PR as a draft:

```bash
cat > "${TMPDIR:-/tmp}/proposed-pr-body.md" <<'EOF'
## What

- **Change:** <what changes and for whom>
- **Related issue:** <issue link, if any>

## Why

- **Reason:** <the concrete problem this change resolves>

## Proof

- **Local gate:** <command and actual result on this head>
- **Requirements:** <requirement id and its test or other evidence>

## Before merge

- [ ] **Acceptance:** All acceptance criteria are met.
- [ ] **Self-review:** Self-reviewed PR (human only).
- [ ] **Unit tests:** Unit test for changes in a method.
- [ ] **Functional tests:** Functional test for each functional change on the components.
- [ ] **E2E tests:** E2E test for new feature or edited feature simulating user interaction.

🤖 Generated with Codex
EOF
# Fill the readable Decision4 section when required, then validate the body locally.
gh pr create --draft --title "<conventional-title>" --body-file "${TMPDIR:-/tmp}/proposed-pr-body.md"
```

The PR title should follow the same convention as commit messages (e.g., `feat(auth): add JWT authentication`). The PR opens as a draft; tell the user to self-review and mark it ready when satisfied.

**Verify the draft state and the self-review item before reporting the PR**, so a missed flag or a dropped template surfaces instead of passing silently:

```bash
gh pr view --json isDraft,url,body \
  -q '"draft=\(.isDraft)  self_review_item=\((.body // "") | test("(?i)self[ -]?review|reviewed my own"))  \(.url)"'
```

If it comes back `draft=false`, say so explicitly in your summary — don't run `gh pr ready`'s inverse (`gh pr edit --add-label` etc.) or try to fix it silently. `gh pr ready --undo` converts it back to a draft; offer that and let the developer decide.

`self_review_item` is a smoke check, not a gate: it only says the phrase is somewhere in the body. If it comes back `false` and the repo's template has the item, the body dropped it. Fix it in the same step with `gh pr edit --body-file` — paste the template back, unticked — and say that you did.

**If a PR already exists** for this branch, push the new commits and **edit the existing description in place**. Never regenerate it: the body on that PR already holds the repo's template, the reviewer's context and any box a human ticked, and `gh pr edit --body` replaces all of it.

```bash
PR_NUMBER=$(gh pr view --json number -q .number)

# Read the body you are about to change, and keep every heading and checklist
gh pr view $PR_NUMBER --json body -q .body > "${TMPDIR:-/tmp}/pr-body.md"
```

Edit that file: extend the description sections to cover the new commits, and leave every heading, every checklist item and every ticked box exactly as they are. A box a human ticked stays ticked; the self-review box stays as you found it. Then:

```bash
gh pr edit $PR_NUMBER --body-file "${TMPDIR:-/tmp}/pr-body.md"
```

Always return the PR URL to the user after creation or update.

### Step 7: Monitor CI

After the PR is created or updated, monitor GitHub Actions. This is a loop with a **hard limit of 3 fix iterations**.

```bash
# Wait briefly for checks to register
sleep 5

# Check status
gh pr checks $(gh pr view --json number -q .number)
```

**If all checks pass** — report success and the PR URL. Done.

**If checks are pending** — wait and re-check. Use `gh run watch` for active runs:

```bash
# Find the latest run for the PR's head SHA
RUN_ID=$(gh run list --branch $(git branch --show-current) --limit 1 --json databaseId -q '.[0].databaseId')
gh run watch $RUN_ID
```

**If checks fail** — attempt to diagnose and fix:

```bash
# Get failed run details
gh run view $RUN_ID --log-failed
```

For each fix iteration (max 3):
1. Read the failure logs
2. Determine if the failure is something you can fix (test failure, lint error, type error, build issue)
3. If fixable: reproduce the exact failure locally, fix it, rerun only failing tests plus the directly affected suite until green, then run the full local gate once and push the batched fixes
4. If not fixable (infrastructure issue, flaky test, external service): inform the user immediately — don't waste iterations
5. After pushing the fix, update the PR description to reflect the new commit
6. Re-check CI status

Track the iteration count explicitly. After 3 failed fix attempts:
- Stop trying
- Summarize what failed and what you attempted
- Show the user the failure logs
- Suggest next steps (e.g., "Reproduce this specific integration test locally with its seed and fixture")

## Important Notes

- **Never force-push** unless the user explicitly asks for it
- **Never push to the default branch** — always work on a feature branch
- **Open PRs as drafts by default** — pass `--draft` to `gh pr create` unless the user explicitly asks for a ready-for-review PR
- **Never mark a PR ready for review** (`gh pr ready`) on the user's behalf — the author marks it ready after self-reviewing
- **Never tick human-attestation checklist items** — leave "Self-reviewed PR" and similar boxes unchecked for the human
- **Always confirm before creating the PR** if the user hasn't explicitly asked for one — they may just want commits
- **Keep the PR description current** — after each fix commit, update the summary so reviewers see accurate information
- The `Co-Authored-By` footer should use the model name from the current session

## Error Handling

### "gh: not found"
Cause: GitHub CLI not installed.
Solution: Tell the user to install it: `brew install gh` (macOS) or see https://cli.github.com/

### "HTTP 401" or auth errors
Cause: gh not authenticated or token expired.
Solution: Run `gh auth status`, then `gh auth login` if needed.

### No changes to commit
Cause: Working tree is clean.
Solution: Check if changes are already committed. If so, skip to Step 6 (push and create PR).

### Lint failures that can't be auto-fixed
Cause: Real syntax or type errors in the code.
Solution: Report the specific errors to the user and stop. Don't commit broken code.

### CI failures after 3 fix iterations
Cause: Persistent issue that automated fixes can't resolve.
Solution: Summarize all attempts, show logs, suggest manual investigation.
