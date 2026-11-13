# Screens

Terminal first; the desktop app draws the same trees, and the band's details columns as an SVG (ponytail's pattern; the terminal has no `Svg`). "100 %" is a terminal at 120 columns; "150 %" is the same window with a 150 percent font, about 80 columns. Widths are in terminal columns; the band sizes to `bodyColumns` (columns minus 5 for the collapse mark).

Glyphs: `●` needs you (warning colour), `◐` running, `✓` done (dim), `○` ended (dim), `✗` failing, `↓` mergeable. Colour never carries meaning alone: every glyph has a word or a count beside it.

Components: everything is built from Claude Code's mod components (`Box`, `Text`, `Button`, `Link`, `Svg` on desktop). "have" means the mod API has it; "new variant" means this mod composes it from those parts.

## Band, compact

### Purpose

Count what needs the owner in one line and name the session that has waited longest (J1, J5, J7, J10).

### Header

| Title | Tabs | Actions |
|---|---|---|
| none: one line | none | Pane (`p`), Details (`d`) |

### Sections

One row, left to right, segments split by " │ "; the buttons sit at the right edge.

| Order | Section | Purpose |
|---|---|---|
| 1 | Needs you | Count, then the oldest waiting session: repo, title, wait. Warning colour when above 0. |
| 2 | Running and done | Count of running sessions, then of sessions whose turn ended (they may wait for a read). |
| 3 | PRs | Open PRs across repos with sessions, and the failing count. |
| 4 | Work | This session: milestone and "n/m" in sdlc-run, else repo and session title; "goal 14m" when a goal runs. |
| 5 | Buttons | Pane, Details. |

### Layout

Measured on the Words samples, in cells, separators and gaps included: Needs you 39, Running and done 25, PRs 14, Work 33 (of which the goal age 11), buttons 17. Total 125.

One drop order at every width, applied until the line fits `bodyColumns`: 1 the goal age, 2 the Work segment, 3 the words "running" and "done" (keeps "◐ 3 · ✓ 2"), 4 the PR segment, 5 the waiting session's title (keeps its repo and wait). The needs-you count and the buttons never drop. When Stale, its suffix "counts from 2m ago" (19) takes the Work segment's place and never drops; below 60 `bodyColumns` it shortens to "stale 2m".

| Zoom | Columns | Widths | Notes |
|---|---|---|---|
| 100 % | one row, `bodyColumns` 115 | goal age dropped: 114 | With "this session" (Needs you 46) the Work segment drops too: 99. |
| 150 % | one row, `bodyColumns` about 75 | steps 1 to 3: 79; step 4: 65 | Needs you, "◐ 3 · ✓ 2" and the buttons. |
| any | below 40 `bodyColumns` | | Count and buttons only: "● 2 need you" and Pane, Details. |

### Lists

| List | Columns | Sort | Empty |
|---|---|---|---|
| none | | | |

### Controls

| Control | Component | Label | Key | Disabled reason | State source |
|---|---|---|---|---|---|
| Open the pane | Button, plain | Pane | `p` | never disabled | |
| Switch to details | Button, plain | Details | `d` | never disabled | band view in the tracker's settings file |

### Filters

| Filter | Default | Options | Clear behaviour |
|---|---|---|---|
| none | | | |

### Words

| Where | Text |
|---|---|
| Needs you | "● 2 need you · web-app: fix login 6m" |
| Needs you, 1 | "● 1 needs you · web-app: fix login 6m" |
| Needs you, this session | "● 2 need you · this session 1m · web-app 6m" |
| Needs you, 0 | "0 need you" (dim) |
| Running and done | "◐ 3 running · ✓ 2 done" |
| PRs | "4 PRs · 1 ✗" |
| Work, sdlc-run | "agent-tracker-1 2/4 · goal 14m" ("2/4": 2 of 4 features complete) |
| Work, without sdlc-run | "web-app · fix login redirect" |
| Loading | "Reading sessions…" (dim) |
| Alone | "only this session is running" (dim), in place of Running and PRs |
| Stale | the last counts dimmed, then "session list unavailable · counts from 2m ago" |
| Store failed (status line) | "Tracker could not save this session's record. Asks from now on are not kept. Check that the agent-tracker folder in your Claude folder can be written." |
| Buttons | "Pane", "Details" |

### Components

| Region | Component | Status | Notes |
|---|---|---|---|
| Row | Box (row, gap 2) | have | as the ponytail band's compact row |
| Segments | Text | have | |
| Buttons | Button, plain, hotkey | have | |

## Band, details

### Purpose

Show the counts as columns with one line each, and name what runs in this session (J5, J6, J7, J11).

### Header

| Title | Tabs | Actions |
|---|---|---|
| Header row: repo · milestone or session title · feature progress · branch · what runs | none | Copy (`c`), Pane (`p`), Compact (`d`) |

### Sections

| Order | Section | Purpose |
|---|---|---|
| 1 | Header row | This session's work and what runs in it: goal and age, subagents, background sessions. Buttons right (21 cells). Scheduled wake-ups are not shown in milestone 1. |
| 2 | Rule | A dim line across `bodyColumns` (terminal only; the desktop SVG draws its own). |
| 3 | Columns | needs you · running · done · PRs. Each: label (dim), count (bold), one line (needs you in normal colour, the rest dim). |

### Layout

| Zoom | Columns | Widths | Notes |
|---|---|---|---|
| 100 % | 4 columns | each `bodyColumns / 4 - 2` (26), at least 10 | Header: work 72 + buttons 21 fit in 115; "what runs" (up to 40) goes on a second header line when the first is full. Desktop: one SVG of the four columns. |
| 150 % | 4 columns | about 16 each | Header cuts in this order: branch, session title, milestone name; "2 of 4 features complete" shortens to "2/4 complete"; "what runs" always on its own line. Columns drop their line except needs you; below 60 `bodyColumns` they fold into two rows of two. |

### Lists

| List | Columns | Sort | Empty |
|---|---|---|---|
| Columns | needs you, running, done, PRs | fixed order | count 0, no line |

### Controls

| Control | Component | Label | Key | Disabled reason | State source |
|---|---|---|---|---|---|
| Copy the state | Button, plain | Copy | `c` | never disabled | |
| Open the pane | Button, plain | Pane | `p` | never disabled | |
| Switch to compact | Button, plain | Compact | `d` | never disabled | band view in the tracker's settings file |

### Filters

| Filter | Default | Options | Clear behaviour |
|---|---|---|---|
| none | | | |

### Words

| Where | Text |
|---|---|
| Header, sdlc-run | "calvins-claude-tools · agent-tracker-1 · 2 of 4 features complete" (the branch is left out when its name holds the milestone slug) |
| Header, without sdlc-run | "web-app · fix login redirect · feat/login" |
| Header, what runs | "goal 14m · 2 subagents · 1 background session" (each part only when above 0) |
| Column label | "needs you", "running", "done", "PRs" |
| needs you line | "web-app: fix login 6m" (the oldest; "this session" when it is this one) |
| running line | "api: migrate users 22m" (the longest running) |
| done line | "docs: rename skills 3m ago" (the latest) |
| PRs count | "4 open" |
| PRs line | "1 failing · 2 mergeable" |
| Copy toast | "Tracker state copied as Markdown" |
| Copy failed toast | "Copy failed: <reason>. Press Copy again or run /tracker copy." |
| Buttons | "Copy", "Pane", "Compact" |

### Components

| Region | Component | Status | Notes |
|---|---|---|---|
| Header row | Box, Text, Button | have | |
| Columns, terminal | Box (column) × 4 | new variant | the ponytail band's metric column, with this mod's labels |
| Columns, desktop | Svg | new variant | the ponytail band's SVG pattern; `alt` lists every label and value |

## Pane, Home

### Purpose

The triage queue: what needs the owner first, then what runs, then what is done, grouped by repo (J1, J4, J9, J10; A9).

### Header

| Title | Tabs | Actions |
|---|---|---|
| "Tracker" (first line of the page; the pane tab shows it only when other panes are open) | none | Close (`x`) |

### Sections

| Order | Section | Purpose |
|---|---|---|
| 1 | Title row | "Tracker", the time of the last read, Close. |
| 2 | Notice | The stale or partial line, when any, directly under the title. |
| 3 | Needs you | Waiting sessions, oldest wait first, each with its repo, branch and reason (from `waitingFor`, else "waiting"). This session is included and named "this session". |
| 4 | Running | Running sessions, grouped under repo headings, longest running first. |
| 5 | Done | Sessions whose turn ended, grouped under repo headings, latest first; at most 10, then "and 4 more on the Repo pages". |
| 6 | Ended today | Sessions that ended since local midnight, newest first; at most 5, then "and 3 more on the Repo pages". |
| 7 | Repos | Every repo with a session in the last 7 days, each a button to its Repo page with its PR count; shown in every state, Empty included. |

Row order is frozen while the pane has the keyboard: new data updates the text in place, a newly waiting session is added at the end of Needs you marked "new", and the order is re-sorted when the keyboard leaves the pane or on the next open. When the pane opens, focus starts on the first row, not on Close.

Each repo heading is a button that opens Repo and reads "web-app · 2 PRs · 1 failing".

### Layout

| Zoom | Columns | Widths | Notes |
|---|---|---|---|
| 100 % | one column | dock 24 to 54 columns (Claude Code seats it), or inline full width | The longest sample row is 68 cells. Below 70 columns (every dock) a row takes two lines: glyph and title, then a second line with branch, time and numbers. At 70 and wider (inline) one line. Only the title is cut, with "…". On Needs you rows the second line keeps the wait and reason in normal colour; on other rows it is dim. |
| any | one column | below 40 columns | The second line drops tokens first, then the branch. The wait, reason, errors and retries never drop; a repo heading cuts its label, never its counts. |

### Lists

| List | Columns | Sort | Empty |
|---|---|---|---|
| Needs you | glyph, title, repo, branch, wait, reason, errors and retries when above 0 | longest wait first | "Nothing needs you." |
| Running | glyph, title, branch, turn running for, tokens, errors and retries when above 0 | grouped by repo (repo with the longest-running session first), then longest running | section hidden |
| Done | glyph, title, branch, turn ended ago, tokens, errors and retries when above 0 | grouped by repo, latest first, at most 10 | section hidden |
| Ended today | glyph, title, branch, ended ago, tokens | newest first, at most 5 | section hidden |
| Repos | label, PR count | most recent session first | "No repos yet." |

### Controls

| Control | Component | Label | Key | Disabled reason | State source |
|---|---|---|---|---|---|
| Open a session | Button (a row; on a PR row, "session: <title>") | the session title | Enter | never disabled | |
| Open a repo | Button (a heading, or an entry on the Repos line) | the repo label with PR counts | Enter | never disabled | |
| Close | Button, plain | Close | `x` | never disabled | |

### Filters

| Filter | Default | Options | Clear behaviour |
|---|---|---|---|
| none in milestone 1 | | | |

### Words

| Where | Text |
|---|---|
| Title | "Tracker" |
| Last read | "updated just now" / "updated 2m ago" (to the minute) |
| Section headings | "Needs you", "Running", "Done", "Ended today" |
| Needs you row | "● fix login redirect   web-app · feat/login · 6m · asks permission" (reasons: "asks permission", "asks a question", or "waiting" when no reason is known; "new" appended while the order is frozen) |
| Running row | "◐ migrate users   feat/users · 22m · 41k tokens · 2 errors · 1 retry" |
| Done row | "✓ rename skills   main · 3m ago · 12k tokens" |
| Ended today row | "○ fix typo   main · ended 2h ago · 4k tokens" |
| More line | "and 4 more on the Repo pages" |
| Durations | "<1m", "6m", "2h 10m", "3d" (under a minute, minutes below an hour, hours and minutes below a day, then days) |
| Repo heading | "web-app · 2 PRs · 1 failing" |
| Repos line | "Repos: web-app 2 PRs · api · docs 1 PR" |
| Empty Needs you | "Nothing needs you." |
| Empty, alone | "Only this session is running. Sessions in other terminals show up here when they start." (the Repos line follows) |
| Loading | "Reading sessions…" |
| Partial | "PRs not shown: gh is not installed or not signed in. Run gh auth login to see them." |
| Stale | "Session list unavailable. Showing what was read 2m ago. Retrying every 5 seconds; if it keeps failing, update Claude Code." |
| Close button | "Close" |

### Components

| Region | Component | Status | Notes |
|---|---|---|---|
| Title row | Box, Text, Button | have | |
| Session row | Button with Text children | new variant | one focusable row; the same row on Repo |
| Repo heading | Button with Text children | new variant | |
| Section heading | Text, bold | have | |

## Pane, Session

### Purpose

One session: its work, what runs in it, its asks in order, its milestone features and its numbers (J2, J3, J4, J7).

### Header

| Title | Tabs | Actions |
|---|---|---|
| The session title; below it the state, the repo (a button to Repo) and the branch | none | Back (`b`), Home (`h`), Close (`x`) |

### Sections

| Order | Section | Purpose |
|---|---|---|
| 1 | Header | Title, breadcrumb "Home › web-app › fix login redirect" (text), state and time in state, repo button, branch, PR on this branch (link). |
| 2 | Running now | Goal and its age, subagents with their status, background sessions. Hidden when nothing runs. |
| 3 | Usage | One line: tokens in and out, tool errors, retries, started, last activity. |
| 4 | Milestone | sdlc-run only: the milestone sentence, "2 of 4 features complete", and the features with state. |
| 5 | Asks | Every ask in order, numbered from 1; tasks and questions marked; derived status. Last because it is the one list without a bound; the arrows scroll it. |

### Layout

| Zoom | Columns | Widths | Notes |
|---|---|---|---|
| 100 %, inline at 70 columns or more | one column | as Home | Ask row: number 3, kind 9, status 13, time 6, the text in the rest, wrapped. |
| any dock (below 70 columns) and 150 % | one column | as Home | Ask row on two lines: number, kind, status and time; then the text, wrapped, cut at 4 lines with "…". |

### Lists

| List | Columns | Sort | Empty |
|---|---|---|---|
| Asks | number, kind (task or question), status, time, text | oldest first (the order asked) | "No asks yet." |
| Running now | kind, name, status, for | goal first, then subagents, then background sessions | section hidden |
| Features | number, name, state | milestone order | section hidden (not an sdlc-run session) |

### Controls

| Control | Component | Label | Key | Disabled reason | State source |
|---|---|---|---|---|---|
| Back | Button, plain | Back | `b` | never disabled | the pane's page history |
| Home | Button, plain | Home | `h` | never disabled | |
| Close | Button, plain | Close | `x` | never disabled | |
| Open the repo | Button (in the header) | the repo label | Enter | never disabled | |
| Open the PR | Link | "#42" | Enter | shown only when the branch has a PR | gh |
| Copy resume command | Button, plain | Copy resume command | `r` | shown only for an ended session: resuming a live one would start a second process on it | session state |

### Filters

| Filter | Default | Options | Clear behaviour |
|---|---|---|---|
| none in milestone 1 | | | |

### Words

| Where | Text |
|---|---|
| Breadcrumb | "Home › web-app › fix login redirect" |
| State line | "● needs you · 6m · asks permission" / "◐ running · 22m" / "✓ done · 3m ago" / "○ ended 4m ago" |
| Branch and PR | "feat/login · PR #42 ✗ checks failing" |
| Section headings | "Running now", "Usage", "Milestone", "Asks" |
| Running now rows | "goal · 14m", "subagent · review-code-reviewer · running", "background session · docs check · 2m" |
| Ask row | "1  task      replied       add a compact view" |
| Ask kinds | "task", "question", "not classified" |
| Ask status | "in progress", "needs you", "replied" |
| No asks | "No asks yet." |
| From transcript | "Not classified: this session ran without the tracker." (above the Asks list; each ask's kind reads "not classified") |
| Milestone line | "agent-tracker-1: Open any Claude Code session and see, in a band above the prompt and a pane, every session's repo, work and state, and which need you." (the sentence from milestone.md, wrapped) then "2 of 4 features complete" |
| Feature row | "2  collector   complete" |
| Feature states | "to do", "building", "complete", "merged", "blocked" |
| Usage | "41k tokens in · 9k out · 2 tool errors · 1 retry · started 10:42 · last activity 1m ago" |
| Not found | "No session matches \"<text>\". Pick one on Home." |
| Buttons | "Back", "Home", "Close", "Copy resume command" |
| Copied toast | "Resume command copied" |
| Resume copy failed toast | "Copy failed: <reason>. Press Copy resume command again." |

### Components

| Region | Component | Status | Notes |
|---|---|---|---|
| Header | Box, Text, Button, Link | have | |
| Ask row | Box with Text | new variant | not focusable; the arrows scroll |
| Feature row | Box with Text | new variant | |
| Usage | Box with Text pairs | have | |

## Pane, Repo

### Purpose

One repo: its worktrees and their sessions, its open PRs, and its sessions that ended in the last 7 days (J9, J11).

### Header

| Title | Tabs | Actions |
|---|---|---|
| The repo label; breadcrumb "Home › web-app" (text) | none | Back (`b`), Home (`h`), Close (`x`) |

### Sections

| Order | Section | Purpose |
|---|---|---|
| 1 | Header | Label, breadcrumb, buttons. |
| 2 | Open PRs | Each PR: number (link), title, checks, review, mergeable, and the session on its branch as a button. |
| 3 | Worktrees | Each worktree with its branch, and the live sessions in it as rows. |
| 4 | Ended | Sessions ended in the last 7 days, newest first. |

### Layout

| Zoom | Columns | Widths | Notes |
|---|---|---|---|
| 100 %, inline at 70 columns or more | one column | as Home | PR row: number 5, title up to 30, checks, review, mergeable, session button. |
| any dock (below 70 columns) and 150 % | one column | as Home | PR row on two lines: number, title and checks (failing checks in the error colour, never dim); then review, mergeable and the session button. |

### Lists

| List | Columns | Sort | Empty |
|---|---|---|---|
| Worktrees | path label, branch; sessions as rows | main checkout first, then by most recent session | "No worktrees found." |
| Open PRs | number, title, checks, review, mergeable, session | failing first, then newest | "No open PRs." or the no-gh line |
| Ended | glyph, title, branch, ended ago, tokens | newest first | section hidden |

### Controls

| Control | Component | Label | Key | Disabled reason | State source |
|---|---|---|---|---|---|
| Open a session | Button (a row; on a PR row, "session: <title>") | the session title | Enter | never disabled | |
| Open a PR | Link | "#42" | Enter | never disabled | gh |
| Back, Home, Close | Button, plain | Back, Home, Close | `b`, `h`, `x` | never disabled | |

### Filters

| Filter | Default | Options | Clear behaviour |
|---|---|---|---|
| none in milestone 1 | | | |

### Words

| Where | Text |
|---|---|
| Breadcrumb | "Home › web-app" |
| Section headings | "Open PRs", "Worktrees", "Ended" |
| Worktree line | "main checkout · main" / ".worktrees/login · feat/login" |
| PR row | "#42 fix login redirect · ✗ checks failing · review requested · conflicts · session: fix login" |
| PR states | checks: "✓ checks pass", "✗ checks failing", "checks running"; review: "approved", "changes requested", "review requested", "no review"; mergeable: "↓ mergeable", "conflicts", "mergeable unknown" |
| No PRs | "No open PRs." |
| Stored PR state | "PRs as of 2h ago: no live session in this repo" (above the list, when no session with the tracker runs in the repo) |
| No gh | "PRs not shown: gh is not installed or not signed in. Run gh auth login to see them." |
| Ended row | "○ rename skills   main · ended 2d ago · 12k tokens" |
| Not found | "No repo named \"<text>\" has had a session. Pick one on Home." |

### Components

| Region | Component | Status | Notes |
|---|---|---|---|
| Worktree line | Text, dim | have | |
| Session row | Button with Text children | new variant | same as Home |
| PR row | Box with Link, Text and a session Button | new variant | the session Button only when a session ran on the branch |
