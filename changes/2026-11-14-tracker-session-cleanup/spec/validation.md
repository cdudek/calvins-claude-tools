---
type: validation
change: 2026-11-14-tracker-session-cleanup
verdict: ready
status: approved
reviewed_by: Calvin Dudek
approved_at: 2026-11-14T23:06
created: 2026-11-14
---

> **Revised 2026-11-14 (owner decision).** Tidy left the tracker and became the skill `git-cleanup-run`. The Home Tidy line, the Tidy button and `/tracker tidy` are gone. This record describes the earlier design on those points. `ia.md`, `interaction.md`, `screens.md`, `sitemap.md` and `../facts.md` govern.

# Validation

Text-only spec loop, three rounds (the cap). Round 1: three independent reviewers, merged after all finished ([r1 heuristics](review/r1-heuristics.md), [r2 Laws of UX](review/r2-laws.md), [r3 screens](review/r3-screens.md)); the spec was fixed. Round 2 re-check: not ready, the new findings were fixed ([round 2](review/round2-recheck.md)). Round 3 re-check: ready, no new severity 3 or 4 ([round 3](review/round3-recheck.md)). No image was drawn.

## Verdict

ready

No severity 3 or 4 finding is open and no severity 3 or 4 contradiction between spec files remains. Items that are the owner's decision are under Decisions Needed with a recommended answer; the loop could not ask the owner, so none was answered. Four were answered afterwards, on 2026-11-14, and are under Decided; the spec changed to match (a Confirming state before every Clear), and the three reviewers have not seen that change. Medium and Low findings go to `plan.md` as Risk rows or are deferred (listed below).

## Definition Of Ready

| Check | Result | Evidence |
|---|---|---|
| Activities | pass | brief, ia, interaction, screens, conformance done; prototype not drawn: "prototype: skip, not marked risky; sdlc decides in the plan" |
| Asks | pass | every ask A1 to A6 maps to a job story, a screen and a state below; the fact column fills in Stage 3 |
| Findings | pass | round 1: 0 Critical; severity 3 findings (13 distinct, listed below) all fixed or listed for the owner; round 2 added one High (N1), fixed; round 3: no High or Critical |
| Laws of UX | pass | 30 rows and the B rows below, from reviewer 2 (round 1); fixes since are in Findings |
| Concerns | pass | conformance C1 to C15 fixed or listed; C1 and C5 are owner decisions; C2 was decided on 2026-11-14 |
| Questions | pass | every question has a recommended answer; none could be asked in this loop |
| Prototype | not yet: prototype follows only if the plan marks the UI risky | |

## Asks To Screens To Facts

| Ask | Job story | Screen | State | Fact or out of scope |
|---|---|---|---|---|
| A1 | J5 | Pane Home (Tidy line); transcript (tidy) | Tidy line, Started, Reported | facts follow (Stage 3) |
| A2 | J1 to J5 | the whole change | all | facts follow (Stage 3) |
| A3 | J3 | Pane Session; the Home task row leads to it. The band gets no control (N8) | Ended, Clearing, Cleared | facts follow (Stage 3) |
| A4 | J3, J4, J5, J6 | Pane Session (Clear, offer); transcript (tidy) | Cleared, Offer, Removing, Live | facts follow (Stage 3) |
| A5 | J1, J2 | Pane Home (needs you); Pane Session (state, age line); Band count | Ended; started and last activity | facts follow (Stage 3) |
| A6 | J1 to J5 | the three options: state fix, Clear, tidy | all | facts follow (Stage 3) |

## Prototype Screenshots

| Screen | State | 100 % | 150 % |
|---|---|---|---|
| none | | not drawn | not drawn |

## Laws Of UX Coverage

Reviewer 2's table, as returned in round 1, before the owner's decision of 2026-11-14 that Clear always asks a confirm: where a row says Clear has no confirm or no undo (L8.5, B5, B7, B11), the spec now confirms; see Decided. Several failed rows were fixed afterwards (R2-02 re-check at the press, R2-04 arrows, R2-13 every item listed, R2-16 matrix, R2-22 weights, R2-29 contradictions and others in the Findings table); the round 2 and 3 re-checks confirm them.

| # | Law | Verdict | Failed checks | Evidence |
|---|---|---|---|---|
| L1 | Aesthetic-Usability Effect | fail | L1.3, L1.6 | L1.1 pass (theme names only: `success`, `error`, dim). L1.5 pass (states exist for Failed, PartlyCleared, Nothing to clear, List unreadable, each as lines at the same standard). L1.3: `<reason>` is cut at 60 cells with no way to read the rest (R2-17). L1.6: Clear, Remove worktree, Keep worktree and Tidy are `Button, plain` with no at-rest cue stated, sitting beside normal-weight text lines (R2-05). L1.2, L1.4, L1.7 n/a: no build |
| L2 | Choice Overload | fail | L2.5 | L2.1 pass (focus on Keep worktree; "(recommended)" on the first option of each tidy question). L2.4 pass (Clear, Close, Remove, Tidy kept apart by the alias table). L2.6: Session +1 button (+2 in the offer), Home +1, two 2-option questions; each reduces choice-set complexity by naming safe items only. L2.5: the page does not say before Clear whether it can be undone (R2-06); the offer does ("so you can make it again"). L2.2, L2.3 n/a: no comparison, no picker |
| L3 | Chunking | fail | L3.5 | L3.4 pass on spec text (a TIDY heading, section blocks). L3.6 pass (Tasks "and N more"; tidy "and 3 more like these"; counts given). L3.5: error lines run 88-117 cells before the reason, above the 50-75 character guide (R2-18). L3.1-L3.3 n/a: no long identifiers, no form |
| L4 | Cognitive Bias | fail | L4.4 | L4.6 pass (every number has a unit or a period: "idle for 30 days or more", "ended 63d ago"). L4.4: "Skip these N" and "Keep worktree" are not remembered, so the Tidy line and the next pass ask again about the same items (R2-14). L4.5 n/a: no money, consent, access, mail or personal-data default (the "(recommended)" on a removal option is recorded under R2-13). L4.1-L4.3, L4.7 n/a: no consent, subscription or money input |
| L5 | Cognitive Load | fail | L5.1 | L5.3 pass (ages computed: "63d ago", "idle 41d"). L5.5 pass (owner's words: Clear, Tidy, idle; no internal codes). L5.7 pass (zero dominant controls). L5.1: the background reason line "This one is still running" repeats the state in the header on the most-viewed state (R2-19). L5.2, L5.4, L5.6 n/a |
| L6 | Doherty Threshold | n/a | none | n/a: no build yet. Stated behaviour: "Clearing…" and "Removing worktree…" replace the button and a second press is ignored (L6.3 half). No duration is stated. Tidy's Checking phase has no per-item progress (B10, R2-15). L6.6 n/a: no code to search, and the spec states no delay or timer. L6.7 n/a: terminal |
| L7 | Fitts's Law | fail | L7.7 | L7.4 pass (offer buttons directly under their two lines; Tidy under its count). L7.6 pass on the letter: Clear sits in the same row as Copy resume command with `gap={2}` (`pane/view.tsx:96`), the spacing exception; the risk is carried by R2-03, not by distance. L7.8 pass (no drag, `interaction.md` Elements). L7.7: the spec fixes the layout under the pointer for Clear's own result but not for the live to ended change, where Clear appears where the reason line was (R2-09). L7.1-L7.3, L7.5 n/a: no build, no popover |
| L8 | Flow | fail | L8.4 | L8.1 pass, L8.2 pass (feedback on the page, next to the tasks), L8.3 pass (`/tracker session <text>`, `/tracker tidy`; no hotkeys by owner decision), L8.5 pass (when checked, Clear acted with no confirm; it now asks one every time), L8.6 pass (no focus move without a press). L8.4: after Clear the focused Home row (the session's task row) no longer exists, and Back's restore is unstated (R2-20). L8.7 n/a |
| L9 | Goal-Gradient Effect | fail | L9.1 | L9.6 pass ("Tidy done."). L9.3 pass (counts are computed). L9.1: the tidy pass can ask up to two questions and the owner is never told how many (R2-21). L9.2, L9.4, L9.5 n/a: no checklist, nothing to keep |
| L10 | Hick's Law | pass | none | L10.1 counts above. L10.2 pass: every added list states a sort (Tasks newest first; tidy items oldest first; Result in step order). L10.3 pass. L10.5 pass (the monthly job sits last on Home). L10.4, L10.6 n/a: flat, no long list |
| L11 | Jakob's Law | fail | L11.2 | L11.2: `interaction.md` line 5 says "Tab and the arrows move the ring", the Elements rows say "arrows scroll", and `screens.md` says the pane "does not scroll" (R2-04). L11.4 pass (glyph beside words). L11.6 pass (Buttons reused; same verb "Clear" in the page and the tidy question; Close and Clear apart on purpose, `conformance.md` Deliberate inconsistencies). L11.7 pass. L11.5 n/a: the pane's one link is a PR number that opens GitHub, and this change adds none. L11.3, L11.8 n/a: no URL; the removal of Copy resume command from live sessions is a restored rule (F005) |
| L12 | Law of Common Region | pass | none | L12.1 pass on spec text (blocks are lines, then actions; the offer is its own two blocks). L12.4 pass (no boxes, no nesting). The offer has no stated boundary or rule: figure-ground look at build (B9). L12.2, L12.3, L12.5, L12.6 n/a: no build, no bordered region |
| L13 | Law of Proximity | pass | none | L13.4 pass (the offer names its worktree in its own line; Tidy sits under its count; Clear is a page-level action). L13.5 pass ("63d ago" beside the state). L13.1-L13.3, L13.6, L13.7 n/a: no build |
| L14 | Law of Prägnanz | pass | none | L14.1 pass (every glyph sits beside words). L14.3: 5 glyphs, all reused (`●` `◐` `✓` `○` `✗`), no new shape. L14.2, L14.4, L14.5 n/a |
| L15 | Law of Similarity | fail | L15.1, L15.2, L15.3 | L15.1: the same kind of line, "why a control is absent", is normal weight for Clear and the worktree but dim for "Tidy waits…" (R2-22). L15.2: plain Buttons are not stated to differ from the normal-weight lines around them (R2-05). L15.3: dim means ended, label, fact, in progress and waiting (R2-22). L15.4 pass (every glyph has words). L15.5 pass (`lines` and `actions` blocks reused). L15.6 n/a |
| L16 | Law of Uniform Connectedness | n/a | none | L16.1-L16.5 n/a: "the change adds no grouped controls, steps, master-detail or tables". Remove worktree and Keep worktree are two separate Buttons in an `actions` row, not a joined group; no row opens a panel |
| L17 | Mental Model | fail | L17.2, L17.3, L17.4, L17.6 | L17.1 pass (alias table: ended, idle, last activity, started, Clear, Remove, Tidy). L17.5 pass (no new page, one place per object). L17.3: the label "ended" is only true if every live background row carries a `pid`, which the spec never states (R2-01). L17.4: Clear and Tidy do not say before the press what they do outside the tracker (R2-06); the tidy sentence "has no task that is not done" claims more than the rule checks (R2-07). L17.2: a session whose only leftover is a removable worktree still shows "Clear", which then only opens the offer (R2-23). L17.6: a needs-you row vanishes with no word (R2-24) |
| L18 | Miller's Law | fail | L18.3 | L18.2 pass (nothing is held in mind: the tidy items are listed). L18.1 pass (nothing judged on a count of 7). L18.3: exceptions to a tidy batch are typed under Other, not picked from the listed items (R2-12). L18.4 n/a |
| L19 | Occam's Razor | fail | L19.3 | L19.1 pass (each element traces to J1-J6). L19.2 pass (Tidy has a button and a command; the command is excepted). L19.5 pass. L19.3: header "○ ended 63d ago" and first line "last activity 63d ago" show one number twice; the worktree line and the offer name the same worktree and branch within a few rows (R2-25). L19.4 n/a |
| L20 | Paradox of the Active User | fail | L20.3 | L20.2 pass ("Nothing to clear: it is not in Claude Code's list and has no open tasks"; "Nothing to tidy. No ended session or worktree has been idle for 30 days."). L20.5 pass (errors give an action). L20.7 pass. L20.3: no in-context hint of what Clear or Tidy will do (R2-06). L20.1, L20.4, L20.6 n/a |
| L21 | Pareto Principle | pass | none | L21.1 pass (Journeys table names frequency and source per job). L21.2 pass: J1 0 moves, J2 2, J3 3 for a weekly act, J5 1 or 2 for a monthly one. L21.3 pass (Clear visible, Tidy visible, rare Remove only after Clear). L21.4 pass (the safe default wins: the ring starts on Copy resume command). L21.5 n/a |
| L22 | Parkinson's Law | pass | none | L22.3 pass (no time limit). L22.5 pass (no urgency styling; the Tidy line is dim). L22.1, L22.2, L22.4, L22.6 n/a: no personal-data input, no session timeout |
| L23 | Peak-End Rule | fail | L23.3 | L23.1 pass (result lines name what happened and what stays). L23.2 pass (Clear's four errors read event, consequence, action). L23.5 pass (inline ✓ lines, no celebration). L23.3: a tidy item whose action fails after the re-check passed (git refuses, `claude rm` fails) has no report line; the Errors table covers only a failed re-check (R2-11). L23.4 n/a |
| L24 | Postel's Law | fail | L24.2, L24.3 | L24.2: how typed exceptions under Other are matched is unstated, and an ambiguous reply is not said to mean "do nothing"; `/tracker tidy <anything>` is unstated (R2-12, R2-26). L24.3: the final list of items is not shown back before "Clear all N" acts after exceptions are typed (R2-12). L24.1, L24.4-L24.7 n/a |
| L25 | Selective Attention | fail | L25.1, L25.6 | L25.4 pass (errors stay as lines until the owner leaves; the Tidy line stays). L25.2 pass for the Session page (results sit under the actions). L25.1: the pane sets no height and does not scroll (`screens.md` Sections row 8), yet a wrapped page runs to roughly 40 rows docked at 36 columns, so the offer, a result or an error can sit below the visible rows (R2-10). L25.6: a needs-you row disappears within 5 seconds with no statement that milestone 1's "order frozen while focused" covers a removal; a Clear button appears under the pointer on live to ended (R2-09, R2-24). L25.3, L25.5 n/a |
| L26 | Serial Position Effect | pass | none | L26.1 pass (state first on the page; the Tidy line last on Home; the outcome last on the Session page). L26.2 pass ("Clear all 5 (recommended)" and "Remove all 3 (recommended)" first). L26.3 n/a: no long form. L26.4 pass (no convention overridden) |
| L27 | Tesler's Law | fail | L27.5 | L27.1 pass (nothing typed that the system holds). L27.2 pass. L27.3 pass (five conditions computed). L27.4 pass. L27.5: "Worktree login stays: it has uncommitted changes." names the rule, not the way forward, and only the first failed condition (R2-27) |
| L28 | Von Restorff Effect | pass | none | L28.1: 0 visually dominant controls (all plain). L28.2 pass (the red Forgotten tasks are the most distinctive items, and they are the unfinished work). L28.3: emphasis is weight and glyph colour only. L28.4 pass (every colour has a glyph and words). L28.5 pass (no advertisement-style emphasis; the Tidy line is dim). L28.7 n/a: no motion in a terminal band or pane. L28.6 n/a: nothing new is inserted in a list. `ia.md` calls Clear "primary" while no style carries that (R2-29) |
| L29 | Working Memory | fail | L29.3, L29.5, L29.7 | L29.1 pass (crumbs and title). L29.8 pass. L29.3 and L29.5: "Clear all 13" is asked with 10 items listed and "and 3 more like these" (R2-13). L29.7: a cleared session and an ended one with leftovers look the same in Ended and on Repo; the tracker stores no cleared mark by decision (R2-28). L29.2, L29.4, L29.6 n/a: no filter, no field |
| L30 | Zeigarnik Effect | pass | none | L30.2 pass (unfinished asks stay visible as Forgotten, red, until Clear). L30.4 pass ("and N more", "and 3 more like these"). L30.5 pass. L30.1, L30.3 n/a. Cited as resumption only: Copy resume command (B14) |
| B1 | Response-time limits | n/a | none | n/a: no build yet. Same checks as L6 |
| B2 | Recognition over recall | pass | none | Help and hint strings gain `tidy`; "Clear" and "Tidy" are the owner's words; glyphs sit beside words. Typed exceptions are recall (R2-12, under L18.3) |
| B3 | Progressive disclosure | pass | none | Band, Pane Home, Session: 2 levels. Rare jobs (Remove worktree, Tidy) are last or behind Clear; frequent items are never behind them |
| B4 | Error-message guidelines | fail | precise, constructive | Clear's four errors score well (near the source, human, constructive, input kept). The Partial state says "its branch is not merged" when `gh` is missing and the PR may be merged (R2-08). `<reason>` is cut at 60 cells (R2-17). "Has no task that is not done" is not precise (R2-07) |
| B5 | Error prevention, confirmation, undo | fail | confirm or undo, re-check | No money, consent, access or mail action, but Clear writes Claude Code's list and closes tasks with no confirm and no undo (R2-03); the process fact is not re-read at the press (R2-02); the rule "no `pid` is ended" fails open (R2-01). Buttons are labelled with outcomes ("Remove worktree" / "Keep worktree", "Clear all 5" / "Skip these 5") |
| B6 | Form guidelines | n/a | none | n/a: the change has no form. The free-text Other is the host's |
| B7 | Shneiderman's eight rules | fail | easy reversal | Closure pass (L23.1). Control pass: nothing runs without a press or a typed command (N4). Reversal fails with B5: closed tasks are never reopened (R2-03) |
| B8 | Signifiers, mapping, constraints | fail | rest signifier | New plain Buttons carry no stated at-rest cue (R2-05). The constraint reason is now stated for Clear ("Clear is for ended sessions…"); Copy resume command also disappears on a live session and no line says so (R2-19). Mapping: Clear sits at the foot, below the tasks it closes; accepted as a page-level action |
| B9 | Gestalt, missing five | n/a | none | n/a: no build yet. Stated: no overlay and no scrim; the offer is inline with no boundary or rule above it. Needs a figure-ground look at build: the offer sits between the actions row and the ✓ lines |
| B10 | Visibility of system status on the object | fail | async state | The Session page shows "Clearing…" and "Removing worktree…" on the object and keeps the result. Tidy's Checking phase has no per-item progress, and a pass running in another session is invisible in this pane (R2-15) |
| B11 | User control and freedom | fail | undo or review | Back, Escape and Keep worktree are stated. Clear has neither undo nor review (R2-03). Interrupting an Acting tidy pass leaves some items done and no report (R2-11) |
| B12 | Deceptive design and consent | n/a | none | n/a: no consent, subscription or steering surface |
| B13 | Keyboard reachability and visible focus | pass | none | Every new control is Tab then Enter; initial focus is stated (Copy resume command, never Clear; Keep worktree when the offer opens; never Tidy); focus after Clear, Remove and Keep returns to the first action. 2.4.7, 2.4.11 n/a: no build (the off-screen risk is R2-10) |
| B14 | Goal-gradient vs Zeigarnik citation | pass | none | The spec cites neither |

## Deliberate Inconsistencies

| Rule | Where | Why | Owner decision needed |
|---|---|---|---|
| `setup.md` "Observe only" and the Safety limits (C1) | Clear, Remove worktree, tidy | The owner asked (A3, A4, A6); acts only on a press or a typed command | Yes. Accept the replacement rule; then edit `docs/ux/setup.md` and the guidelines (outside this folder). |
| Milestone 1 no-go N6 and the owner's 2026-11-13 words "ok never mind lets remove this intervention rules" | the same | The tracker now acts, never on its own | Yes, with C1. |
| Confirm before what cannot be undone (`intent.md`) | Clear asks one confirm every time; Remove worktree asks its own; tidy asks once per batch | none now: the spec follows the intent | Decided: owner, dialog, 2026-11-14, "Always confirm". |
| `claude rm` removes a worktree the session made without the offer's confirm | Clear | Claude Code's own "if safe" test; named in Clear's confirm and in the result | Decided: owner, dialog, 2026-11-14, "Allow, name it (Recommended)". |
| A button that leaves the pane | Home: Tidy closes the pane | Tidy runs in the owner's session | Yes, once Stage 3 shows the hand-off works. |
| "Every model call pins haiku" (`setup.md`) | tidy supervisor | The rule was written for the mod's own calls | Yes: reword to "every model call the mod makes". |
| Copy resume command on every session (built) against ended only (milestone 1, F005) | Session page | Resuming a live session starts a second process | Accept (recommended). |
| Close and Clear | Clear acts on a session; Close ends a pane or one task | The owner's word is "Clear" (A6) | Decided: owner, dialog, 2026-11-14, "Keep "Clear" (Recommended)". |
| Clear has no `/tracker` command of its own | Session | The act is taken with its tasks and worktree in view | Accept or add one. |
| No hotkeys shown, so no key per control | all new controls: "Tab to it, Enter" | Owner, 2026-11-14 | none (decided) |

## Findings

Round 1 had 0 Critical. Status after the three rounds:

| Severity | Location | Finding | Status |
|---|---|---|---|
| 3 | R1-01, R2-03: Clear without confirm or undo | A line before the press says what it does; Reopen tasks undoes the closing; the confirm itself is the owner's decision | fixed in the spec; the owner decided on 2026-11-14: "Always confirm" |
| 3 | R1-02, R3-13: `claude rm` removes a worktree silently | Named before and after the press; the result line says Claude Code removed it | fixed; Clear's confirm and the worktree are decided ("Always confirm"; "Allow, name it (Recommended)", owner, dialog, 2026-11-14) |
| 3 | R1-03: ignored files (such as `.env`) deleted with a worktree | Named in the offer and in the tidy question | fixed (round 2, N1); the offer now lists the files ("List them in the offer (Recommended)", owner, dialog, 2026-11-14) |
| 3 | R1-04, R2-02, R3-03: no process re-check at the press | Clear re-reads the list first; Refused state and words | fixed |
| 3 | R1-05, R2-13, R3-12: batch answered with items not listed | Every item listed; batches of 25 | fixed |
| 3 | R2-01, R3-24: the no-pid rule fails open | Limited to blocked and done rows; "Pid not reported" state; self never ended; the Stage 3 fixture of a live background row is a gate | fixed, one residual risk named |
| 3 | R2-04: arrows move or scroll | "↑↓ move the ring; no page scrolls"; row count named for the render check | fixed |
| 3 | R3-01: resume command points at a removed worktree | Not drawn when the folder is gone; the result says what to do | fixed |
| 3 | R3-02: the Tasks line is not the set Clear closes | Ended sessions show only the tasks Home lists | fixed |
| 3 | R3-04: Tidy count includes items tidy never acts on | Counts only what passes every check | fixed |
| 3 | R3-05: tidy checks done by a model | Checks by code; subagents describe | fixed |
| 3 | R3-06: worktree idle time undefined | Newest of last commit, folder change and sessions' activity; unknown is not stale | fixed |
| 3 | N1 (round 2): tidy questions lacked the disclosures | Added | fixed |
| 2 | R1 and R3 mediums, R2-05 to R2-12, R2-14 (Skip is not remembered), R2-15 to R2-28 | Deferred to `plan.md` as Risk rows; none is a contradiction | deferred |
| 2 | Round 3 M2 to M5 (focus after Clear, Reopened offers no Clear, tidy "never removed" against `claude rm` on a session batch) | M2 and M3 fixed after the round; M4 and M5 deferred | partly fixed |

## Decided

Answered by the owner in a dialog on 2026-11-14; each answer is quoted as selected. The numbers keep the ones the questions had under Decisions Needed.

| Question | Owner's answer | Source | What the spec does |
|---|---|---|---|
| 1. Should Clear ask for a confirm? | "Always confirm" | owner, dialog, 2026-11-14 | Clear opens one confirm every time it would write; focus lands on Cancel; "Clear session" runs it. |
| 2. Is `claude rm`'s own removal of a worktree it made allowed inside Clear? | "Allow, name it (Recommended)" | owner, dialog, 2026-11-14 | The confirm names it before the press, the result after. |
| 8. Ignored files (such as `.env`) are deleted with a worktree. | "List them in the offer (Recommended)" | owner, dialog, 2026-11-14 | The offer lists up to 3 names and "and N more". |
| The button word | "Keep "Clear" (Recommended)" | owner, dialog, 2026-11-14 | The button stays "Clear". |

## Decisions Needed

| Question | Recommended answer | Why it matters |
|---|---|---|
| 3. Replace the hard rule "observe only" (and the Safety list) in `docs/ux/setup.md` and the guidelines. | Yes: acts only on the owner's press or typed command; never stops a running session; never forces; never deletes a branch. | The tracker now writes outside its folder. |
| 4. Does "every model call pins haiku" cover tidy's supervisor? | No: it covers the mod's own calls; recommend haiku for the describing subagents. | The rule says "every". |
| 5. Where does tidy run, and how does a mod command start it? | In the session where it is typed; Stage 3 verifies the hand-off, the fallback is a plugin skill. | Unverified mechanism. |
| 6. Do Clear, the offer and the Tidy line fit the owner's mockups of 2026-11-14? | Show the owner `screens.md`; the mockups were local files and are not in the repo. | Approved mockups win; nothing here could be compared with them. |
| 7. Should "Skip these N" and "Keep worktree" be remembered? | No for now: the Tidy line counts only what passes every check, so it shrinks as the owner clears. | A5's "breathing" complaint; a stored mark adds a field the spec set aside. |
| 9. After a worktree is removed, resuming needs it made again from the branch. Acceptable? | Yes; Stage 3 confirms resuming works that way. | The brief calls the conversation resumable. |
| 10. Should a forgotten task of an ended session age out sooner than 7 days? | No; Clear is the answer. | The state fix alone removes the 63-day rows. |

## Did Not Run

| Check | Reason |
|---|---|
| The three reviewers on the Confirming state and the longer offer | Added after the loop for the owner's answers of 2026-11-14; they need a re-check before build |
| Prototype images and the visual pass | Not drawn: the plan decides whether the UI is risky; the loop is text-only |
| A real terminal render at 120, 80 and 40 columns | Nothing is built; cell counts are arithmetic on the strings |
| Laws checks with S, I, T or M evidence only (L1.2, L1.4, L1.7, L7.1 to L7.3, L12, L13, L6, B1, L20.1 and more) | No build, no pixels, no timings (reviewer 2's Did not run list) |
| Comparison with the owner's mockups | The mockups are not in the repo |
| `claude rm` on an interactive session not in the list; whether a live background row always carries `pid`; where last activity comes from | Facts for Stage 3 (`ia.md`, Open Questions) |
