---
type: challenge
change: 2026-11-18-gate-loops
created: 2026-11-18
---

# Challenge: the gate hooks stop looping

| ID | Severity | Lens | Where | Challenge | Status |
|----|----------|------|-------|-----------|--------|
| H1 | CRITICAL | Implicit choices | facts F1–F3, F4; `chain-gate.sh` lines 354–361 | `chain-gate.sh` denies source edits when no goal is active ("building happens inside /goal"). One helper reporting "no goal" after a failed goal, `/goal clear` or the off switch makes that hook stricter. The intent says no hook blocks on the goal. The helper needs a tri-state or a per-hook meaning. | answered: facts Assumptions, Building |
| H2 | HIGH | Failure assumptions | plan Risks, off switch; `gate-bash.sh` | The guard against an agent creating the off file is a `blocked[]` regex in `sdlc.json`. `: > f`, `cp`, `python3 -c` and the Write tool all bypass it. | answered: facts F3 and Assumptions, Off switch: the file is dropped |
| H3 | HIGH | Failure assumptions | facts F3; `chain-gate.sh` lines 61–64 | The off file sits in the git common dir, outside the work tree. `chain-gate.sh` exits 0 for any path outside the root, so an agent can Write the file directly. | answered: facts Assumptions, Off switch: no file exists |
| H4 | HIGH | Implicit choices | facts F13, Assumptions | The repeat message is read by the agent and prints the exact off-switch command. An agent told not to retry will run that command itself. The message should name the owner action without a pasteable one-liner. | answered: facts Assumptions, Owner action: `/goal clear` |
| H5 | HIGH | Who else is affected | facts F3, Assumptions | The off file is repo-wide: every worktree and every concurrent session shares it, and it never expires. One session's unblock silently disables the goal rule for all, and for good. | answered: facts Assumptions, Off switch: env per Claude process |
| H6 | MEDIUM | Failure assumptions | facts F9–F11, plan Approach | Hooks read only `tool_input` today. The plan assumes the payload carries `session_id` for all three hooks, and never says what happens when it is missing. Subagent builders may share the parent's id, so two builders blocked once each look like one repeat. | answered: facts N1 and Assumptions, State file |
| H7 | MEDIUM | Failure assumptions | facts Assumptions ("same message") | Messages embed a sha, a branch or a path. A loop across new commits never repeats byte-for-byte, while two unrelated blocks hours apart do. There is no window and no reset after the cause is fixed. | answered: facts Assumptions, Same message |
| H8 | MEDIUM | Implicit choices | facts F13; `chain-gate.sh`, `gate-bash.sh` | "One owner command" exists only for the goal block. Most blocks name a route, not a command, such as the Stage 1.1 dialog or a `blocked[]` message. "Repeat the first command" is undefined for them. | answered: facts Assumptions, Owner action |
| H9 | MEDIUM | Implicit choices | facts F1–F4, N1; `pr-gate.sh`, `chain-gate.sh`, `verify-on-stop.sh` | The three hooks treat an unreadable transcript differently today: false, None with a warning, and run verify. One helper must keep three outcomes, and the plan only says "keeps today's fail-open warning". | answered: facts F14 |
| H10 | MEDIUM | Failure assumptions | facts F9, N1; plan Risks | The block file is read then appended with no lock. Two parallel tool calls both see no history, so the STOP is missed. Appends are safe, the read-decide step is not. N1 covers only an unwritable directory. | answered: facts Assumptions, Races |
| H11 | MEDIUM | Who else is affected | plan Files, `adopt.py`; `session-check.sh` | Repos in flight hold old `.claude/hooks/*.sh` until re-adopted. A new hook calling a missing `goal_active.py` exits 1, which does not block, so the gate silently opens. | answered: facts F15 and Assumptions, Old copies |
| H12 | LOW | Failure assumptions | facts F7, F8, Assumptions | `pr-gate.sh` already resolves a pushed repo by `cd` or `-C`. The plan leaves open which common dir holds the off file and the block state: the session's repo or the pushed one. Files also never get cleaned up. | answered: facts Assumptions, State file |
