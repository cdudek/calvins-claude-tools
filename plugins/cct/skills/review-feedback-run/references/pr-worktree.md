---
description: Check whether the PR's worktree is already entered, switch into an existing one, or create a new one
---

# PR Worktree

```bash
git worktree list
```

Identify the PR's head branch (`gh pr view <pr_number> --json headRefName -q .headRefName`) and decide:

1. **Already in the right worktree** — current directory appears in `git worktree list` AND its checked-out branch matches the PR's head branch. Skip `EnterWorktree`; you're already where you need to be.
2. **Worktree exists elsewhere** — `git worktree list` shows a worktree for the PR's head branch at a different path. `EnterWorktree` with that absolute path.
3. **No worktree yet** — `EnterWorktree` with bare `name="<dirname>"` (directory name = branch name; the tool rejects `@` in `name=`, and the hook mis-targets branch names containing `/`). The custom hooks handle branch creation/checkout and cleanup automatically. If the PR's head branch contains `/` (bot-generated branches), fall back to a manual `git worktree add` + `EnterWorktree path=`, accepting the one-time confirmation prompt.

## Dirty worktree

If `git status` shows uncommitted changes (whether you were already there or after entering), show the dirty files and ask the user whether to stash, commit, or discard before proceeding.
