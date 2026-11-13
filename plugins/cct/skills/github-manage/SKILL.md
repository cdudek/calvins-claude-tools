---
name: github-manage
description: "Persists and inspects supplied GitHub resources with the gh CLI: lists PRs and issues, reads CI and Actions status, merges, labels, edits repo settings, runs raw API queries. Delegates domain authoring: changelog text to cct:docs-changelog-write. Use when the user says 'list PRs', 'check CI status', 'merge this PR', 'close the issue', 'gh api', 'workflow status'. Skip for: opening a PR (use cct:git-pr-run), reviewing PR code (use cct:review-code-run), cutting a release (use cct:git-release-run)."
allowed-tools: "Bash(gh *) Bash(bash */github-manage/scripts/*)"
user_invocable: true
metadata:
  version: 1.0.0
  author: calvindudek
effort: low
---



# GitHub CLI

Verification and every push follow the [local-first contract](../sdlc-run/references/local-first.md); read it before running checks or preparing a push.

Always use the `gh` CLI for GitHub operations. Never use raw `curl` to the GitHub API, never construct URLs manually, and never ask the user to open a browser when `gh` can do it.


## Scannable PR text (required)

- **Order:** `## What` → `## Why` → `## Proof` → `## Before merge` (only while something is open).
- **Bullets:** Every section is a list; start each bullet with a bold label (`- **Source plan:** 0 adds, 8 updates, 38 destroys.`). Keep one idea per bullet, at most two lines, and no paragraph longer than two sentences. Keep checklist syntax and bold-label the item.
- **Proof:** Name the check and result (`- **Unit tests:** 1,320 passed.`). Put links on the label or result, never a bare URL in prose. Preserve claims and human checklist attestations when restructuring an existing body.
- **Milestone and review text:** The same layout covers milestone-close PRs, issue bodies and PR comments. Put addressed feedback under What, its rationale under Why and its check results under Proof. A short thread reply can be one bold-labelled bullet; include only applicable sections.
- **Validation:** Validate the proposed body before pushing and the actual body after creation or edits against these rules. Use `--body-file`.

Read the full [body example](../sdlc-run/references/pr-body.md) before writing a PR, milestone-close body, issue or review reply.

## Routing

The user input is: $ARGUMENTS

Read the first word as the subcommand and route to its file, passing the rest on as arguments.

| Subcommand | Does |
|---|---|
| `create-changelog` | Generates or updates a CHANGELOG.md file from merged PRs and git history → `references/commands/create-changelog.md` |

No subcommand, or one that is not in the table: say
`Usage: /cct:github-manage <create-changelog>`
and ask which one they meant. Never guess — the subcommands do different things.

## Instructions

### Core Principle

`gh` is installed and authenticated. Prefer it over:
- Raw GitHub API calls (`curl -H "Authorization: ..."`)
- Opening browser links and asking the user to click things
- Suggesting the user do something manually on github.com

### Always Provide Links

After creating or retrieving any resource (PR, issue, release, repo), always include the URL in your response so the user can navigate directly to it. Use `--json url -q .url` or extract the URL from command output.

### Pull Requests

For every PR body, follow the scannable rules above. Validate the proposed body locally before pushing and the actual body before publishing successful checks; use `--body-file`.

#### Create a PR

PRs are always opened as **drafts** — `--draft` is not an option here, it's the default. Only the author marks a PR ready for review, after reading their own diff. No hook enforces it any more (removed 2026-09-07 — it kept prompting in sdlc-run repos, where PRs open ready on purpose); `gh pr ready` stays out of the allow-list, so it prompts on its own.

```bash
# From current branch — interactive title/body
gh pr create --draft

# With explicit title and body
cat > "${TMPDIR:-/tmp}/proposed-pr-body.md" <<'EOF'
## What

- **Change:** Add JWT authentication and middleware for protected routes.

## Why

- **Access:** Protected routes require an authenticated session.

## Proof

- **Unit tests:** <command and observed result>

## Before merge

- [ ] **Login/logout:** Manual flow verification remains open.
EOF
gh pr create --draft --title "feat(auth): add JWT authentication" --body-file "${TMPDIR:-/tmp}/proposed-pr-body.md"

# Target a specific base branch
gh pr create --draft --base develop
```

The author flips it ready themselves (`gh pr ready`, or the "Ready for review" button). Never run that on their behalf.

#### Review a PR
```bash
# View PR details
gh pr view 123

# View diff
gh pr diff 123

# Check CI status
gh pr checks 123

# List files changed
gh pr diff 123 --name-only

# Review with inline comments (use gh api for line-level comments)
gh api repos/{owner}/{repo}/pulls/123/comments -f body="Comment" -F path="src/file.ts" -F line=42 -f side="RIGHT" -F commit_id="$(gh pr view 123 --json headRefOid -q .headRefOid)"
```

#### Merge a PR
```bash
# Merge (defaults to merge commit)
gh pr merge 123

# Squash merge
gh pr merge 123 --squash

# Rebase merge
gh pr merge 123 --rebase

# Auto-merge when checks pass
gh pr merge 123 --auto --squash
```

#### List and filter PRs
```bash
# My open PRs
gh pr list --author @me

# PRs needing review
gh pr list --search "review-requested:@me"

# PRs by label
gh pr list --label "bug"
```

### Issues

```bash
# Create an issue
gh issue create --title "Bug: login fails" --body "Steps to reproduce..."

# Create with labels and assignee
gh issue create --title "Fix auth" --label "bug,priority:high" --assignee "@me"

# List open issues
gh issue list

# View issue details
gh issue view 456

# Close an issue
gh issue close 456 --reason "completed"

# Search issues
gh issue list --search "auth error" --label "bug"
```

### GitHub Actions / CI

```bash
# List recent workflow runs
gh run list

# View a specific run
gh run view 789

# Watch a run in progress
gh run watch 789

# View failed step logs
gh run view 789 --log-failed

# Diagnose failures locally
# Diagnose the exact failed test locally under the linked local-first contract.
# Never rerun a pipeline to retry a flaky or failed test.

# Trigger a workflow manually
gh workflow run deploy.yml -f environment=staging
```

### Releases

```bash
# Create a release from a tag
gh release create v1.2.0 --generate-notes

# Create with custom notes
gh release create v1.2.0 --title "v1.2.0" --notes "Bug fixes and improvements"

# Draft release
gh release create v1.2.0 --draft

# List releases
gh release list

# Download release assets
gh release download v1.2.0
```

### Repository Management

```bash
# Clone a repo
gh repo clone owner/repo

# Fork a repo
gh repo fork owner/repo

# Create a new repo
gh repo create my-project --private --clone

# View repo info
gh repo view owner/repo

# Set default repo (useful in multi-remote setups)
gh repo set-default owner/repo
```

### Advanced: gh api

Use `gh api` for anything not covered by built-in commands. It handles auth automatically.

```bash
# GET request
gh api repos/{owner}/{repo}

# POST with JSON body
gh api repos/{owner}/{repo}/issues -f title="New issue" -f body="Details"

# GraphQL query
gh api graphql -f query='{ viewer { login } }'

# Paginate results
gh api repos/{owner}/{repo}/issues --paginate

# Use jq for filtering
gh api repos/{owner}/{repo}/pulls --jq '.[].title'
```

## Examples

### Example 1: Create a PR after finishing work
User says: "create a PR for this"
Actions:
1. Run `git status` and `git log` to understand changes
2. Run `gh pr create --draft` with a descriptive title and structured body
3. Return the PR URL to the user, and tell them to self-review and mark it ready when satisfied
Result: draft PR created and URL displayed

### Example 2: Check why CI is failing
User says: "why is CI failing on my PR?"
Actions:
1. Run `gh pr checks` to see which checks failed
2. Run `gh run view --log-failed` on the failed run to get logs
3. Summarize the failure and suggest a fix
Result: Root cause identified from logs

### Example 3: Review a PR
User says: "review PR 123"
Actions:
1. Run `gh pr view 123` for context
2. Run `gh pr diff 123` to read the changes
3. Post inline comments using `gh api` for line-level feedback
Result: Review with specific, inline comments on the PR

## Reusable Scripts

The `scripts/` directory ships sequential, parseable wrappers around common PR workflows. Other skills reference them via `Bash(bash */github-manage/scripts/*)`. Each script has a header comment with usage and output sections — `head -20 scripts/<name>.sh` is the source of truth.

| Script | Purpose |
|---|---|
| `scripts/pr-context.sh <pr_number>` | PR metadata, commits, body, linked issues, reviews |
| `scripts/pr-diff.sh <pr_number>` | Full PR diff (separate so callers can skip the cost) |
| `scripts/pr-checks.sh <pr_number>` | Detailed CI check list (name, state, link, workflow) as JSONL |
| `scripts/pr-readiness.sh <pr_number>` | Informational mergeability state with ahead/behind staleness (no gating) |
| `scripts/pr-merge-policy.sh` | Repo's squash/merge/rebase policy and default-message rules |
| `scripts/pr-squash-merge.sh <pr_number> <subject> [--auto]` | Squash-merge with custom subject (arg) and body (stdin) |

Output sections use the `-#-#- SECTION -#-#-` convention (see CLAUDE.md scripts rule).

## Error Handling

### "gh: not found"
Cause: gh CLI not installed
Solution: `brew install gh` (macOS) or see https://cli.github.com/

### "HTTP 401" or "auth" errors
Cause: gh not authenticated or token expired
Solution: Run `gh auth status` to check, then `gh auth login` if needed

### "no default repository"
Cause: Running gh outside a git repo or remote not set
Solution: Run `gh repo set-default owner/repo` or `cd` into the repo first
