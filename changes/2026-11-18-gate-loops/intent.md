---
linear: none
type: intent
change: 2026-11-18-gate-loops
design: none
author: Claude for Calvin Dudek
status: approved
reviewed_by: Calvin Dudek
approved_at: 2026-11-18
created: 2026-11-18
---

# Intent: the gate hooks stop looping

> The gate hooks stop blocking once a goal has ended, and a block that comes back twice tells the agent to stop and what the owner runs.

## Asks

Every request that this change answers, in the asker's own words. Never paraphrased.

| # | Date | Source | Words | Screen | Resources |
|---|---|---|---|---|---|
| A1 | 2026-11-14 | owner, fail-early plan, M2 | "`pr-gate.sh`, `chain-gate.sh` and `gate-bash.sh` record each block message in a per-session state file." | none | [plan](asks/2026-11-14-fail-early/plan.md) |
| A2 | 2026-11-14 | owner, fail-early plan, M2 | "On the second identical block, the message changes to a stop. It names the hook script and the state it read, gives the one owner command, and says not to retry." | none | [plan](asks/2026-11-14-fail-early/plan.md) |
| A3 | 2026-11-14 | owner, fail-early plan, M2 | "A test replays two identical blocks and asserts the second message." | none | [plan](asks/2026-11-14-fail-early/plan.md) |
| A4 | 2026-11-14 | owner, fail-early plan, Why | "an active `/goal` plus `pr-gate.sh` blocked three finished pushes. Claude repeated \"type /goal clear\", and the gate still blocked after that." | none | [plan](asks/2026-11-14-fail-early/plan.md) |
| A5 | 2026-11-18 | owner, chat | "then do the recommendation" — the recommendation was: "build M2 there from the gate-fixes commits and port it to the kit." | none | none |

A5's gate-fixes commits are three downstream fixes from 2026-11-10 that never landed:
the goal check ends on a failed goal, on `/goal clear` and on an off switch, in one shared
helper; goal texts accept a merged PR and stop after 4 hours; `pr-gate.sh` ignores shell
redirects, scopes the goal to its own repo and reads `prExceptions` from the session's repo.
The goal-text fix is already covered here: since 3.10.0 every goal text is an end state that
counts an early merge and stops after 4 hours. The other two still apply to cct.

## Job stories

| # | When … | I want to … | So I can … | Evidence |
|---|---|---|---|---|
| J1 | a goal has failed or I ran `/goal clear` | the hooks to stop treating the goal as active | push and edit without fighting a gate that guards nothing | reported — A4, A5 |
| J2 | a hook blocks the same action a second time | the agent to stop and show me one command and the state the hook read | fix the cause once instead of watching retries | reported — A1, A2 |
| J3 | a hook misbehaves and I need to get past it now | one documented off switch that every hook honours | unblock myself without editing hook code | assumed — A5 |
| J4 | I push with `2>&1` on the line, or in another repo while a goal runs elsewhere | the push gate to judge only the branch and the repo the push touches | stop getting blocked by a goal that is not about this repo | reported — A5 |

## Success measure

- **Measure:** identical blocks repeated in one session. **Read in:** the new block state files, 14 days after release. **Target:** none shown more than twice by 2026-12-06.

## Problem

- **What is wrong or missing:** three hooks read "goal active" separately and miss a failed goal, `/goal clear` or an off switch. A repeated block looks like the first.
- **Who feels it:** the owner, whose finished pushes are refused while the agent retries.
- **Evidence:** A4: three finished pushes blocked, and "type /goal clear" repeated without effect.

## Proposed outcome

- After a failed goal, `/goal clear` or the off switch, no hook blocks on the goal.
- The second identical block in a session says stop, names the hook and the state it read, and gives one owner command.
- A push is judged only on its own repo and branches, never on redirects or another repo's goal.
- Every hook reads the same goal state from one helper.

## Affected users and systems

| Kind | Name | How |
|------|------|-----|
| users | engineers running sdlc-run | fewer false blocks; a clear stop instead of a loop |
| service | `templates/hooks/pr-gate.sh`, `chain-gate.sh`, `gate-bash.sh`, `verify-on-stop.sh` | share one goal helper and one block-state file |
| data | per-session block state file under the git common dir | new; local only, never committed |

## Constraints

- **Must not change:** what each gate refuses while a goal is genuinely active; the single-push milestone rule.
- **Deadline:** none.
- **Rules that apply:**
  - `CLAUDE.md#Public repo rule` — no employer or private names in the plan, tests or fixtures.
  - `CLAUDE.md#Checks` — unit tests and plugin tests pass.
  - `CLAUDE.md#How work moves: the SDLC` — one milestone, one push, one PR.
  - Fail-early principle 2 — a rule that must hold every time is a hook, never prose.
  - Fail-early principle 1 — lands in cct first, then the downstream kit is ported.

## Open questions

None. The downstream port runs after this milestone merges, as its own change in that repo.
