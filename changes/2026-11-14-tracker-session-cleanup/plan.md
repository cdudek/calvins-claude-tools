---
linear: none
type: plan
change: 2026-11-14-tracker-session-cleanup
design: docs/designs/agent-tracker.md
author: Calvin Dudek
status: draft
reviewed_by: null
approved_at: null
created: 2026-11-14
---

# Plan: Tracker shows only live sessions and clears dead ones

> Make the tracker count a session with no process as ended, show its real last activity, let the owner clear dead sessions and merged worktrees from the tracker, and clean up many stale ones with the skill `git-cleanup-run`.

A person with no context builds from this file alone. [intent](intent.md) and
[facts](facts.md) are for the gate, not for the build. The UX spec is in [spec/](spec/).

## Approach

- **What changes:** the state rule reads `pid`. The Session page gains Clear, a worktree offer and honest ages. The agent-tracker plugin gains the user-invocable skill `git-cleanup-run` with a bundled script.
- **What stays the same:** the band gets no control (F70). Home, the help line and the command hint gain nothing (F76). The collector, the lease, the asks and the model calls stay as they are. The mod makes no new model call and registers no tool.
- **Why this way:** every safety check is pure code, in `core/` for the tracker and in `scripts/cleanup.py` for the skill. Both implement the five conditions of F35 and share one list of test cases, so a drift shows.
- **Pure core:** `core/` takes time as a parameter and imports nothing with I/O. New files `activity.ts`, `clear.ts` and `worktree.ts` follow that rule. The layout test enforces it.
- **The skill (owner, dialog, 2026-11-14):** "Code acts, Claude reports (Recommended)". The script's `list` prints candidates as JSON with every check's result. Haiku subagents, read only, summarise what each item was doing. The skill asks the owner one AskUserQuestion per batch. The script's `act` runs with the exact ids the owner chose and re-checks each one. No model runs `claude rm` or a worktree removal.
- **Nothing is armed:** the old design had mod tools and an arming step. They are gone. The act step takes only the ids of the owner's answer (F81), each re-checked (F59). No model call reaches a removal on its own (F66).
- **No real session is cleared by the build:** script tests use a fake `claude` and a fake `gh` on `PATH`. Git fixtures live in a temporary folder (F82). The one real `claude rm` is the owner's press of Clear at the render check.
- **`claude rm` and git:** the tracker runs both through `$.process.run` from `clear.ts` and `worktrees.ts` only. The script runs them through `subprocess` with an argument list and no shell. Neither passes a banned flag (F64). `git worktree remove <path>` runs without force from the main checkout, never from the worktree.
- **Decision4:** the milestone PR is Repair. The tracker and the script now write Claude Code's session list and git state, and the new ADR is the decision record. The owner merges it (owner, dialog, 2026-11-14, "You merge it (Recommended)"). Auto-merge is never armed.
- **Rejected, a Clear button or hotkey on the band:** the owner kept the band passive (F70). The path is band, pane, task row, Clear.
- **Rejected, a stored "cleared" flag:** a derived "has work left" test needs no new field and never goes stale (spec `ia.md`).
- **Rejected, a supervisor inside the tracker:** a Home Tidy line, `/tracker tidy`, `$.prompt.submit`, `$.tool.register` and arming. Owner, dialog, 2026-11-14: "I think you are right it shouldnt be part of the tracker, but there should be another skill in the same plugin".
- **Rejected, the skill's model runs `claude rm` or git:** a model would then decide safety. The script decides, and Claude only summarises and asks.
- **Rejected, a standing supervisor or a day-count argument:** out of scope in `facts.md`. The skill always uses 30 days.
- **Rejected, one big feature:** the state fix is small and valuable alone, so it builds first. Clear, worktrees and the skill build on one another in order.
- **Calls:** `arch-plan-write` is this plan. `review-security-run` is not needed: no auth, money or consent, and every write follows an owner press or answer. `review-dependency-run` is not needed: the script uses only the standard library. `tracking-apply` is not needed: the success measure is the owner's spot check.
- **Prototype images:** none. The UX plan marked the UI not risky, and a terminal mod cannot be mocked as an image.

## Rules check

The rules in `intent.md` → "Rules that apply", checked twice: before the design (can the approach
obey them?) and again after it (does the design?). `facts.md` names them PUB-1, PUB-2, NAME-1,
MODEL-1, DATA-1, WT-1 and ACT-1.

- Before design: pass. Every write is the owner's press or answer, git never forces, the data sources stay the allowed list, and no model call is added.
- After design: pass, with these steps that make it true. `cleanup-safety.test.ts` and `tests/test_git_cleanup_run.py` hold an allow-list for the writes and fail on the banned arguments of F64 and on `claude stop`. `tests/test_agent_tracker_layout.py` also bans `$.tool.register` (F76). The layout test keeps `core/` pure.
- ACT-1: the owner's 2026-11-13 observe-only words are amended by the intent. The new ADR records it and `docs/ux/setup.md` is edited to match.
- NAME-1: one skill is added, `git-cleanup-run`. The build must do what "The skill's name" below says. The two old tidy tools are gone.

### The skill's name (what the build must do)

Checked against `docs/adr/0001-skill-taxonomy.md` and `scripts/taxonomy.py` on 2026-11-14.

- **Name:** `git-cleanup-run` passes. `git` is a family, `run` is in `VERBS` and a process ends in `run`, no word repeats, and it is 15 characters. It needs no `NOUN_TAILS` entry and no `AGENT_NOUNS` entry.
- **Frontmatter:** `name: git-cleanup-run` equal to the folder, `user_invocable: true`, a description of at most 1024 characters, and no quoted trigger phrase that another skill uses.
- **What the tests scan:** `tests/test_taxonomy.py` and `tests/test_plugin.py` read only `plugins/cct` (`PLUGIN = plugins/cct`). Nothing scans `plugins/agent-tracker/skills`, so no existing test checks the new skill's name or frontmatter. F77's test in `tests/test_git_cleanup_run.py` does, by calling `taxonomy.check_names({"git-cleanup-run": "P"}, set())` and reading the frontmatter.
- **What still reaches the skill:** `test_plugin.test_no_private_or_internal_names` greps the whole repo, so `SKILL.md` and `cleanup.py` hold no internal name. `tests/test_no_claude_ai_publishing.py` scans the mod, so they use no publishing tool. `claude plugin validate --strict plugins/agent-tracker` reads the skill. If it needs a `skills` key in `plugin.json`, the build adds `"skills": "./skills"`.
- **Where the script's tests run:** `scripts/run-plugin-tests.sh` finds `test_*.py` only under `plugins/cct`. So the script's tests live in `tests/test_git_cleanup_run.py`, which `python3 -m unittest discover -s tests` finds.

### Justified violations

One row per rule the plan breaks. A row with an empty cell blocks the gate; `none` when clean.

| Violation | Why needed | Simpler alternative rejected because |
|---|---|---|
| none | | |

## Design changes

`docs/designs/agent-tracker.md` is edited in feature 5, in place, as sections that state what is true now. No dated log and no "Since" paragraph.

- **Decisions, live sessions:** a row with no `pid` is ended, whatever its state. The line "a failed or old read shows the stale state, never ended" stays true: a failed read marks nothing ended.
- **Decisions, new bullet:** the tracker acts only on the owner's press, and the skill only on the owner's answer. Neither stops a session, forces or deletes a branch. It points to the new ADR.
- **Decisions, model calls:** the sentence says "every model call the mod makes uses `haiku`". The skill's subagents are `haiku` and read only.
- **Code layout:** names `core/activity.ts`, `clear.ts`, `worktree.ts`, the I/O files `clear.ts`, `worktrees.ts`, `lastline.ts`, and the skill folder `skills/git-cleanup-run/`.
- **Work:** one new item for the Session page's Clear and offer, and one for the skill `git-cleanup-run`.
- **New ADR:** `docs/designs/2026-11-14-adr-tracker-acts-on-owner-press.md`. The choice is worth its reasons in a year, and it reverses the owner's words of 2026-11-13. It carries the Repair decision record. It chose acting on a press, and cleanup by a script the owner triggers, over staying observe-only. The owner asked for it. It commits us to the confirm, the five checks and keeping the tracker free of cleanup.
- **Then:** `python3 scripts/design_index.py write`.

## Where things go

The folder for every new file, so the build cannot invent a place. A file outside these folders
is `scope-growth`.

| New file or kind | Folder |
|---|---|
| Pure logic `activity.ts`, `clear.ts`, `worktree.ts` | `plugins/agent-tracker/hooks/tracker/core/` |
| I/O files `clear.ts`, `worktrees.ts`, `lastline.ts` | `plugins/agent-tracker/hooks/tracker/` |
| The skill `SKILL.md` | `plugins/agent-tracker/skills/git-cleanup-run/` |
| The skill's script `cleanup.py` | `plugins/agent-tracker/skills/git-cleanup-run/scripts/` |
| New mod tests `clear.test.ts`, `worktree.test.ts`, `cleanup-safety.test.ts` | `plugins/agent-tracker/tests/` |
| The script's tests `test_git_cleanup_run.py` | `tests/` |
| Fixtures: git output for linked worktrees and ignored files, agent rows with and without `pid` and with and without `id` | `plugins/agent-tracker/tests/fixtures/` |
| The new ADR | `docs/designs/` |
| Render screenshots of step 17 | `changes/2026-11-14-tracker-session-cleanup/verify/shots/` |
| Open questions and the defaults taken | `changes/2026-11-14-tracker-session-cleanup/questions.md` |

## Feature PRs

In order, grouped under `### Milestone <n> — <what a user can do after it>`. One go (the
default): each row is a commit on `milestone/<slug>-<n>` with touched tests and required pre-commit checks between rows; each
milestone gets the checks and validation once, and one PR that releases it. For E2E, run
the full suite once, ×3 only for changed and flaky specs. Use the committed
`e2e/flaky-specs.txt` list per `cct:test-e2e-policy`, `suite-speed-and-reliability.md`
section G (selection and line format). `delivery: "feature-prs"`: each row is one PR into
`milestone/<slug>` (a hotfix: into the default branch), the next starts when it auto-merges.

This repo has no browser E2E. The tests are `*.test.ts` files run by `claude plugin test`, and `e2e/` does not exist. Each fact is owned by one row. Where a fact spans two rows, the row where its named check first fully passes owns it, and the earlier row builds its half.

### Milestone 1 — the owner sees only live sessions and can clear dead ones and their merged worktrees

| # | Feature | Facts | Branch | State |
|---|---|---|---|---|
| 0 | Sync: `git fetch origin && git merge origin/main`, locally; again before the close | none | `milestone/agent-tracker-4-1` | todo |
| 1 | State and age: a row with no `pid` is ended, the last-activity age line, this session never ended | F1-F7, F71, F72 | `agent-tracker-4/1-state-age` | todo |
| 2 | Clear with confirm, Reopen tasks, task closing and its store write | F8-F20, F22-F34, F70 | `agent-tracker-4/2-clear` | todo |
| 3 | Worktree offer: five checks, ignored-file list, never force, branch kept | F21, F35-F47, F73, N1 | `agent-tracker-4/3-worktree` | todo |
| 4 | git-cleanup-run skill and script | F48, F49, F58-F62, F64-F69, F74-F82 | `agent-tracker-4/4-cleanup-skill` | todo |
| 5 | Docs and release: design edits, ADR, setup.md, version bump | none, records only | `agent-tracker-4/5-docs-release` | todo |

Counts: 9, 27, 16 and 22 facts, 74 in all. Every live id is in exactly one row. The nine retired ids (F50 to F57 and F63) are in none. Row 5 carries no fact: its proof is the docs checks and the final gate. The branch of row 0 is `milestone/agent-tracker-4-1`. `sdlc_status.py` `branches()` builds `milestone/<slug>-<i>` from `decisions.json` `milestone.slug` and the one row under `## Milestones`. The goal looks for that branch.

Shared facts: F8 (work left includes a removable worktree) and F19 (the worktree line of the confirm) are built in row 2. They use a seam `ctx.worktree` that is `null` until row 3. Row 3 completes the worktree half and extends `clear.test.ts`. F46 (`claude rm` removed the worktree) needs both and is owned by row 3. F21 and F73 need the offer, so row 3 owns them. N1 is the render check of the Session page with its offer, so row 3 owns it. F70 is a band test, but the Clear button is where a band control would tempt, so row 2 owns it. The safety facts F64 to F69 are owned by row 4. Rows 1 to 3 add their own calls to the `cleanup-safety.test.ts` scenarios as they land. Row 4 adds the script side and the skill. `safety.test.ts` is not edited: its scenarios press nothing, so its no-write assertions stay true. The new file holds the allow-list for the two write shapes after an owner press.

## Files that change

| File | Change |
|------|--------|
| `plugins/agent-tracker/hooks/tracker/types.d.ts` | `AgentRow.pid` (optional number); `AgentRow.id` optional if missing |
| `plugins/agent-tracker/hooks/tracker/core/states.ts` | `parseAgents` reads `pid`; `resolveState` marks a pid-less row ended when some row has one, never this session (F1, F4, F72) |
| `plugins/agent-tracker/hooks/tracker/core/merge.ts` | compute "some row has a pid" once per read; take a last-line time map for F71 |
| `plugins/agent-tracker/hooks/tracker/core/activity.ts` | new: `lastActivity` (newest of prompt, turn end, transcript line), start-date words (F6, F71) |
| `plugins/agent-tracker/hooks/tracker/core/pane-model.ts` | `Local.date`; six new `ActionItem.action` values; `actions` wrap. No TIDY block (F76) |
| `plugins/agent-tracker/hooks/tracker/core/session-model.ts` | the facts line, the ended header, Clear, the confirm, the offer, the result lines, the focus rule |
| `plugins/agent-tracker/hooks/tracker/core/clear.ts` | new: what Clear does, the confirm parts, the refusals, the closing of tasks |
| `plugins/agent-tracker/hooks/tracker/core/worktree.ts` | new: the five conditions, the first failed one, the ignored-file list, the one label helper |
| `plugins/agent-tracker/hooks/tracker/core/repo-model.ts` | use the shared worktree label helper |
| `plugins/agent-tracker/hooks/tracker/core/words.ts` | every new string of the Session page. The help line and the command hint stay as built |
| `plugins/agent-tracker/hooks/tracker/core/index.ts` | re-export the three new core files |
| `plugins/agent-tracker/hooks/tracker/clear.ts` | new: re-read the list, `claude rm`, close tasks, reopen (F22-F31) |
| `plugins/agent-tracker/hooks/tracker/worktrees.ts` | new: gather git and `gh` facts, re-check, `git worktree remove` without force (F35-F47) |
| `plugins/agent-tracker/hooks/tracker/lastline.ts` | new: the time of a transcript's last line, read with `tail` (F71) |
| `plugins/agent-tracker/hooks/tracker/collector.ts` | pass the pid fact and the last-line map into the merge |
| `plugins/agent-tracker/hooks/tracker/store.ts` | `unmarkTask` for Reopen tasks (F31); Clear closes tasks with the existing `markTask` (F29) |
| `plugins/agent-tracker/hooks/tracker/pane.tsx` | handle the six actions, page-local Clear state, `local.date`, ring rules |
| `plugins/agent-tracker/hooks/tracker/pane/view.tsx` | `flexWrap="wrap"` on the actions row |
| `plugins/agent-tracker/tests/*.test.ts` | extend `collector`, `band`, `pane`, `tasks`; new `clear`, `worktree`, `cleanup-safety` |
| `plugins/agent-tracker/tests/fixtures/*.ts` | agent rows with and without `pid` and with and without `id` (a live background row among them, an interactive pid-less row); git fixtures |
| `plugins/agent-tracker/skills/git-cleanup-run/SKILL.md` | new: the conversation of `spec/screens.md`, `user_invocable: true`, `allowed-tools` for the script only |
| `plugins/agent-tracker/skills/git-cleanup-run/scripts/cleanup.py` | new: `list` and `act`, Python 3 standard library, every check and every removal |
| `tests/test_git_cleanup_run.py` | new: F48, F49, F58 to F62, F64 to F69 (script side), F74 to F82 |
| `tests/test_agent_tracker_layout.py` | ban `$.tool.register` too (F76); update the comment "The mod only observes"; the Board's own `/tracker web` exception stays |
| `plugins/agent-tracker/README.md` | "It only observes" becomes "acts only on your press"; the two writes; the skill `git-cleanup-run` |
| `plugins/agent-tracker/.claude-plugin/plugin.json` | version `0.2.1` to `0.3.0`; the description names the two writes (`claude rm`, `git worktree remove`); a `skills` key only if validation needs it |
| `.claude-plugin/marketplace.json` | the agent-tracker description names the same two writes |
| `docs/designs/agent-tracker.md` | the Design changes above |
| `docs/designs/2026-11-14-adr-tracker-acts-on-owner-press.md` | new ADR |
| `docs/designs/INDEX.md` | regenerated by `design_index.py write` |
| `docs/ux/setup.md` | replace the "Observe only" hard rule and the Safety lines with the owner's decision; "every model call the mod makes pins `haiku`" |
| `docs/ux/interaction-guidelines.md` | one section for acts that write outside the tracker: confirm, result lines, focus |
| `docs/ux/glossary-proposal.md` | the terms Clear, Remove, Tidy (the skill), idle, ended, last activity, started |
| `changes/2026-11-14-tracker-session-cleanup/{milestone,questions,findings,validation}.md` | records |
| `changes/2026-11-14-tracker-session-cleanup/verify/shots/` | the render screenshots of step 17 |

## Order of work

Each step has a proof. The proof is a command, a file, or a fact. After each step the builder
runs `claude plugin validate --strict plugins/agent-tracker`, `claude plugin test plugins/agent-tracker`
and `python3 -m unittest discover -s tests`, then commits with a Conventional Commit subject.

- [ ] 0. Sync the milestone branch with `origin/main`. Proof: `git merge-base --is-ancestor origin/main HEAD` exits 0.
- [ ] 1. Feature 1, fixtures: a scrubbed `claude agents --json`. It holds a live background row with `pid`, an exited background row with none, and an interactive row with neither `pid` nor `id`. This gates R2-01 and the interactive half of F1. Proof: `git grep -nE '/Users/|/home/' plugins/agent-tracker/tests/fixtures` prints nothing.
- [ ] 2. Feature 1, tests first, then `AgentRow.pid`, `parseAgents`, `resolveState` and the pid-known flag in `merge.ts`. Proof: F1, F2, F4 and F72 pass in `collector.test.ts`; F3 passes in `band.test.ts`.
- [ ] 3. Feature 1, `core/activity.ts`, `lastline.ts`, `Local.date` and the Session header and facts line. Proof: F5, F6, F7 and F71 pass in `pane.test.ts` and `collector.test.ts`.
- [ ] 4. Feature 2, tests first, then `core/clear.ts` and the Session page states: Ended, Live, Nothing to clear, Pid not reported, List unreadable, Confirming. Proof: F8 to F20 pass in `clear.test.ts` and `pane.test.ts`.
- [ ] 5. Feature 2, `clear.ts` and the Clearing, Refused, Cleared, Failed and PartlyCleared states, `store.ts` `unmarkTask` and Reopen tasks. Proof: F22 to F34 pass in `clear.test.ts`, `tasks.test.ts` and `pane.test.ts`.
- [ ] 6. Feature 2, the `claude rm` boundary on a fake `claude` binary first on `PATH`: a hang, a refusal and a success, with closed stdin. The build never runs `claude rm` on a real session. Proof: F28 passes against the fake, and the defaults taken are in `questions.md`. The one real run is the owner's press at the render check.
- [ ] 7. Feature 2, the band guard. Proof: F70 passes in `band.test.ts`.
- [ ] 8. Feature 3, git fixtures, tests first, then `core/worktree.ts` and `worktrees.ts` gathering. Proof: F35 to F38 and F41 pass in `worktree.test.ts`.
- [ ] 9. Feature 3, the offer, Remove, Keep, the result states and the focus rule. Proof: F39, F40, F42 to F45, F47 and F73 pass.
- [ ] 10. Feature 3, the post-`claude rm` re-check and the offer-only Clear. Proof: F21 and F46 pass in `clear.test.ts` against the git fixtures.
- [ ] 11. Feature 3, the render check at 120, 80, 54 and 40 columns and a 24-column dock, rows counted. Proof: N1 holds, with a terminal screenshot kept under `changes/2026-11-14-tracker-session-cleanup/verify/shots/`.
- [ ] 12. Feature 4, tests first in `tests/test_git_cleanup_run.py`, then `cleanup.py` `list`: collection, checks, verdicts, the no-pid rule, no job id. Proof: F48, F49, F74, F75, F79 and F80 pass.
- [ ] 13. Feature 4, `cleanup.py` `act`: explicit ids, re-check per id, refusals, the result JSON. Proof: F59, F61, F62 and F81 pass.
- [ ] 14. Feature 4, `SKILL.md`: the conversation, the haiku subagents, `allowed-tools`, `user_invocable: true`. Proof: F58, F60, F77 and F78 pass, and `claude plugin validate --strict plugins/agent-tracker` exits 0.
- [ ] 15. Feature 4, the safety tests and the layout test change. Proof: F64 to F69, F76 and F82 pass, and `python3 -m unittest discover -s tests` exits 0.
- [ ] 16. Feature 4, one owner-run pass of `/git-cleanup-run` is left to the owner at the render check. The build only proves the script and the text. Proof: the note is in `questions.md`.
- [ ] 17. Feature 5, design edits, the ADR, `setup.md`, the guidelines, the glossary, the README, the plugin description and the version. Proof: `python3 scripts/design_index.py write` leaves `git diff --stat docs/designs/INDEX.md` showing only the new ADR line.
- [ ] 18. Sync again, then hand the close to one `Mode: close` builder. Proof: `python3 scripts/verify_gate.py milestone 2026-11-14-tracker-session-cleanup` ends `VERIFY PASS milestone`.

## Milestones

One row per milestone, in order; a change small enough for one has one. Each milestone is cut
from the default branch and merges on its own, unless `needs` names one whose code it calls.
Different files do not prove independence: an API and its caller conflict without a merge
conflict.

| Milestone | Features | needs |
|-----------|----------|-------|
| M1 agent-tracker-4: live sessions only, Clear and the cleanup skill | rows 0 to 5, 74 facts | none |

## Risks

Findings from `spec/validation.md` and its review files are cited by id: R1 (heuristics), R2 (Laws of UX), R3 (screens) and M1 to M5 (round 3). Findings the facts already close are in the last group.

| Risk | What we do | Where it lands |
|------|------------|----------------|
| Clear on a session whose process appears between the read and the press. | F22 and F23 re-read `claude agents --json` at the press and change nothing when a `pid` shows. The re-read and `claude rm` still leave a gap of milliseconds. Accepted: `claude rm` of a live job is Claude Code's own call. | Step 5, F22, F23, F65 |
| `claude rm` may need a TTY or ask a question (unverified). `$.process.run` gives it no stdin. | A 15-second timeout turns a hang into F28's error line. Step 6 proves the boundary on a fake `claude`. The build never runs `claude rm` on a real session. The owner presses Clear once at the render check and the result goes to `questions.md` (X3). | Step 6, F28 |
| The act step removes an id the owner did not choose (X2, H1). | `act` takes explicit ids only (F81), re-checks each (F59) and refuses an id not in a fresh `list`. `SKILL.md` allows only the script, so no model runs `claude rm` or git (F66, F77). Nothing is armed and no tool is registered (F76). | Steps 13, 14, F59, F66, F81 |
| No row in the read carries `pid`, so a live session looks dead (H2). | F4 and F11 withhold Clear. F75 marks every session `needs-look` and `act` removes none. | Steps 2, 12, F75 |
| A live background row with no `pid` reads ended (R2-01, M1). `claude rm` would then run on live work. | Step 1's fixture is a gate: no Clear for a background row until it passes. F72 keeps this session safe. F4 keeps the old rule when no row has a `pid`. Residual: one live background row with no `pid` among others that have one. The re-read at the press (F22, F23) is the second guard. | Steps 1, 2, F4, F22 |
| `claude rm` may remove a worktree the session made, with no offer (R1-02, R3-13). | The confirm names it before and the result names it after (F19, F46). The owner chose "Allow, name it". | Step 10, F19, F46 |
| Ignored files such as `.env` are deleted with a worktree (R1-03). | The offer lists up to 3 names and "and N more", and the list is re-read at the press (F41, F42, F44). The owner chose "List them in the offer". | Step 9, F41 |
| The skill's "never removed" rule against `claude rm` on a session batch (M5). | The session question says Claude Code may remove a worktree it made, when safe. The rule is worded for worktrees: a failed worktree check is never removed (F62). | Step 12, F62 |
| Reopened state offers only Copy resume command although open tasks exist again (M4). | After Reopen the page re-reads and draws Clear again, since work is left. The exit goes to Ended, not Done. | Step 5, F31 |
| After a Clear with no resume button, focus would fall on Reopen tasks (M2). | F73 fixes the order: Keep worktree, Copy resume command, the Home crumb. A test says never Reopen tasks. | Step 9, F73 |
| "Refused, unreadable" and "Pid not reported" strings differ between spec files (M3). | The strings of `spec/screens.md` Words are the constants in `core/words.ts`. F11, F12 and F24 name them. | Steps 4, 5 |
| Stale spec text: conformance C9, ring "Pass" row, Reopen label, "only when something is idle" (L1, N8). | The facts govern. Spec files are not edited in this change. | Accepted |
| Plain Buttons look like text lines (R2-05, R1 carried). | Spacing and a glyph-free label as built. Check at the render check; record the result. | Step 11, N1 |
| Nothing before the press says what Clear does (R2-06, R1-18). | The confirm says it (F17, F19). The skill's question says what a batch does. No extra line on the page. | Accepted, F17, F19 |
| A Clear that appears through a re-read sits under the pointer (R2-09). | The ring never starts on Clear (F13) and Clear always confirms (F17), with focus on Cancel (F18). | Steps 4, F13, F17, F18 |
| The page can run longer than the visible rows when docked (R2-10, R3-17). | `↑↓` move the ring and nothing scrolls. The render check counts rows at each width and moves the offer above the results if needed. | Step 11, N1 |
| "Skip these N" and "Keep worktree" are not remembered, so the skill asks again (R2-14). | The list holds only items that pass every check, so it shrinks as the owner clears. No stored mark. | Accepted, F49 |
| Typed exceptions under Other are matched by text (R1-20, R2-12). | An unmatched or ambiguous one asks again and runs nothing, and the final list is shown before `act` (F60). | Step 14, F60 |
| The report merges "skipped", "needs a look" and failures (R1-13, R2-11). | F61 and F62 fix three separate lines and count only successes. | Steps 13, 14, F61, F62 |
| Error reasons are cut at 60 cells (R2-17). | Accepted. The line ends with an action: "Check it in a terminal." | Accepted, F28, F44, F45 |
| Error lines run 88 to 117 cells before the reason (R2-18, C8). | They wrap in a `wrap` block, so nothing clips. The render check tests 54 and 40 columns. | Step 11, N1 |
| The live line repeats the header state, and "running" has two meanings (R2-19, R3-11). | Wording is fixed by F9. Accepted. | Accepted, F9 |
| After Clear, Back lands on a row that is gone (R2-20, R3-14). | The page keeps focus per F73. Home restores the ring to the first row when its key is gone. | Step 9, F73 |
| "Question 1 of 2" is not shown when two cleanup batches ask in a row (R2-21). | Accepted. Each question names its batch (F58). | Accepted, F58 |
| Dim and normal weight mean different things across lines (R2-22, C7). | Next-step lines are normal weight and facts are dim. The render check reads dim contrast on a light and a dark theme. | Step 11, N1 |
| A session whose only leftover is a worktree shows Clear (R2-23, R1-08). | The worktree line adds "Clear offers to remove it." (F36) and F21 opens the offer with no confirm. | Step 9, F21, F36 |
| A needs-you row vanishes without a word (R2-24, R1-24). | The session shows in Ended with "ended just now" on its page. No extra trace. Accepted. | Accepted, F7 |
| Header and facts line show one age twice (R2-25). | Accepted: the header says "ended", the line says "last activity". | Accepted, F5, F7 |
| The skill takes no day-count argument (R2-26). | The script's `list` has no `--days`. The 30 days are fixed. | Step 12, F48 |
| "Worktree stays" names only the first failed condition (R2-27, R1-23). | Accepted: F37 names the first, with its next step. | Accepted, F37 |
| A cleared session and an ended one with leftovers look alike (R2-28). | Accepted: the page says "Nothing to clear" on a fresh visit (F33). | Accepted, F33 |
| Spec contradictions on "primary" and the offer's place (R2-29). | Closed by the facts: F39 draws the offer under the actions row. | Closed, F39 |
| Last activity is `started` for some rows (R3-15, R1-07). | F71 takes the newest of prompt, turn end and transcript line. A row with none reads "last activity unknown". | Step 3, F71 |
| The "started" time comes from three sources (R3-15). | Accepted: the page words say "started" only. The fixture covers each source. | Accepted, F5 |
| The owner's mockups of 2026-11-14 are not in the repo, so new controls were not compared (conformance, brief). | Show the owner the render screenshots at the gate. A departure goes to the owner as a question. | Gate, step 11 |
| A worktree with no session has no page, so only the skill can remove it (conformance). | Accepted. A control on the Repo page is a later change. | Accepted |
| A live session that waited 63 days stays in NEEDS YOU (R3-23). | Out of scope. Clear is withheld and the skill skips it, by design (F9, F65). | Accepted |
| The milestone PR is Repair, and unattended work above Undo goes to a person. | The owner merges it (owner, dialog, 2026-11-14, "You merge it (Recommended)"). Auto-merge is never armed. | Gate |
| A fixture or string holds a path, name or e-mail address. | `cleanup-safety.test.ts` fails on `/Users/`, `/home/` and `@` addresses, and `tests/test_plugin.py` greps known names (F68). The plan's own text holds no local path (X4). | Step 15, F68 |
| `git` and `gh` read calls grow, so the safety allow-list must grow (`rev-list`, `merge-base`, `symbolic-ref`, `tail`). | Row 3 and row 4 extend the allow-list in `cleanup-safety.test.ts` and add the two writes by exact argument list only. | Steps 8, 15, F64, F65 |
| The default branch is not `main`. | origin HEAD, then `main`, then `master`. With none, the PR alone decides, as with no `gh` (F38). | Steps 8, 12, F35, F38 |
| A squash-merged branch looks unmerged to git. | The PR route of condition 4 clears it. Without `gh` the page names the real reason. | Steps 8, 12, F37, F38 |
| `git worktree remove` fails on a locked worktree or a submodule. | It runs without `--force`, so git refuses, and F45 shows the reason. Nothing is lost. | Step 9, F45 |
| Resuming from a worktree made again from the branch is unverified. | The page text of F43 says what to do. Logged as deferred in `facts.md`. | Accepted, F43 |
| A feature row of 28 facts (row 2) under a 150-turn cap. | Steps split row 2 by page state and by module. Each step is a commit with a proof. At 150 turns the run reports what is missing and resumes from the branch. | Steps 4 to 7 |
| Conditions 3 and 4 of F35 protect only tidiness, because the branch is always kept (M1). | Kept: both are cheap in the script and the page, and the owner chose the five checks. The `gh` call falls back to the branch alone (F38). | Accepted, F35, F38 |
| The surface is large for the first value (M5). | Row 1 builds and commits first and is complete alone. The owner chose all three features, so there is no split push. | Accepted, rows 1 to 4 |
| A public plugin that only observed can now run `claude rm` and `git worktree remove` (M6). | The README, the plugin description and the marketplace description name the two writes, and the version goes `0.2.1` to `0.3.0`. | Step 17, Files that change |
| A repository's labels persuade the skill's model (M4). | Labels go to the subagents as quoted data. Their text never reaches `act`, which takes ids only (F78, F81). | Step 14, F78 |
| The tracker's TypeScript and the script's Python drift on F35. | Both test files use the same case names for the five conditions, so a drift shows. | Steps 8, 12, F35 |
| `claude agents --json` rows may carry no last-activity time (F48). | The script reads the row's time and the transcript's modified time, and an unknown time is not collected. A fixture covers a row with neither. | Step 12, F48 |
| The plugin may need a `skills` key, or the skill may not load (unverified). | Step 14 runs `claude plugin validate --strict plugins/agent-tracker` and adds the key only if it asks. | Step 14, F77 |
| The skill's conversation is run by a model, so no test proves it asks one question per batch (X7). | The tests prove the script and the text of `SKILL.md`. The owner runs one pass at the render check. | Accepted, F58, F60 |
| Milestone 1's plan holds the same local paths in its goal block (X4). | Outside this change's folder, so not edited here. The template that fills the block is a separate fix. | Accepted |

## Out of scope

- The cleanup by hand of 72 worktrees and 6 sessions: done on 2026-11-14.
- A Clear button, cell or hotkey on the band, and any action on the web Board (F70).
- A standing supervisor, a tidy line, button or command in the tracker, and a day-count argument for the skill (fixed at 30 days).
- `claude stop`, and any stop or removal of a running session (F65).
- A page or a control for a worktree that no session used.
- Editing the spec files in `spec/`.

## Done

What must hold, as data in [done.json](done.json) (facts, test tags, pages, states). The goal
below ends on the status line of `sdlc_status.py goal` (from the sdlc-run plugin), which reads the verify gate and the PRs,
so every line here is proven by a check, not by a claim.

- `python3 scripts/verify_gate.py feature 2026-11-14-tracker-session-cleanup` ends `VERIFY PASS` for every feature.
- `python3 scripts/verify_gate.py milestone 2026-11-14-tracker-session-cleanup` ends `VERIFY PASS` once, on the milestone.
- `scripts/run-plugin-tests.sh` prints `ok   agent-tracker: validate` and `ok   agent-tracker: test`.
- `plugins/agent-tracker/skills/git-cleanup-run/SKILL.md` and `scripts/cleanup.py` exist, and `tests/test_git_cleanup_run.py` passes.
- `docs/designs/2026-11-14-adr-tracker-acts-on-owner-press.md` exists and `docs/designs/INDEX.md` lists it.
- `plugins/agent-tracker/.claude-plugin/plugin.json` holds version `0.3.0`.
- `docs/ux/setup.md` no longer says "Observe only".
- Every live fact in `done.json` passes by its named check, and N1 holds by the render check.
- Nothing outside `## Files that change` is edited.
- Stop and report as soon as a step cannot proceed. Never work around a blocker.
- Stop after 150 turns if not met. Report what is missing.

## How to run

The process of the build. The `/goal` below holds only the end state; everything the run does
lives here, in the skill's stages and in the hooks. Read the [local-first
contract](https://github.com/cdudek/calvins-claude-tools/blob/main/plugins/cct/skills/sdlc-run/references/local-first.md)
before any check or push: it owns local iteration, failures and the final full check.

- **Scope:** deliver this change in one go, per this plan and `facts.md`.
- **Milestones:** every row of `## Milestones`, in order. Each one is a local branch
  `milestone/<slug>-<n>`, cut from fresh `origin/<parent>`. `<parent>` is `project/<slug>` when
  the project has a branch, else `<default>`. A milestone with `needs:` is cut from that local
  milestone instead. Building never waits for a merge. Nothing is pushed before its gate passes.
- **Sync:** the first row of a milestone is a local `git fetch origin && git merge
  origin/<default>` (also `git merge origin/project/<slug>` when the project has a branch).
  Repeat it right before each close, and after any earlier milestone merges. It is never a PR.
  The milestone gate fails `check=parent-sync` without it. The merge may run in the supervisor's
  worktree.
- **Features:** write the tests for the feature's facts, build in the folders of `## Where things
  go`, commit. Between features run the touched tests, their directly affected suite and the
  required pre-commit checks, then start the next feature at once.
- **Builders:** feature builds and fix parts go to `cct:sdlc-feature-builder` agents. Each prompt
  carries a context pack: the feature's facts, its plan excerpt and the text of the rule IDs
  those facts cite, not whole files. Dispatch with isolation `worktree` and a `Base: <milestone
  head sha>` line after you commit your records. Merge their branches back one at a time. When
  `sdlc.json` `builders` is `codex`, use the kit's `scripts/codex-build.sh` instead; with codex
  the close builder runs checks and the gate only. Either way use `builderModel` and
  `builderEffort`, or the pair this plan's Approach names (`stages.md`).
- **Records:** plans, handover, findings, validation, gate output and every fix or test repair are
  commits on the milestone branch. Open no other PR and push nothing else (`pr-gate.sh` refuses
  it). A record that can only be written after a merge goes in the next milestone's first commit.
- **Questions:** an open question never stops the build. Write it to `questions.md` with the
  default you took, tell the engineer in one line, and carry on.
- **Close:** once a milestone's features are committed, hand its local pipeline to one
  `cct:sdlc-feature-builder` subagent with `Mode: close` and the head it runs on. It spawns no
  agents and nothing merges into the milestone while it runs. It runs the unit tests, the full
  E2E suite once (changed and flaky specs ×3, the committed `e2e/flaky-specs.txt` per
  `cct:test-e2e-policy`, `suite-speed-and-reliability.md` section G), the one fix round on the
  blocking findings, then `python3 scripts/verify_gate.py milestone 2026-11-14-tracker-session-cleanup`. Its full output
  is pasted.
- **Meanwhile:** dispatch the Stage 6 reviews on the milestone diff in parallel. Validate every
  fact and ask of the milestone against the built app into `validation.md` (expected, observed,
  evidence, verdict). Run the append-only converge pass from `quality-passes.md` into
  `findings.md` (ticked boxes are not evidence; repeat after the fix round until it adds nothing
  and writes `Converged: round <n>`). Write one `findings.md` section for the subagent's fix
  round. Keep building the next milestone where it does not depend on this one.
- **Publish:** only on `VERIFY PASS milestone 2026-11-14-tracker-session-cleanup <sha>` with `<sha>` equal to the local
  head: one push, one PR `milestone/<slug>-<n>` to its parent. The owner merges it (owner, dialog, 2026-11-14): never arm auto-merge. Ask first when a Critical or High is deferred. A
  milestone that needs another opens its PR after that one merges.
- **Red CI:** CI is the last check, not the test loop. Read the exact failed job or test and its
  reason, reproduce it locally, fix it, then run only the failing tests plus the directly affected
  suite until green, the full suite once, and one batched push. Never a pipeline retry or a
  speculative push.
- **Scope the owner adds:** it re-locks (`verify_gate.py approve 2026-11-14-tracker-session-cleanup`) and gets one more
  close. Log it under `## Revisions`.
- **Blocked:** on `VERIFY BLOCKED`, stop and summarize `verify/report.md` for the engineer. Never
  edit protected paths (`facts.md`, `done.json`, `lock.json`, baselines, allowlists, `sdlc.json`
  `checks`) or accept baselines.
- **Bookkeeping:** tick plan tasks as they land. Log departures under `## Revisions`.
- **Agents:** every build, fix, test, capture, restack or records agent is
  `cct:sdlc-feature-builder` (Sonnet). Review and checks use their typed agents
  (`cct:review-code-reviewer`, `cct:test-behavior-verifier`, `cct:review-criteria-auditor`,
  `cct:ux-usability-reviewer`, `cct:review-finding-validator`). Never launch general-purpose for
  this work: it inherits the session's model. Any other subagent gets `model: sonnet` explicitly.
  The session's own model is only for the gate's visual judgement and for decisions. Dispatch
  builders yourself, never through a closer agent that spawns its own.
- **One milestone** (`/goal` from `templates/goal/milestone.txt`): close it per `milestone.md`.
  Sync first, one fix round, diagnose locally with failing tests and affected suites until green,
  then the full suite once before the push: unit, E2E (changed and flaky specs ×3) and
  `python3 scripts/verify_gate.py milestone 2026-11-14-tracker-session-cleanup`, output pasted. Then one push and PR. Records and
  repairs are commits there, never separate PRs.
- **Feature PRs** (`delivery: "feature-prs"`): each feature is its own `/goal` from
  `templates/goal/feature.txt`: `cct:sdlc-feature-builder`, or `codex-build.sh` when `builders` is
  `codex`, with `builderModel` and `builderEffort`. Run the touched tests and affected suites until
  green, then the full suite before the push, `python3 scripts/verify_gate.py feature
  2026-11-14-tracker-session-cleanup`, output pasted. Use this worktree's E2E slot. After opening the PR run
  `cct:ux-assessment-run` unless `ux` is off, and fix Critical and High before arming auto-merge.
  Tick plan tasks and log departures under `## Revisions`. Stages 5 and 6 in `stages.md` have the
  steps.

## Goal handover

Two blocks, filled when the gate returns approved and committed verbatim, so the handover is not
one chat message. The kickoff prompt tells the run what to do. The `/goal` line holds only the end
state: the status command prints `GOAL <ID> DONE` or `GOAL <ID> BLOCKED`, and the run stops after
150 turns (`goal.runTurns`). Feature PRs: one `/goal` per feature from
`templates/goal/feature.txt`, not used here.

Kickoff prompt:

```
Run change 2026-11-14-tracker-session-cleanup: follow `## How to run` in changes/2026-11-14-tracker-session-cleanup/plan.md to the end, then
print `<STATUS>`.
```

The goal:

```
/goal `<STATUS>` printed `GOAL 2026-11-14-tracker-session-cleanup DONE` or `GOAL 2026-11-14-tracker-session-cleanup BLOCKED` as its last run in this conversation, or stop after 150 turns.
```

`<STATUS>` is the command `python3 plugins/cct/skills/sdlc-run/scripts/sdlc_status.py goal 2026-11-14-tracker-session-cleanup`, run from the repo root. The process fills it only in the `/goal` line it gives the owner, and never commits the filled line. The status script looks for a PR from `milestone/agent-tracker-4-1`.

## Revisions

Only after approval. One line per change: `YYYY-MM-DD — what changed, and why`.

Verification follows the [local-first contract](https://github.com/cdudek/calvins-claude-tools/blob/main/plugins/cct/skills/sdlc-run/references/local-first.md).
