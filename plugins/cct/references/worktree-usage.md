# Worktrees: Worktrunk first, Git fallback

Every worktree lives at `<repo>/.worktrees/<name>`. New independent work starts from a freshly fetched `origin/<default>`; explicit milestone dependencies use their named base. Existing PRs use their fetched head, never a new branch from the default.

## Preflight and installation

Worktrunk (`wt`, https://worktrunk.dev) is the preferred CLI. In sdlc-run preflight and project setup, check `command -v wt`. If missing, ask once with `AskUserQuestion`: **"Install Worktrunk (brew install worktrunk && wt config shell install)? Recommended"**. Offer Install (Recommended) and Continue with Git. Run the command only on acceptance; a decline, unavailable Homebrew or failed installation continues with Git. Reuse the answer for this session, including when setup invokes sdlc-run; hooks and scripts never prompt or install anything.

## Agent commands

Invoke the executable with `command wt`, never the interactive shell function or picker. Use `--no-cd --format json` for switching, read `.path` and set the working directory explicitly (or `EnterWorktree path=<path>` when session isolation/setup is needed). Do not source shell integration. Use `--no-hooks` for lifecycle calls from the cct hooks to prevent recursion; they emit only the absolute path on stdout. Ad-hoc commands must stop on unapproved hooks rather than silently approving them.

Creation must override Worktrunk's sibling-directory default with an exact path. `<path-config>` below is a TOML fragment `worktree-path = "<repo>/.worktrees/<name>"` (properly quote any path characters). Do not change global configuration. Fetch failures stop creation; do not fall back to a stale base.

| Operation | Worktrunk when installed | Plain Git when missing |
|---|---|---|
| New branch | `git fetch origin`, then `command wt switch -c <branch> -b origin/<default> --no-cd --format json --config-set '<path-config>'` | `git fetch origin`, then `git worktree add --no-track -b <branch> <path> origin/<default>` |
| Explicit dependency base | Same create command with `-b <base>` | Same add command with `<base>` |
| List | `command wt list --format json` | `git worktree list --porcelain` |
| Existing branch / PR | `command wt switch <branch> --no-cd --format json --config-set '<path-config>'` | `git worktree add <path> <branch>` when absent; reuse its registered path otherwise |
| Remove after merge | `command wt remove <exact-path> --foreground --format json` | `git worktree remove <exact-path>`; delete only that merged branch with `git branch -d <branch>` |
| Integrate a clean builder locally | From target: `command wt merge <target> --branch <builder> --no-commit --no-rebase --no-remove` | From target: `git merge --ff-only <builder>` |

`wt list` schema 2 stores rows in `.items[]`, with `.branch` and `.worktree.path`; legacy schema 1 is an array with `.branch` and `.path`. Read the path rather than guessing it. Never retry a failed installed `wt` operation with Git: inspect its JSON even on failure, as creation may have succeeded before a later hook failed. A new branch must not track the default branch (`git branch --unset-upstream <branch>` if needed).

`wt merge` integrates the source **into the target**, and normally squashes, rebases and removes the source. The flags above preserve prepared commits and worktrees; require clean trees and a target ancestor. If the target advanced, merge it into the builder with Git, resolve and validate there before retrying. Parent sync (`git merge origin/<parent>`) still uses Git: a remote ref has no source worktree, and pushed milestone/project branches must never be rebased. GitHub PR merges still use `gh pr merge` and their required gates. Follow [local-first verification](../skills/sdlc-run/references/local-first.md) before every push.

## EnterWorktree hook

The create hook accepts `name[@target-branch[@base-branch]]`; the tool itself may reject `@`, so explicit branch/base flows should create with the commands above and enter by path. Names and supplied paths are reduced to their basename under `.worktrees/`. A bare name is also the branch; `@feat/login` uses directory `login` and branch `feat/login`. An existing worktree is reused. With no origin, the hook supports local `master`/`main`, then HEAD for offline repositories.

An EnterWorktree session remains isolated. Use `ExitWorktree` from the owning session after merge; a path-entered worktree may need the explicit removal command above. Remove only the exact worktree you own. Never delete other worktrees or run a repository-wide prune. Removal refuses uncommitted and untracked changes with a nonzero exit, even when other hooks run concurrently. It never forces removal or branch deletion: Worktrunk keeps the branch, then `git branch -d` deletes it only when Git confirms it merged; otherwise the branch and its commits stay. Failed worktree removal leaves everything for inspection.

References: [switch](https://worktrunk.dev/switch/), [list](https://worktrunk.dev/list/), [merge](https://worktrunk.dev/merge/), [remove](https://worktrunk.dev/remove/), [config](https://worktrunk.dev/config/), [agent integration](https://worktrunk.dev/claude-code/).
