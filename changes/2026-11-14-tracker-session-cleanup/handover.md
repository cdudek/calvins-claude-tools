---
type: handover
change: 2026-11-14-tracker-session-cleanup
created: 2026-11-14
---

# Handover: agent-tracker-4

## Done

- **Cleanup by hand (2026-11-14):** 72 worktrees removed (63 merged or never started, 9 older than a month with leftovers committed first, 5 of those pushed), 6 dead or idle sessions closed. Nothing forced; branches kept.
- **Stage 1:** decisions (L, feature, new milestone agent-tracker-4, project agent-tracker without a branch, Beads cct-83h.4, design `docs/designs/agent-tracker.md`). Intent confirmed by the owner.
- **Repo:** sdlc stamped 3.15.1 with the repo's own `adopt.py`. The installed cct cache lags the repo source, so run the repo's scripts, not the cache's.

## Root cause found

- **Dead sessions:** `claude agents --json` keeps exited background sessions as `state: blocked` with no `pid`. `core/states.ts` `deriveState` maps `blocked` to needs-you and never looks at `pid`.
- **"since":** the session page shows when the tracker first saw the row, not the last activity.
- **Asks:** open asks of an ended session stay in "Your tasks not done" by design; nothing dismisses them.

## Next

- **Stage 2:** UX plan for the Clear action on the session page, its confirm, and `/tracker tidy`.
- **Then:** facts, plan, analyze, challenge, one gate.
