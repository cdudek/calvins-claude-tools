---
type: analyze
change: 2026-11-14-tracker-session-cleanup
reviewer: fresh context, read-only
reads: intent.md, facts.md, checklist.md, plan.md, done.json, milestone.md, decisions.json, spec/, sdlc.json, docs/designs/agent-tracker.md, docs/ux/setup.md, CLAUDE.md, AGENTS.md, plugins/cct/skills/sdlc-run/scripts/sdlc_status.py, plugins/agent-tracker/ (hooks, tests), tests/test_agent_tracker_layout.py
created: 2026-11-14
---

# Analyze: Tracker session cleanup, milestone agent-tracker-4

Six passes, read-only: duplication, ambiguity, underspecification, rules alignment, coverage, inconsistency. Claims were checked by reading files and running read-only scripts, not taken from the plan.

Counts: 0 CRITICAL, 4 HIGH, 7 MEDIUM, 3 LOW (14 in all). No `open` CRITICAL, so `verify_gate.py approve` is not blocked by this pass. Four HIGH should be closed before gate 2.

## Checked and clean

- **Fact to done.json:** 74 facts (F1 to F73, N1) in `facts.md`, 74 entries in `done.json`. No id on one side only. `tag` equals `@F<n>` for every entry (N1 is manual, tag null). `feature` equals the plan row for every fact.
- **Fact to plan row:** each of the 74 ids is in exactly one of rows 1 to 4 (counts 9, 27, 15, 23 = 74). No gap, no overlap, no id outside the facts. Row 5 and row 0 carry none, as stated.
- **Test files:** every file named in the Verification block exists (`collector`, `band`, `pane`, `tasks`, `safety`) or is a new file listed in the plan's Where things go (`clear.test.ts`, `worktree.test.ts`, `tidy.test.ts`).
- **Core purity:** `core/` may import only `./` and two type paths, and may not touch `$.`, `Date.now` or `new Date(` (layout test). The plan's new core files take time as a parameter, and the start date uses the injected `Local` formatter (`Local.clock` and `Local.day` already work this way). No violation.
- **Safety invariants:** never `--force` or `branch -D` (F64, `safety.test.ts`); never `claude stop`, never `claude rm` with a `pid`, never remove a worktree with a live session (F65, F9, F23, F35); never act on its own (F66, F17, F18). Each has a fact and a named test. The weak point is X2.
- **Intent to facts:** every proposed-outcome bullet and every constraint (never force, branch kept, running session untouched, owner press only) maps to a fact.
- **Folders:** every file in Files that change sits in a Where things go folder, except the screenshots of step 17 (X11).
- **Repo rules:** no skill or agent is added (NAME-1 clean, but see X6), no hosted page (PUB-2), no dependency, `haiku` for the mod's own calls (MODEL-1, none added).

## Milestone branch name

`sdlc_status.py goal` (`branches()`, lines 181 to 192) derives the head branch as `milestone/<slug>-<i>`, with `<slug>` from `decisions.json` `milestone.slug` (`agent-tracker-4`) and `<i>` from 1 to the number of `| M<n>` rows under `## Milestones` (one here). It expects `milestone/agent-tracker-4-1`. The plan's Feature PRs table, `milestone.md` `branch:` and the checked-out branch say `milestone/agent-tracker-4`. See X1.

## Coverage

Ask, facts, tags, plan row. A2 has no fact by design.

| Ask | Facts | Tags | Plan row |
|---|---|---|---|
| A1 | F48, F49, F51, F54, F62, F63, F69 | `@F48 @F49 @F51 @F54 @F62 @F63 @F69` | 4 |
| A2 | out of scope (facts and plan Out of scope: done by hand 2026-11-14) | none | none |
| A3 | F8, F10, F13 to F18, F25, F29 to F32, F70 | `@F<n>` each | 2 |
| A4 | F8 to F14, F16 to F28, F33 to F47, F49, F57 to F62, F64 to F70, N1 | `@F<n>` each | 2, 3, 4 |
| A5 | F1 to F7, F15, F32, F71, F72 | `@F<n>` each | 1, 2 |
| A6 | F1 to F4, F22, F25, F29, F48 to F63, F64, F65, F72, F73 | `@F<n>` each | 1, 2, 3, 4 |

No fact without an ask. No ask without a fact except A2.

## Findings

| ID | Severity | Pass | Where | Finding | Status |
|---|---|---|---|---|---|
| X1 | HIGH | inconsistency | `plan.md` Feature PRs (rows 0 to 5), How to run, `milestone.md` `branch:`, `decisions.json`, `sdlc_status.py` `branches()` | The goal script looks for a PR from `milestone/agent-tracker-4-1`; the plan and the live branch are `milestone/agent-tracker-4`. `GOAL ... DONE` cannot print: it ends `OPEN no-pr:milestone/agent-tracker-4-1`. Fix: use `milestone/agent-tracker-4-1` in plan rows, `milestone.md` and the branch (`git branch -m`, local only), or change the script to accept `milestone/<slug>` for a one-row plan. Milestone 1 has the same shape (`milestone/agent-tracker-1`). | fixed: `plan.md` Feature PRs row 0, `milestone.md` `branch:` and its Done line now say `milestone/agent-tracker-4-1`, the branch `sdlc_status.py` `branches()` builds as `milestone/<slug>-<i>` |
| X2 | HIGH | rules alignment | `plan.md` Approach "Arming a batch", Risks "supervisor's tools run without the owner's answer"; `facts.md` F59, F66 | If the host's question result carries no chosen label, the plan keeps only the fixed list and the re-check as the guard, so a model can call `tidy_clear_session` with no owner answer. That breaks F66 and ACT-1 (every write follows a press or an answer). No fact says an unarmed tool call refuses, so no test proves it. Fix: fail closed (no arming, no act), add "an unarmed call refuses and writes nothing" to F59 or F66 with a test in `tidy.test.ts`, and make step 15's probe a stop-and-report gate. | fixed: the tools and arming are gone; `act` runs only the ids the owner chose, re-checked (F59, F66, F81) |
| X3 | HIGH | rules alignment | `plan.md` step 6, Risks "`claude rm` may need a TTY" | Step 6 has the build agent run `claude rm` on a real dead session. That removes a list entry that "does not come back" (F19) with no owner press, against F66 and the intent's "never on its own". The Risks row says the owner presses Clear once. Fix: drop the real-session probe from the unattended build; probe with a throwaway session the builder starts, or leave it to the owner at the render check, and write the default in `questions.md`. | fixed: `plan.md` step 6 probes a fake `claude` on `PATH` (F82); the one real `claude rm` is the owner's press at the render check |
| X4 | HIGH | rules alignment | `plan.md` Goal handover (lines 360 and 366, four hits) | The committed plan holds `/Users/<name>/projects/...` local paths. CLAUDE.md public repo rule bans local paths; `tests/test_plugin.py` does not grep them, so nothing catches it. Milestone 1's plan has the same four. Fix: write the repo-relative `plugins/cct/skills/sdlc-run/scripts/sdlc_status.py`, and fix the template that fills the block. | fixed: `plan.md` Goal handover keeps `<STATUS>` literal with a repo-relative command; milestone 1's plan is outside this folder (Risk row) |
| X5 | MEDIUM | inconsistency | `facts.md` N1, `done.json` `widths`, `plan.md` step 17 and Risks | N1 and step 17 say 120, 80, 40 and a 24-column dock; `done.json` lists 24, 40, 54, 80, 120; the Risks rows say 54 and 36. Fix: one list in all four places. | fixed: one width list, 24, 40, 54, 80 and 120, in N1, `done.json`, `plan.md` step 11 and its Risks |
| X6 | MEDIUM | rules alignment | `plan.md` Approach "Hand-off", step 14 | The hand-off fallback is "a plugin skill", but no skill path is in Files that change or Where things go, and the Done line forbids edits outside Files that change. NAME-1 says no skill is planned. Fix: name the folder and the NAME-1 check, or make a failed probe a stop-and-report. | fixed: the hand-off fallback is gone with tidy; the skill is named in `plan.md` Files that change and "The skill's name" |
| X7 | MEDIUM | underspecification | `facts.md` F58, F60, F61 | The supervisor is a model. A `*.test.ts` can only prove the prompt text, not that the model asks one question per batch or shows the final list. Fix: say in the facts that the test proves the prompt and the tools, and add a manual check (one real tidy pass, owner-run) to Verification. | fixed: `facts.md` Verification says the tests prove the script and the text of `SKILL.md`, with one owner-run pass; Risk row in `plan.md` |
| X8 | MEDIUM | underspecification | `facts.md` F35 condition 5 | "No live session uses it" does not say how: a live row whose `cwd` equals the worktree, or lies inside it. A session started in a subfolder would pass. Fix: define it as `cwd` equal to or under the worktree path, and test both. | fixed: F35 condition 5 compares `cwd` equal to or under the worktree; `worktree.test.ts` covers a subfolder |
| X9 | MEDIUM | inconsistency | `plugins/agent-tracker/tests/safety.test.ts` `@F62` "no write call reaches a session", `@F65` "no ... spawned process"; plan Rules check | Milestone 1's tests assert the mod writes nothing to a session and spawns nothing. This change adds `prompt.submit`, tools and `claude rm`. The plan says the allow-list "grows" but not that those two tests are amended, nor which locked milestone 1 facts they supersede. Fix: add a line to the plan listing the amended tests and the ACT-1 reason. | fixed: `plan.md` Shared facts says `safety.test.ts` is not edited and `cleanup-safety.test.ts` holds the allow-list |
| X10 | MEDIUM | coverage | `facts.md` tags `@F60` to `@F65`; `safety.test.ts` already uses `@F60` to `@F65` and `@F130` | New tags repeat milestone 1's `@F<n>` tags in the same file. The title also carries the change tag, but a check on `@F64` alone matches two tests. Fix: confirm `verify_gate.py` matches the change tag as well; if not, prefix new tags. | fixed: the new safety tests live in `cleanup-safety.test.ts`, so no `@F<n>` repeats within one file (`facts.md` intro) |
| X11 | MEDIUM | underspecification | `plan.md` Files that change, step 17, F29 | Step 17 writes screenshots to `changes/.../verify/shots/`, which is not in Files that change. F29's "close the tasks" reuses the existing `markTask` in `store.ts`, but the table lists only `unmarkTask`. Fix: add both lines. | fixed: `plan.md` Files that change adds `verify/shots/` and notes that Clear uses the existing `markTask` |
| X12 | LOW | duplication | `facts.md` Assumptions (two sections, lines 203 and 225) | Two `## Assumptions` headings. "Tidy models (F57)" and "Tidy model", and the two "Reopen"/"Copy resume" notes, say the same thing. Fix: merge into one section. | fixed: `facts.md` has one Assumptions section, merged |
| X13 | LOW | duplication | `facts.md` F62, F35 condition 5, F49 | F62's "never ask about a worktree with a live session" restates F35 condition 5. Fix: keep one. | fixed: F62 no longer restates F35 condition 5 |
| X14 | LOW | rules alignment | `tests/test_agent_tracker_layout.py` `test_the_mod_never_writes...` | The plan scopes only the `prompt.submit` ban. The test's comment still says "The mod only observes" and bans `$.tool.call`; the plan's "tool.call hook" for the tidy tools must not use that literal. Fix: update the comment and note the allowed form in step 16. | fixed: `plan.md` Files that change updates the layout test comment and bans `$.tool.register`; no `tool.call` hook is used |

Reworked 2026-11-14 after the owner's decisions (tidy became the skill `git-cleanup-run`): all 14 findings are `fixed`, none open.
