---
type: validation
change: 2026-11-18-gate-loops
created: 2026-11-18
---

# Validation: the gate hooks stop looping

Each fact against the test that proves it, run on the milestone head after feature 4
(`pytest test_goal_active.py test_pr_gate.py test_block_repeat.py test_adopt.py`: 206 passed).
Count = passing test cases whose name ends in the tag (parametrized cases count once each).

| Fact | Tests | Cases | Evidence | Verdict |
|---|---|---|---|---|
| F1 | `test_goal_active.py` failed-goal cases | 3 | failed `goal_status` reads as no goal; CLI exits 1 | met |
| F2 | `test_goal_active.py` `/goal clear` cases | 2 | clear command plus `No goal set` reads as no goal; quoted text in an `api-request-blob` does not | met |
| F3 | `test_goal_active.py` env switch and file negative | 2 | `SDLC_GOAL_OFF=1` turns a running goal off; a `sdlc-goal-off` file does not | met |
| F4 | `test_hooks_share_helper_F4` | 1 | no template but `goal_active.py` contains `goal_status`; the three hooks call it | met |
| F5 | `test_goal_active.py` running cases | 5 | a set goal not ended reads as running | met |
| F6 | `test_pr_gate.py` redirect cases | 10 | `2>&1`, `> f`, `>f`, `2>> f`, `2>>f`, `&>f`, `&> f` never read as refspecs; a refused push stays refused | met |
| F7 | `test_pr_gate.py` other-repo cases | 3 | a push in another repo skips the goal rule; other rules still apply; a worktree of the start repo counts | met |
| F8 | `test_pr_gate.py` session `prExceptions` | 2 | a start-repo row excepts the branch; an empty `words` does not | met |
| F9 | `test_block_repeat.py` record cases | 9 | each hook appends `{hook, message, ts}` to `<common-dir>/sdlc-blocks/<session>.jsonl`; 14-day cleanup | met |
| F10 | `test_block_repeat.py` repeat cases | 13 | a second and a third identical block start `STOP: this block repeated.`; another session or message is not a repeat | met |
| F11 | `test_block_repeat.py` source cases | 6 | the repeat names the hook script and what it read | met |
| F12 | `test_block_repeat.py` replay cases | 4 | two identical blocks replayed per hook, second message asserted | met |
| F13 | `test_block_repeat.py` owner-action cases | 6 | `Do not retry` and one `Owner action:`; `/goal clear` for the push-gate goal block | met |
| F14 | `test_goal_active.py` unreadable cases | 9 | helper returns None; each hook keeps its old handling | met |
| F15 | `test_goal_active.py`, `test_adopt.py` | 7 | a hook without the helper exits 2 and names `sdlc-run adopt`; adopt copies the helpers | met |
| N1 | `test_block_repeat.py` unwritable cases | 11 | read-only state dir or `.git`, a file in place of the dir, no session id, a bad cwd: the normal block, never a crash | met |

## Asks

| Ask | Covered by | Verdict |
|---|---|---|
| A1 `pr-gate.sh`, `chain-gate.sh` and `gate-bash.sh` record each block per session | F9, N1 | met |
| A2 the second identical block says stop, names the hook and its state, gives one owner command, says not to retry | F10, F11, F13 | met |
| A3 a test replays two identical blocks and asserts the second message | F12 | met |
| A4 a finished goal no longer blocks pushes, and `/goal clear` takes effect | F1, F2, F5, F7 | met |
| A5 the downstream gate fixes built here: one goal reading, an off switch, redirects, repo scope, session exceptions | F3, F4, F6, F7, F8, F14, F15 | met |
