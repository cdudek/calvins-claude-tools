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

> Make the tracker count a session with no process as ended, show its real last activity, and let the owner clear dead sessions and merged worktrees by hand or in one tidy pass.

A person with no context builds from this file alone. [intent](intent.md) and
[facts](facts.md) are for the gate, not for the build. The UX spec is in [spec/](spec/).

## Approach

- **What changes:** the state rule reads `pid`. The Session page gains Clear, a worktree offer and honest ages. Home gains a Tidy line. `/tracker tidy` hands a supervisor prompt to the session.
- **What stays the same:** the band gets no control (F70). The collector, the lease, the asks and the model calls stay as they are. The mod makes no new model call.
- **Why this way:** every safety check is pure code in `core/`, fed by facts that thin I/O files gather. The Session page and the tidy tools call the same checked functions, so there is one set of checks.
- **Pure core:** `core/` takes time as a parameter and imports nothing with I/O. New files `activity.ts`, `clear.ts`, `worktree.ts` and `tidy.ts` follow that rule. The layout test enforces it.
- **No new model call:** the tidy supervisor is the owner's own session on its own model. Its gathering subagents are told `model: "haiku"` and are read only. MODEL-1 binds only the mod's own `$.model` calls, and the plan adds none.
- **How the supervisor acts (F59):** the mod registers two tools with `$.tool.register`, `tidy_clear_session` and `tidy_remove_worktree`, served by a `tool.call` hook. Each accepts only an item in the fixed list the mod stored at hand-off. Each re-runs the same checks as the Session page, and refuses when no pass is armed.
- **Arming a batch:** the mod reads the result of the host's question tool for each batch. A batch is armed only by the answer "Clear all N" or "Remove all N". Step 15 checks that the result carries the chosen label. If it does not, the fixed list and the per-item re-check stay as the guard, and a Risk row records it.
- **Hand-off (F53):** `$.prompt.submit({ text })` starts a turn once the session is idle. Step 14 checks it on a fixture first. The fallback is a plugin skill that holds the same prompt text, recorded in `questions.md`.
- **`claude rm` and git:** both run through `$.process.run` with an argument list and no shell, from `clear.ts` and `worktrees.ts` only. `git worktree remove <path>` runs without `--force` from the main checkout, never from the worktree.
- **Decision4:** the milestone PR is Repair. The mod now writes Claude Code's session list and git state, and the new ADR is the decision record.
- **Rejected, a Clear button or hotkey on the band:** the owner kept the band passive (F70). The path is band, pane, task row, Clear.
- **Rejected, a stored "cleared" flag:** a derived "has work left" test needs no new field and never goes stale (spec `ia.md`).
- **Rejected, the supervisor runs `claude rm` or git itself:** a model would then decide safety. The mod's tools decide, and the supervisor only asks and reports.
- **Rejected, a standing supervisor or a day-count argument:** out of scope in `facts.md`. Tidy always uses 30 days.
- **Rejected, one big feature:** the state fix is small and valuable alone, so it ships first. Clear, worktrees and tidy build on one another in order.
- **Calls:** `arch-plan-write` is this plan. `review-security-run` is not needed: no auth, money or consent, and every write follows an owner press. `review-dependency-run` is not needed: no dependency is added. `tracking-apply` is not needed: the success measure is a by-hand spot check.
- **Prototype images:** none. The UX plan marked the UI not risky, and a terminal mod cannot be mocked as an image.

## Rules check

The rules in `intent.md` → "Rules that apply", checked twice: before the design (can the approach
obey them?) and again after it (does the design?). `facts.md` names them PUB-1, PUB-2, NAME-1,
MODEL-1, DATA-1, WT-1 and ACT-1.

- Before design: pass. Every write is the owner's press, git never forces, the data sources stay the allowed list, and no model call is added.
- After design: pass, with three steps that make it true. `safety.test.ts` grows an allow-list for the new writes, and fails on `--force`, `-f`, `branch -D` and `claude stop`. `tests/test_agent_tracker_layout.py` scopes its `prompt.submit` ban to `tidy.ts` only. The layout test keeps `core/` pure.
- NAME-1: no skill or agent is added. The two tidy tools are mod tools, named `mcp__agent-tracker__<name>`, outside the taxonomy.
- ACT-1: the owner's 2026-11-13 observe-only words are amended by the intent. The new ADR records it and `docs/ux/setup.md` is edited to match.

### Justified violations

One row per rule the plan breaks. A row with an empty cell blocks the gate; `none` when clean.

| Violation | Why needed | Simpler alternative rejected because |
|---|---|---|
| none | | |

## Design changes

`docs/designs/agent-tracker.md` is edited in feature 5, in place, as sections that state what is true now. No dated log and no "Since" paragraph.

- **Decisions, live sessions:** a row with no `pid` is ended, whatever its state. The line "a failed or old read shows the stale state, never ended" stays true: a failed read marks nothing ended.
- **Decisions, new bullet:** the tracker acts only on the owner's press or answer. It never stops a session, never forces, never deletes a branch. It points to the new ADR.
- **Decisions, model calls:** the sentence says "every model call the mod makes uses `haiku`". The tidy supervisor is the session's own model.
- **Code layout:** names `core/activity.ts`, `clear.ts`, `worktree.ts`, `tidy.ts` and the I/O files `clear.ts`, `worktrees.ts`, `tidy.ts`, `lastline.ts`.
- **Work:** one new item for the Session page's Clear and offer, and one for `/tracker tidy`.
- **New ADR:** `docs/designs/2026-11-14-adr-tracker-acts-on-owner-press.md`. The choice is worth its reasons in a year, and it reverses the owner's words of 2026-11-13. It carries the Repair decision record. It chose acting on a press over staying observe-only. The owner asked for it. It commits us to the confirm and the five checks.
- **Then:** `python3 scripts/design_index.py write`.

## Where things go

The folder for every new file, so the build cannot invent a place. A file outside these folders
is `scope-growth`.

| New file or kind | Folder |
|---|---|
| Pure logic `activity.ts`, `clear.ts`, `worktree.ts`, `tidy.ts` | `plugins/agent-tracker/hooks/tracker/core/` |
| I/O files `clear.ts`, `worktrees.ts`, `tidy.ts`, `lastline.ts` | `plugins/agent-tracker/hooks/tracker/` |
| New mod tests `clear.test.ts`, `worktree.test.ts`, `tidy.test.ts` | `plugins/agent-tracker/tests/` |
| Fixtures: git output for linked worktrees and ignored files, agent rows with and without `pid` | `plugins/agent-tracker/tests/fixtures/` |
| The new ADR | `docs/designs/` |
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
| 0 | Sync: `git fetch origin && git merge origin/main`, locally; again before the close | none | `milestone/agent-tracker-4` | todo |
| 1 | State and age: a row with no `pid` is ended, the last-activity age line, this session never ended | F1-F7, F71, F72 | `agent-tracker-4/1-state-age` | todo |
| 2 | Clear with confirm, Reopen tasks, task closing and its store write | F8-F20, F22-F34, F70 | `agent-tracker-4/2-clear` | todo |
| 3 | Worktree offer: five checks, ignored-file list, never force, branch kept | F21, F35-F47, F73 | `agent-tracker-4/3-worktree` | todo |
| 4 | Tidy: Home line, `/tracker tidy`, prompt hand-off, supervisor tools, safety guards | F48-F69, N1 | `agent-tracker-4/4-tidy` | todo |
| 5 | Docs and release: design edits, ADR, setup.md, version bump | none, records only | `agent-tracker-4/5-docs-release` | todo |

Counts: 9, 27, 15 and 23 facts, 74 in all. F1 to F73 and N1 are each in exactly one row. Row 5 carries no fact: its proof is the docs checks and the final gate.

Shared facts: F8 (work left includes a removable worktree) and F19 (the worktree line of the confirm) are built in row 2. They use a seam `ctx.worktree` that is `null` until row 3. Row 3 completes the worktree half and extends `clear.test.ts`. F46 (`claude rm` removed the worktree) needs both and is owned by row 3. F21 and F73 need the offer, so row 3 owns them. F70 is a band test, but the Clear button is where a band control would tempt, so row 2 owns it. The safety facts F64 to F69 are owned by row 4. Rows 1 to 3 add their own calls to the `safety.test.ts` scenarios as they land. Row 4 adds only the tidy tools and the arming.

## Files that change

| File | Change |
|------|--------|
| `plugins/agent-tracker/hooks/tracker/types.d.ts` | `AgentRow.pid` (optional number) |
| `plugins/agent-tracker/hooks/tracker/core/states.ts` | `parseAgents` reads `pid`; `resolveState` marks a pid-less row ended when some row has one, never this session (F1, F4, F72) |
| `plugins/agent-tracker/hooks/tracker/core/merge.ts` | compute "some row has a pid" once per read; take a last-line time map for F71 |
| `plugins/agent-tracker/hooks/tracker/core/activity.ts` | new: `lastActivity` (newest of prompt, turn end, transcript line), start-date words (F6, F71) |
| `plugins/agent-tracker/hooks/tracker/core/pane-model.ts` | `Local.date`; seven new `ActionItem.action` values; the Home TIDY block; `actions` wrap |
| `plugins/agent-tracker/hooks/tracker/core/session-model.ts` | the facts line, the ended header, Clear, the confirm, the offer, the result lines, the focus rule |
| `plugins/agent-tracker/hooks/tracker/core/clear.ts` | new: what Clear does, the confirm parts, the refusals, the closing of tasks |
| `plugins/agent-tracker/hooks/tracker/core/worktree.ts` | new: the five conditions, the first failed one, the ignored-file list, the one label helper |
| `plugins/agent-tracker/hooks/tracker/core/tidy.ts` | new: collection by idle time, the passing items, the counts, the batches, the supervisor prompt, the report words |
| `plugins/agent-tracker/hooks/tracker/core/repo-model.ts` | use the shared worktree label helper |
| `plugins/agent-tracker/hooks/tracker/core/words.ts` | every new string; the help line and the command hint name `tidy` (F63) |
| `plugins/agent-tracker/hooks/tracker/core/index.ts` | re-export the four new core files |
| `plugins/agent-tracker/hooks/tracker/clear.ts` | new: re-read the list, `claude rm`, close tasks, reopen (F22-F31) |
| `plugins/agent-tracker/hooks/tracker/worktrees.ts` | new: gather git and `gh` facts, re-check, `git worktree remove` without force (F35-F47) |
| `plugins/agent-tracker/hooks/tracker/tidy.ts` | new: `/tracker tidy`, the hand-off, the two tools, the arming, the pane's tidy state |
| `plugins/agent-tracker/hooks/tracker/lastline.ts` | new: the time of a transcript's last line, read with `tail` (F71) |
| `plugins/agent-tracker/hooks/tracker/collector.ts` | pass the pid fact and the last-line map into the merge |
| `plugins/agent-tracker/hooks/tracker/store.ts` | `unmarkTask` for Reopen tasks (F31) |
| `plugins/agent-tracker/hooks/tracker/pane.tsx` | handle the seven actions, page-local Clear state, `local.date`, ring rules, `/tracker tidy` word |
| `plugins/agent-tracker/hooks/tracker/pane/view.tsx` | `flexWrap="wrap"` on the actions row |
| `plugins/agent-tracker/hooks/tracker/register.tsx` | register the tidy module |
| `plugins/agent-tracker/tests/*.test.ts` | extend `collector`, `band`, `pane`, `tasks`, `safety`; new `clear`, `worktree`, `tidy` |
| `plugins/agent-tracker/tests/fixtures/*.ts` | agent rows with and without `pid` (a live background row among them); git fixtures |
| `tests/test_agent_tracker_layout.py` | scope the `prompt.submit` ban to everything but `tidy.ts`; keep the rest |
| `plugins/agent-tracker/README.md` | "It only observes" becomes "acts only on your press"; the new writes; the tidy command |
| `plugins/agent-tracker/.claude-plugin/plugin.json` | version `0.2.1` to `0.3.0` (no changelog file exists) |
| `docs/designs/agent-tracker.md` | the Design changes above |
| `docs/designs/2026-11-14-adr-tracker-acts-on-owner-press.md` | new ADR |
| `docs/designs/INDEX.md` | regenerated by `design_index.py write` |
| `docs/ux/setup.md` | replace the "Observe only" hard rule and the Safety lines with the owner's decision; "every model call the mod makes pins `haiku`" |
| `docs/ux/interaction-guidelines.md` | one section for acts that write outside the tracker: confirm, result lines, focus |
| `docs/ux/glossary-proposal.md` | the terms Clear, Remove, Tidy, idle, ended, last activity, started |
| `changes/2026-11-14-tracker-session-cleanup/{milestone,questions,findings,validation}.md` | records |

## Order of work

Each step has a proof. The proof is a command, a file, or a fact. After each step the builder
runs `claude plugin validate --strict plugins/agent-tracker`, `claude plugin test plugins/agent-tracker`
and `python3 -m unittest discover -s tests`, then commits with a Conventional Commit subject.

- [ ] 0. Sync the milestone branch with `origin/main`. Proof: `git merge-base --is-ancestor origin/main HEAD` exits 0.
- [ ] 1. Feature 1, fixtures: a scrubbed `claude agents --json` with a live background row that carries `pid`, and one exited background row with none. This is the gate for R2-01. Proof: `git grep -nE '/Users/|/home/' plugins/agent-tracker/tests/fixtures` prints nothing.
- [ ] 2. Feature 1, tests first, then `AgentRow.pid`, `parseAgents`, `resolveState` and the pid-known flag in `merge.ts`. Proof: F1, F2, F4 and F72 pass in `collector.test.ts`; F3 passes in `band.test.ts`.
- [ ] 3. Feature 1, `core/activity.ts`, `lastline.ts`, `Local.date` and the Session header and facts line. Proof: F5, F6, F7 and F71 pass in `pane.test.ts` and `collector.test.ts`.
- [ ] 4. Feature 2, tests first, then `core/clear.ts` and the Session page states: Ended, Live, Nothing to clear, Pid not reported, List unreadable, Confirming. Proof: F8 to F20 pass in `clear.test.ts` and `pane.test.ts`.
- [ ] 5. Feature 2, `clear.ts` and the Clearing, Refused, Cleared, Failed and PartlyCleared states, `store.ts` `unmarkTask` and Reopen tasks. Proof: F22 to F34 pass in `clear.test.ts`, `tasks.test.ts` and `pane.test.ts`.
- [ ] 6. Feature 2, probe `claude rm` on a real dead background session if one exists, with closed stdin, and log the result in `questions.md`. Proof: the line is in `questions.md`; with no dead session it says so and F28 covers a hang by timeout.
- [ ] 7. Feature 2, the band guard. Proof: F70 passes in `band.test.ts`.
- [ ] 8. Feature 3, git fixtures, tests first, then `core/worktree.ts` and `worktrees.ts` gathering. Proof: F35 to F38 and F41 pass in `worktree.test.ts`.
- [ ] 9. Feature 3, the offer, Remove, Keep, the result states and the focus rule. Proof: F39, F40, F42 to F45, F47 and F73 pass.
- [ ] 10. Feature 3, the post-`claude rm` re-check and the offer-only Clear. Proof: F21 passes in `clear.test.ts` and F46 passes in `clear.test.ts` against the git fixtures.
- [ ] 11. Feature 4, tests first, then `core/tidy.ts`: collection, passing items, counts, batches, report words. Proof: F48, F49 and F57 to F62 pass in `tidy.test.ts`.
- [ ] 12. Feature 4, the Home TIDY block and the waiting lines. Proof: F50, F51 and F52 pass in `pane.test.ts`.
- [ ] 13. Feature 4, `/tracker tidy` and its answers, the help line and the hint. Proof: F54, F55, F56 and F63 pass.
- [ ] 14. Feature 4, probe `$.prompt.submit` on a fixture, then the hand-off. Proof: F53 passes in `tidy.test.ts`; a failed probe is logged and the plugin-skill fallback is built instead.
- [ ] 15. Feature 4, the two tools, the fixed list, the arming from the question result, and the re-check per item. Proof: F59 passes in `tidy.test.ts`; the probe result of the question tool is in `questions.md`.
- [ ] 16. Feature 4, `safety.test.ts` allow-list and the layout test change. Proof: F64 to F69 pass, and `python3 -m unittest discover -s tests` exits 0.
- [ ] 17. Feature 4, the render check at 120, 80 and 40 columns and a 24-column dock, rows counted. Proof: N1 holds, with a terminal screenshot kept under `changes/2026-11-14-tracker-session-cleanup/verify/shots/`.
- [ ] 18. Feature 5, design edits, the ADR, `setup.md`, the guidelines, the glossary, the README and the version. Proof: `python3 scripts/design_index.py write` leaves `git diff --stat docs/designs/INDEX.md` showing only the new ADR line.
- [ ] 19. Sync again, then hand the close to one `Mode: close` builder. Proof: `python3 scripts/verify_gate.py milestone 2026-11-14-tracker-session-cleanup` ends `VERIFY PASS milestone`.

## Milestones

One row per milestone, in order; a change small enough for one has one. Each milestone is cut
from the default branch and merges on its own, unless `needs` names one whose code it calls.
Different files do not prove independence: an API and its caller conflict without a merge
conflict.

| Milestone | Features | needs |
|-----------|----------|-------|
| M1 agent-tracker-4: live sessions only, Clear and Tidy | rows 0 to 5, F1 to F73 and N1 | none |

## Risks

Findings from `spec/validation.md` and its review files are cited by id: R1 (heuristics), R2 (Laws of UX), R3 (screens) and M1 to M5 (round 3). Findings the facts already close are in the last group.

| Risk | What we do | Where it lands |
|------|------------|----------------|
| Clear on a session whose process appears between the read and the press. | F22 and F23 re-read `claude agents --json` at the press and change nothing when a `pid` shows. The re-read and `claude rm` still leave a gap of milliseconds. Accepted: `claude rm` of a live job is Claude Code's own call. | Step 5, F22, F23, F65 |
| `claude rm` may need a TTY or ask a question (unverified). `$.process.run` gives it no stdin. | A 15-second timeout turns a hang into F28's error line. Step 6 probes a real dead session with closed stdin. Recommendation: the owner presses Clear once at the render check and the result goes to `questions.md`. | Step 6, F28 |
| A tidy turn is submitted while the session is busy. | The Home line and `/tracker tidy` both check "Claude is replying" and a readable list first (F52, F55). `$.prompt.submit` also queues until the session is idle. | Steps 12, 13, F52, F55 |
| The supervisor's tools run without the owner's answer (a model skips the question). | The tools take only items from the stored list, refuse unless the batch is armed, and re-check each item. Arming reads the host question result. If the result has no chosen label, the list and the re-check are the guard, and the prompt says so. Recommendation: accept, since a model never decides safety and a wrong tool call still faces five checks. | Step 15, F57, F59, F66 |
| `$.prompt.submit` or `$.tool.register` behave differently from the types (unverified). | Steps 14 and 15 probe both on fixtures before building on them. The fallback for the hand-off is a plugin skill. | Steps 14, 15 |
| A live background row with no `pid` reads ended (R2-01, M1). `claude rm` would then run on live work. | Step 1's fixture is a gate: no Clear for a background row until it passes. F72 keeps this session safe. F4 keeps the old rule when no row has a `pid`. Residual: one live background row with no `pid` among others that have one. The re-read at the press (F22, F23) is the second guard. | Steps 1, 2, F4, F22 |
| `claude rm` may remove a worktree the session made, with no offer (R1-02, R3-13). | The confirm names it before and the result names it after (F19, F46). The owner chose "Allow, name it". | Step 10, F19, F46 |
| Ignored files such as `.env` are deleted with a worktree (R1-03). | The offer lists up to 3 names and "and N more", and the list is re-read at the press (F41, F42, F44). The owner chose "List them in the offer". | Step 9, F41 |
| Tidy's "never removed" rule against `claude rm` on a session batch (M5). | The session question says Claude Code may remove a worktree it made, when safe. The rule is worded for worktrees: a failed worktree check is never removed. | Step 11, F62 |
| Reopened state offers only Copy resume command although open tasks exist again (M4). | After Reopen the page re-reads and draws Clear again, since work is left. The exit goes to Ended, not Done. | Step 5, F31 |
| After a Clear with no resume button, focus would fall on Reopen tasks (M2). | F73 fixes the order: Keep worktree, Copy resume command, the Home crumb. A test says never Reopen tasks. | Step 9, F73 |
| "Refused, unreadable" and "Pid not reported" strings differ between spec files (M3). | The strings of `spec/screens.md` Words are the constants in `core/words.ts`. F11, F12 and F24 name them. | Steps 4, 5 |
| Stale spec text: conformance C9, ring "Pass" row, Reopen label, "only when something is idle" (L1, N8). | The facts govern. Spec files are not edited in this change. | Accepted |
| Plain Buttons look like text lines (R2-05, R1 carried). | Spacing and a glyph-free label as built. Check at the render check; record the result. | Step 17, N1 |
| Nothing before the press says what Clear or Tidy do (R2-06, R1-18). | The confirm and the tidy answer say it (F17, F19, F53). No extra line on the page. | Accepted, F17, F19 |
| A Clear that appears through a re-read sits under the pointer (R2-09). | The ring never starts on Clear (F13) and Clear always confirms (F17), with focus on Cancel (F18). | Steps 4, F13, F17, F18 |
| The page can run longer than the visible rows when docked (R2-10, R3-17). | `↑↓` move the ring and nothing scrolls. The render check counts rows at each width and moves the offer above the results if needed. | Step 17, N1 |
| A pass running in another session leaves a live Tidy button here (R2-15). | The per-item re-checks stop a double act. A double question is accepted. | Accepted, F59 |
| "Skip these N" and "Keep worktree" are not remembered, so Tidy asks again (R2-14). | The count holds only items that pass every check, so it shrinks as the owner clears. No stored mark. | Accepted, F49 |
| Typed exceptions under Other are matched by text (R1-20, R2-12). | An unmatched or ambiguous one pauses the batch, and the final list is shown before acting (F60). | Step 11, F60 |
| The report merges "skipped", "needs a look" and failures (R1-13, R2-11). | F61 and F62 fix three separate lines and count only successes. | Step 11, F61, F62 |
| Error reasons are cut at 60 cells (R2-17). | Accepted. The line ends with an action: "Check it in a terminal." | Accepted, F28, F44, F45 |
| Error lines run 88 to 117 cells before the reason (R2-18, C8). | They wrap in a `wrap` block, so nothing clips. The render check tests 54 and 36 columns. | Step 17, N1 |
| The live line repeats the header state, and "running" has two meanings (R2-19, R3-11). | Wording is fixed by F9. Accepted. | Accepted, F9 |
| After Clear, Back lands on a row that is gone (R2-20, R3-14). | The page keeps focus per F73. Home restores the ring to the first row when its key is gone. | Step 9, F73 |
| "Question 1 of 2" is not shown when two tidy batches ask in a row (R2-21). | Accepted. Each question names its batch (F58). | Accepted, F58 |
| Dim and normal weight mean different things across lines (R2-22, C7). | Next-step lines are normal weight and facts are dim. The render check reads dim contrast on a light and a dark theme. | Step 17, N1 |
| A session whose only leftover is a worktree shows Clear (R2-23, R1-08). | The worktree line adds "Clear offers to remove it." (F36) and F21 opens the offer with no confirm. | Step 9, F21, F36 |
| A needs-you row vanishes without a word (R2-24, R1-24). | The session shows in Ended with "ended just now" on its page. No extra trace. Accepted. | Accepted, F7 |
| Header and facts line show one age twice (R2-25). | Accepted: the header says "ended", the line says "last activity". | Accepted, F5, F7 |
| Tidy argument handling (R2-26). | F56 answers any argument with the 30-day line. | Step 13, F56 |
| "Worktree stays" names only the first failed condition (R2-27, R1-23). | Accepted: F37 names the first, with its next step. | Accepted, F37 |
| A cleared session and an ended one with leftovers look alike (R2-28). | Accepted: the page says "Nothing to clear" on a fresh visit (F33). | Accepted, F33 |
| Spec contradictions on "primary" and the offer's place (R2-29). | Closed by the facts: F39 draws the offer under the actions row. | Closed, F39 |
| Last activity is `started` for some rows (R3-15, R1-07). | F71 takes the newest of prompt, turn end and transcript line. A row with none reads "last activity unknown". | Step 3, F71 |
| The "started" time comes from three sources (R3-15). | Accepted: the page words say "started" only. The fixture covers each source. | Accepted, F5 |
| The owner's mockups of 2026-11-14 are not in the repo, so new controls were not compared (conformance, brief). | Show the owner the render screenshots at the gate. A departure goes to the owner as a question. | Gate, step 17 |
| A worktree with no session has no page, so only tidy can remove it (conformance). | Accepted. A control on the Repo page is a later change. | Accepted |
| A live session that waited 63 days stays in NEEDS YOU (R3-23). | Out of scope. Clear is withheld and tidy skips it, by design (F9, F65). | Accepted |
| The milestone PR is Repair, and unattended work above Undo goes to a person. | The owner decides auto-merge at the gate. Recommendation: do not arm it, as in milestone 1. | Gate |
| A fixture or string holds a path, name or e-mail address. | `safety.test.ts` fails on `/Users/`, `/home/` and `@` addresses, and `tests/test_plugin.py` greps known names (F68). | Step 16, F68 |
| `git` and `gh` read calls grow, so the safety allow-list must grow (`rev-list`, `merge-base`, `symbolic-ref`, `tail`). | Row 3 and row 4 extend `isRead` and add the two writes by exact argument list only. | Steps 8, 16, F64, F65 |
| The default branch is not `main`. | origin HEAD, then `main`, then `master`. With none, the PR alone decides, as with no `gh` (F38). | Step 8, F35, F38 |
| A squash-merged branch looks unmerged to git. | The PR route of condition 4 clears it. Without `gh` the page names the real reason. | Step 8, F37, F38 |
| `git worktree remove` fails on a locked worktree or a submodule. | It runs without `--force`, so git refuses, and F45 shows the reason. Nothing is lost. | Step 9, F45 |
| Resuming from a worktree made again from the branch is unverified. | The page text of F43 says what to do. Logged as deferred in `facts.md`. | Accepted, F43 |
| A feature row of 28 facts (row 2) under a 150-turn cap. | Steps split row 2 by page state and by module. Each step is a commit with a proof. At 150 turns the run reports what is missing and resumes from the branch. | Steps 4 to 7 |

## Out of scope

- The cleanup by hand of 72 worktrees and 6 sessions: done on 2026-11-14.
- A Clear button, cell or hotkey on the band, and any action on the web Board (F70).
- A standing supervisor, and a day-count argument for tidy (fixed at 30 days).
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
- `docs/designs/2026-11-14-adr-tracker-acts-on-owner-press.md` exists and `docs/designs/INDEX.md` lists it.
- `plugins/agent-tracker/.claude-plugin/plugin.json` holds version `0.3.0`.
- `docs/ux/setup.md` no longer says "Observe only".
- F1 to F73 pass by their named checks, and N1 holds by the render check.
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
  head: one push, one PR `milestone/<slug>-<n>` to its parent, auto-merge armed with a merge
  commit (`gh pr merge <n> --merge --auto`). Ask first when a Critical or High is deferred. A
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
print `python3 /Users/calvindudek/projects/calvins-claude-tools/plugins/cct/skills/sdlc-run/scripts/sdlc_status.py goal 2026-11-14-tracker-session-cleanup`.
```

The goal:

```
/goal `python3 /Users/calvindudek/projects/calvins-claude-tools/plugins/cct/skills/sdlc-run/scripts/sdlc_status.py goal 2026-11-14-tracker-session-cleanup` printed `GOAL 2026-11-14-tracker-session-cleanup DONE` or `GOAL 2026-11-14-tracker-session-cleanup BLOCKED` as its last run in this conversation, or stop after 150 turns.
```

## Revisions

Only after approval. One line per change: `YYYY-MM-DD — what changed, and why`.

Verification follows the [local-first contract](https://github.com/cdudek/calvins-claude-tools/blob/main/plugins/cct/skills/sdlc-run/references/local-first.md).
