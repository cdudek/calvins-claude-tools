---
name: git-commits-squash
description: "Squashes commits into one conventional commit. Branch mode analyzes a feature branch, composes the commit message, discusses concerns and squashes locally with a soft reset. PR mode composes the message from the PR's context and delegates the server-side squash-merge to the scripts of cct:github-manage. Use when someone says 'squash the branch', 'squash my commits', 'prepare the branch for merge', 'squash and merge this PR', 'squash this PR'. Skip for: opening a PR, owned by cct:git-pr-run; other GitHub merge operations, owned by cct:github-manage."
allowed-tools: "Bash(bash */git-commits-squash/scripts/*) Bash(bash */github-manage/scripts/*) Bash(git *) Bash(gh *) Read Grep Glob Agent mcp__claude_ai_Linear__get_issue mcp__linear__get_issue"
user_invocable: true
metadata:
  version: 2.0.0
  author: mpapis
effort: low
---

# Squash

Squashes commits into one — either a local feature branch's commits (`branch` mode) or a GitHub PR's commits via server-side squash-merge (`pr` mode).

The user input is: $ARGUMENTS

## Routing

Parse the first word of `$ARGUMENTS` as the command name and route, passing remaining args as `$ARGUMENTS`:

| Word | Routes to | Notes |
|---|---|---|
| `branch` | `references/commands/branch.md` | Local soft-reset squash of feature-branch commits |
| `local` | `references/commands/branch.md` | Alias for `branch` |
| `pr` | `references/commands/pr.md` | Server-side squash-merge of a GitHub PR via `gh` |
| `<number>` (e.g., `123`) | `references/commands/pr.md` | Numeric arg → infer PR mode, pass through as PR number |
| `<github pr url>` | `references/commands/pr.md` | URL arg → infer PR mode, extract PR number |

### No argument given

If `$ARGUMENTS` is empty, propose a mode based on context — but always let the user override.

1. Run `git rev-parse --abbrev-ref HEAD` to read the current branch.
2. If the branch is `main`, `master`, `develop`, `production`, or `staging`: **refuse**. Print: "Cannot squash on a protected branch. Switch to a feature branch first." This is a hard rule — squashing main has no correct scenario.
3. Otherwise, gather context:
   ```bash
   git status --porcelain                              # dirty tree?
   git rev-list "@{upstream}..HEAD" --count 2>/dev/null  # local commits ahead of remote
   gh pr view --json number,title,state,statusCheckRollup,reviewDecision 2>/dev/null  # open PR?
   ```
4. Print a one-line context summary and a one-line rationale, then ask:
   ```
   Branch: <name> (<n> commits ahead of <upstream-or-none>)
   Open PR: #<num> "<title>" — <ci_status>, <review_decision>     (only if PR exists)

   Suggested: <pr|branch> (<rationale>)

   Squash mode? [P]r / [b]ranch / [n] abort
   ```
   Rationale construction (short, single sentence):
   - PR exists, no blockers → "PR is ready to merge"
   - PR exists, CI pending → "PR has CI pending; --auto available in pr mode"
   - PR exists, CI failing or changes requested → "PR has blockers; you may want branch first to amend"
   - No PR, local commits ahead → "no PR yet; squash locally before opening one"
   - No PR, no commits ahead → "nothing obvious to squash"
   - If no clear signal: no rationale line; no suggestion; offer all three keys.
5. Enter accepts the suggestion. `b` / `p` overrides. `n` aborts. Pass any remaining context (PR number, base branch) into the routed command's `$ARGUMENTS`.

### Unrecognized first word

If the first word doesn't match the table and isn't a PR number/URL, treat the entire `$ARGUMENTS` as a base-branch argument and route to `references/commands/branch.md` (preserves the bare `/cct:git-commits-squash <base-branch>` shorthand from before subcommands existed).

## Policies

### Branch mode
Rewrites local history; backup branch made before squashing; optional force-push to remote at the end. Reversible via the backup branch until it's deleted on successful verification.

### PR mode
Changes the base branch on GitHub. **Not reversible** without a revert commit. Always confirm before executing. Never auto-merge by default — the user must explicitly pick `y` or `auto` at the merge prompt.

### Both modes
- Composition rules come from `references/message-composition.md` (multi-commit synthesis) which references `../role-conventional-commits/references/format.md` for canonical format.
- Ticket enrichment via Linear MCP and `gh issue/pr view` is best-effort — warn loudly if unavailable, don't silently proceed.
