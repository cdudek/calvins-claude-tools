---
type: checklist
change: 2026-11-18-gate-loops
created: 2026-11-18
---

# Checklist: the gate hooks stop looping

- [x] **Conflict** (F1) `chain-gate.sh` blocks edits when no goal is active ("building happens inside /goal"). Does "no active goal" after a failed goal or `/goal clear` there mean allow or still block?
- [x] **Gap** (F1, F2, F5) `chain-gate.sh` also treats an unreadable transcript as a third state and allows with a warning. Does the helper report active, inactive and unknown?
- [x] **Ambiguity** (F5) "Set and has not ended" is not the same test as today's last `goal_status` with `met: false`. Which transcript entries count as set, and which as ended?
- [x] **Ambiguity** (F3) Where is `SDLC_GOAL_OFF=1` set: the hook's environment, the agent's shell, or a settings file? Which of those can the agent change itself?
- [x] **Ambiguity** (F3) `<git-common-dir>` is resolved from which directory: the payload `cwd`, the sdlc root, or the pushed repo? Worktrees and other repos give different answers.
- [x] **Gap** (F4) Only `pr-gate.sh`, `chain-gate.sh` and `verify-on-stop.sh` must use the helper. Does `gate-bash.sh` or any other hook read goal state?
- [x] **Ambiguity** (F7) "The session's own repo" is not defined. Is it the repo of the payload `cwd`, the sdlc root, or the repo holding the transcript?
- [x] **Ambiguity** (F8) The session's repo `prExceptions` are read from which `decisions.json`, and does a row there override a pushed repo's own exceptions?
- [x] **Ambiguity** (F10, F11) A "repeat" is not defined. Is it any earlier identical block in the session, or only the previous one, and does an allowed call in between reset it?
- [x] **Gap** (F10, F13) What does a third identical block say, and does the stop wording stay for the rest of the session?
- [x] **Conflict** (F13) Facts say every repeated block gives one owner command. Assumptions say only goal blocks get the off-switch command and others "repeat their first command". Which rule wins for `gate-bash.sh` routes that name no command?
- [x] **Gap** (F9, N1; Risks) The plan has `gate-bash.sh` refuse an agent `touch …sdlc-goal-off`. That needs an `sdlc.json` `blocked[]` row, which is not in Files that change and has no fact or test.
