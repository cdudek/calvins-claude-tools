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
- [ ] **F3** (A5; rules principle 2) While `SDLC_GOAL_OFF=1` is set or `<git-common-dir>/sdlc-goal-off` exists, the helper shall report no active goal. Screen/state: `goal_active.py`. Tag: `@F3`.
- [ ] **F4** (A5; rules principle 2) The hooks `pr-gate.sh`, `chain-gate.sh` and `verify-on-stop.sh` shall read goal state only through `goal_active.py`. Screen/state: all three hooks. Tag: `@F4`.
- [ ] **F5** (A4; rules none) When a goal has been set and has not ended, the goal helper shall report an active goal. Screen/state: `goal_active.py`. Tag: `@F5`.

<details>
<summary>Verification</summary>

- F1 to F3, F5 — `test_goal_active.py`, one transcript fixture each, test names ending `_F1` and so on.
- F4 — `test_goal_active.py › test_hooks_share_helper_F4`: no hook template outside `goal_active.py` contains `goal_status`.

</details>

### The push gate judges only its own push

- [ ] **F6** (A5; rules none) When a `git push` line carries a redirect such as `2>&1`, `pr-gate.sh` shall not read it as a refspec. Screen/state: `pr-gate.sh`. Tag: `@F6`.
- [ ] **F7** (A5; rules none) While a goal is active, `pr-gate.sh` shall apply the goal rule only in the session's own repo. Screen/state: `pr-gate.sh`. Tag: `@F7`.
- [ ] **F8** (A5; rules none) When the session's repo has a `prExceptions` row for the pushed branch, `pr-gate.sh` shall honour it. Screen/state: `pr-gate.sh`. Tag: `@F8`.

<details>
<summary>Verification</summary>

- F6 to F8 — `test_pr_gate.py`, test names ending `_F6`, `_F7`, `_F8`.

</details>

### A repeated block says stop

- [ ] **F9** (A1; rules principle 2) When `pr-gate.sh`, `chain-gate.sh` or `gate-bash.sh` blocks, it shall append hook and message to the session's state file. Screen/state: the three hooks. Tag: `@F9`.
- [ ] **F10** (A2, A4; rules principle 2) When a hook repeats a block, its message shall start `STOP: this block repeated.` Screen/state: the three hooks. Tag: `@F10`.
- [ ] **F11** (A2; rules principle 2) When a hook repeats a block in one session, the message shall name the hook and its state. Screen/state: the three hooks. Tag: `@F11`.
- [ ] **F13** (A2; rules principle 2) When a hook repeats a block, the message shall give one owner command and say not to retry. Screen/state: the three hooks. Tag: `@F13`.
- [ ] **F12** (A3; rules CLAUDE.md#Checks) A test shall replay two identical blocks per hook and assert the second message. Screen/state: tests. Tag: `@F12`.
- [ ] **N1** (A1; rules none) A missing or unwritable state file shall never make a hook fail. The hook then gives its first-time message.

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

- The block state lives at `<git-common-dir>/sdlc-blocks/<session_id>.jsonl`: outside the work tree, so it is never committed, and shared by all worktrees of a repo.
- "The same message" means the same hook and byte-identical message text after stripping the `STOP:` prefix.
- The owner command for a repeated goal block is `touch "$(git rev-parse --git-common-dir)/sdlc-goal-off"`. Other blocks repeat their first command.
- The transcript shapes for a failed goal and `/goal clear` are the ones the downstream fix pinned on 2026-11-10; tests pin them again here.

## Deferred

none

## Open questions

none
