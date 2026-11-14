# Screens

Terminal first. "100 %" is a terminal at 120 columns (the pane inline, `bodyColumns` about 118, or docked at 54 columns); "150 %" is the same window with a 150 percent font, about 80 columns (docked about 36). The pane keeps one cell of margin on the left. Widths are terminal cells, counted with the string in the Words table (wide glyphs counted as the terminal draws them).

**What this file describes.** The Session page as built (`core/session-model.ts`), which follows the owner's "Session detail" mockup of 2026-11-14, and what this change adds or alters on it; Home as built (`core/pane-model.ts`) plus one line; the band, unchanged; and the transcript surface of the tidy pass. It does not redraw anything the owner approved. Milestone 1's [screens.md](../../2026-11-13-agent-tracker/spec/screens.md) is superseded on the points where the mockups differ from it; this file does not restate those points.

**Keys.** The template asks for a key on every control. The owner banned shown hotkeys on 2026-11-14, so every control's key route is "Tab to it, Enter", and the footer's hint stays "↑↓ move  ⏎ open". Recorded once in conformance.

**A real terminal render.** No page of this change is built, so no terminal render exists. The cell counts below are measured on the strings. The render check at build is: the Session page of an ended session, its confirm-free Clear, its offer, and Home with the Tidy line, each at 120, 80 and 40 columns, with a screenshot of the terminal window.

Glyphs reused: `●` needs you, `◐` running, `✓` done, `○` ended (dim), `✗` failing. `✓` and `✗` also open a result line; every glyph sits beside words.

## Pane, Session

### Purpose

One session: its real age, its tasks, its worktree, and for an ended session the one act the owner came for, Clear (J1, J2, J3, J4, J6).

### Header

| Title | Tabs | Actions |
|---|---|---|
| Crumbs "Home › web-app › fix login redirect" (Buttons for Home and the repo; the title is bold text); the state at the right, "○ ended 63d ago" | none | Back, Close (the footer, right) |

### Sections

Built order, with this change's rows marked. Each is a block of lines; blocks are separated by a dim rule only where the built page has one.

| Order | Section | Purpose |
|---|---|---|
| 1 | Header | Crumbs and state. **Changed:** an ended session reads "○ ended 63d ago" because a row with no `pid` is ended; it no longer reads "● waiting". |
| 2 | Facts | Line 1 **changed**: "branch main  started 12 Sep 16:13  last activity 63d ago" (was "branch main  since 16:13  last activity 63d ago"). Then tokens, struggles, running, as built. |
| 3 | Milestone | as built (sdlc-run sessions only) |
| 4 | Tasks | up to 6 task asks, "and N more". **Changed for an ended session:** only the tasks Home lists for it (the set Clear closes), each with Home's glyph and word (for example red "○ forgotten"); a finished task is not shown. Other sessions: as built. |
| 5 | PR | as built (when the branch has one) |
| 6 | Worktree | **new.** One line: the worktree's label and branch (dim); or, when a condition fails, why it stays (normal weight). When all five conditions hold it adds "Clear offers to remove it." Drawn only when the session's `cwd` is a linked worktree. |
| 7 | Actions | **changed.** Ended sessions: above the buttons, one line saying what Clear will do; then "Copy resume command" (only while the worktree folder exists), then "Clear". After Clear: "Copy resume command", "Reopen tasks". Live sessions: no actions; one reason line instead. |
| 8 | Offer | **new.** Three lines and two buttons, directly under the actions row, after Clear, when a worktree passes all five conditions. It sits above the result lines so it is on screen without scrolling (the pane code sets no height and does not scroll). |
| 9 | Result | **new.** Lines for what the last Clear did (✓ and ✗ lines); "Clearing…"; or "Nothing to clear". Page-local: the lines stay until the owner leaves the page, and survive the 5-second re-read; a fresh visit shows "Nothing to clear". |

### Layout

| Zoom | Columns | Widths | Notes |
|---|---|---|---|
| 100 % (120, inline) | one column | first line 56 cells; reason line 70; success result lines 50 to 53; offer line 1 up to 57, line 2 62, line 3 54; action row 26 (19 + gap 2 + 5); offer buttons 30 (13 + 2 + 15). Error lines run 88 to 117 cells before the reason (which is cut at 60 more). | Everything but an error fits one line in 118 cells. An error wraps to 2 lines at 120 and 3 or more at a dock; it sits in a `wrap` block, so nothing clips. |
| 100 % (docked, 54, 53 usable) | one column | the same strings | Lines marked `wrap` wrap at 53 cells: first line 56 → 2 lines; reason 70 → 2; offer line 1 up to 57 → 2; line 2 64 → 2; a success result fits one line or wraps to 2; an error 3 to 4. The action row (26) and the offer buttons (30) fit. |
| 150 % (about 80, 79 usable) | one column | as 100 % inline | 56, 70, 57, 64 and the success lines fit in 79; an error wraps to 2 lines. The action row fits. |
| 150 % (docked, about 36, 35 usable) | one column | as above | Wrapped lines run to 2 or 3 lines; an error to 4 or 5. Action row 26 fits 35; offer buttons 30 fit 35. |
| all zooms, longer lines added after validation | one column | the line before Clear 87 cells (168 with the worktree sentence); the background reason 87; "Worktree … stays" up to 85; offer line 2 62 | At 120 inline each is one line (the long pre-press form wraps to 2). At 80 and below they wrap in their `wrap` blocks: 2 lines at 54 and 80, 3 at 36. Row count of the Session page at 54 columns docked can reach about 30 lines with tasks, the offer and an error; the pane does not scroll, so the render check must count rows as well as columns, and cut the Tasks list at the window height if the page is taller. |
| narrowest dock (24, so 23 usable) | one column | | The action row (26) and the offer buttons (30) do not fit: they must wrap, one button per line. **Build change:** the actions `Box` in `pane/view.tsx` has no `flexWrap` today; it needs `flexWrap="wrap"`. No button may clip at any width. |

The band is **unchanged at every width**: this change adds no cell, no button and no word to either band view. Milestone 1 measured the compact line at 125 cells needed against 115 at 100 percent; segments still drop in the same order. The needs-you count is shorter by the dead sessions it no longer counts.

### Lists

| List | Columns | Sort | Empty |
|---|---|---|---|
| Tasks | glyph, text (cut to 40), state | newest first, at most 6 | the line is not drawn |
| Result | glyph, words | the order the steps ran: left the list, tasks closed, worktree | not drawn |

### Controls

| Control | Component | Label | Key | Disabled reason | State source |
|---|---|---|---|---|---|
| Reopen tasks | Button, plain | Reopen tasks | Tab to it, Enter | drawn only after a Clear that closed tasks, and only while the owner is on the page | the page's result state |
| Clear | Button, plain | Clear | Tab to it, Enter | not drawn for a live session (a reason line takes its place); not drawn when the session list is unreadable; not drawn when nothing is left to clear | the session's `pid` in the snapshot; the snapshot's freshness; its open tasks; the worktree check |
| Copy resume command | Button, plain | Copy resume command | Tab to it, Enter | not drawn for a live session (milestone 1, F005: resuming a live session starts a second process on it), and not drawn once the session's worktree folder is gone (the command would `cd` into it) | the session's state |
| Remove worktree | Button, plain | Remove worktree | Tab to it, Enter | not drawn unless all five conditions held when the page opened and still hold when it is pressed | the git check |
| Keep worktree | Button, plain | Keep worktree | Tab to it, Enter | never disabled | |
| Back, Close, crumbs | as built | Back, Close | Tab, Enter | as built | the pane's page history |

Ring on opening the page: the first action, which is **Copy resume command** (not Clear): a double Enter that opens the page and then presses a button must not clear. When Copy resume command is not drawn (the worktree folder is gone, common for old sessions) the ring starts on the Home crumb. The ring never starts on Clear or Remove worktree. When the offer appears the ring goes to **Keep worktree**.

### Filters

| Filter | Default | Options | Clear behaviour |
|---|---|---|---|
| none | | | |

### Words

Dates in "started": today `16:13`; yesterday through 6 days back `Tue 16:13`; older `12 Sep 16:13`; older than a year `12 Sep 2025 16:13`. Local time. Durations as milestone 1: "<1m", "6m", "2h 10m", "3d" (days stay days, so 63d, 400d).

| Where | Text |
|---|---|
| State, ended | "○ ended 63d ago" (dim); with no time known "○ ended" |
| Facts line 1 | "branch main  started 12 Sep 16:13  last activity 63d ago" (labels dim, values normal) |
| Reason, interactive with a process | "Clear is for ended sessions. Close its terminal first." (normal weight: it says what to do next) |
| Reason, background with a process | "Clear is for ended sessions. This one is still running. Resume comes back when it ends." (normal weight). The interactive line is "Clear is for ended sessions. Close its terminal first." |
| Worktree line | "worktree login · fix-login" (dim: a fact, not an instruction). The label is the one the Repo page's WORKTREES list shows today (`core/repo-model.ts:103`: the path inside the repo's folder with a leading `.worktrees/` removed, else the folder name); never an absolute path. One helper serves both pages. When all five conditions hold, the line adds "Clear offers to remove it." |
| Worktree stays | "Worktree login stays: it has uncommitted changes. Commit or stash them in a terminal." / "…: it has commits that are not pushed." / "…: its branch is not merged." / "…: another session is using it." (normal weight) |
| Before Clear | built from the parts that apply, in this order, in normal weight: when the session is still in Claude Code's list, "Clear leaves Claude Code's list"; when it has tasks, "closes the 2 tasks above" ("1 task"); then "The conversation is kept." (only when it left the list); when listed and in a linked worktree, "Claude Code also removes a worktree it made for this session, when that is safe." Example, all parts: "Clear leaves Claude Code's list and closes the 2 tasks above. The conversation is kept." When only a removable worktree is left: "Clear offers to remove the worktree below." With nothing left, no line (the Nothing to clear line shows). |
| Actions | "Copy resume command", "Clear"; after Clear "Copy resume command", "Reopen tasks" |
| Clearing | "Clearing…" (dim) |
| Result, left the list | "✓ Left Claude Code's list. The conversation is kept." |
| Result, tasks | "✓ 2 tasks closed." / "✓ 1 task closed." |
| Nothing to clear | "Nothing to clear: it is not in Claude Code's list and has no open tasks." (normal weight) |
| Offer, line 1 | "Worktree login is clean, pushed and merged." / "Worktree login is clean and pushed, and its PR is merged." / "…, and its PR is closed." |
| Offer, line 2 | "Remove it? Ignored files in it, such as .env, are deleted too." |
| Offer, line 3 | "The branch fix-login stays, so you can make it again." |
| Offer buttons | "Remove worktree", "Keep worktree" |
| Removing | "Removing worktree…" (dim) |
| Result, worktree | "✓ Worktree login removed. The branch fix-login stays." and, because the resume command needs the folder: "To resume this conversation, make the worktree again from the branch first." |
| Result, Claude Code removed it | "✓ Claude Code also removed the worktree login." (then the same resume sentence) |
| Result, running again | "This session is running again. Nothing was changed." |
| Result, reopened | "✓ 2 tasks reopened." |
| Refused, unreadable | "Clear waits: Claude Code's session list could not be read. Nothing was changed." (normal weight; the re-read at the press failed) |
| Pid not reported | "Clear waits: Claude Code did not say which sessions have a process." (normal weight; shown when no row in a read carries a `pid`) |
| Error, `claude rm` | "✗ Claude Code could not clear this session: <reason>. Nothing else was changed. Press Clear to try again." |
| `<reason>` in the three error strings | What the command printed, passed through `clean()` (`core/format.ts`): one line, cut at 60 cells. No usable reason: the clause ", <reason>" is dropped. Never a stack trace. |
| Error, save | "✗ The tracker could not close the tasks: <reason>. The session left Claude Code's list. Press Clear to close them." |
| Error, worktree | "✗ Git could not remove the worktree: <reason>. Nothing was lost. Check it in a terminal." |
| Error, changed | "✗ The worktree changed since it was checked: it has uncommitted changes. Nothing was removed. Check it in a terminal." (the reason is one of the four "stays" reasons) |
| List unreadable | "Clear waits: Claude Code's session list could not be read. Retrying every 5 seconds." (normal weight) |
| Toasts | "Resume command copied" (unchanged); no new toast |

### Components

| Region | Component | Status | Notes |
|---|---|---|---|
| Facts, reason, worktree and result lines | Text in a `lines` block (`wrap`) | have | the built `lines` block |
| Actions row | Button, plain (the `actions` block) | have, one change | gains `flexWrap="wrap"` |
| Offer | `lines` block, then an `actions` block | have | the same two blocks, no new component |
| Result glyphs | Text with theme colours (`success` for ✓, `error` for ✗) | have | |
| Started date | `Local` | new variant | `Local` has `midnight`, `clock` and `day` (weekday) only (`core/pane-model.ts:29`); it gains a `date` function for "12 Sep" and "12 Sep 2025". `when()` in `core/pane-model.ts:68` stays for the other pages. |
| Action values | `ActionItem.action` | new variant | the union at `core/pane-model.ts:33` gains `clear`, `reopen`, `remove-worktree`, `keep-worktree`, `tidy` (`reopen` needs a new store write that removes the `closed` marks; `markTask` only adds today); `act()` in `pane.tsx` handles them. Its comment "the only writes" must change (conformance C1). |
| Worktree label | one helper | new variant | extracted from `worktreeItems` (`core/repo-model.ts:103`), used by both the Repo and Session pages. |
| Process fact | `AgentRow.pid` | new variant | `parseAgents` pins the 2.1.323 fields and has no `pid` (`core/states.ts:11`); the row gains `pid?: number`. |

## Pane, Home

### Purpose

The triage queue as built: open tasks first, then needs you, then running, repos. This change fixes what counts as needs you and adds one last line (J1, J5).

### Header

| Title | Tabs | Actions |
|---|---|---|
| "Agent tracker", at the right "5 live · 2 need you" | none | Close (footer) |

### Sections

| Order | Section | Purpose |
|---|---|---|
| 1 to 5 | YOUR TASKS NOT DONE; NEEDS YOU; YOU SHOULD KNOW and DECIDED WITHOUT YOU; RUNNING; REPOS | as built. **Changed:** NEEDS YOU, the right-hand count and the needs-you task rows no longer include a session with no process. |
| 6 | TIDY | **new.** Last block, dim, below REPOS and above "N sessions run without the tracker". Hidden when nothing idle for 30 days or more passes every check. |

### Layout

| Zoom | Columns | Widths | Notes |
|---|---|---|---|
| 100 % (120 inline, or 54 docked) | one column | the TIDY heading and count line: 59 cells in the longest form ("TIDY  12 sessions and 40 worktrees idle for 30 days or more"); the button row below it, 4 | A `lines` block (heading and count, `wrap`) followed by an `actions` block holding Tidy. At 120 the count is one line; docked at 54 it wraps to 2 and the button stays on its own row. An `inline` block cannot carry an action (`Item` opens a page, links out or shows text), so it is not used. |
| 150 % (about 80, docked about 36) | one column | as above | Fits at 80; wraps at 36. The ring still starts on the first row, never on Tidy. |

### Lists

| List | Columns | Sort | Empty |
|---|---|---|---|
| TIDY | heading, count text, button | not a list | the block is not drawn |

### Controls

| Control | Component | Label | Key | Disabled reason | State source |
|---|---|---|---|---|---|
| Tidy | Button, plain | Tidy | Tab to it, Enter | replaced by a dim reason while Claude is replying in this session, or the session list is unreadable | the snapshot: stale items, this session's state, the list's freshness |

### Filters

| Filter | Default | Options | Clear behaviour |
|---|---|---|---|
| none | | | |

### Words

| Where | Text |
|---|---|
| Heading | "TIDY" |
| Count | counts only what tidy can act on (items that pass every check). "5 sessions idle for 30 days or more" / "3 worktrees idle for 30 days or more" / "5 sessions and 3 worktrees idle for 30 days or more"; "1 session", "1 worktree" (dim) |
| Button | "Tidy" |
| Waiting, a reply is running | "Tidy waits until Claude finishes replying in this session." (normal weight, in place of the button) |
| Waiting, list unreadable | "Tidy waits until Claude Code's session list can be read." (normal weight, in place of the button) |

### Components

| Region | Component | Status | Notes |
|---|---|---|---|
| TIDY block | `lines` block (heading and count) then an `actions` block (Tidy) | have | the same two blocks the Session page uses; no new component |

## Band, compact and details

Unchanged. No segment, button or word is added or removed. Its needs-you count and the line naming the oldest waiting session no longer include a session whose row has no `pid`; its task count (the owner's "Your tasks not done" count) falls when tasks are closed. The buttons stay spaced and show no hotkeys. The built band follows the owner's later mockup, not milestone 1's measurements (compact 125 cells needed against 115 at 100 percent); this change does not alter either, so its widths are whatever the built band measures today.

## Transcript, the tidy pass

The surface is the transcript of the session where the owner typed `/tracker tidy`, drawn by Claude Code, not by the mod. The mod writes the answer line to the command; the supervisor (Claude, in that session) writes the rest from the rules below. The prompt that carries these rules is a plan item; this spec fixes what the owner reads.

### Purpose

Resolve everything idle 30 days or more in one pass, ask once per batch, never touch what runs, and say plainly what was kept (J5, J6).

### Header

| Title | Tabs | Actions |
|---|---|---|
| none: the transcript | none | the batch question's options |

### Sections

| Order | Section | Purpose |
|---|---|---|
| 1 | Answer line | The command's answer: started, or why not. |
| 2 | Supervisor line | How many items it checks, one agent each; "nothing that is running is touched". |
| 3 | Batch question: sessions | Only items that passed every check. |
| 4 | Batch question: worktrees | Only items that passed every check. |
| 5 | Report | What was cleared and removed; what is kept and why; what was skipped. |

### Layout

| Zoom | Columns | Widths | Notes |
|---|---|---|---|
| 100 % and 150 % | the host's own | question lines are items of one line each (about 60 cells: "web-app · fix login · idle 41d"); every item listed | The host wraps. |

### Lists

| List | Columns | Sort | Empty |
|---|---|---|---|
| Sessions in a question | repo, title, idle days | oldest first | no question is asked |
| Worktrees in a question | repo, worktree label, branch, idle days | oldest first | no question is asked |
| Kept in the report | name and the reason | by repo | the line is not written |

### Controls

| Control | Component | Label | Key | Disabled reason | State source |
|---|---|---|---|---|---|
| Batch answer | the host's question (options) | "Clear all 5" (recommended) / "Skip these 5"; "Remove all 3" (recommended) / "Skip these 3"; Other for exceptions | the host's keys | none | the checks |

### Filters

| Filter | Default | Options | Clear behaviour |
|---|---|---|---|
| Idle threshold | 30 days | fixed (no argument) | n/a |

### Words

| Where | Text |
|---|---|
| Answer, nothing | "Nothing to tidy. Nothing idle for 30 days is ready to clear." |
| Answer, started | "Tidy started: 5 sessions and 3 worktrees to check. Nothing that is running is touched." |
| Answer, busy | "Tidy waits until Claude finishes replying in this session." |
| Answer, unreadable | "Tidy waits: Claude Code's session list could not be read. Try again in a minute." |
| Supervisor, opening | "Checking 8 items, one agent each to describe it. Nothing that is running will be touched." |
| Question, sessions | "Clear these 5 sessions? Each has been idle 30 days or more and has no ask marked partly done or not started. Claude Code also removes a worktree it made for a session, when that is safe." |
| Question, worktrees | "Remove these 3 worktrees? Each is clean, pushed and merged, and no session is using it. Ignored files in them, such as .env, are deleted too." |
| Question items | every item, one line each, grouped by repo: "web-app · fix login · idle 41d" / "api · users · fix-users · idle 52d". A batch over 25 items splits into batches of 25, each asked once. The owner never answers for an item that is not listed. |
| Option details | "Clear all 5: Leaves Claude Code's list. Conversations are kept." / "Remove all 3: Branches are kept, so each can be made again. Ignored files in them are deleted." / "Skip: Nothing changes." |
| Report, cleared | "Cleared 5 sessions." (counts only what succeeded) |
| Report, failed | "Could not clear: web-app · fix login (<reason>)." |
| Report, removed | "Removed 3 worktrees. Branches kept." |
| Report, kept | "Kept, needs a look: web-app/login (uncommitted changes); api/users (2 commits not pushed)." |
| Report, skipped | "Skipped: docs (a session is running in it)." |
| Report, opening | "Tidy done." |
| Help | "Try /tracker, details, compact, copy, repo, session, tidy, web, band on, band off." |
| Command hint | "details \| compact \| copy \| web \| repo <name> \| session <text> \| tidy \| band on \| band off" |

The rules behind the words (each is a fact the prompt must hold, checked in the plan):

- **Collected:** ended sessions idle 30 days or more for which Clear would still do something; linked worktrees with no live session in them whose idle time is 30 days or more, where idle time is the newest of the branch's last commit, the folder's last change and its sessions' last activity (unknown: not collected, so a worktree made today never is). Only items that pass every check are counted on Home or put in a question. Never a session with a process. A worktree skipped because a session is running in it is named in the report.
- **Checked by code, never by a model:** every condition (process alive via `pid`; worktree clean; commits not pushed; merged, or PR merged or closed; another session using it; for a session, any ask whose last verdict is "partly" or "not started") is computed by the mod's code, the same functions the Session page uses. Subagents may only gather and narrate; a model never decides that something is safe. The supervisor acts through the same checked path.
- **Batches:** "safe" items go in a question; any item that failed a check is "needs a look" and is never removed by tidy, whatever the owner answers. Nothing safe: no question.
- **Acting:** after "Clear all" or "Remove all", item by item, each re-checked right before it acts (the session list re-read for sessions); a failed re-check, or an action that fails, skips that item and names it with the reason. The same limits as Clear: no `--force`, no `-D`, branches kept. Typed exceptions under Other: an unmatched or ambiguous name pauses the batch with "I could not tell which one you meant. Nothing was changed."; the final list ("Clearing 4, keeping 1: web-app · fix login") is shown before acting. `/tracker tidy <anything>` answers "Tidy takes no number: it always uses 30 days."

### Components

| Region | Component | Status | Notes |
|---|---|---|---|
| Answer line | the command's `{ text }` answer | have | `pane.tsx:115` answers the same way |
| Questions | the host's question dialog | have (host) | the tracker draws nothing |

## Words index (strings added or changed)

Every string above becomes a constant in `core/words.ts` at build: `COMMAND_HELP`, `COMMAND_HINT`, a `HEADINGS.tidy` entry ("TIDY"), a `PANE_BUTTONS` entry for Clear, the offer buttons and Tidy, `REASON`-style constants for the two live reason lines, and the started-date format. The existing `COMMAND_HELP` and `COMMAND_HINT` in `core/words.ts:56`, `:61` gain the word `tidy`.
