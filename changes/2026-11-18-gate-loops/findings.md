---
type: findings
change: 2026-11-18-gate-loops
created: 2026-11-18
---

# Findings: the gate hooks stop looping

Source: `cct:review-code-run changes` (deep, Claude and Codex) on `origin/main...83ac599`. 16 findings: 14 confirmed,
1 unverifiable, 1 rejected. One fix round; each fix is its own commit. Line numbers are from the reviewed head.

## Fix round 1

- [x] **R7 off switch blocks every build edit** (`chain-gate.sh:374`, warning): with `SDLC_GOAL_OFF=1` the helper reports no goal, so chain-gate denies every milestone source edit with "building happens inside /goal", the opposite of what the switch is for (J3). Fix: while `SDLC_GOAL_OFF=1`, chain-gate skips the goal requirement and allows the edit; the docs say so.
- [x] **R8 a non-dict `message` crashes the helper** (`goal_active.py:48`, warning): a `user` row whose `message` is a list raises, both PreToolUse hooks exit with a traceback and fail open. Fix: check `isinstance(..., dict)`.
- [x] **R10 helper import can fall back to a project module** (`pr-gate.sh:84`, `chain-gate.sh`, warning): `sys.path` import finds a same-named module from the working directory when the sibling is missing. Fix: load both helpers by exact sibling path (`importlib.util.spec_from_file_location`); a missing or broken file still blocks and names `sdlc-run adopt`.
- [ ] **R12 `words: null` counts as the engineer's words** (`pr-gate.sh:156`, warning): `str(None)` is non-empty. Fix: accept only a dict row with a non-blank string `words`.
- [ ] **R14 `&>` splits the push** (`pr-gate.sh:273`, warning): `git push &> log origin <branch>` drops the refspec, so the current branch is judged instead. Fix: treat `&` followed by a `>` token as a redirect, not a separator.
- [ ] **R15 repeated relative `-C`** (`pr-gate.sh:304`, warning): each `-C` resolves against the first directory, not the previous one, as git does. Fix: resolve against the running directory.
- [ ] **R1 adopt checks only a `.sh` for ignore rules** (`adopt.py:1050`, warning): a repo that ignores `*.py` under `.claude/` keeps the helpers untracked and fresh clones block. Fix: run the check for a helper `.py` too.
- [ ] **R4 cleanup deletes any old file in the state dir; session id unchecked** (`block_state.py:48`, warning): cleanup removes only regular `*.jsonl` files, never through a symlink, and a `session_id` outside `[A-Za-z0-9_-]` gets no state file (first-time message, N1).

## Advisory

Kept, not fixed in this milestone; none blocks the gate.

- [ ] **R2 fixture copies helpers silently** (`test_block_repeat.py:60`, nit): tests are locked (`testLocked`); a later change can make the guard loud.
- [ ] **R3 F8 tested only through `gh pr create`** (`test_pr_gate.py:282`, suggestion): locked tests; the push path shares `Repo.excepted`.
- [ ] **R5 history parsed in full on every block** (`block_state.py:53`, suggestion): one session's file stays small; revisit if a session records hundreds of blocks.
- [ ] **R6 chain-gate repeat action points back at the message** (`chain-gate.sh:84`, suggestion): F13 allows "the route its first message names"; per-block actions are a later polish.
- [ ] **R11 session exceptions apply across repositories by branch name** (`pr-gate.sh:151`, unverifiable): this is F8 as approved (C8: a row in either repo excepts the branch).
- [ ] **R13 `gh pr create --repo` from another checkout skips the goal rule** (`pr-gate.sh:260`, warning): mapping a GitHub slug to the session repo needs the remote URL; a follow-up change, recorded in `questions.md`.
- [ ] **R16 a broken helper makes verify-on-stop run verify** (`verify-on-stop.sh:52`, warning): running verify is the pre-change behaviour for an unknown goal (F14), so it fails safe.

## Rejected

- **R9 clear only from `subtype: local_command`** (`goal_active.py:70`): rejected by the validator; the exact-entry match in `fbbff9d` already ignores quoted text.

## Converge
