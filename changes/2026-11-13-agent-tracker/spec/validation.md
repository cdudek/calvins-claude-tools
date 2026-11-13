---
type: validation
change: 2026-11-13-agent-tracker
verdict: ready
status: draft
reviewed_by: null
approved_at: null
created: 2026-11-13
---

# Validation

One pass, as sdlc-run Stage 2 step 5 asks: three independent reviewers on the spec text, merged after all finished, then one fix round in the spec. No second review round. Reviewer notes: [r1 heuristics](review/r1-heuristics.md), [r2 Laws of UX](review/r2-laws.md), [r3 screens](review/r3-screens.md).

## Verdict

ready. No severity 3 or 4 finding is open after the one fix round; the four owner questions were answered on 2026-11-13. Medium and Low findings go to `plan.md` as Risk rows or are deferred, as sdlc-run Stage 2 step 5 asks.

## Definition Of Ready

| Check | Result | Evidence |
|---|---|---|
| Activities | pass | brief, ia, interaction, screens, conformance done; prototype not drawn (sdlc-run draws images only when the plan marks the UI risky) |
| Asks | pass for this stage | every ask maps to a job story and a screen below; the fact column fills in Stage 3 and the gate pass checks it |
| Findings | pass | 22 High findings from the reviewers (contradictions counted as High), 16 once merged, all fixed in the spec; none Critical; see Findings |
| Laws of UX | pass | 30 rows and the B rows below, from reviewer 2 |
| Concerns | pass | conformance F001 to F016 resolved or listed in Decisions Needed |
| Questions | pass | four asked in one batch, all answered 2026-11-13 |
| Prototype | not yet: prototype follows only if the plan marks the UI risky | |

## Asks To Screens To Facts

| Ask | Job story | Screen | State | Fact or out of scope |
|---|---|---|---|---|
| A1 | J1, J2, J3, J4, J11 | Band, Pane Home, Session, Repo | needs you, running, done | facts follow (Stage 3) |
| A2 | none (cost rule) | none | none | facts follow (Stage 3) |
| A3 | J8 | none in milestone 1 | reserved | facts follow (Stage 3) |
| A4 | J5 | Band, compact | all | facts follow (Stage 3) |
| A5 | none in milestone 1 | web page, milestone 2 | n/a | facts follow (Stage 3) |
| A6 | J5, J6 | Band, compact and details | all | facts follow (Stage 3) |
| A7 | J7 | Band, details header; compact Work segment | all | facts follow (Stage 3) |
| A8 | J3, J6 | Pane Home, Session, Repo | all | facts follow (Stage 3) |
| A9 | J1 | Pane Home (triage queue) | needs you first | facts follow (Stage 3) |
| A10 | J9 | all, without milestone parts | without sdlc-run | facts follow (Stage 3) |
| A11 | J5, J6 | band and pane | all | facts follow (Stage 3) |
| A12 | J9 | all | standalone | facts follow (Stage 3) |

## Prototype Screenshots

| Screen | State | 100 % | 150 % |
|---|---|---|---|
| none | | not drawn | not drawn |

## Laws Of UX Coverage

Reviewer 2's table, as returned.

| # | Law | Verdict | Failed checks | Evidence |
|---|---|---|---|---|
| L1 | Aesthetic-Usability Effect | fail | L1.6 | L1.1 pass (theme names only, `conformance.md` Design system), L1.5 pass (states exist for every screen). L1.6: session rows are `plain` Buttons that look like text (R2-03). L1.2-L1.4, L1.7 n/a: no build |
| L2 | Choice Overload | fail | L2.4 | L2.6: no picker added; 2-3 band buttons. L2.4: two sessions can share a title and the Needs-you row and band show no branch (R2-07). L2.1-L2.3, L2.5 n/a: no picker or committing choice |
| L3 | Chunking | fail | L3.6 | L3.4 pass (section headings). L3.6: Asks and Home lists are unbounded and headings carry no total (R2-16). L3.1-L3.3, L3.5 n/a: no long identifiers or forms |
| L4 | Cognitive Bias | fail | L4.6 | L4.6: errors, retries and tokens shown with no reference (R2-05). L4.1-L4.5, L4.7 n/a: no consent, money or access action |
| L5 | Cognitive Load | fail | L5.5 | L5.5: engine `waitingFor` shown raw as the reason, unbounded (R2-19); "2/4" vs "feature 2 of 4" (R2-04). L5.1 listed: Done column and Repos line carry no owner ask (R2-14). L5.7 pass (one warning-coloured count, no primary). L5.4, L5.6 n/a |
| L6 | Doherty Threshold | n/a | none | n/a: no build yet. Stated value: 5 s refresh (`interaction.md` line 11), not a feedback time. Pending state gap raised under B10 |
| L7 | Fitts's Law | fail | L7.4 | L7.6, L7.8 pass (no destructive target, no drag). L7.4: Back, Home, Close sit in the page header only; sticky or not is unstated (R2-11). L7.1-L7.3, L7.7 n/a: no build (band buttons are one row high) |
| L8 | Flow | fail | L8.4 | L8.2, L8.3, L8.5 pass. L8.4: closing the pane and reopening always lands on Home, so the open session is lost (design choice F006, R2-22). L8.1, L8.6, L8.7 n/a/not adopted |
| L9 | Goal-Gradient Effect | fail | L9.3 | L9.1, L9.2 pass (feature list names each state). L9.3: what "2/4" counts is not defined (R2-04) |
| L10 | Hick's Law | pass | none | L10.1 counts above. L10.2 pass: every list has a stated sort (`screens.md` Lists tables). L10.5 pass (Copy only in details). L10.6 n/a: no build; no filter in milestone 1 |
| L11 | Jakob's Law | fail | L11.2, L11.4, L11.6 | L11.2: arrow keys walk buttons, scroll, or "move" depending on the file (R2-08). L11.4: `↓` for mergeable is unconventional, `✗` has no label on the compact band (R2-12). L11.6: one entry, four names (R2-02). L11.7 pass. L11.1, L11.3, L11.5 n/a: no build |
| L12 | Law of Common Region | pass | none | L12.1 pass on spec text (sections and columns group related items), L12.4 pass (no nesting). L12.2, L12.3, L12.5 n/a: no build |
| L13 | Law of Proximity | fail | L13.4 | L13.4: Copy resume command has no place in Header or Sections (R2-15). L13.5 pass. L13.1-L13.3, L13.6, L13.7 n/a: no build |
| L14 | Law of Prägnanz | fail | L14.1 | L14.1: `1 ✗` has no label; `◐ 3` loses "running" at 150 % (R2-12). L14.3: 6 glyphs, from Claude Code's set. L14.2, L14.4, L14.5 n/a |
| L15 | Law of Similarity | fail | L15.2, L15.3 | L15.2: clickable rows and static ask, feature and run rows have the same look (R2-03). L15.3: dim means zero, stale, done, ended, loading and secondary (R2-17). L15.4 pass: every glyph has a word or count. L15.1, L15.6 n/a |
| L16 | Law of Uniform Connectedness | n/a | none | n/a: no joined controls, steps or master-detail. Ask and feature rows are terminal text rows; L16.4 (hover, zebra) n/a: no build |
| L17 | Mental Model | fail | L17.2, L17.5 | L17.2: "0 need you" while finished sessions wait for review (R2-10); "ended" inferred from absence enables Copy resume command (R2-20). L17.5: one entry, four names (R2-02). L17.1 pass (alias table consistent except "2/4"). L17.4 pass (Copy is clipboard only) |
| L18 | Miller's Law | fail | L18.3 | L18.2 pass (1-2 items held). L18.3: `/tracker session <title or id>` takes an id that is shown nowhere (R2-07). L18.4 n/a |
| L19 | Occam's Razor | fail | L19.2, L19.3 | L19.2: repo opens from heading, heading again, Repos line; Home beside Back (R2-14). L19.3: breadcrumb, title and repo button repeat; details header repeats milestone in branch (R2-14). L19.1, L19.5 pass (each element traces to a job or F-code) |
| L20 | Paradox of the Active User | fail | L20.3 | L20.3: no hint for `ctrl+x tab`, hotkeys, the glyphs, or `/tracker band off` (R2-13). L20.2, L20.4, L20.5, L20.7 pass. L20.1 n/a: no build |
| L21 | Pareto Principle | pass | none | L21.1 pass (Journeys table gives frequency per job). L21.2 pass: J1 and J5 need 0 moves, J11 needs 2. L21.3, L21.5 pass. J1 ends at a name (R2-22, design choice) |
| L22 | Parkinson's Law | pass | none | L22.3 pass (no time limit), L22.5 pass (no urgency styling beyond real wait times). L22.1, L22.2, L22.4, L22.6 n/a: no personal-data input |
| L23 | Peak-End Rule | pass | none | L23.1 pass (toasts name the outcome), L23.2 pass (every error reads event, consequence, action), L23.5 pass. L23.3, L23.4 n/a |
| L24 | Postel's Law | fail | L24.2 | L24.2: match rule for `/tracker session` and `/tracker repo` unstated; many matches unhandled (R2-07). L24.1, L24.5-L24.7 n/a: no build |
| L25 | Selective Attention | fail | L25.3, L25.4, L25.6 | L25.3: the only push is a colour change in a band-shaped row (R2-09). L25.4: Copy failed is a toast (R2-18). L25.6: live re-sort moves rows under the pointer (R2-01). L25.1, L25.5 pass |
| L26 | Serial Position Effect | pass | none | L26.1 pass: count first in the compact line, state glyph first in every row. L26.2 pass: longest wait first |
| L27 | Tesler's Law | pass | none | L27.2, L27.4, L27.5 pass. J1 hands the user the job of finding the terminal (R2-22, design choice). L27.1, L27.3 n/a |
| L28 | Von Restorff Effect | fail | L28.6 | L28.1 pass (no primary; 2 plain buttons), L28.2 pass (warning count), L28.4 pass. L28.6: a session that starts waiting sorts last in Needs you and is not marked (R2-01). L28.3 count: 4 bold counts + 1 warning |
| L29 | Working Memory | pass | none | L29.1 pass (breadcrumb, title), L29.8 pass (all sessions on Home). L29.2-L29.7 n/a: no filter, selection, form or review step |
| L30 | Zeigarnik Effect | pass | none | L30.4 pass for titles ("…"); list length cue is R2-16 under L3.6. L30.5 pass. L30.1-L30.3 n/a: nothing is authored or interrupted. Cited as resumption only (B14) |

### B rows

| L29 | Working Memory | pass | none | L29.1 pass (breadcrumb, title), L29.8 pass (all sessions on Home). L29.2-L29.7 n/a: no filter, selection, form or review step |
| L30 | Zeigarnik Effect | pass | none | L30.4 pass for titles ("…"); list length cue is R2-16 under L3.6. L30.5 pass. L30.1-L30.3 n/a: nothing is authored or interrupted. Cited as resumption only (B14) |
| B1 | Response-time limits | n/a | none | n/a: no build yet. Same checks as L6 |
| B2 | Recognition over recall | fail | icon label | Icons in early use must carry text: `1 ✗` and `◐ 3` do not (R2-12). Pane rows and Repos line offer recognition. `/tracker` arguments are recall (R2-07) |
| B3 | Progressive disclosure | pass | none | 2 levels from the band (Pane Home, then Session or Repo). "Pane" does not name what it reveals; the owner kept it (`conformance.md` Copy pass) |
| B4 | Error-message guidelines | pass | none | Store failed, stale, gh missing, not found, copy failed each score against the 12: near the source, human, constructive, input kept |
| B5 | Error prevention, confirmation, undo | pass | none | No money, consent, access or mail action. Nothing writes outside the tracker's folder; no Yes/No button |
| B6 | Form guidelines | n/a | none | n/a: the change has no form |
| B7 | Shneiderman's eight rules | pass | none | Closure (L23.1) pass, reversal (B5) pass, control: no automatic action beyond refresh |
| B8 | Signifiers, mapping, constraints | fail | rest signifier, constraint reason | Rows and headings are `plain` Buttons with no stated at-rest cue (R2-03). Copy resume command is hidden for a live session and the reason is stated only in the spec (R2-15) |
| B9 | Gestalt, missing five | n/a | none | n/a: no build yet. Stated: band and pane share one key ring; two bands stack when ponytail is on (F011). Needs a figure-ground and alignment look at build |
| B10 | Visibility of system status on the object | fail | async state | An ask being classified has no state; "not classified" covers pending, failed and transcript-only (R2-06) |
| B11 | User control and freedom | pass | none | Escape in two steps plus Close and `ctrl+x x`; Back restores row and scroll |
| B12 | Deceptive design and consent | n/a | none | n/a: no consent, subscription or steering surface |
| B13 | Keyboard reachability and visible focus | fail | initial focus, focus order | Pane opens "with the keyboard" but the first focus stop is unstated and Close is the first control on Home (R2-11). 2.4.7, 2.4.11 n/a: no build |
| B14 | Goal-gradient vs Zeigarnik citation | pass | none | The spec cites neither as evidence |

## Deliberate Inconsistencies

| Rule | Where | Why | Owner decision needed |
|---|---|---|---|
| RC-1, RC-2 plural route ids | pane `repo/<repo>`, `session/<sessionId>` | ids match object names; no list page | decided: keep singular (EX-1) |
| Relationships in words, not symbols | compact band "4 PRs · 1 ✗" | width; the details line says "1 failing", the desktop SVG `alt` spells it out | no |
| Buttons name an action | band "Pane" | names a place, as the design file's button set and ponytail's "Board" do | decided: keep as is |

## Findings

Merged from the three reviewers; the review files hold the full text. "Contradiction" items were rated 3 by rule.

| Severity | Location | Finding | Status |
|---|---|---|---|
| 3 | ia.md, setup.md S2 | Needs-you boundary: a turn ending with a plain-text question is `idle`, counted as done; the band read "0 need you" while sessions waited (r1 R1, C7; r2 R2-10) | fixed: owner chose "Yes, via haiku"; the band also shows a done count |
| 3 | ia.md, screens.md | No route from the band to a waiting live session; resume is for ended sessions only (r1 R2) | fixed in part: Needs you rows add the branch; that the title matches the Claude Code tab is a Risk for the plan |
| 3 | Home | Home is a dead end for review (S3): ended sessions were 3 to 4 moves away, Empty had no way on (r1 R3; r3 9) | fixed: "Ended today" on Home; the Repos line shows in every state |
| 3 | Session | Section order: Asks first or Running now first (r1 C1; r3 4, 6) | fixed: header, Running now, Usage, Milestone, Asks last |
| 3 | interaction.md | Arrows scroll or move focus (r1 C2; r3 1) | fixed: Tab moves focus, the arrows scroll |
| 3 | Home rows | Errors and retries on Running rows only, though J4 needs them on every row (r1 C3) | fixed: on every row when above 0 |
| 3 | ia.md, screens.md | Compact band's first segment: repo or count (r1 C4) | fixed: count first, Work last, everywhere |
| 3 | brief, interaction, screens | "feature 2 of 4" against "2/4" (r1 C5; r2 R2-04; r3) | fixed: "2 of 4 features complete"; compact "2/4" defined |
| 3 | setup, sitemap, interaction | A "without bd" state with no screen (r1 C6) | fixed: nothing from bd in milestone 1 |
| 3 | interaction.md | Redraw only on data change, yet times tick (r1 C8; r3 5) | fixed: a one-minute redraw, times to the minute |
| 3 | interaction.md | Alone state drops the needs-you segment (r1 C9) | fixed: kept |
| 3 | screens.md Home | Stale line in the footer or at the top (r3 2) | fixed: top, under the title |
| 3 | Repo PR row | The PR's session had no control (r3 3) | fixed: a session button on the PR row |
| 3 | Session ask row | Too narrow in a 24 to 54 column dock (r3 7) | fixed: two-line rows below 70 columns |
| 3 | Repo PR row | One line of about 80 cells in a dock of 54; failing checks dim (r3 8) | fixed: two lines below 70; failing checks in the error colour |
| 3 | Home rows | Needs-you wait and reason dim (r3 10) | fixed: normal colour |
| 2 | Home | Rows re-sort under focus; a new waiting row is unmarked (r2 R2-01) | fixed: order frozen while focused, "new" marker |
| 2 | Pane open | First focus stop unstated; Close first (r2 R2-11) | fixed: focus starts on the first row |
| 2 | band | One drop order at every width; stale suffix placement (r3) | fixed |
| 2 | Home | Durations above an hour; Done uncapped (r3) | fixed: "2h 10m", "3d"; Done at most 10 |
| 2 | various | 27 more Medium and Low findings: hotkey hints, `/tracker` argument matching, layout shift when the band view changes in other sessions, PR count scope, pending classification state, duplicate Back and Home, glyph meanings and others | to `plan.md`: Risk rows or deferred (r1 R4 to R22, r2 R2-02 to R2-20, r3 Medium and Low) |

## Decisions Needed

None open. Answered by the owner on 2026-11-13, each the recommended option:

| Question | Answer | Where written |
|---|---|---|
| Does a turn ending with a plain-text question count as needs you? | "Yes, via haiku" | ia.md State Diagrams |
| WCAG scope for band and pane | "AA as a target" (R2, no EAA) | docs/ux/setup.md |
| Singular page ids | "Keep singular" | docs/ux/exceptions.md EX-1 |
| Three names for the pane | "Keep as is" | ia.md Decisions Taken Here |

## Did Not Run

| Check | Reason |
|---|---|
| Visual pass, `visual-check.py` | No images: nothing is built and no prototype is drawn. No visual compliance is claimed. |
| Second review round | sdlc-run runs validation once; the fixes were checked by grep against the contradicted strings, not re-reviewed. |
