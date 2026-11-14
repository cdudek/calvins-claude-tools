---
type: milestone
change: 2026-11-14-tracker-session-cleanup
milestone: agent-tracker-4
branch: milestone/agent-tracker-4-1
linear_milestone: none
status: building
created: 2026-11-14
---

# Milestone: agent-tracker-4

> The owner sees only sessions that are really alive or really waiting, and can clear dead sessions and their merged worktrees from the tracker one at a time, or in one pass with the skill `git-cleanup-run`.

Kind: new. Project: agent-tracker (no project branch). Beads: cct-83h.4. Changes that joined it record `milestone.slug` in their own `decisions.json` and add their features below.

## Features

In build order. `state` is `todo`, `building`, `done <sha>` (one go: a commit on the milestone
branch), `merged` (feature PRs) or `blocked: <reason>`.

| # | Change | Feature | PR or commit | State |
|---|---|---|---|---|
| 0 | 2026-11-14-tracker-session-cleanup | sync: `git fetch origin && git merge origin/main`, locally; again after every earlier milestone merges | 115978f | done 115978f |
| 1 | 2026-11-14-tracker-session-cleanup | State and age: a row with no `pid` is ended, the last-activity age line, this session never ended | <commit> | todo |
| 2 | 2026-11-14-tracker-session-cleanup | Clear with confirm, Reopen tasks, task closing and its store write | <commit> | todo |
| 3 | 2026-11-14-tracker-session-cleanup | Worktree offer: five checks, ignored-file list, never force, branch kept | <commit> | todo |
| 4 | 2026-11-14-tracker-session-cleanup | git-cleanup-run skill and script: list, act, haiku summaries, safety guards | <commit> | todo |
| 5 | 2026-11-14-tracker-session-cleanup | Docs and release: design edits, ADR, setup.md, version bump | <commit> | todo |

## Done

- Every feature above is `done` on `milestone/agent-tracker-4-1`.
- `python3 scripts/verify_gate.py milestone 2026-11-14-tracker-session-cleanup` ends `VERIFY PASS milestone`.
- `findings.md` has no open blocking item after the one fix round.
- Row 0 ran after the last earlier milestone merged (the gate's `parent-sync` check proves it).
- One push and one PR from `milestone/agent-tracker-4-1` to `main`, after the gate passed. The owner merges it (owner, dialog, 2026-11-14, "You merge it (Recommended)"); auto-merge is never armed.
  No other PR or push for this milestone (`pr-gate.sh`).

## Outcome

Written after release (Stage 7): the success measure from `intent.md`, read where it says.

- **Measured:** <value> on <date> — **target:** <target> — **met:** <yes | no → next change>
