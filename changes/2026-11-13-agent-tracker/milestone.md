---
type: milestone
change: 2026-11-13-agent-tracker
milestone: agent-tracker-1
branch: milestone/agent-tracker-1
linear_milestone: none
status: building
created: 2026-11-13
---

# Milestone: agent-tracker-1

> Open any Claude Code session and see, in a band above the prompt and a pane, every session's repo, work and state, and which need you.

Kind: new. Changes that joined it record `milestone.slug` in their own `decisions.json` and add their features below.

## Features

In build order. `state` is `todo`, `building`, `done <sha>` (one go: a commit on the milestone
branch), `merged` (feature PRs) or `blocked: <reason>`.

| # | Change | Feature | PR or commit | State |
|---|---|---|---|---|
| 0 | 2026-11-13-agent-tracker | sync: `git fetch origin && git merge origin/<default>` (in a project also `origin/project/<slug>`), locally; again after every earlier milestone merges | <commit> | todo |
| 1 | 2026-11-13-agent-tracker | collector: `claude agents --json` plus the mod's per-session file, asks classified task or question with a pinned cheap model | <commit> | todo |
| 2 | 2026-11-13-agent-tracker | backfill and scans: sessions without the mod from transcripts, plus git, gh and bd scans | <commit> | todo |
| 3 | 2026-11-13-agent-tracker | band: details and compact views, Copy, Pane and Board buttons, header naming repo, work and what runs | <commit> | todo |
| 4 | 2026-11-13-agent-tracker | pane: attention, sessions by repo, tasks in order, PRs, opened by `/tracker` | <commit> | todo |

## Done

- Every feature above is `done` (one go) or `merged` (feature PRs) on `milestone/agent-tracker-1`.
- `python3 scripts/verify_gate.py milestone 2026-11-13-agent-tracker` ends `VERIFY PASS milestone`.
- `findings.md` has no open blocking item after the one fix round.
- Row 0 ran after the last earlier milestone merged (the gate's `parent-sync` check proves it).
- One push and one PR from `milestone/agent-tracker-1` to its parent, after the gate passed, auto-merge armed.
  No other PR or push for this milestone (`pr-gate.sh`).

## Outcome

Written after release (Stage 7): the success measure from `intent.md`, read where it says.

- **Measured:** <value> on <date> — **target:** <target> — **met:** <yes | no → next change>
