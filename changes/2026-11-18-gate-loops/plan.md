---
linear: none
type: plan
change: 2026-11-18-gate-loops
design: none
author: Claude for Calvin Dudek
status: approved
reviewed_by: Calvin Dudek
approved_at: 2026-11-18
created: 2026-11-18
---

# Plan: the gate hooks stop looping

> One shared goal helper that sees an ended goal, a push gate that judges only its own push, and a second identical block that says stop.

A person with no context builds from this file alone. [intent](intent.md) and
[facts](facts.md) are for the gate, not for the build.

## Approach

- **What changes:** a new `goal_active.py` replaces three copies of the goal reading. A new `block_state.py` records blocks and rewrites a repeat. `pr-gate.sh` drops redirects, scopes the goal and reads session `prExceptions`.
- **What stays the same:** what each gate refuses while a goal genuinely runs; the one-push milestone rule; hook exit codes and timeouts.
- **Why this way:** the downstream fix of 2026-11-10 already proved the helper and the pr-gate fixes with tests; porting them is cheaper than redesigning. Block state is one small module because three hooks need the same rewrite.
- **Rejected:** a counter inside each hook — three copies drift, which is the bug F4 removes. A Stop-hook check of the agent's replies — judging replies is prose territory (facts, Out of scope).
- **Seed:** the downstream commits `2dabdce` and `1d108ad` are context, not a patch. cct's hooks moved since, so builders re-apply the idea.

## Rules check

- Before design: pass. No private names (the seed's names stay out of every file); tests run under `CLAUDE.md#Checks`; one milestone.
- After design: pass. New files sit in `templates/hooks/` and `scripts/`, the state file lives outside the work tree.

### Justified violations

| Violation | Why needed | Simpler alternative rejected because |
|---|---|---|
| none | | |

## Design changes

none — no design file covers the hooks. `docs/sdlc.md` (template `templates/docs-sdlc.md`) gains the off switch under "Hooks".

## Where things go

| New file or kind | Folder |
|---|---|
| goal helper, block-state helper | `plugins/cct/skills/sdlc-run/templates/hooks/` |
| their tests | `plugins/cct/skills/sdlc-run/scripts/` |
| repo copies (refreshed by `adopt`) | `.claude/hooks/` |

## Feature PRs

### Milestone 1 — an ended goal stops blocking, and a repeated block says stop

| # | Feature | Facts | Branch | State |
|---|---|---|---|---|
| 0 | sync: `git fetch origin && git merge origin/main` | — | `milestone/gate-loops-1` | todo |
| 1 | Shared goal helper; `pr-gate.sh`, `chain-gate.sh`, `verify-on-stop.sh` call it; `adopt` copies it | F1–F5, F14, F15 | `milestone/gate-loops-1` | todo |
| 2 | `pr-gate.sh`: redirects are not refspecs, goal scoped to the session repo, session-repo `prExceptions` | F6–F8 | `milestone/gate-loops-1` | todo |
| 3 | Block state and the repeat stop in `pr-gate.sh`, `chain-gate.sh`, `gate-bash.sh`; `adopt` copies it | F9–F13, N1 | `milestone/gate-loops-1` | todo |
| 4 | Release: changelog 3.16.0, plugin 0.13.0, docs off switch, `adopt` refresh of `.claude/hooks/` | all | `milestone/gate-loops-1` | todo |

Features 1 and 2 both edit `pr-gate.sh`; 3 edits the same hooks. Build them in order, not in parallel.

## Files that change

| File | Change |
|------|--------|
| `plugins/cct/skills/sdlc-run/templates/hooks/goal_active.py` | new: the one goal reading, off switch |
| `plugins/cct/skills/sdlc-run/templates/hooks/block_state.py` | new: record a block, rewrite the repeat |
| `plugins/cct/skills/sdlc-run/templates/hooks/pr-gate.sh` | helper, redirects, repo scope, session `prExceptions`, block state |
| `plugins/cct/skills/sdlc-run/templates/hooks/chain-gate.sh` | helper, block state |
| `plugins/cct/skills/sdlc-run/templates/hooks/gate-bash.sh` | block state |
| `plugins/cct/skills/sdlc-run/templates/hooks/verify-on-stop.sh` | helper |
| `plugins/cct/skills/sdlc-run/scripts/adopt.py` | copy `*.py` from `templates/hooks/` too, and let the repo's ignore rules keep them |
| `plugins/cct/skills/sdlc-run/SKILL.md` | `version: 3.16.0` |
| `plugins/cct/skills/sdlc-run/scripts/test_goal_active.py` | new |
| `plugins/cct/skills/sdlc-run/scripts/test_block_repeat.py` | new |
| `plugins/cct/skills/sdlc-run/scripts/test_pr_gate.py`, `test_chain_gate.py`, `test_gate_bash.py`, `test_adopt.py` | updated for the above |
| `plugins/cct/skills/sdlc-run/references/changelog.md` | 3.16.0 entry |
| `plugins/cct/skills/sdlc-run/templates/docs-sdlc.md`, `docs/sdlc.md` | the off switch |
| `plugins/cct/.claude-plugin/plugin.json` | 0.13.0 |
| `.claude/hooks/*`, `sdlc.json` `kitTemplates` | refreshed by `adopt` |
| `changes/2026-11-18-gate-loops/**` | records |

## Order of work

- [x] 0. Sync — proof: `git merge-base --is-ancestor origin/main HEAD` exits 0.
- [ ] 1. Goal helper — proof: `test_goal_active.py` F1–F5, F14, F15 pass; `grep -l goal_status templates/hooks/*.sh` prints nothing.
- [ ] 2. pr-gate fixes — proof: `test_pr_gate.py` F6–F8 pass.
- [ ] 3. Block state — proof: `test_block_repeat.py` F9–F13 and N1 pass.
- [ ] 4. Release — proof: `python3 -m unittest discover -s tests && scripts/run-plugin-tests.sh` exits 0; `adopt` leaves no diff on a second run.

## Milestones

| Milestone | Features | needs |
|-----------|----------|-------|
| M1 gate-loops | F1–F15, N1 | none |

## Risks

| Risk | What we do | Where it lands |
|------|------------|----------------|
| The transcript shapes for a failed goal and `/goal clear` are undocumented and may change | pin each shape in a fixture; an unreadable transcript keeps today's fail-open warning | step 1, `test_goal_active.py` |
| The off switch lets an agent skip the gate on its own | env only, read from the environment Claude starts with; no file the agent can write | step 1, F3 |
| A hook gets slower | block state is one append and one read of a small file; each hook stays under its 5 s timeout | step 3 |
| The seed's names leak into cct | builders get the ideas in the context pack, never the seed's paths; `tests/test_plugin.py` greps | step 4 |

## Out of scope

- The downstream kit port: its own change in that repo after this milestone merges.
- Fail-early M0, M1, M3–M6: later changes.

## Done

- `python3 scripts/verify_gate.py milestone 2026-11-18-gate-loops` ends `VERIFY PASS` once, on the milestone.
- `plugins/cct/skills/sdlc-run/templates/hooks/goal_active.py` and `block_state.py` exist.
- F1 to F15 and N1 pass by their named tests.
- Nothing outside `## Files that change` is edited.
- Stop and report as soon as a step cannot proceed. Never work around a blocker.
- Stop after 150 turns if not met. Report what is missing.

## How to run

The process of the build. The `/goal` below holds only the end state. Read the [local-first
contract](https://github.com/cdudek/calvins-claude-tools/blob/main/plugins/cct/skills/sdlc-run/references/local-first.md)
before any check or push.

- **Scope:** deliver this change in one go, per this plan and `facts.md`.
- **Milestone:** one, `milestone/gate-loops-1`, already cut from `origin/main` in `.worktrees/gate-loops`. Nothing is pushed before its gate passes.
- **Sync:** row 0 is a local `git fetch origin && git merge origin/main`. Repeat it right before the close. Never a PR.
- **Features:** in order 1 to 4, never in parallel (they share files). Write the tests for the feature's facts first, then build in the folders of `## Where things go`, commit with a Conventional Commit subject. Between features run the touched tests only, then start the next feature at once.
- **Builders:** each feature goes to one `cct:sdlc-feature-builder` (sonnet, high). Its context pack holds the facts, plan rows, cited rules and, for 1 and 2, the seed idea. Dispatch with isolation `worktree` and `Base: <milestone head sha>`; merge back one at a time.
- **Tests found:** `scripts/run-plugin-tests.sh` runs every `test_*.py` under `plugins/cct/skills`, so new tests need no wiring.
- **Bug lock:** after feature 1's failing tests are committed, set `testLocked: true` in `decisions.json` (`docs/sdlc.md`, bugs).
- **Records:** findings, validation, gate output and every fix are commits on the milestone branch. No other PR or push.
- **Questions:** never stop the build; write them to `questions.md` with the default taken.
- **Close:** one `cct:sdlc-feature-builder` with `Mode: close` runs the unit and plugin tests, the one fix round, then `python3 scripts/verify_gate.py milestone 2026-11-18-gate-loops`, full output pasted. No E2E suite exists in this repo.
- **Meanwhile:** dispatch `cct:review-code-run` on the milestone diff; validate every fact and ask into `validation.md`; run the converge pass into `findings.md` until `Converged: round <n>`.
- **Publish:** only on `VERIFY PASS milestone 2026-11-18-gate-loops <sha>` at the local head. Then one push, one PR to `main`, `gh pr merge <n> --merge --auto`. Ask first when a Critical or High is deferred.
- **Red CI:** reproduce the failing test locally, fix, run it and its suite, the full suite once, one push.
- **Blocked:** on `VERIFY BLOCKED`, stop and summarize `verify/report.md`. Never edit `facts.md`, `done.json`, `lock.json` or `sdlc.json` checks.
- **Bookkeeping:** tick this plan's tasks as they land; log departures under `## Revisions`.
- **Agents:** builders are `cct:sdlc-feature-builder`; reviews use their typed agents; any other subagent gets `model: sonnet`.

## Goal handover

Kickoff prompt:

```
Run change 2026-11-18-gate-loops: follow `## How to run` in changes/2026-11-18-gate-loops/plan.md to the end, then
print `python3 <STATUS> goal 2026-11-18-gate-loops`.
```

The goal:

```
/goal `python3 <STATUS> goal 2026-11-18-gate-loops` printed `GOAL 2026-11-18-gate-loops DONE` or `GOAL 2026-11-18-gate-loops BLOCKED` as its last run in this conversation, or stop after 150 turns.
```

## Revisions

Only after approval.

- **2026-11-18, test lock order:** the failing tests for every fact (F1-F15, N1) and the fixture updates land in one test-first commit before feature 1, then `testLocked: true`. Why: this is a v3 bug, and once locked `chain-gate.sh` refuses every `test_*.py` edit on this branch, so features 2-4 could not add their tests after feature 1. Recorded in `questions.md`.
