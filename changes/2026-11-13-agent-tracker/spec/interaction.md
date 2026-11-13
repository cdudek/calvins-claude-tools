# Interaction

Every guideline in `docs/ux/interaction-guidelines.md` is `unresolved`. Each row below cites the rule area it proposes a default for (`IG: <area>`); the owner accepts or changes them at the gate.

What the mod API allows, and so what this spec uses (Claude Code 2.1.323 types, checked 2026-11-13):

- **Band keys:** `ctrl+x tab` or a click gives the band the keyboard; Tab and the arrows walk its buttons, Enter presses one, a one-letter `hotkey` presses it directly. A letter hotkey never fires from the prompt: only while the band or pane has the keyboard (engine types, the `hotkey` rule). Digit hotkeys are not used, because a bare digit in an empty prompt does press them.
- **Pane keys:** the same ring (`ctrl+x tab`, Tab, Enter, letter hotkeys, arrows scroll). No raw key handler, so every move is a Button. `ctrl+x x` closes a pane.
- **Escape, one step at a time:** the first Escape hands the keyboard from the band or pane back to the prompt. The pane opens with `closeOnEscape`, so a second Escape, at an empty idle prompt, closes the pane. Over typed text or a running turn, Escape is Claude Code's own.
- **Menu route:** the mod has no menus. The menu route for every action is the `/tracker` command with an argument (`/tracker details`, `/tracker compact`, `/tracker copy`, `/tracker repo <name>`, `/tracker session <title or id>`, `/tracker band off`, `/tracker band on`).
- **Refresh:** the collector reads `claude agents --json` every 5 seconds and the session files on change; the band and an open pane redraw when the data changes, and once a minute so the times ("6m", "goal 14m", "updated 2m ago") stay true. Times are shown to the minute.
- **Words:** every on-screen string lives in the Words tables of `screens.md`. Text quoted here is the same string; where they ever differ, `screens.md` wins.

## Wireflows

### J1 Answer the blocked one first

| From control | Action | To screen or state | Notes |
|---|---|---|---|
| (none) | a session starts to wait | Band compact: needs you | Every session's band turns the count to the warning colour within 5 seconds. |
| Band compact: needs-you segment | read | (no move) | Names the oldest waiting session's repo and title (its Claude Code tab title) and how long it has waited; "this session" when it is this one. Switching to it is the owner's move in their terminal; the tracker never switches (observe only). |
| Band: Pane (`p`) | press | Pane Home: Needs you | Shows every waiting session with its reason, for when more than one waits. |

### J2 Read my asks in order

| From control | Action | To screen or state | Notes |
|---|---|---|---|
| Band: Pane button (`p`) | press | Pane Home | Pane opens with the keyboard. |
| Pane Home: session row | Enter | Pane Session | Running now, Usage and Milestone are short and come first; Asks is the last section, scrolled with the arrows. |
| Pane Session: Back (`b`) | press | Pane Home | Same row focused. |

### J3 See milestone progress

| From control | Action | To screen or state | Notes |
|---|---|---|---|
| Band compact: Details (`d`) | press | Band details | Header row: milestone, "2 of 4 features complete". |
| Band details: Pane (`p`) | press | Pane Home | |
| Pane Home: session row | Enter | Pane Session: Milestone section | Lists features with state. Absent without sdlc-run. |

### J4 Spot where a session struggles

| From control | Action | To screen or state | Notes |
|---|---|---|---|
| Band: Pane (`p`) | press | Pane Home | Each row shows tokens, and errors and retries when above zero. |
| Pane Home: session row | Enter | Pane Session: Usage section | Tokens in and out, tool errors, retries, started, last activity. |

### J5 Stay aware while typing

| From control | Action | To screen or state | Notes |
|---|---|---|---|
| (none) | the session starts | Band compact | Default view. No move needed. |

### J6 Dig from a count to one item

| From control | Action | To screen or state | Notes |
|---|---|---|---|
| Band compact: Details (`d`) | press | Band details | Columns: needs you, running, done, PRs. |
| Band details: Pane (`p`) | press | Pane Home | |
| Pane Home: session row | Enter | Pane Session | |

### J7 Tell sessions apart

| From control | Action | To screen or state | Notes |
|---|---|---|---|
| (none) | read | Band compact: Work segment, last on the line | Milestone and "2/4" (features complete), or repo and session title. |
| Band compact: Details (`d`) | press | Band details: header row | Adds what runs: goal and its age, subagents, background sessions. |

### J9 Without sdlc-run

| From control | Action | To screen or state | Notes |
|---|---|---|---|
| (any of the above) | | same screens | Milestone parts are absent; the header shows the session title and branch instead. |

### J10 Pushed attention

| From control | Action | To screen or state | Notes |
|---|---|---|---|
| (none) | a session starts to wait | Band compact: needs you, warning colour | In every session. No notification, sound or toast in milestone 1: Claude Code already notifies for its own session, and a tracker notifying from every session would repeat it once per open session. |

### J11 Open PRs and their state

| From control | Action | To screen or state | Notes |
|---|---|---|---|
| Band: Pane (`p`) | press | Pane Home | Each repo heading shows "3 PRs · 1 failing". |
| Pane Home: repo heading | Enter | Pane Repo | PRs section lists each PR. |
| Pane Repo: PR number link | Enter | the browser | Opens the PR on GitHub. |
| Pane Repo: the PR row's session button | Enter | Pane Session | Only when a session ran on that branch. |

## State Tables

### Band, compact

Words: `screens.md`, Band, compact.

| State | Entry or trigger | What the user sees | Words | Actions with key | Exit |
|---|---|---|---|---|---|
| Loading | session start, before the first read | a dim placeholder | Loading | Pane `p`, Details `d` | first read done |
| Needs you | at least one session needs you | warning-coloured count, then the oldest waiting session (normal colour) and its wait | Needs you | Pane `p`, Details `d` | none needs you |
| Needs you, this session | this session is the oldest waiting | as Needs you, naming "this session", then the oldest other one | Needs you, this session | Pane `p`, Details `d` | |
| All quiet | sessions run or are done, none needs you | count 0 dim, the other counts normal | Needs you, 0 | Pane `p`, Details `d` | a session needs you |
| Alone | this is the only live session | the needs-you segment (this session may wait), a dim note, and the work segment | Alone | Pane `p`, Details `d` | another session starts |
| Partial | `gh` missing or failing; sessions still read | the counts without the PR segment | as All quiet | Pane `p`, Details `d` | gh works again |
| Stale | `claude agents --json` failed twice in a row | the last good counts, dimmed, with their age and the reason | Stale | Pane `p`, Details `d` | the next read works |
| Hidden | `/tracker band off` | no tracker row; other mods' rows unchanged | none | `/tracker band on` | `/tracker band on` |

### Band, details

Words: `screens.md`, Band, details.

| State | Entry or trigger | What the user sees | Words | Actions with key | Exit |
|---|---|---|---|---|---|
| Default | Details pressed, or kept from last time | header row, buttons right; columns below, each a label, a bold count and one line (the needs-you line in normal colour, the others dim) | Header, Column label | Copy `c`, Pane `p`, Compact `d` | Compact |
| Column empty | a column has 0 | the count 0 and no line | Column label | as Default | |
| Loading, Partial, Stale | as compact | as compact, in one line under the header | as compact | as Default | as compact |
| Narrow | `bodyColumns` below 80 | the columns drop their line, except needs you; below 60 they fold into two rows of two | | as Default | wider |

### Pane, Home

Words: `screens.md`, the page of the same name, by the row named in the Words column.

| State | Entry or trigger | What the user sees | Words | Actions with key | Exit |
|---|---|---|---|---|---|
| Loading | opened before the first read | the title and a dim line | Loading | Close `x` | first read |
| Default | sessions exist | sections Needs you, Running, Done; each lists rows grouped under repo headings | see screens.md | Enter on a row or heading, Close `x` | Session, Repo, close |
| All quiet | none needs you | the Needs you section shows one line | Empty Needs you | as Default | |
| Empty | no live session but this one | one line, then Ended today and the Repos line | Empty, alone | Close `x`, the Repos line | a session starts |
| Partial | gh missing | rows as Default; repo headings without PR counts; one dim line at the bottom | Partial | as Default | |
| Stale | sessions unreadable twice in a row | the last good list, dim, and a line at the top | Stale | as Default | next read |

### Pane, Session

| State | Entry or trigger | What the user sees | Words | Actions with key | Exit |
|---|---|---|---|---|---|
| Live | a row of a live session | header, Running now, Usage, Milestone (sdlc-run only), Asks | Section headings | Back `b`, repo line, Close `x` | Back, close |
| Ended | the session left `claude agents` while open | the same, header state "ended", the time it ended | State line, ended | as Live, plus Copy resume command `r` | |
| From transcript | a session without the mod | Asks and Usage from its transcript; asks not classified are marked so | From transcript | as Live | |
| No asks | no prompt yet | Asks section one line | No asks | as Live | |
| Not found | the session id is unknown (command argument) | one line | Not found | Close `x`, Home `h` | |

### Pane, Repo

| State | Entry or trigger | What the user sees | Words | Actions with key | Exit |
|---|---|---|---|---|---|
| Default | a repo heading | Worktrees with their sessions, Open PRs, Ended | see screens.md | Back `b`, rows, PR links, Close `x` | Back, close |
| No PRs | gh works, none open | PR section one line | No PRs | as Default | |
| No gh | gh missing or signed out | PR section one line | No gh | as Default | |
| Not found | unknown repo name (command argument) | one line | Not found | Close `x`, Home `h` | |

## State Diagrams

```mermaid
stateDiagram
    [*] --> Loading
    Loading --> NeedsYou: a session needs you
    Loading --> AllQuiet: none needs you
    Loading --> Alone: no other session
    Loading --> Stale: read failed twice
    NeedsYou --> AllQuiet: last one answered
    AllQuiet --> NeedsYou: a session waits
    AllQuiet --> Alone: others end
    Alone --> AllQuiet: another starts
    NeedsYou --> Stale: read failed twice
    AllQuiet --> Stale: read failed twice
    Stale --> AllQuiet: read works
    Stale --> NeedsYou: read works
```

Band view is a separate two-state toggle (compact, details), kept across sessions.

## Elements x Interactions

"nothing" means the element ignores the gesture. No element accepts drag, drop or right-click: the mod draws no menus and takes no files.

| Screen | Element | Click | Double-click | Drag | Drop onto | Hover | Right-click / More | Keys | Selection | Rules |
|---|---|---|---|---|---|---|---|---|---|---|
| Band | view button (Details / Compact) | toggles the view | toggles twice (no net change) | nothing | nothing | nothing | nothing | `d` when focused; Enter | nothing | IG: remembered state |
| Band | Pane button | opens the pane with the keyboard | opens once (already open: focuses it) | nothing | nothing | nothing | nothing | `p`; Enter | nothing | IG: side panels |
| Band | Copy button (details) | copies the state as Markdown, toast | copies twice | nothing | nothing | nothing | nothing | `c`; Enter | nothing | IG: copy and paste |
| Band | counts and text | nothing | nothing | nothing | nothing | nothing | nothing | nothing | nothing | IG: lists and selection |
| Pane | session row | opens Session | opens once | nothing | nothing | nothing | nothing | Enter when focused; Tab and Shift+Tab move focus; the arrows scroll | one focused row, no multi-select | IG: lists and selection |
| Pane | repo heading, Repos line entry | opens Repo | opens once | nothing | nothing | nothing | nothing | Enter | as session row | IG: lists and selection |
| Pane | PR number link | opens the PR in the browser | opens once | nothing | nothing | nothing | nothing | Enter | as session row | IG: navigation and return |
| Pane | ask row | nothing (text only) | nothing | nothing | nothing | nothing | nothing | arrows scroll | nothing | IG: lists and selection |
| Pane | Copy resume command button (ended session) | copies the command, toast | copies twice | nothing | nothing | nothing | nothing | `r`; Enter | nothing | IG: copy and paste |
| Pane | Back button | previous page | goes back twice | nothing | nothing | nothing | nothing | `b`; Enter | nothing | IG: navigation and return |
| Pane | Home button | Home | Home | nothing | nothing | nothing | nothing | `h`; Enter | nothing | IG: navigation and return |
| Pane | Close button | closes the pane, keys to the prompt | closes | nothing | nothing | nothing | nothing | `x`; Enter; `ctrl+x x`; Escape at an empty prompt | nothing | IG: keyboard and focus |

## Action Behaviour

Nothing the tracker does changes anything outside its own folder, so nothing needs confirming and nothing needs undo.

| Action | Pointer route | Keyboard route | Menu route | Save | Leave | Undo | Guideline |
|---|---|---|---|---|---|---|---|
| Switch band view | click Details / Compact | `ctrl+x tab`, `d` | `/tracker details`, `/tracker compact` | saved at once, kept across sessions | nothing to lose | press again | IG: remembered state |
| Open the pane | click Pane | `ctrl+x tab`, `p` | `/tracker` | nothing | nothing | Close | IG: side panels |
| Copy the state | click Copy (details) | `ctrl+x tab`, `c` | `/tracker copy` | nothing | nothing | not needed (clipboard only) | IG: copy and paste |
| Open a session | click its row | `ctrl+x tab`, Tab to the row, Enter | `/tracker session <title or id>` | nothing | nothing | Back | IG: navigation and return |
| Open a repo | click its heading | Tab to the heading, Enter | `/tracker repo <name>` | nothing | nothing | Back | IG: navigation and return |
| Open a PR | click its number | Tab to it, Enter | none (the browser is outside the tracker) | nothing | nothing | close the browser tab | IG: navigation and return |
| Go back | click Back | `b` | `/tracker` (Home) | nothing | nothing | open again | IG: navigation and return |
| Copy resume command (ended session) | click Copy resume command on its Session page | Tab to it, `r` | none | nothing | nothing | not needed (clipboard only) | IG: copy and paste |
| Hide or show the band | none | none | `/tracker band off`, `/tracker band on` | saved at once in the settings file | nothing | the other command | IG: remembered state |
| Close the pane | click Close or the close mark | `x`, `ctrl+x x`, Escape at an empty prompt | none | nothing | nothing | `/tracker` reopens on Home | IG: keyboard and focus |

## Feedback

| Action | Feedback | Reason | Where shown |
|---|---|---|---|
| Switch band view | visible: the band redraws | the change is the feedback | band |
| Open the pane | visible: the pane appears with the keyboard | | pane |
| Copy the state, Copy resume command | visible: toast (Words: Copy toast, Copy failed toast) | the clipboard shows nothing by itself; the toast carries nothing the user needs later | toast |
| A session starts waiting | visible: count and colour change in every band | J10 | band |
| A read fails | visible: dim line on the band, top line in the pane | the data shown may be old; never only a toast | band, pane |
| The store cannot be written | visible: status line (Words: Store failed) | asks of this session are not kept until it works | status line under the prompt |

## Errors

Every error reads event, consequence, action; the exact strings are in `screens.md` Words.

| Event | Consequence | Action |
|---|---|---|
| Claude Code's session list could not be read twice in a row. | The counts shown are from the last good read, dimmed, with their age. | It retries every 5 seconds; if it keeps failing, update Claude Code. |
| `gh` is not installed or not signed in. | PR counts and the PR list are not shown. | Run `gh auth login`. |
| A transcript could not be read (missing or unreadable). | That session shows without its asks or numbers. | Nothing to do; it is read again on the next change. |
| The tracker could not save this session's record. | Asks from now on are not kept until it can. | Check that the tracker's folder in your Claude folder can be written. |
| The question check at turn end failed (model call or transcript read). | The session shows as done, without the "asks a question" flag; no false alarm. | Nothing to do; the next turn is checked again. |
| An ask could not be classified (the model call failed). | The ask is kept and shown as "not classified". | Nothing to do; the next ask is tried again. |
| Copy failed. | Nothing was copied. | Press Copy again, or run `/tracker copy`. |
| `/tracker session <text>` or `/tracker repo <text>` matched nothing. | No page opens on that item; the pane shows the not-found line. | Open Home and pick one. |

## Open Questions

| Question | Recommended answer | Why it matters |
|---|---|---|
| Should the tracker send one notification when a session starts waiting? | No in milestone 1 (J10 is met by the band in every session). Revisit if a waiting session is still missed. | One notification per open session would repeat Claude Code's own. |
