---
description: Check whether the PR's worktree is already entered, switch into an existing one, or create a new one
---

# PR Worktree

Follow the [shared worktree policy](../../../references/worktree-usage.md): use `wt list --format json` when installed, otherwise `git worktree list --porcelain`.

Identify the PR's head branch (`gh pr view <pr_number> --json headRefName -q .headRefName`) and decide:

1. **Already in the right worktree** — the listed current path and branch match. Reuse it.
2. **Worktree exists elsewhere** — read its registered path. With Worktrunk, `wt switch <head> --no-cd --format json` returns `.path`; otherwise use the Git listing. `EnterWorktree path=<path>`.
3. **No worktree yet** — fetch the PR head to its local branch (`git fetch origin <head>:<head>`), then use the policy’s existing-branch switch/create flow at `<repo>/.worktrees/pr-<number>-<slug>`. With Worktrunk, `wt switch <head> --no-cd --format json` plus the exact path override; otherwise `git worktree add <path> <head>`. `EnterWorktree path=<returned-path>` runs session setup for all branch shapes, including `/`. Verify HEAD matches the PR head SHA before reviewing or changing it.

Do not fetch into a branch already checked out elsewhere; enter and inspect it first. Do not reset a dirty or divergent checkout automatically. No installation prompt here; setup/preflight owns it.

## Dirty worktree

If `git status` shows uncommitted changes (whether you were already there or after entering), show the dirty files and ask the user whether to commit or discard before proceeding.
