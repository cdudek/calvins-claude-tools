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
| 2 | Running | Count of running sessions. |
| 3 | PRs | Open PRs across repos with sessions, and the failing count. |
| 4 | Work | This session: milestone and "n/m" in sdlc-run, else repo and session title; "goal 14m" when a goal runs. |
| 5 | Buttons | Pane, Details. |

### Layout

Measured on the Words samples, in cells, separators included: Needs you 36, Running 14, PRs 14, Work 33 (separators included), buttons 15 with their gaps. Total 112. With "this session" Needs you is 43, total 119: the Work segment drops first.

| Zoom | Columns | Widths | Notes |
|---|---|---|---|
| 100 % | one row, `bodyColumns` 115 | as measured; the title inside Needs you is cut at 20 cells with "…" | Fits whole. |
| 150 % | one row, `bodyColumns` about 75 | | Drop in this order until it fits: Work's goal age, Work, PRs, the word "running" (keeps "◐ 3"). Then cut the waiting session's title, down to the repo alone. The count and the buttons never drop. At 75 cells: Needs you 36, "◐ 3" 6, buttons 15 = 57. |
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
| Running | "◐ 3 running" |
| PRs | "4 PRs · 1 ✗" |
| Work, sdlc-run | "agent-tracker-1 2/4 · goal 14m" |
| Work, without sdlc-run | "web-app · fix login redirect" |
| Loading | "Reading sessions…" (dim) |
| Alone | "only this session is running" (dim), in place of Running and PRs |
| Stale | the last counts dimmed, then "read 2m ago · session list unavailable" |
| Store failed (status line) | "Tracker: this session's asks are not being kept: could not write to the tracker folder. Check it can be written." |
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
| 1 | Header row | This session's work and what runs in it: goal and age, subagents, background tasks and wake-ups. Buttons right (21 cells). |
| 2 | Rule | A dim line across `bodyColumns` (terminal only; the desktop SVG draws its own). |
| 3 | Columns | needs you · running · done · PRs. Each: label (dim), count (bold), one line (needs you in normal colour, the rest dim). |

### Layout

| Zoom | Columns | Widths | Notes |
|---|---|---|---|
| 100 % | 4 columns | each `bodyColumns / 4 - 2` (26), at least 10 | Header: work 72 + buttons 21 fit in 115; "what runs" (up to 40) goes on a second header line when the first is full. Desktop: one SVG of the four columns. |
| 150 % | 4 columns | about 16 each | Header cuts in this order: branch, session title, milestone name (keeps "2/4"); "what runs" always on its own line. Columns drop their line except needs you; below 60 `bodyColumns` they fold into two rows of two. |

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
| Header, sdlc-run | "calvins-claude-tools · agent-tracker-1 · 2/4 · milestone/agent-tracker-1" |
| Header, without sdlc-run | "web-app · fix login redirect · feat/login" |
| Header, what runs | "goal 14m · 2 subagents · 1 background task" (each part only when above 0) |
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
| 2 | Needs you | Waiting sessions, oldest wait first, each with its reason when `waitingFor` gives one. |
| 3 | Running | Running sessions, grouped under repo headings, longest running first. |
| 4 | Done | Sessions whose turn ended, grouped under repo headings, latest first. |
| 5 | Repos | Every repo with a session in the last 7 days, each a button to its Repo page with its PR count. |
| 6 | Footer | Partial or stale line, when any. |

Each repo heading is a button that opens Repo and reads "web-app · 2 PRs · 1 ✗".

### Layout

| Zoom | Columns | Widths | Notes |
|---|---|---|---|
| 100 % | one column | dock 24 to 54 columns (Claude Code seats it), or inline full width | The longest sample row is 68 cells. Below 70 columns (every dock) a row takes two lines: glyph and title, then a dim line with branch, time and numbers. At 70 and wider (inline) one line. Only the title is cut, with "…". |
| 150 % | one column | dock about 36 | Two-line rows; the dim line drops tokens first, then the branch. Errors and retries never drop. |

### Lists

| List | Columns | Sort | Empty |
|---|---|---|---|
| Needs you | glyph, title, repo, wait, reason | longest wait first | "Nothing needs you." |
| Running | glyph, title, branch, running for, tokens, errors and retries when above 0 | grouped by repo (repo with the longest-running session first), then longest running | section hidden |
| Done | glyph, title, branch, ended turn ago, tokens | grouped by repo, latest first | section hidden |

### Controls

| Control | Component | Label | Key | Disabled reason | State source |
|---|---|---|---|---|---|
| Open a session | Button (a row) | the session title | Enter | never disabled | |
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
| Last read | "updated 3s ago" |
| Section headings | "Needs you", "Running", "Done" |
| Needs you row | "● fix login redirect   web-app · 6m · asks permission" |
| Running row | "◐ migrate users   feat/users · 22m · 41k tokens · 2 errors · 1 retry" |
| Done row | "✓ rename skills   main · 3m ago · 12k tokens" |
| Repo heading | "web-app · 2 PRs · 1 ✗" |
| Repos line | "Repos: web-app 2 PRs · api · docs 1 PR" |
| Empty Needs you | "Nothing needs you." |
| Empty, alone | "Only this session is running. Sessions in other terminals show up here when they start." |
| Loading | "Reading sessions…" |
| Partial | "PRs not shown: gh is not installed or not signed in. Run gh auth login to see them." |
| Stale | "Session list unavailable: showing what was read 2m ago. Retrying every 5s; update Claude Code if this stays." |
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
| 2 | Running now | Goal and its age, subagents with their status, background tasks and wake-ups. Hidden when nothing runs. |
| 3 | Asks | Every ask in order, numbered from 1; tasks and questions marked; derived status. |
| 4 | Milestone | sdlc-run only: the milestone sentence and its features with state. |
| 5 | Numbers | Tokens in and out, tool errors, retries, started, last activity. |

### Layout

| Zoom | Columns | Widths | Notes |
|---|---|---|---|
| 100 % | one column | as Home | Ask row: number 3, kind 9, status 13, text rest, wrapped. |
| 150 % | one column | as Home | Ask row: number and kind on the first line, the text wrapped below. |

### Lists

| List | Columns | Sort | Empty |
|---|---|---|---|
| Asks | number, kind (task or question), status, text, time | oldest first (the order asked) | "No asks yet." |
| Running now | kind, name, status, for | goal first, then subagents, then background tasks | section hidden |
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
| Section headings | "Running now", "Asks", "Milestone", "Numbers" |
| Running now rows | "goal · 14m", "subagent · review-code-reviewer · running", "background task · npm test · 2m" |
| Ask row | "1  task      replied       add a compact view" |
| Ask kinds | "task", "question", "not classified" |
| Ask status | "in progress", "waiting on you", "replied" |
| No asks | "No asks yet." |
| From transcript | "Kinds not known: this session ran without the tracker." (above the Asks list; each ask's kind reads "not classified") |
| Milestone line | "agent-tracker-1: Open any Claude Code session and see …" |
| Feature row | "2  collector   complete" |
| Feature states | "to do", "building", "complete", "merged", "blocked" |
| Numbers | "Tokens 41k in · 9k out", "Tool errors 2", "Retries 1", "Started 10:42", "Last activity 1m ago" |
| Not found | "No session matches \"<text>\". Open the pane to pick one." |
| Buttons | "Back", "Home", "Close", "Copy resume command" |
| Copied toast | "Resume command copied" |

### Components

| Region | Component | Status | Notes |
|---|---|---|---|
| Header | Box, Text, Button, Link | have | |
| Ask row | Box with Text | new variant | not focusable; the arrows scroll |
| Feature row | Box with Text | new variant | |
| Numbers | Box with Text pairs | have | |

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
| 2 | Worktrees | Each worktree with its branch, and the live sessions in it as rows. |
| 3 | Open PRs | Each PR: number (link), title, checks, review, mergeable, the session on its branch. |
| 4 | Ended | Sessions ended in the last 7 days, newest first. |

### Layout

| Zoom | Columns | Widths | Notes |
|---|---|---|---|
| 100 % | one column | as Home | PR row: number 5, title up to 30, checks, review, mergeable. |
| 150 % | one column | as Home | PR row: number and title, then a dim line with checks, review, mergeable, session. |

### Lists

| List | Columns | Sort | Empty |
|---|---|---|---|
| Worktrees | path label, branch; sessions as rows | main checkout first, then by most recent session | "No worktrees found." |
| Open PRs | number, title, checks, review, mergeable, session | failing first, then newest | "No open PRs." or the no-gh line |
| Ended | glyph, title, branch, ended ago, tokens | newest first | section hidden |

### Controls

| Control | Component | Label | Key | Disabled reason | State source |
|---|---|---|---|---|---|
| Open a session | Button (a row) | the session title | Enter | never disabled | |
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
| Section headings | "Worktrees", "Open PRs", "Ended" |
| Worktree line | "main checkout · main" / ".worktrees/login · feat/login" |
| PR row | "#42 fix login redirect · ✗ checks failing · review requested · not mergeable · fix login redirect (session)" |
| PR states | checks: "✓ checks pass", "✗ checks failing", "checks running"; review: "approved", "changes requested", "review requested", "no review"; mergeable: "↓ mergeable", "not mergeable", "conflicts" |
| No PRs | "No open PRs." |
| No gh | "PRs not shown: gh is not installed or not signed in. Run gh auth login to see them." |
| Ended row | "○ rename skills   main · ended 2d ago · 12k tokens" |
| Not found | "No repo named \"<text>\" has had a session." |

### Components

| Region | Component | Status | Notes |
|---|---|---|---|
| Worktree line | Text, dim | have | |
| Session row | Button with Text children | new variant | same as Home |
| PR row | Box with Link and Text | new variant | |
