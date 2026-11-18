---
type: milestone
change: 2026-11-18-gate-loops
milestone: gate-loops
branch: milestone/gate-loops-1
linear_milestone: none
status: building
created: 2026-11-18
---

# Milestone: gate-loops

> When a goal has ended, the gate hooks stop blocking, and a block that repeats tells the agent to stop and what the owner runs.

Kind: milestone of one. Beads: cct-62u. Changes that joined it record `milestone.slug` in their
own `decisions.json` and add their features below.

## Features

In build order. `state` is `todo`, `building`, `done <sha>` (one go: a commit on the milestone
branch), `merged` (feature PRs) or `blocked: <reason>`.

| # | Change | Feature | PR or commit | State |
|---|---|---|---|---|
| 0 | 2026-11-18-gate-loops | sync: `git fetch origin && git merge origin/main`, locally; again after every earlier milestone merges | 6787eb9 (up to date) | done 6787eb9 |
| T | 2026-11-18-gate-loops | failing tests for F1-F15, N1, then `testLocked` | 97e239c | done 4040936 |
| 1 | 2026-11-18-gate-loops | shared goal helper | 5479733 | done 5479733 |
| 2 | 2026-11-18-gate-loops | pr-gate fixes | <commit> | building |
| 3 | 2026-11-18-gate-loops | block state and the repeat stop | <commit> | todo |
| 4 | 2026-11-18-gate-loops | release 3.16.0 / 0.13.0 | <commit> | todo |

## Done

- Every feature above is `done` on `milestone/gate-loops-1`.
- `python3 scripts/verify_gate.py milestone 2026-11-18-gate-loops` ends `VERIFY PASS milestone`.
- `findings.md` has no open blocking item after the one fix round.
- Row 0 ran after the last earlier milestone merged (the gate's `parent-sync` check proves it).
- One push and one PR from `milestone/gate-loops-1` to `main`, after the gate passed, auto-merge armed.
  No other PR or push for this milestone (`pr-gate.sh`).

## Outcome

Written after release (Stage 7): the success measure from `intent.md`, read where it says.

- **Measured:** <value> on <date> — **target:** <target> — **met:** <yes | no → next change>
