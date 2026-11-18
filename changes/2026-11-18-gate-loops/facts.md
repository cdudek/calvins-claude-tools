---
linear: none
type: facts
change: 2026-11-18-gate-loops
design: none
author: Claude for Calvin Dudek
status: draft
reviewed_by: null
approved_at: null
created: 2026-11-18
---

# Facts: the gate hooks stop looping

## Goal

Once a goal has ended, no sdlc-run hook blocks on it. A block that comes back in the same
session says stop and names the one command the owner runs. This is one change because every
part reads the same two things: the session's goal state and the session's block history.

## Acceptance criteria

The hooks are the templates in `plugins/cct/skills/sdlc-run/templates/hooks/`; `adopt` copies
them to a repo's `.claude/hooks/`. There is no screen: "Screen/state" names the hook. Tests are
unittest files in `plugins/cct/skills/sdlc-run/scripts/`, each fact's test name carries its tag.

### One reading of the goal

- [ ] **F1** (A4, A5; rules principle 2) When the transcript's last goal entry is a failed goal, the helper shall report no active goal. Screen/state: `goal_active.py`. Tag: `@F1`.
- [ ] **F2** (A4, A5; rules principle 2) When `/goal clear` follows a running goal in the transcript, the goal helper shall report no active goal. Screen/state: `goal_active.py`. Tag: `@F2`.
- [ ] **F3** (A5; rules principle 2) While `SDLC_GOAL_OFF=1` is in the hook's environment, the helper shall report no active goal. Screen/state: `goal_active.py`. Tag: `@F3`.
- [ ] **F4** (A5; rules principle 2) The hooks `pr-gate.sh`, `chain-gate.sh` and `verify-on-stop.sh` shall read goal state only through `goal_active.py`. Screen/state: all three hooks. Tag: `@F4`.
- [ ] **F5** (A4; rules none) When a goal has been set and has not ended, the goal helper shall report an active goal. Screen/state: `goal_active.py`. Tag: `@F5`.
- [ ] **F14** (A5; rules none) When the transcript is unreadable, each hook shall behave as it did before this change. Screen/state: the three hooks. Tag: `@F14`.
- [ ] **F15** (A5; rules principle 2) If `goal_active.py` is missing beside a hook, the hook shall block and name `sdlc-run adopt`. Screen/state: the three hooks. Tag: `@F15`.

<details>
<summary>Verification</summary>

- F1 to F3, F5 — `test_goal_active.py`, one transcript fixture each, test names ending `_F1` and so on.
- F4 — `test_goal_active.py › test_hooks_share_helper_F4`: no hook template outside `goal_active.py` contains `goal_status`.
- F14, F15 — `test_goal_active.py`, one case per hook, names ending `_F14`, `_F15`.

</details>

### The push gate judges only its own push

- [ ] **F6** (A5; rules none) When a `git push` line carries a redirect such as `2>&1`, `pr-gate.sh` shall not read it as a refspec. Screen/state: `pr-gate.sh`. Tag: `@F6`.
- [ ] **F7** (A5; rules none) While a goal is active, `pr-gate.sh` shall apply the goal rule only to pushes in the session's start repo. Screen/state: `pr-gate.sh`. Tag: `@F7`.
- [ ] **F8** (A5; rules none) When the session's start repo has a `prExceptions` row for the pushed branch, `pr-gate.sh` shall honour it. Screen/state: `pr-gate.sh`. Tag: `@F8`.

<details>
<summary>Verification</summary>

- F6 to F8 — `test_pr_gate.py`, test names ending `_F6`, `_F7`, `_F8`.

</details>

### A repeated block says stop

- [ ] **F9** (A1; rules principle 2) When `pr-gate.sh`, `chain-gate.sh` or `gate-bash.sh` blocks, it shall append hook and message to the session's state file. Screen/state: the three hooks. Tag: `@F9`.
- [ ] **F10** (A2, A4; rules principle 2) When a hook repeats a block, its message shall start `STOP: this block repeated.` Screen/state: the three hooks. Tag: `@F10`.
- [ ] **F11** (A2; rules principle 2) When a hook repeats a block, the message shall name the hook script and the file or entry it read. Screen/state: the three hooks. Tag: `@F11`.
- [ ] **F12** (A3; rules CLAUDE.md#Checks) A test shall replay two identical blocks per hook and assert the second message. Screen/state: tests. Tag: `@F12`.
- [ ] **F13** (A2; rules principle 2) When a hook repeats a block, the message shall give one owner action and say not to retry. Screen/state: the three hooks. Tag: `@F13`.
- [ ] **N1** (A1; rules none) A missing session id or unwritable state file shall never make a hook fail. The hook then gives its first-time message. Screen/state: the three hooks. Tag: `@N1`.

<details>
<summary>Verification</summary>

- F9 to F13 — `test_block_repeat.py`, test names ending `_F9` to `_F13`.
- N1 — `test_block_repeat.py › test_unwritable_state_N1`: a read-only common dir still yields the normal block.

</details>

## Verification

- **Automated:** `python3 -m unittest discover -s tests && scripts/run-plugin-tests.sh` exits 0.
- **Manual:** none; there is no screen.

## Out of scope

- **The 4-hour goal stop and early-merge handling** (A5) — already true since sdlc-run 3.10.0. Every goal text is an end state with a 4-hour stop.
- **Reply length and "still waiting"** (fail-early M2) — judging a reply is not a hook's job; it stays prose.
- **The downstream kit port** (A5) — its own change in that repo after this milestone merges.
- **Fail-early M0, M1, M3–M6** — later changes; the umbrella plan is in `asks/2026-11-14-fail-early/plan.md`.

## Assumptions

Answers to `checklist.md`, one line each.

- **Goal states (C1–C3):** the helper returns active, inactive, or unknown when the transcript is unreadable. Each hook keeps today's handling of unknown.
- **Running (C3):** the last goal entry is a `goal_status` with `met: false`, or the "Stop hook is now active" line. Not `failed`.
- **Ended (C3):** a `goal_status` with `met: true` or `failed: true`, or `/goal clear`.
- **Building (C1, H1):** with no running goal, `chain-gate.sh` keeps refusing code edits. Building happens only inside a goal. An ended goal must not count as running.
- **Off switch (C4, H2–H5):** only `SDLC_GOAL_OFF=1` in the environment Claude starts with. An agent's Bash export never reaches a hook. No off-switch file exists: the agent could write one.
- **Common dir (C5):** resolved from the hook payload's `cwd`. All worktrees of one repo share it.
- **Readers (C6):** only `pr-gate.sh`, `chain-gate.sh` and `verify-on-stop.sh` read goal state today. F4's test checks every template.
- **Start repo (C7, C8):** the repo of the session's project dir. A push in another repo skips the goal rule.
- **Exceptions (C8):** a `prExceptions` row in either the pushed repo or the start repo excepts the branch.
- **Repeat (C9):** any earlier entry with the same hook and message in this session. Allowed calls in between do not reset it.
- **Third block (C10):** every repeat after the first carries the `STOP:` wording.
- **Owner action (C11, H4, H8):** for a goal block, "type `/goal clear`", which only the owner can run. For any other block, the route its first message names.
- **State file (H6, H12):** `<git-common-dir>/sdlc-blocks/<session_id>.jsonl`, from the payload's `session_id` and `cwd`. Never committed; files older than 14 days are deleted on write.
- **Same message (H7):** byte-identical text. A block naming a new sha is a new block, on purpose.
- **Races (H10):** two parallel identical blocks may both read as first. One append per block; the next repeat still stops.
- **Old copies (H11):** `adopt` copies the helpers with the hooks; F15 makes a missing helper block, not open.
- **Shapes:** the failed-goal and `/goal clear` transcript lines pinned downstream on 2026-11-10; tests pin them again.

## Deferred

none

## Open questions

none
