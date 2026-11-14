---
type: ux-spec-review
reviewer: r2 of 3 (Laws of UX, every check)
change: 2026-11-13-agent-tracker
spec: brief, ia, sitemap, interaction, screens, conformance (text only, no images)
checklist: laws-of-ux.md (30 laws, 184 checks, B1-B14)
created: 2026-11-13
---

# Review 2: Laws of UX

## Method and limits

- **Read:** all six spec files, `intent.md`, `docs/ux/setup.md`. Worked independently of the other two reviewers.
- **Evidence rule:** a check whose evidence codes are all S, I, T or M is `n/a: no build yet` unless the spec states the value or the behaviour that decides it. Checks with C or N ran on the spec text (counts below).
- **What "pass" means here:** every check that could run on the spec text passed. The S, I, T and M checks that could not run are named in the Evidence column, not hidden. A pass is not a pixel check.
- **Not run for any law:** contrast (L1.4, L12.2), alignment and gaps (L1.2, L13.x), target size in CSS px (L7.1-L7.3), timings (L6.1-L6.5, L7.7), cold walk (L20.1). The spec states one fact for L7.1: band buttons are one terminal row high, so the 24 px check needs measuring at build.
- **Already resolved in `conformance.md`:** F001-F016 are not re-raised unless the resolution left the law check failing. Where a finding overlaps one, it says so.
- **Severity:** Nielsen 0-4 from the checklist (4 Critical, 3 High, 2 Medium, 1 Low, 0 design choice). B2B escalation did not apply: no money, consent, access or mail action exists (observe only, N1).
- **Result:** no finding at severity 3 or 4. Eleven at 2 (R2-01 to R2-08, R2-10, R2-11, R2-19), nine at 1, one group of design choices at 0 (R2-22).

## Counts taken (N evidence)

| Where | Count |
|---|---|
| Band compact, controls | 2 buttons (Pane, Details); both `plain`, no primary |
| Band compact, text segments at 100 % | 4 (needs you, running, PRs, work); 9 items on one line counting the oldest session name, its wait, the failing count and the goal age separately |
| Band details, controls | 3 buttons (Copy, Pane, Compact); 4 bold counts, 1 in warning colour when above 0 |
| Pane Home, decision points | 3 sections (Needs you, Running, Done), then rows (unbounded), repo headings (unbounded), 1 Repos line with one entry per repo, 1 Close |
| Pane Session and Repo, header controls | 3 buttons (Back, Home, Close) plus the repo button on Session, Copy resume command on an ended Session |
| Glyphs | 6 (`●` `◐` `✓` `○` `✗` `↓`), each with a word only in some places (R2-12) |
| Moves from the band to one session | 2 (Pane, row); to a PR row 2 (Pane, repo heading) |
| Names for the one entry to the pane | 4: "Pane" (button), `/tracker` (command), "Home" (page, breadcrumb), "Tracker" (title) |

## Coverage table

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

## Findings

### R2-01 Live updates re-sort the list under the pointer and mark nothing new (Medium, 2)

- **Checks:** L25.6, L28.6 (also L7.7, L8.6, which need a build to run).
- **Evidence:** `interaction.md` line 11: the open pane redraws when data changes. `screens.md` Pane Home Lists (lines 194-198): Needs you sorts longest wait first, Running sorts repos by "the repo with the longest-running session first", Done by latest first. A session that starts waiting has the shortest wait, so it lands last in Needs you; one that goes idle jumps from Running to Done. Nothing says focus follows the row, what happens to the scroll position, or that a new arrival is marked.
- **Why it matters:** S2 triage is the moment sessions change state fastest. A row moves just before the click, and Enter opens a different session.
- **Fix:** state that the focused row keeps focus by session id, that rows do not move while the keyboard or pointer is on the list (apply the new order on the next idle refresh or on Back), and that a row new to a section carries a one-refresh marker. Alternative: sort Needs you newest first and say so.
- **Overlaps:** none in `conformance.md`.

### R2-02 One entry, four names (Medium, 2)

- **Checks:** L17.5, L11.6.
- **Evidence:** the button "Pane", the command `/tracker`, the first page "Home" (breadcrumb root), the page title "Tracker". `ia.md` Decisions Taken Here lists this as SM-4 "put to the owner"; `conformance.md` Deliberate inconsistencies lists it as undecided.
- **Fix:** choose one noun. The cheapest: the pane's title row says "Tracker", the first page's breadcrumb root says "Tracker", the band button says "Tracker". Keep "Pane" out of the words people read.
- **Overlaps:** SM-4, F004. Still open at the gate.

### R2-03 Clickable rows look like the static rows beside them (Medium, 2)

- **Checks:** L15.2, L1.6, B8.
- **Evidence:** `screens.md` Components: Session row, Repo heading and PR row are `Button` or `Box` with `Text` children; Controls: Button `plain`. Ask rows, feature rows and Running now rows are `Box` with `Text` and "not focusable". Words for a session row ("◐ migrate users   feat/users · 22m · 41k tokens") and an ask row ("1  task      replied       add a compact view") are both a glyph or number plus dim text. No at-rest signifier (chevron, underline, prefix) is stated, only the focused state.
- **Fix:** give every row that opens a page a signifier at rest, for example a trailing `›`, and say that static rows never carry it. State the focus style once.
- **Overlaps:** none.

### R2-04 "2/4" has no definition and disagrees with the brief (Medium, 2)

- **Checks:** L9.3, L17.1, L5.5.
- **Evidence:** `brief.md` J3 and J7: "feature 2 of 4". `screens.md` lines 72 and 139: "agent-tracker-1 2/4" and "· 2/4 ·". `conformance.md` F003 resolution says wording is fixed, but the Words tables still hold "2/4". Neither file says whether 2 is the feature being built (an index) or the number complete. Feature states are "to do", "building", "complete", "merged", "blocked"; whether "merged" and "blocked" count toward the first number is unstated.
- **Why it matters:** progress that gates nothing but reads wrong costs trust in every other number on the band.
- **Fix:** define it as "features complete or merged, of all features" and write "2 of 4 done" where width allows, "2/4" only as the fallback; or show "building 3 of 4". Pick one and make the brief, both band views and the Session page say the same.
- **Overlaps:** F003 (left open in the Words tables).

### R2-05 Errors, retries and tokens have nothing to compare to (Medium, 2)

- **Checks:** L4.6.
- **Evidence:** J4 asks to "spot where it struggles". `screens.md` Home and Usage rows: "41k tokens · 2 errors · 1 retry", "Tokens 41k in · 9k out", "Tool errors 2". No total tool calls, no context size, no per-session norm.
- **Fix:** show errors as a share ("2 of 31 tool calls") on the Usage list and keep the bare count on Home only when above a stated share; show tokens against the model's context window or the session's own previous turn. Or drop the claim in J4 to "see the numbers".
- **Overlaps:** none.

### R2-06 No pending state for an ask being classified (Medium, 2)

- **Checks:** B10, L6.3.
- **Evidence:** `screens.md` Ask kinds: "task", "question", "not classified". `interaction.md` Errors: a failed call leaves the ask "not classified", a session without the mod also reads "not classified". The haiku call runs after the owner sends the ask; its duration is unstated.
- **Fix:** add a fourth kind "classifying…" (dim) that persists until the call returns or fails, and a distinct "not classified" for a failed call. State a timeout after which it becomes "not classified".
- **Overlaps:** none.

### R2-07 Two waiting sessions can look identical, and the open-by-text route has no matching rule (Medium, 2)

- **Checks:** L2.4, L24.2, L18.3, B2.
- **Evidence:** Needs you rows show title, repo, wait, reason, with no branch (`screens.md` line 221); the compact band shows repo and title only. Two worktrees on one repo running a session each titled "fix login" read the same. `/tracker session <title or id>` and `/tracker repo <name>` (`interaction.md` line 10) say nothing on case, partial match or several matches; the id is shown nowhere on screen, only inside the copied resume command.
- **Fix:** add the branch to the Needs-you row (it is already on the other two); define the match as case-insensitive substring, one match opens, several open a short list on Home filtered to them, none shows the not-found line; show the short id on the Session page header.
- **Overlaps:** F004-style naming only; the repo-label collision is already handled (`ia.md`, SM-6).

### R2-08 Arrow keys mean three things (Medium, 2)

- **Checks:** L11.2, L15.6.
- **Evidence:** `interaction.md` line 7: "Tab and the arrows walk its buttons". Line 8: "arrows scroll". Elements x Interactions, session row: "Tab and arrows move". On Home the rows are Buttons, so arrows must either move focus or scroll; the text claims both.
- **Fix:** say one rule: Tab and Shift-Tab move focus between buttons; arrows scroll the pane; or arrows move focus and the pane scrolls to keep it in view. Write it in the keyboard paragraph and delete the other two phrases.
- **Overlaps:** none in `conformance.md` (F001 and F012 are about letter hotkeys and Escape).

### R2-09 The only push is a colour change in a band-shaped row (Low, 1)

- **Checks:** L25.3.
- **Evidence:** J10 ("pushed attention, not a list I must poll") is met by "the count turns to the warning colour" in the band (`brief.md` J10; `interaction.md` J10 table, which rejects notifications because "Claude Code already notifies for its own session"). Evidence for J10 is "assumed" in `intent.md`. A fixed row above the prompt that changes colour is what banner blindness and change blindness describe.
- **Why Low:** the host's own per-session notification already covers a session waiting in its own terminal, so the tracker's job is awareness while typing, which a glance meets. The residual risk is the owner away from every terminal.
- **Fix:** none needed for milestone 1. Write the residual risk into the open question so it is revisited with real use. Consider one shared, de-duplicated notifier later, not one per open session.
- **Overlaps:** `interaction.md` Open Questions.

### R2-10 "0 need you" can sit beside finished sessions waiting for review (Medium, 2)

- **Checks:** L17.2 (and L21.3).
- **Evidence:** `ia.md` Open Question 1 decides that a session whose turn ended is "done", not "needs you", so the count stays meaningful. The compact band then shows needs you, running, PRs and work, with no done count; done appears only in the details columns and Home. A session that finished at 14:02 and waits for the owner's review is invisible in compact at 15:30. S3 (review) is a named scene.
- **Fix:** keep the decision, but show a dim "✓ 2 done" segment in compact (it drops with Work at 150 %), or colour it after a stated idle time. Owner confirms at the gate.
- **Overlaps:** `ia.md` Open Question 1.

### R2-11 Pane chrome: first focus stop and position of Back and Close (Medium, 2)

- **Checks:** B13, L7.4.
- **Evidence:** `screens.md` Pane Home Sections: the title row with Close is first, then the sections. `interaction.md` J2: the pane "opens with the keyboard" and the next step is "Enter" on a session row. The spec never says which control holds focus on open; if Close, the first Enter closes the pane. Back, Home and Close are header actions; whether the header stays visible while a long Asks list scrolls is unstated.
- **Fix:** state that on open the first Needs-you row (else the first row, else Close) has focus, and that the header row stays pinned or, if the mod API cannot pin it, that `b`, `h`, `x` are the route and the hint says so.
- **Overlaps:** none.

### R2-12 Glyph without a word on the narrow compact band (Low, 1)

- **Checks:** L14.1, L11.4, B2.
- **Evidence:** `screens.md` Band compact: "4 PRs · 1 ✗" is kept as is "for width"; at 150 % the word "running" drops and leaves "◐ 3" (lines 40, 71, 316). `●` and `◐` are two circles that differ by half a fill. The stated rule "every glyph has a word or a count beside it" is met only by the count. No legend exists anywhere.
- **Fix:** keep "1 failing" or "1 ✗ failing" while the width allows, drop it only below 60 columns; write the glyph meanings in the first-run hint (R2-13).

### R2-13 No in-context hint for the keys, the glyphs or hiding the band (Low, 1)

- **Checks:** L20.3.
- **Evidence:** `screens.md` Words have no hint string. Nothing on screen says `ctrl+x tab` gives the band the keyboard, that buttons have hotkeys (Buttons read "Pane", "Details"), or that `/tracker band off` hides the row. `conformance.md` F011 resolution says the band "says in its hint how to hide itself"; the Words tables do not carry it.
- **Fix:** one dim hint line in the pane footer and the details view: "ctrl+x tab to use the band · /tracker band off to hide it". State the hotkey letter beside each label if the component can draw it.

### R2-14 The same information appears two or three times in one view (Low, 1)

- **Checks:** L19.2, L19.3, L5.1.
- **Evidence:** Session header: title, then a breadcrumb that ends in the title and holds the repo, then a repo button (`screens.md` lines 252, 258, 300). Home: a repo heading under Running, again under Done, and a Repos line, each a button to the same page with the PR count. Repo and Session pages offer both Back and Home, which usually go to the same place. Details header: "agent-tracker-1 … milestone/agent-tracker-1" says the milestone twice. The Done column in the details band has no job story.
- **Fix:** drop the breadcrumb or the title; give the repo one control per view (the Repos line only if a repo has no heading, which `ia.md` F009 already states as the reason); drop the branch from the header when it equals `milestone/<name>`.

### R2-15 Copy resume command has no place on the page (Low, 1)

- **Checks:** L13.4, B8.
- **Evidence:** the Session Controls table lists it with key `r`; the Header Actions, Sections and Layout never place it. It is hidden for a live session; the reason is written in the spec ("would start a second process"), not shown to the owner.
- **Fix:** put it in the Header row with the state line "○ ended 4m ago"; on a live session show a dim line "resume is available once it ends".

### R2-16 Long lists have no total and no stated cut-off cue (Low, 1)

- **Checks:** L3.6, L30.4.
- **Evidence:** Asks "every ask in order, numbered from 1" (a long session can have hundreds); Home sections and Repo "Ended" have no cap; headings read "Needs you", "Running", "Done", "Asks" with no counts.
- **Fix:** counts in headings ("Asks 42"); a stated cap with "show older" for Asks and Ended; a scroll cue if the mod API draws none.

### R2-17 Dim stands for six different things (Low, 1)

- **Checks:** L15.3.
- **Evidence:** dim is used for zero counts ("0 need you"), stale data, loading, done, ended and secondary text (`screens.md` Glyphs, Words, Stale rows). In the Stale state the warning-coloured needs-you count is dimmed, so it reads like a quiet "0".
- **Fix:** keep the last warning colour on a stale needs-you count and add the age; reserve dim for secondary text and zero.

### R2-18 Copy failed is a toast (Low, 1)

- **Checks:** L25.4.
- **Evidence:** `interaction.md` Feedback: Copy success and failure are toasts; "the toast carries nothing the user needs later". A failed copy leaves the old clipboard, and the next paste puts it in a PR or message.
- **Fix:** keep the success toast; show the failure as a line in the band or pane until the next action.

### R2-19 The reason a session waits is shown raw and unbounded (Medium, 2)

- **Checks:** L5.5.
- **Evidence:** `ia.md` State Diagrams: "What `waitingFor` holds (permission or question) is read at build time and shown as the reason when present". `screens.md` line 221 shows "asks permission". `intent.md` Open question 1 says the mapping is unverified. Showing engine text as is can be long or contain an enum key, in the one spot where the Home row has a 68-cell budget.
- **Fix:** map known values to "asks permission" and "asks a question"; show anything else as "needs input", never the raw string; cap at 24 cells.

### R2-20 "Ended" is inferred from absence, and it switches on Copy resume command (Low, 1)

- **Checks:** L17.2.
- **Evidence:** `ia.md`: "a session missing from the list is ended". Resuming a live session starts a second process (the spec's own reason for hiding the button). If the list drops a live session for any reason, the owner is offered the wrong command.
- **Fix:** treat "missing" as ended only after the process id is gone or after two reads; show "ended?" until then.

### R2-22 Design choices to confirm at the gate (0)

- **F006 (L8.4):** the pane always reopens on Home, so a closed Session page is lost; one extra move for S3 against a triage-first entry. Taken in the spec, owner confirms.
- **F005 (L21, L27):** J1 ends at a name; the owner finds the terminal by hand and the tracker cannot switch sessions (N1). Showing the worktree folder on Needs-you rows (R2-07) helps at no cost to N1.
- **Home grouping:** Needs you is flat with the repo on each row; Running and Done sit under repo headings, so scanning changes style between sections. `conformance.md` records it as deliberate.

## What passed and is worth keeping

- **Count first:** the compact line starts with the needs-you count in the warning colour and names the oldest waiting session (L26, L28.2).
- **No primary action:** both band buttons are `plain`, so the count is the one distinctive element (L28.1).
- **Errors read event, consequence, action** in every Words row (B4, L23.2).
- **Observe only holds** in every control: nothing confirms, nothing needs undo (B5, B11).
- **Colour never alone:** every glyph has a word or count beside it, with the one exception in R2-12 (L15.4).
- **Every list has a stated sort**, and the one repo-name collision is handled (L10.2, SM-6).

## Did not run

- Visual, measurement and timing checks (see Method).
- The other two reviewers' lenses (Nielsen, screen critique against the audience): out of scope for this review.
