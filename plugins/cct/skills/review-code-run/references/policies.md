# Policies

Every subcommand (`references/commands/<mode>-<lane>.md`) follows these.

## Autonomy

Once a review starts, finish it. Every selected dimension gets a reviewer. Every finding gets a validator. Do not ask the user how thorough to be, whether to skip a subset, or to confirm cost.

The only stop that is not a failure is a usage limit. Then stop, report how far you got, and re-run later; checkpoints resume it.

The only interactive gates: a dirty tree or a diverged branch in `changes` mode, and posting.

## Never post without a request

Show findings first. Post only when the user says so, naming findings by `F<id>`. `posting-pipeline.md` owns posting.

## Worktrees — `pr` modes

`pr-deep` and `pr-max` enter the PR head with `EnterWorktree`. Both routes in `mode-pr.md` (`name:` and the bot-branch `path:` fallback) run the repo's worktree-setup hook (`make worktree_setup` / Docker) the same way: it fires on the `EnterWorktree` call itself, not on the parameter. Do not `ExitWorktree` yourself. The user removes the worktree and branch.

## Codex co-review — every mode except `pr-quick`

- **Read-only.** The Codex pass runs with `--sandbox read-only`. Never drop that flag.
- **The surface leaves the machine.** Read-only stops writes, not reads. The diff and the files Codex opens go to a third-party API. Enabling co-review accepts that. The report says when it happened.
- **Secret-shaped files are withheld, not grounds to refuse.** Codex never sees `$ROOT`. `codex-review.sh` scans for secret-shaped **file names** and for **every symlink** (a link with an innocent name can point outside the repo), copies the tree without them, re-scans the copy, removes the sections of secret-shaped files from the diff it embeds, then runs Codex on the copy. Every step fails closed. There is no fallback that sends the real root. The scan never opens a file.

  **What this does not do.** It removes files whose *name* says secret. A token in `config.py` or a password in `application.yml` still reaches the API. Reading files to check would break the rule the scan serves. Co-review reduces the exposure. It does not remove it.
- **Independence is structural.** Codex starts in the same message as the Claude reviewers and never sees their findings. Agreement means something only because of that.

## `gh` failures

A failed `gh` command stops the review. Report it. Do not retry or skip.

## Changes Reviews

Committed changes only. A dirty tree stops the review; the user commits first. No posting.

## Files Reviews

Reviews code as it is. No git, no posting.

## Large diffs

Over 500 lines: suggest `pr-max` / `changes-max`. Do not narrow the scope on your own.

## Review principles

1. Check every claim against the code. Do not assert what an API does without reading it.
2. Be specific. "Could be null" is not a finding. "Null when the API returns 404, because line 23 returns undefined" is.
3. Say "Consider…" unless it is security or correctness.
4. Review the change, not the codebase.
5. A clean change is a clean change. Say so.

## `gh` errors

| Error | Cause | Fix |
|---|---|---|
| Resource not accessible by integration | token lacks `repo` scope | `gh auth status`, fix the scope |
| Validation Failed on comment post | line is not in the diff | comment only on diff lines |
