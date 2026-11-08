---
type: milestone
change: {{CHANGE}}
milestone: <slug>
branch: milestone/<slug>
linear_milestone: <name, or none>
status: building
created: {{DATE}}
---

# Milestone: <slug>

> One sentence. What a user can do when this milestone reaches the default branch.

Kind: <new | milestone of one | hotfix>. Changes that joined it record `milestone.slug` in their
own `decisions.json` and add their features below.

## Features

In build order. `state` is `todo`, `building`, `done <sha>` (one go: a commit on the milestone
branch), `merged` (feature PRs) or `blocked: <reason>`.

| # | Change | Feature | PR or commit | State |
|---|---|---|---|---|
| 0 | {{CHANGE}} | sync: `git fetch origin && git merge origin/<default>` (in a project also `origin/project/<slug>`), locally; again after every earlier milestone merges | <commit> | todo |
| 1 | {{CHANGE}} | <feature> | <commit> | todo |

## Done

- Every feature above is `done` (one go) or `merged` (feature PRs) on `milestone/<slug>`.
- `python3 scripts/verify_gate.py milestone {{CHANGE}}` ends `VERIFY PASS milestone`.
- `findings.md` has no open blocking item after the one fix round.
- Row 0 ran after the last earlier milestone merged (the gate's `parent-sync` check proves it).
- One push and one PR from `milestone/<slug>` to its parent, after the gate passed, auto-merge armed.
  No other PR or push for this milestone (`pr-gate.sh`).

## Outcome

Written after release (Stage 7): the success measure from `intent.md`, read where it says.

- **Measured:** <value> on <date> — **target:** <target> — **met:** <yes | no → next change>
