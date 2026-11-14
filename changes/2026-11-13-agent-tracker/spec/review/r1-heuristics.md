---
type: ux-spec-review
reviewer: r1-heuristics
lens: Nielsen's ten heuristics, severity 0-4
change: 2026-11-13-agent-tracker
spec: brief, ia, sitemap, interaction, screens, conformance (text only, no images)
created: 2026-11-13
---

# Reviewer 1: heuristic evaluation

Text only: nothing is built and no prototype image exists, so every "Verified" line is "read in the files" or "assumption, not checked". Method: walked S1, S2 and S3 and the flows J1, J2, J4, J6, J10, J11 as a first-time and as a returning user, named the heuristic per stumble, rated frequency, impact and persistence. Items `conformance.md` resolved (F001 to F016) are not re-raised unless the fix is wrong or incomplete; R2 is the one case where a fix is incomplete.

Contradictions between spec files are rated 3 under the brief's rule; where the practical effect is smaller, the entry says so.

## Count

| Severity | Count |
|---|---|
| 4 Critical | 0 |
| 3 High (3 findings, 9 contradictions) | 12 |
| 2 Medium | 11 |
| 1 Low | 8 |
| 0 Design choice | 0 |

## Severity 3 findings

### R1: The "needs you" boundary is ambiguous, and the whole product rests on it
- **Impact:** High · J1, J5 and J10 are only as good as the count; a session that stopped and waits for the next prompt shows as "done", dim, and the band can say "0 need you" while four sessions sit stopped.
- **Current experience:** `ia.md` maps `waiting` and `blocked` to needs you and `idle` to done (State Diagrams). Its Open Question says needs you is "a permission prompt or a question the session asked". A question asked in plain text ends the turn, so the engine reports `idle`: the spec counts it as done. `docs/ux/setup.md` scene S2 reads "several sessions have stopped; decides which to answer first", which is the sessions the spec files under Done. `intent.md` Open Question 1 says which engine state means a permission prompt is unverified. The success measure compares the running count with `claude agents --json`, the same source the band reads, so it cannot show the needs-you count is right.
- **Heuristic:** 2 (match with the real world: to the owner "needs me" is anything waiting on them), 1 (status: the one number the band exists for may be wrong).
- **Recommendation:** Decide the boundary with the owner before build, in two parts. (a) Verify `waiting`, `blocked` and `waitingFor` on a live session. (b) Decide what a finished turn is: keep it "done" but give it its own visible count in the band ("2 done"), or count turns that end in a question. Add a success measure that checks needs-you against a by-hand check, not only running.
- **Tradeoff:** A "done" count adds width to a full line; counting finished turns makes the main number high.
- **Decision needed:** Is a session that finished its turn and waits for your next prompt "needs you", "done", or its own count?
- **Verified:** read in the files; engine behaviour assumption, not checked.
- **Owner's words:** "which agent needs attention"; the research note on blocked sessions missed for ten minutes (intent Problem).
- Where: `ia.md:98`, `ia.md:203`, `docs/ux/setup.md:18`, `intent.md:102`, `intent.md:59`. Broken: heuristics 1 and 2; job J1.

### R2: The J1 fix (F005) does not help the case J1 is about
- **Impact:** High · the owner reads "web-app: fix login 6m" on the band and has no stated way to find that session; the one control added for this (Copy resume command) exists only for ended sessions, and a session that needs you is live by definition.
- **Current experience:** `ia.md:189` says the band names the session "by its title, which is the title of its Claude Code tab". Nothing in the spec checks that the tab shows that title (the owner runs terminals in worktree tabs, so a tab may show a folder or branch, not a title). The compact needs-you segment shows repo and title only: two sessions in one repo with similar auto-titles look the same, and branch or worktree is not shown until the Home row. The live Session page offers no hint on how to reach the session.
- **Heuristic:** 7 (efficiency: the most frequent job ends in a dead end), 6 (recognition: the owner must recall which terminal), 10 (no help on the page that names the problem).
- **Recommendation:** Verify what the tab title is before the string is fixed. Add the worktree folder label (and branch when it fits) to the needs-you segment and to the Session header, and a dim line on a live waiting session's page, such as "Switch to the terminal named <title>". Observe-only holds: it is text.
- **Tradeoff:** More width in the band, one more line on the page.
- **Decision needed:** Which handle names a session in the band: title, worktree folder, or both?
- **Verified:** read in the files; the tab-title claim is an assumption, not checked.
- **Owner's words:** "which agent needs attention" (owner-words, "What the tracker is for").
- Where: `ia.md:189`, `screens.md:288`, `screens.md:66-68`, `conformance.md` F005 resolution. Broken: heuristics 6 and 7. Rung: not settled by an accepted rule.

### R3: Home is a dead end for the end-of-day review (S3), and ended sessions are four moves away
- **Impact:** High · S3 is "after a run or at the end of the day, reads what was asked, done and decided"; by then the sessions have ended, and Home shows none of them.
- **Current experience:** `ia.md:194` keeps ended sessions off Home. They live under "Ended" on the Repo page, reached from Home's Repos line (F009 fix). `interaction.md:126` says the Empty state (no live session but this one) shows "one line": that state has no Repos line, and this session itself is not listed, so the owner alone at the end of the day has no control on Home to reach a repo or a session. The journey table (`ia.md:159`) claims J2 takes 2 moves; for an ended session it takes Pane, Repos entry, Ended row: 3 moves plus the open, and only when Repos is shown. `/tracker repo <name>` needs the owner to remember the name.
- **Heuristic:** 7 (a daily job has no fast path), 3 (the page offers no exit from an empty state), 6 (recall of the repo name).
- **Recommendation:** Show the Repos line in every Home state, including Empty. List this session on Home as a row. Add a "Recent" section (ended in the last 24 hours, capped) so S3 starts on Home; correct the journey table.
- **Tradeoff:** A longer Home; "Recent" competes with the live queue (keep it last and collapsed past 5 rows).
- **Decision needed:** Do ended sessions of the last day appear on Home, or only under their repo?
- **Verified:** read in the files.
- **Owner's words:** no earlier request found.
- Where: `interaction.md:126`, `ia.md:159`, `ia.md:194`, `screens.md:227`. Broken: heuristics 3 and 7; scene S3.

## Contradictions between spec files (severity 3 by the brief's rule)

### C1: Session page section order
- **Impact:** High (contradiction rule) · a builder follows one file and ships the other order.
- **Current experience:** `interaction.md:29` says the Asks section "is first after the header" and `ia.md:91-92` ranks asks 1 and running now 2. `screens.md:254-262` and `interaction.md:134` put Running now (2) before Asks (3).
- **Recommendation:** Pick one. Asks first suits J2 (the page's main job); Running now is hidden when nothing runs, so it costs little above the asks only when a goal runs. Fix `ia.md` rank or `screens.md` order to match.
- **Decision needed:** Routine fix once the order is chosen. **Verified:** read in the files.
- Where: `interaction.md:29,134`, `ia.md:91-92`, `screens.md:254-262`.

### C2: Do the arrow keys scroll or move focus in the pane?
- **Impact:** High (contradiction rule) · decides whether a keyboard user can reach rows at all.
- **Current experience:** `interaction.md:8` and `:183` say arrows scroll; `interaction.md:7` says Tab and the arrows walk a band's buttons; `interaction.md:180` says on a Home row "Tab and arrows move".
- **Recommendation:** State once: Tab and Shift+Tab move focus, arrows scroll the pane (or move focus when a row is focused). With 20 rows on Home, say how a keyboard user jumps to a section (for example the first row of each section).
- **Decision needed:** Routine fix. **Verified:** read in the files.
- Where: `interaction.md:7,8,180,183`.

### C3: Which Home rows show tokens, errors and retries (J4)
- **Impact:** High (contradiction rule) · J4, "spot where a session struggles", is met only for running rows.
- **Current experience:** `brief.md:41`, `ia.md:87` and `interaction.md:44` say each row shows tokens, and errors and retries when above zero. `screens.md:194-198` and the Words rows (`screens.md:221-223`): the Needs you row has none of the three, the Done row has tokens only, only Running shows errors and retries. A session that struggled and finished shows no errors on Home.
- **Recommendation:** Show errors and retries (when above zero) on every row kind; tokens may stay off Needs you.
- **Decision needed:** Routine fix. **Verified:** read in the files.
- Where: `brief.md:41`, `ia.md:87`, `interaction.md:44`, `screens.md:194-198,221-223`.

### C4: The compact band's "first segment" and the repo in sdlc-run mode
- **Impact:** High (contradiction rule); practical effect Medium · J7 ("tell sessions apart at a glance") is only partly met on the line that is always visible.
- **Current experience:** `ia.md:157` (journey J7) says "compact keeps the repo and work in its first segment". After F016 the first segment is Needs you and Work is fourth and first to be cut (`screens.md:25-31`, `ia.md:79`). The sdlc-run Work sample, "agent-tracker-1 2/4 · goal 14m" (`screens.md:72`), has no repo name; the non-sdlc sample has one. `brief.md:44` promises the repo in the band header.
- **Recommendation:** Rewrite the journey row, and decide whether the sdlc-run Work segment carries the repo (it is the first thing cut, so say what stays when it is cut: at 75 cells the session names nothing).
- **Decision needed:** Routine fix for the row; owner choice for what stays at 75 cells. **Verified:** read in the files.
- Where: `ia.md:157`, `screens.md:25-31,72`, `brief.md:44`.

### C5: "feature 2 of 4" against "2/4", and what the fraction means
- **Impact:** High (contradiction rule); practical effect Medium · "2/4" reads as "2 done of 4" while "feature 2 of 4" means "working on the second", and the conformance fix (F003: "feature 2 of 4 where it fits, 2/4 only as the width fallback") was marked fixed but is not in `screens.md`.
- **Current experience:** `brief.md:40,44` and `interaction.md:36` say "feature 2 of 4"; `screens.md:72` and `:139` say "2/4" in both views, with no word. The details header also shows the milestone name twice ("… · agent-tracker-1 · 2/4 · milestone/agent-tracker-1").
- **Heuristic:** 2 (a bare fraction), 4 (two spellings), 8 (repeated name).
- **Recommendation:** "feature 2 of 4" in details, "2/4" in compact with the meaning defined (current feature number, not completed count) in `screens.md`; drop the branch when it only repeats the milestone name.
- **Decision needed:** Routine fix; define the number first (is feature 2 the one building, or two complete?). **Verified:** read in the files.
- Where: `brief.md:40,44`, `interaction.md:36`, `screens.md:72,139`, `conformance.md` F003.

### C6: The "without bd" state exists in three files and in none of the screens
- **Impact:** High (contradiction rule) · a builder cannot tell what a missing `bd` looks like, or where `bd` data appears at all.
- **Current experience:** `docs/ux/setup.md:82` and `sitemap.md:75` list a Repo state "without bd"; `interaction.md:127` makes Home Partial "gh or bd missing". `screens.md:229` (Partial) and the Repo Words (`:386-387`) mention gh only, and no Repo or Home section shows anything from `bd`.
- **Recommendation:** Either say what `bd` adds in milestone 1 and write its missing state, or remove `bd` from the states and the Partial condition (intent lists it as polled).
- **Decision needed:** Routine fix. **Verified:** read in the files.
- Where: `docs/ux/setup.md:82`, `sitemap.md:75`, `interaction.md:127,144-147`, `screens.md:229,386-387`.

### C7: What "stopped" sessions are (S2) against the state mapping
- **Impact:** High (contradiction rule) · see R1; recorded separately so the setup file is corrected whichever way R1 goes.
- **Current experience:** `docs/ux/setup.md:18` S2: "several sessions have stopped; decides which to answer first". `ia.md:98` maps a stopped turn (`idle`) to done, outside the needs-you queue.
- **Decision needed:** answered by R1. **Verified:** read in the files.
- Where: `docs/ux/setup.md:18`, `ia.md:98,203`.

### C8: "Redraw only when data changes" against counters that change with time
- **Impact:** High (contradiction rule); practical effect Low to Medium · every "6m", "goal 14m" and Home's "updated 3s ago" changes without data changing.
- **Current experience:** `interaction.md:11` says the band and pane "redraw when the data changes, never more often". `screens.md:219` shows "updated 3s ago" and every row carries a running duration. Either they redraw each second or minute (breaking the rule, and causing focus or scroll jitter in the pane) or they go stale.
- **Recommendation:** Rule: durations redraw once a minute, "updated Ns ago" is either dropped or redrawn every 5 seconds with the read, and a redraw never moves focus or scroll.
- **Decision needed:** Routine fix. **Verified:** read in the files.
- Where: `interaction.md:11`, `screens.md:219`, Words rows with a duration.

### C9: What the compact band shows when it is the only session
- **Impact:** High (contradiction rule); practical effect Low.
- **Current experience:** `screens.md:75` says "only this session is running" replaces Running and PRs, so Needs you and Work stay. `interaction.md:101` says Alone shows "the work segment and a dim note", with no needs-you segment. This session can need the owner (state "this session").
- **Recommendation:** Keep the needs-you segment in Alone, as in `screens.md`; correct `interaction.md`.
- **Decision needed:** Routine fix. **Verified:** read in the files.
- Where: `screens.md:75`, `interaction.md:101`.

## Severity 2 findings

### R4: The live list re-sorts under the focused row
- **Impact:** Medium · the owner presses Enter on a row that has just moved and opens a different session (a slip), or the row they were reading jumps sections when its state changes.
- **Current experience:** Home is sorted by state and wait and regrouped by repo (`screens.md:194-198`), refreshed every 5 seconds. Nothing says focus follows the item or stays on the position. Back restores "the focused row" (`ia.md:174`), which is undefined once the list changed.
- **Heuristic:** 5 (slip), 1 (the screen changes without a cue). Frequency: every triage; persistence: every time.
- **Recommendation:** Focus follows the session id, not the position; a row that changes section keeps focus; when the focused row leaves the list, focus goes to its section heading.
- **Tradeoff:** The list may scroll while read.
- **Decision needed:** Routine fix. **Verified:** assumption, not checked (the mod API's re-render behaviour).
- Where: `screens.md:194-198`, `interaction.md:11`.

### R5: Done, Repos and worktree lists have no cap and no ageing
- **Impact:** Medium · every session whose turn ended stays in Done for as long as Claude Code lists it (a session left idle for days), and the Repos line lists every repo of the last 7 days; in a 24 to 54 column dock that wraps over several lines and sits last, below all rows.
- **Current experience:** `screens.md:179-180`, `:197-198`. The Repo page's Worktrees list shows every worktree, including those with no session (Orca creates many).
- **Heuristic:** 8 (the triage queue is buried under the done list), 7.
- **Recommendation:** Cap Done at about 5 rows with "N more" (a button), age sessions idle past a stated time (say 24 hours) into Recent (see R3), put Repos as one row per repo only after the sections, and hide worktrees with no session behind "N without sessions".
- **Tradeoff:** More states.
- **Decision needed:** Which age limit moves a done session off the main list? **Verified:** read in the files.
- Where: `screens.md:172-181,197-198,359`.

### R6: The ask row has no room at docked widths
- **Impact:** Medium · the text of the ask is the point of J2, and gets the leftover cells.
- **Current experience:** "Ask row: number 3, kind 9, status 13, text rest" (`screens.md:268`) is 25 cells before any text, at "dock 24 to 54 columns" (`screens.md:189`): at a typical 40-cell dock the text has 15 cells, at 24 it has none. Home got a two-line threshold (F002); the Session page did not. Only the 150 % row has the two-line form.
- **Heuristic:** 8, 4 (Home and Session handle narrow differently).
- **Recommendation:** Same rule as Home: below 70 columns the ask row is two lines (number, kind and status first; text wrapped below).
- **Decision needed:** Routine fix. **Verified:** measured on the spec's strings.
- Where: `screens.md:189,266-269`.

### R7: Ask text and ask count are unbounded, and push Milestone and Usage out of reach
- **Impact:** Medium · a pasted log is one "ask"; a 40-prompt session makes the page scroll for pages, with Milestone (J3) and Usage (J4) at the bottom, and the newest ask (the most useful for "where is it now") last.
- **Current experience:** `screens.md:273-277,309`: every ask, oldest first, text "wrapped", no cut and no section jump.
- **Heuristic:** 8, 7 (no fast path to a section).
- **Recommendation:** Show the first two lines of each ask with "more" as a button; start the list at the newest 10 with "earlier asks" above (the order stays oldest-first); put Milestone and Usage before the Asks when they are short, or give each section a hotkey.
- **Tradeoff:** More controls on a page.
- **Decision needed:** Is oldest-first with a cap enough, or newest-first? **Verified:** read in the files.
- Where: `screens.md:254-262,273-277`.

### R8: A hidden band leaves no sign on screen of how to get it back
- **Impact:** Medium · `/tracker band off` hides the band in every session at once and forever, and J10's attention channel with it, and nothing on screen says so.
- **Current experience:** The Hidden state is "no tracker row" (`interaction.md:104`); `conformance.md` F011 asked that the band's hint say how to hide itself; no string for it exists in `screens.md`. The flag is machine-wide (`ia.md:185`), so one command silences every session. Home does not show that the band is off.
- **Heuristic:** 1 (status), 3 (the way back is recall), 10 (help).
- **Recommendation:** Add a Words string for the hint (a dim "/tracker band off hides this" in the details view only) and, when hidden, one dim line on Home: "The band is hidden. Run /tracker band on to show it."
- **Tradeoff:** One more line.
- **Decision needed:** Routine fix. **Verified:** read in the files.
- Where: `interaction.md:104,203`, `screens.md` (no string), `conformance.md:291`.

### R9: Hotkeys and the way into the keyboard ring are not visible
- **Impact:** Medium · `ctrl+x tab`, `p`, `d`, `c`, `b`, `h`, `x` and `r` do not appear in any label (Buttons read "Pane", "Details", "Back"), so a hotkey nobody sees is not a shortcut; the daily keyboard user has to learn them from the spec.
- **Current experience:** `screens.md` Buttons rows; `interaction.md:7`.
- **Heuristic:** 6, 7, 10.
- **Recommendation:** Show the letter in the label when width allows ("Pane p"), and name `ctrl+x tab` once, in the details view's dim hint (or the pane's footer).
- **Tradeoff:** Eight cells of width in the compact band; the 150 % drop order must then count it.
- **Decision needed:** Does the mod's `Button` already draw its hotkey? Check the types; if yes, no change. **Verified:** assumption, not checked.
- Where: `screens.md:78,150,315`, `interaction.md:7`.

### R10: `/tracker` arguments: several matches, bad words, no usage line
- **Impact:** Medium · the menu route for every action is a typed command, and its failure cases are mostly missing.
- **Current experience:** Errors list only "matched nothing" (`interaction.md:229`). Two sessions titled "fix login", or two repos with the label `web-app` (the spec disambiguates the label, not the argument, `ia.md:195`), match twice. An unknown word (`/tracker foo`) and `/tracker help` have no behaviour; no screen lists the arguments.
- **Heuristic:** 5, 9, 10.
- **Recommendation:** On several matches open Home with the matching rows listed; on an unknown word show one line with the arguments ("Try /tracker, details, compact, copy, repo, session, band on, band off."); accept the disambiguated label as an argument.
- **Tradeoff:** Two more states in `interaction.md`.
- **Decision needed:** Routine fix. **Verified:** read in the files.
- Where: `interaction.md:10,229`, `ia.md:195`.

### R11: The scope of "4 PRs · 1 ✗" is not stated
- **Impact:** Medium · on a team repo the count and the red "1 failing" on every prompt of every session may be other people's pull requests.
- **Current experience:** `ia.md:78` and `screens.md:29` say "open PRs across repos with sessions"; the Repo page lists "each PR" with the session on its branch; J11 (`brief.md:48`) asks for "each PR's state next to its session". All open PRs and PRs on session branches are different numbers, and the owner works in team repos.
- **Heuristic:** 2 (what the count means), 8 (noise on the always-on line).
- **Recommendation:** Decide the scope in the spec: the band counts the owner's open PRs (or those on session branches); the Repo page lists all, with the owner's first.
- **Tradeoff:** An author filter costs a `gh` call per repo.
- **Decision needed:** Whose PRs does the band count? **Verified:** read in the files.
- Where: `screens.md:29,71`, `ia.md:78`, `brief.md:48`.

### R12: Identity fallbacks are missing: no title, no repo, no branch
- **Impact:** Medium · a new session has no title until its first prompt, a session started outside a git repository has no repo, a detached HEAD has no branch; the rows and the band segment are written as if all three always exist.
- **Current experience:** `ia.md:195` defines repo identity as the git top-level path. `screens.md` Words give no sample for an untitled session ("fix login redirect" is always present), and "No asks yet" is the only no-prompt string.
- **Heuristic:** 1, 2 (a blank row looks broken).
- **Recommendation:** Add fallbacks to the Words: "untitled session" (with its folder name), "no repo" grouped under the folder, "detached HEAD" for the branch.
- **Tradeoff:** None.
- **Decision needed:** Routine fix. **Verified:** read in the files.
- Where: `screens.md:62-78,214-231`, `ia.md:195`.

### R13: The compact band gives no sign that the PR segment is missing
- **Impact:** Medium · when `gh` fails the band drops the PR segment and says nothing (`interaction.md:102`, "as All quiet"); the owner reads the absence of "1 ✗" as "no failing PRs". It is also unsaid whether zero PRs shows "0 PRs" or hides the segment, so the two cases look the same.
- **Heuristic:** 1 (a silent failure that looks like success), 9.
- **Recommendation:** A dim "PRs: gh unavailable" (cut first at narrow widths) in Partial; state the zero case.
- **Tradeoff:** Seven more cells that most days are noise; show it only while Partial.
- **Decision needed:** Routine fix. **Verified:** read in the files.
- Where: `interaction.md:102`, `screens.md:29,71`.

### R14: "Question" means two things
- **Impact:** Medium · an ask of kind "question" (the owner asked something) and a session that "asks a question" (needs you) use one word in both directions, the same defect the spec fixed for "done".
- **Current experience:** `ia.md:33` defines question as the owner's ask kind; `ia.md:203` defines needs you as "a question the session asked"; Ask status "needs you" sits beside kind "question" in one ask row (`screens.md:306-307`).
- **Heuristic:** 2, 4.
- **Recommendation:** Keep "question" for the owner's asks; name a session's question "asks you" (the Home row already says "asks permission") and add both to the alias table.
- **Tradeoff:** None.
- **Decision needed:** Routine fix. **Verified:** read in the files.
- Where: `ia.md:33,203`, `screens.md:221,306-307`.

## Severity 1 findings

### R15: Escape may collide with Claude Code's own double Escape
- **Impact:** Low · at an empty idle prompt, a second Escape closes the pane (`interaction.md:9`); Claude Code may use that gesture itself. **Verified:** assumption, not checked (mod API gives `closeOnEscape`, nothing on precedence). **Fix:** confirm at build; the Close button and `ctrl+x x` stay the primary routes. Where: `interaction.md:9`.

### R16: The details view is one setting for the whole machine, and bands stack
- **Impact:** Low · toggling Details in one session grows the band to about five rows in every session, including small terminal tiles, and with ponytail's own details view on, ten rows sit above the prompt. **Fix:** keep per-machine as decided (A6) but let the narrow rule fold the tracker's details to compact below a stated terminal height. Where: `ia.md:185,191`, `screens.md:88-158`.

### R17: Details columns at 150 % cut the line the owner reads
- **Impact:** Low · four columns of about 16 cells cut "web-app: fix login 6m" (21 cells) with no drop order for the column line, where the compact band cuts the title down to the repo. **Fix:** the same rule: repo first, then wait. Where: `screens.md:113`.

### R18: One glyph, two meanings; an arrow for "mergeable"
- **Impact:** Low · `✓` is a done session and "✓ checks pass"; `↓` for "mergeable" does not suggest merge. Words sit beside each, so the harm is small. **Fix:** a different glyph for done or leave it with words only. Where: `screens.md:5,223,385`.

### R19: No rule for duration formats
- **Impact:** Low · "6m", "3m ago", "2d ago" are shown; 90 minutes, 26 hours and seconds are not defined, and a count beside a wait ("goal 14m") will meet "1h 12m" in a 36-cell budget. **Fix:** one rule in `screens.md` (seconds under 1 minute, then minutes, then "1h 12m", then days). Where: `screens.md` Words.

### R20: The Markdown that Copy produces is not specified
- **Impact:** Low · F4 (copy the state and paste elsewhere) names no content: sections, whether titles and branches are included, or a length limit; the toast is the only visible result. **Fix:** one sample in `screens.md`. Where: `screens.md:148`, `docs/ux/setup.md` F4.

### R21: J10 "pushed attention" rests on an unverified claim
- **Impact:** Low · the spec rules out a notification because "Claude Code already notifies for its own session" (`interaction.md:78`), a premise nobody checked; the band is a passive display, and `intent.md` marks J10 "assumed". It becomes Medium if the owner turns terminal notifications off. **Fix:** verify the premise at build and keep Open Question 1 live. Where: `interaction.md:78,235`, `intent.md:51`.

### R22: Setup file lists a single hard rule against two Safety lines
- **Impact:** Low · `docs/ux/setup.md:96` and `:98` both govern writes; the clipboard copy of a resume command (a local path) and the settings file are the only outputs, and neither is named under Safety. **Fix:** one line naming the clipboard as an allowed output. Where: `docs/ux/setup.md:94-98`.

## Checked and clean

- **Observe only:** no control writes to a session, agent, git, gh or bd (heuristic 3 needs no undo and 5 needs no confirmation).
- **Back and exits (3):** every pane page has Back or Close, Back is history-based, Escape steps up one level.
- **Error shape (9):** each error reads event, consequence, action; no codes; the stale state keeps the last data with its age.
- **Colour (4, 8):** theme colours only, each glyph beside a word or count, sentence case, no exclamation marks.
- **Navigation (4):** one canonical page per object; breadcrumb and Home button on every pane page below Home.
- **Naming (2):** the alias table is consistent apart from R14; "needs you", "ask" and "session" match the owner's words.

## Not run

- **Visual pass, contrast, target sizes:** no images; WCAG scope not accepted.
- **Walkthrough on a running build:** nothing exists.
