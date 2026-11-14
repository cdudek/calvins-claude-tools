---
type: milestone
change: 2026-11-14-tracker-session-cleanup
milestone: agent-tracker-4
branch: milestone/agent-tracker-4
linear_milestone: none
status: building
created: 2026-11-14
---

# Milestone: agent-tracker-4

> The owner sees only sessions that are really alive or really waiting, and can clear dead sessions and their merged worktrees from the tracker, one at a time or in one tidy pass.

Kind: new. Project: agent-tracker (no project branch). Beads: cct-83h.4. Changes that joined it record `milestone.slug` in their own `decisions.json` and add their features below.

## Features

In build order. `state` is `todo`, `building`, `done <sha>` (one go: a commit on the milestone
branch), `merged` (feature PRs) or `blocked: <reason>`.

| # | Change | Feature | PR or commit | State |
|---|---|---|---|---|
| 0 | 2026-11-14-tracker-session-cleanup | sync: `git fetch origin && git merge origin/main`, locally; again after every earlier milestone merges | <commit> | todo |
| 1 | 2026-11-14-tracker-session-cleanup | <feature rows come from plan.md> | <commit> | todo |

## Done

- Every feature above is `done` on `milestone/agent-tracker-4`.
- `python3 scripts/verify_gate.py milestone 2026-11-14-tracker-session-cleanup` ends `VERIFY PASS milestone`.
- `findings.md` has no open blocking item after the one fix round.
- Row 0 ran after the last earlier milestone merged (the gate's `parent-sync` check proves it).
- One push and one PR from `milestone/agent-tracker-4` to `main`, after the gate passed, auto-merge armed.
  No other PR or push for this milestone (`pr-gate.sh`).

## Outcome

Written after release (Stage 7): the success measure from `intent.md`, read where it says.

- **Measured:** <value> on <date> — **target:** <target> — **met:** <yes | no → next change>
