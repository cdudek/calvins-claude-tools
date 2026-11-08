# Worktree Hook Usage

The cct plugin provides WorktreeCreate/WorktreeRemove hooks that change how `EnterWorktree` and `ExitWorktree` work. One rule: **a worktree lives at `<repo>/.worktrees/<name>` and starts from a freshly fetched `origin/<default branch>`.** Never a `../` sibling, never the main checkout's branch.

An EnterWorktree session is isolated to its worktree: Claude Code refuses git commands that reach outside it (the main checkout included) and refuses shell commands it cannot verify stay inside. Do not fight that — nothing in the flow needs the main checkout. New branches come from `origin/<default>` (the hook fetches), and the worktree goes away with `ExitWorktree`, which deletes the branch too.

## EnterWorktree — Name Format

**Format:** `path[@target-branch[@base-branch]]`

| Input | Worktree dir | Branch | Base |
|-------|-------------|--------|------|
| `my-feature` | `.worktrees/my-feature` | `my-feature` | `origin/<default>` |
| `my-feature@feat/login` | `.worktrees/my-feature` | `feat/login` | `origin/<default>` |
| `my-feature@feat/login@develop` | `.worktrees/my-feature` | `feat/login` | `develop` |
| `@feat/login` | `.worktrees/login` | `feat/login` | `origin/<default>` |
| `./somewhere/x` or `/abs/x` | as given | `x` | `origin/<default>` |

- A bare name lands under `<repo>/.worktrees/`; only a path starting with `/` or `.` is used as given
- The default base is `origin/<default branch>` after `git fetch origin` (`origin/HEAD`, else `master`, else `main`); with no remote, the local `master`/`main`
- A new branch is created with `--no-track`, so it never pushes back to the default branch
- If the branch already exists locally, it is checked out (no base needed)
- If the worktree already exists, it is re-entered without recreating

## ExitWorktree — Auto-Cleanup

On worktree removal:
1. Removes the git worktree (`git worktree remove --force`)
2. Deletes the local branch (if it was checked out in the worktree)
3. Prunes stale worktree metadata

If removal fails, falls back to `rm -rf` + `git worktree prune`.

## After a merge

Call `ExitWorktree` from the session that owns the worktree. Do not try to update the main checkout from inside a worktree session — the isolation refuses it, and the next `EnterWorktree` fetches anyway.
