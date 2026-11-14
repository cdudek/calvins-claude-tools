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

## Stage 2 done

- **UX plan:** `spec/` written, validation ready after 3 rounds; prototype skipped (not risky).
- **Owner answers (dialog, 2026-11-14):** Clear "Always confirm" (focus on Cancel); `claude rm` removing its own worktree "Allow, name it"; ignored files "List them in the offer" (cap 3, then "and N more"); keep the word "Clear".
- **Not re-reviewed:** the new Confirming state and the longer offer; the analyze and challenge passes cover them.

## Verified for Stage 3 (2026-11-14)

- **pid:** all 22 live rows of `claude agents --json` carried `pid` (1 background working, 21 interactive). Exited background rows have none.
- **`claude rm` on an unlisted id:** prints "No job matching", exit non-zero; Clear skips it then.
- **Mod API:** `$.prompt.submit({ text })` starts a turn once the session is idle (tidy); `$.prompt.fill` prefills; `$.process.run(argv, { cwd, timeoutMs })` runs `claude rm` and git without a shell (30 s default, 10 min max); `$.ui.focus({ requestId, key })` or `autoFocus` sets focus. Source: the plugin-authoring skill's `types/claude-code.d.ts`.

## Next

- **Stage 3:** facts with E2E tags, checklist by a fresh reviewer, lint.
- **Stage 4:** plan, done.json, analyze, challenge, one plannotator gate, approve.
