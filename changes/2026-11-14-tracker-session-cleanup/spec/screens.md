# Screens

Terminal first. "100 %" is a terminal at 120 columns (the pane inline, `bodyColumns` about 118, or docked at 54 columns); "150 %" is the same window with a 150 percent font, about 80 columns (docked about 36). The pane keeps one cell of margin on the left. Widths are terminal cells, counted with the string in the Words table (wide glyphs counted as the terminal draws them).

**What this file describes.** The Session page as built (`core/session-model.ts`), which follows the owner's "Session detail" mockup of 2026-11-14, and what this change adds or alters on it; Home as built (`core/pane-model.ts`), changed only in its counts; the band, unchanged; and the conversation of the skill `git-cleanup-run`. It does not redraw anything the owner approved. Milestone 1's [screens.md](../../2026-11-13-agent-tracker/spec/screens.md) is superseded on the points where the mockups differ from it; this file does not restate those points.

**Keys.** The template asks for a key on every control. The owner banned shown hotkeys on 2026-11-14, so every control's key route is "Tab to it, Enter", and the footer's hint stays "↑↓ move  ⏎ open". Recorded once in conformance.

**A real terminal render.** No page of this change is built, so no terminal render exists. The cell counts below are measured on the strings. The render check at build is: the Session page of an ended session, its Clear confirm, its offer and Home, each at 120, 80, 54 and 40 columns and a 24-column dock, with a screenshot of the terminal window.

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
| 7 | Actions | **changed.** Ended sessions: "Copy resume command" (only while the worktree folder exists), then "Clear"; when only a removable worktree is left, one line above them says Clear offers to remove it. After Clear: "Copy resume command", "Reopen tasks". Live sessions: no actions; one reason line instead. |
| 7b | Confirm | **new.** Replaces the actions row when Clear is pressed and Clear would write something. A question line, up to three lines saying what will happen, then two buttons, "Clear session" and "Cancel". Focus is on Cancel. Cancel puts the actions row back. Nothing is written until Clear session is pressed. |
| 8 | Offer | **new.** Two or three lines and two buttons, directly under the actions row, after Clear, when a worktree passes all five conditions: its state, the ignored files it would delete (a line only when there are any), and the question. It sits above the result lines so it is on screen without scrolling (the pane code sets no height and does not scroll). |
| 9 | Result | **new.** Lines for what the last Clear did (✓ and ✗ lines); "Clearing…"; or "Nothing to clear". Page-local: the lines stay until the owner leaves the page, and survive the 5-second re-read; a fresh visit shows "Nothing to clear". |

### Layout

| Zoom | Columns | Widths | Notes |
|---|---|---|---|
| 100 % (120, inline) | one column | first line 56 cells; reason line 70; success result lines 50 to 53; confirm lines 19, 58, 78 and 60; offer line 1 up to 57, ignored-files line up to 94, last line 64; action row 26 (19 + gap 2 + 5); confirm buttons 21 (13 + 2 + 6); offer buttons 30 (13 + 2 + 15). Error lines run 88 to 117 cells before the reason (which is cut at 60 more). | Everything but an error fits one line in 118 cells. An error wraps to 2 lines at 120 and 3 or more at a dock; it sits in a `wrap` block, so nothing clips. |
| 100 % (docked, 54, 53 usable) | one column | the same strings | Lines marked `wrap` wrap at 53 cells: first line 56 → 2 lines; reason 70 → 2; confirm line 3 (78) → 2; offer line 1 up to 57 → 2; ignored-files line up to 94 → 2; last line 64 → 2; a success result fits one line or wraps to 2; an error 3 to 4. The action row (26), the confirm buttons (21) and the offer buttons (30) fit. |
| 150 % (about 80, 79 usable) | one column | as 100 % inline | 56, 70, 57, 64, the confirm lines and the success lines fit in 79; the ignored-files line (94) and an error wrap to 2 lines. The action row fits. |
| 150 % (docked, about 36, 35 usable) | one column | as above | Wrapped lines run to 2 or 3 lines; an error to 4 or 5. Action row 26 fits 35; confirm buttons 21 fit 35; offer buttons 30 fit 35. |
| all zooms, longer lines added after validation | one column | the confirm's longest line 78 cells; the background reason 87; "Worktree … stays" up to 85; the offer's ignored-files line up to 94 | At 120 inline each is one line. At 80 and below they wrap in their `wrap` blocks: 2 lines at 54 and 80, 3 at 36. Row count of the Session page at 54 columns docked can reach about 30 lines with tasks, the offer and an error; the pane does not scroll, so the render check must count rows as well as columns, and cut the Tasks list at the window height if the page is taller. |
| narrowest dock (24, so 23 usable) | one column | | The confirm buttons (21) fit 23. The action row (26) and the offer buttons (30) do not fit: they must wrap, one button per line. **Build change:** the actions `Box` in `pane/view.tsx` has no `flexWrap` today; it needs `flexWrap="wrap"`. No button may clip at any width. |

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
| Clear | Button, plain | Clear (opens the confirm) | Tab to it, Enter | not drawn for a live session (a reason line takes its place); not drawn when the session list is unreadable; not drawn when nothing is left to clear | the session's `pid` in the snapshot; the snapshot's freshness; its open tasks; the worktree check |
| Clear session | Button, plain | Clear session | Tab to it, Enter | drawn only inside the confirm; the process fact is re-read when it is pressed | the page's confirm state |
| Cancel | Button, plain | Cancel | Tab to it, Enter | never disabled | |
| Copy resume command | Button, plain | Copy resume command | Tab to it, Enter | not drawn for a live session (milestone 1, F005: resuming a live session starts a second process on it), and not drawn once the session's worktree folder is gone (the command would `cd` into it) | the session's state |
| Remove worktree | Button, plain | Remove worktree | Tab to it, Enter | not drawn unless all five conditions held when the page opened and still hold when it is pressed | the git check |
| Keep worktree | Button, plain | Keep worktree | Tab to it, Enter | never disabled | |
| Back, Close, crumbs | as built | Back, Close | Tab, Enter | as built | the pane's page history |

Ring on opening the page: the first action, which is **Copy resume command** (not Clear): a double Enter that opens the page and then presses a button must not clear. When Copy resume command is not drawn (the worktree folder is gone, common for old sessions) the ring starts on the Home crumb. The ring never starts on Clear, Clear session or Remove worktree. When the confirm appears the ring goes to **Cancel**, the second button, so a stray Enter (a double Enter, a held key) cancels and never clears; after Cancel the ring returns to Clear, because the press that matters now is Clear session. When the offer appears the ring goes to **Keep worktree**.

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
| Clear, only a worktree left | "Clear offers to remove the worktree below." (normal weight, above the actions; Clear writes nothing then and opens the offer, which is its own confirm). With nothing left, no line (the Nothing to clear line shows). |
| Confirm, question | "Clear this session?" (normal weight) |
| Confirm, what happens | built from the parts that apply, in this order, normal weight: when the session is still in Claude Code's list, "It leaves Claude Code's list"; when it has tasks, "and closes the 2 tasks above" ("1 task"), or "It closes the 2 tasks above." when it is not listed. Example, all parts: "It leaves Claude Code's list and closes the 2 tasks above." (The tasks are named on the Tasks line above, as the page lists them.) |
| Confirm, worktree | "If it made the worktree login, Claude Code also removes it, when that is safe." (only when the session is listed and in a linked worktree; Claude Code decides, so the line says "if") |
| Confirm, kept | "The conversation is kept. The list entry does not come back." (only when it leaves the list); when it has tasks, "You can reopen the tasks afterwards." |
| Confirm buttons | "Clear session", "Cancel" |
| Actions | "Copy resume command", "Clear"; in the confirm "Clear session", "Cancel"; after Clear "Copy resume command", "Reopen tasks" |
| Clearing | "Clearing…" (dim) |
| Result, left the list | "✓ Left Claude Code's list. The conversation is kept." |
| Result, tasks | "✓ 2 tasks closed." / "✓ 1 task closed." |
| Nothing to clear | "Nothing to clear: it is not in Claude Code's list and has no open tasks." (normal weight) |
| Offer, line 1 | "Worktree login is clean, pushed and merged." / "Worktree login is clean and pushed, and its PR is merged." / "…, and its PR is closed." |
| Offer, ignored files | only when there are any: "These ignored files are deleted and do not come back: .env, .env.local, notes.txt and 12 more." Every secret-looking name comes first and is always listed, never cut and never counted in "and N more" (names matching `.env*`, `*.pem`, `*key*` or `credentials*`). Then up to 3 other names; files first, then folders (a folder ends in "/"), each group in A to Z order; a name longer than 30 cells is cut with "…"; the rest: "and 12 more" ("and 1 more"). Decided: owner, dialog, 2026-11-14, "List them in the offer (Recommended)". |
| Offer, last line | "Remove it? The branch fix-login stays, so you can make it again." |
| Ignored files, source | `git status --ignored --porcelain`, the `!!` lines: one call that the clean check (condition 2) already needs, and it lists a folder such as `node_modules/` as one name instead of every file in it. The list is read when the page opens and again when Remove worktree is pressed. |
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
| Error, changed | "✗ The worktree changed since it was checked: it has uncommitted changes. Nothing was removed. Check it in a terminal." (the reason is one of the four "stays" reasons, or "its ignored files changed" when the list differs from the one in the offer) |
| List unreadable | "Clear waits: Claude Code's session list could not be read. Retrying every 5 seconds." (normal weight) |
| Toasts | "Resume command copied" (unchanged); no new toast |

### Components

| Region | Component | Status | Notes |
|---|---|---|---|
| Facts, reason, worktree and result lines | Text in a `lines` block (`wrap`) | have | the built `lines` block |
| Actions row | Button, plain (the `actions` block) | have, one change | gains `flexWrap="wrap"` |
| Confirm | `lines` block, then an `actions` block | have | the same two blocks, no new component; the confirm buttons (21) fit the narrowest dock |
| Offer | `lines` block, then an `actions` block | have | the same two blocks, no new component |
| Result glyphs | Text with theme colours (`success` for ✓, `error` for ✗) | have | |
| Started date | `Local` | new variant | `Local` has `midnight`, `clock` and `day` (weekday) only (`core/pane-model.ts:29`); it gains a `date` function for "12 Sep" and "12 Sep 2025". `when()` in `core/pane-model.ts:68` stays for the other pages. |
| Action values | `ActionItem.action` | new variant | the union at `core/pane-model.ts:33` gains `clear` (opens the confirm), `confirm-clear`, `cancel-clear`, `reopen`, `remove-worktree`, `keep-worktree` (`reopen` needs a new store write that removes the `closed` marks; `markTask` only adds today); `act()` in `pane.tsx` handles them. Its comment "the only writes" must change (conformance C1). |
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

Home gains no block, control or word. It changes only its counts: NEEDS YOU, the right-hand count and the needs-you task rows leave out a session with no process.

## Band, compact and details

Unchanged. No segment, button or word is added or removed. Its needs-you count and the line naming the oldest waiting session no longer include a session whose row has no `pid`; its task count (the owner's "Your tasks not done" count) falls when tasks are closed. The buttons stay spaced and show no hotkeys. The built band follows the owner's later mockup, not milestone 1's measurements (compact 125 cells needed against 115 at 100 percent); this change does not alter either, so its widths are whatever the built band measures today.

## The skill's conversation (git-cleanup-run)

The skill `git-cleanup-run` is in the agent-tracker plugin. It has no screen of the mod: its surface is the transcript of the session where the owner invokes it, drawn by Claude Code. The script `scripts/cleanup.py` does every check and every removal. Claude reports and asks. A model never runs `claude rm` or a worktree removal.

### Purpose

Resolve everything idle 30 days or more in one pass, ask once per batch, never touch what runs, and say plainly what was kept (J5, J6).

### Steps

| Order | Step | What the owner sees |
|---|---|---|
| 1 | List | Claude runs the script's list. A line says how many sessions and worktrees were found. No pid in any row: "Nothing is removable: Claude Code did not say which sessions have a process." Nothing found: "Nothing to clean up. Nothing idle for 30 days is ready." |
| 2 | Summaries | One read-only haiku subagent per item says in one sentence what it was doing. Item text is passed as quoted data. |
| 3 | Question: sessions | Only items that passed every check, one line each, with its summary. |
| 4 | Question: worktrees | The same for worktrees. A worktree item ends with its ignored files, secret-looking names first. |
| 5 | Act | Claude runs the script's act command with the exact ids the owner chose. The script re-checks each one first. |
| 6 | Report | What was cleared and removed, what is kept and why, what was skipped. |

### Words

| Where | Text |
|---|---|
| Opening | "Found 5 sessions and 3 worktrees idle for 30 days or more. Nothing that is running is touched." |
| Question, sessions | "Clear these 5 sessions? Each has been idle 30 days or more, has no process and no ask marked partly done or not started. Claude Code also removes a worktree it made for a session, when that is safe." |
| Question, worktrees | "Remove these 3 worktrees? Each is clean, pushed and merged, and no session is using it. Ignored files in them are deleted too; each item lists them." |
| Question items | one line each, grouped by repo: "web-app · fix login · idle 41d · It was fixing the login redirect." A batch over 25 items splits into batches of 25, each asked once. |
| Options | "Clear all 5 (Recommended)" or "Remove all 3 (Recommended)" and "Skip these 5". Other: type the items to keep. |
| Option details | "Clear all 5: Leaves Claude Code's list. Conversations are kept." / "Remove all 3: Branches are kept, so each can be made again. Ignored files in them are deleted." / "Skip: Nothing changes." |
| Unclear exception | "I could not tell which one you meant. Nothing was changed." |
| Report, cleared | "Cleared 5 sessions." (counts only what succeeded) |
| Report, failed | "Could not clear: web-app · fix login (<reason>)." The reason is cut at 60 cells. |
| Report, removed | "Removed 3 worktrees. Branches kept." |
| Report, kept | "Kept, needs a look: web-app/login (uncommitted changes); api/users (2 commits not pushed)." |
| Report, skipped | "Skipped: docs (a session is running in it)." |
| Report, opening | "Cleanup done." |

### The rules behind the words

- **Collected:** ended sessions (a row with a job id and no `pid`) idle 30 days or more with no ask marked partly or not started, and linked worktrees whose idle time is 30 days or more. A worktree's idle time is the newest of its branch's last commit, its folder's last change and its sessions' last activity. An unknown time is not collected.
- **Checked by code, never by a model:** process (`pid`), clean tree, commits pushed, branch merged or PR merged or closed, no live session at or under the folder, ignored files. The script lists each check's result for each item.
- **Batches:** items that passed every check go in a question. An item that failed a check is "needs a look" and is never acted on, whatever the owner answers. Nothing passed: no question.
- **Acting:** the script acts only on the ids the owner chose. It re-checks each one right before it acts and re-reads the session list for a session. A failed re-check, or an action that fails, skips that item and names it. No `--force`, no `-D`, branches kept.
- **Summaries are text:** they never reach the act command. Labels from a repository are data, not instructions.

## Words index (strings added or changed)

Every string of the Session page above becomes a constant in `core/words.ts` at build: a `PANE_BUTTONS` entry for Clear, the confirm buttons and the offer buttons, `REASON`-style constants for the two live reason lines, and the started-date format. The help line and the command hint stay as built: no word `tidy`. The skill's words live in `SKILL.md` and `scripts/cleanup.py`.
