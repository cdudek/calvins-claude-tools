// A `changes/<id>/milestone.md` as sdlc-run writes it, made up for the tests.
export const MILESTONE_MD = `---
type: milestone
change: 2026-01-01-demo
milestone: demo-1
branch: milestone/demo-1
status: building
---

# Milestone: demo-1

> Open any session and see every session's repo, work and state.

## Features

| # | Change | Feature | PR or commit | State |
|---|---|---|---|---|
| 0 | 2026-01-01-demo | sync with the default branch | abc1234 | done abc1234 |
| 1 | 2026-01-01-demo | collector | def5678 | done def5678 |
| 2 | 2026-01-01-demo | backfill | <commit> | building |
| 3 | 2026-01-01-demo | band | <commit> | merged |
| 4 | 2026-01-01-demo | pane | <commit> | blocked: waits on review |

## Done

- Every feature above is done.
`

// A changes folder that holds no milestone.md (F10): it must not count as a milestone.
export const CHANGE_FOLDER_ONLY = ['changes/2026-01-01-other/plan.md', 'changes/2026-01-01-other/facts.md']
