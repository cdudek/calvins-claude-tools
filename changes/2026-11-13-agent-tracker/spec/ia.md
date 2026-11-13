# Information Architecture

Milestone 1: the band and the pane. The pane has three pages (Home, Repo, Session); the web page in milestone 2 repeats them with links and adds Milestone and Feature pages. Routes are proposed in [the sitemap](sitemap.md); nothing exists as built.

## Objects

| Object | Definition | Status | Need |
|---|---|---|---|
| Session | One Claude Code conversation on this machine, live or ended, with its repo, worktree, branch, title, state, tokens, errors and retries. | new | J1, J4, J5, J7, J10 |
| Repo | A git repository at least one session ran in; named by its folder. | new | J1, J9, J11 |
| Worktree | A checkout of a repo (the main one or a linked worktree), with its branch. | new | J1 |
| Ask | One prompt the owner typed in a session, kept in order, classified task or question. | new | J2 |
| PR | A pull request on a repo's branch, with checks, review and mergeable state. | new | J11 |
| Run | Something running inside a session besides the main turn: a goal, a subagent, a background task or a scheduled wake-up. | new | J7 |
| Milestone | An sdlc-run milestone the session's branch belongs to (`changes/*/milestone.md`), with its features. Only in sdlc-run repos. | new | J3 |
| Feature | One row of a milestone's feature table, with its state. | new | J3 |
| Needs-you item | A session in a state that waits for the owner. Not stored: derived from Session state. | attribute of Session | J1, J5, J10 |
| Note (you should know, decided without you) | Milestone 3. Named here so milestone 1 leaves room. | deferred | J8 |

Set aside: "agent" (a session is the unit; a subagent is a Run), "task tracker item" (Beads, Linear, GitHub issues are milestone 3 links, not objects here), "plan" (milestone 3, step 5).

## Alias Table

| Canonical | Rejected | Reason |
|---|---|---|
| session | agent, conversation, chat, thread | Claude Code calls it a session (`claude agents` lists sessions). "Agent" is kept for subagents. |
| needs you | blocked, waiting, attention, needs input | The owner's own framing ("which agent needs attention"), short enough for the band. The engine states stay internal. |
| running | busy, working, active | Plain and matches "what runs in the session" (A7). |
| done | idle, finished, complete, ready for review | The turn ended and nothing asks the owner anything. |
| ended | closed, dead, stopped, exited | The session's process is gone. |
| ask | prompt, message, request | The owner's word ("what I asked for"); covers both kinds. |
| task | todo, job, work item | The owner's word. |
| question | query | The owner's word. |
| PR | pull request, merge request | Short; the owner uses it. |
| goal | loop, /goal run | The command's own name. |
| subagent | agent, worker | Claude Code's word. |
| background task | job, shell | Claude Code's word. |
| repo | repository, project | "Project" is taken by sdlc-run projects. |
| compact, details | collapsed, expanded, mini, full | ponytail's labels (A6). |

## Nested Object Matrix

| Parent | Child | Cardinality | Role name | Rank |
|---|---|---|---|---|
| Repo | Worktree | 1 to many | worktrees | 2 |
| Repo | Session | 0 to many | sessions | 1 |
| Repo | PR | 0 to many | open PRs | 3 |
| Worktree | Session | 0 to many | sessions here | 1 |
| Session | Ask | 0 to many, ordered | asks | 1 |
| Session | Run | 0 to many | running now | 2 |
| Session | PR | 0 to 1 (by branch) | this branch's PR | 3 |
| Session | Milestone | 0 to 1 (by branch, sdlc-run only) | working on | 4 |
| Milestone | Feature | 1 to many, ordered | features | 1 |

## CTA Inventory

The tracker never acts on a session (no-go N1). Its verbs open, switch view, copy and go back.

| Object | Verb | Control | Type | Contra-CTA |
|---|---|---|---|---|
| Band | Switch to details / compact | band button "Details" / "Compact" | primary | the same button, renamed |
| Band | Open the pane | band button "Pane"; `/tracker` | primary | Close in the pane |
| Band | Copy the state as Markdown | band button "Copy" (details view) | secondary | none |
| Session | Open its page | row in the pane | primary | Back |
| Session (ended) | Copy its resume command | Session page button "Copy resume command" | secondary | none |
| Band | Hide or show | `/tracker band off`, `/tracker band on` | secondary | the other command |
| Repo | Open its page | repo heading in the pane; Repos line on Home | primary | Back |
| PR | Open on GitHub | PR number as a link (the mod's `Link`) | secondary | none |
| Pane | Close | Escape, "Close" | primary | `/tracker` or Pane reopens |

## Attribute Priority

| View | Attribute | Rank | Reason |
|---|---|---|---|
| Band compact | needs-you count | 1 | J1, J5: the reason the band exists. |
| Band compact | oldest waiting session: title and wait time | 2 | J1: which to answer first. |
| Band compact | running count | 3 | J5, success measure. |
| Band compact | open PR count and failing count | 4 | J11 |
| Band compact | this session's work (milestone and progress, or title) and goal age | 5 | J7; last on the line, first to be cut. |
| Band header | repo name | 1 | J7 |
| Band header | milestone and feature progress, or session title | 2 | J3, J7, J9 |
| Band header | goal and its age, subagent count, background task count | 3 | J7 |
| Pane Home row | state | 1 | J1 |
| Pane Home row | session title | 2 | J7 |
| Pane Home row | repo and branch | 3 | J1 |
| Pane Home row | time in state | 4 | J1, J10 |
| Pane Home row | tokens; errors and retries when above zero | 5 | J4 |
| Pane Repo PR row | number and title | 1 | J11 |
| Pane Repo PR row | checks, review, mergeable | 2 | J11 |
| Pane Repo PR row | session on that branch | 3 | J11 |
| Pane Session | asks in order, kind and status | 1 | J2 |
| Pane Session | running now (goal, subagents, background tasks) | 2 | J7 |
| Pane Session | milestone features (sdlc-run only) | 3 | J3 |
| Pane Session | tokens, errors, retries, started, last activity | 4 | J4 |

## State Diagrams

Session state as shown. `claude agents --json` (2.1.323, checked 2026-11-13) reports interactive sessions with `status` (`idle`, `busy`, `waiting`, plus a `waitingFor` string when waiting) and background sessions with `state` (`working`, `blocked`, `done`). Mapping: `busy` and `working` are running; `waiting` and `blocked` are needs you; `idle` is done; `done` (only with `--all`) is ended; a session missing from the list is ended. What `waitingFor` holds (permission or question) is read at build time and shown as the reason when present.

```mermaid
stateDiagram-v2
    [*] --> running: session starts a turn
    running --> needs_you: status waiting or state blocked
    needs_you --> running: the owner answers
    running --> done: turn ends (status idle)
    done --> running: the owner sends a prompt
    needs_you --> ended: session exits
    running --> ended: session exits
    done --> ended: session exits
    ended --> [*]
```

Ask status, derived, never set by hand (no-go N6):

```mermaid
stateDiagram-v2
    [*] --> in_progress: owner sends the ask
    in_progress --> needs_you: session needs you before the turn ends
    needs_you --> in_progress: owner answers
    in_progress --> replied: the turn ends
    replied --> [*]
```

## Sitemap

Written by `cct:ux-sitemap-create` into [sitemap.md](sitemap.md) and [sitemap.json](sitemap.json), scoped to this change.

## Screen Inventory

| Screen | Route | Purpose | Job stories served | Arrive from | Go next to |
|---|---|---|---|---|---|
| Band, compact | above the prompt | Count what needs the owner in one line, name the oldest waiting session. | J1, J5, J10 | every session, always | Band details; Pane Home |
| Band, details | above the prompt | Columns with a count and one line each; header names this session's work. | J5, J6, J7, J11 | Band compact | Band compact; Pane Home; Copy |
| Pane, Home | pane `home` | The triage queue: needs you first, then running, then done, grouped by repo; PR summary per repo. | J1, J4, J9, J10 | `/tracker`; band Pane | Session; Repo; Close |
| Pane, Repo | pane `repo/<repo>` | One repo: its worktrees with their sessions, and its open PRs. | J9, J11 | Home repo heading; Session's repo line | Session; Home (Back) |
| Pane, Session | pane `session/<id>` | One session: header, running now, asks in order, milestone features, numbers. | J2, J3, J4, J7 | Home row; Repo session row | Repo; Home (Back) |

## Navigation Tree

```
Band (always above the prompt)
├── compact ⇄ details            lateral (button)
└── Pane                         forward (button or /tracker)
    └── Home                     the triage queue
        ├── Repo <name>          forward (repo heading)
        │   └── Session <title>  forward (row)
        └── Session <title>      forward (row)
            └── Repo <name>      lateral (repo line in the header)
```

## Journeys

| Job story | How often | Path (screen → control → screen …) | Moves | Why this length |
|---|---|---|---|---|
| J1 answer the blocked one first | many times a session | Band compact (reads the oldest waiting session) | 0 | The most frequent job needs no move: the name is on the band. Switching to that session is Claude Code's own move, outside the tracker. |
| J5 stay aware | every prompt | Band compact | 0 | Always on. |
| J7 tell sessions apart | every prompt | Band details header; or compact title row | 0 to 1 | The header row is in details; compact keeps the repo and work in its first segment. |
| J6 dig from a count to one item | several times a day | Band → Pane → Home row → Session | 2 | Pane, then the row. |
| J2 read my asks in order | daily | Band → Pane → Home row → Session (asks section) | 2 | Same as J6. |
| J4 spot struggle | daily | Band → Pane → Home (numbers on the row) | 1 | Errors and retries show on the Home row. |
| J3 see milestone progress | daily | Band details header (feature n of m); Session page for the list | 0 to 2 | Progress on the header, list one level down. |
| J11 open PRs and their state | daily | Band → Pane → Repo heading → Repo (PRs) | 2 | Home shows a PR count per repo; the list is on Repo. |
| J9 without sdlc-run | as above | as above | as above | Same paths; milestone parts are absent. |
| J10 pushed attention | continuous | Band compact turns warning colour | 0 | The band is in every session. |

## Move Table

| From | Control | To | Type | Why (job story or ask) | Back target | Restores |
|---|---|---|---|---|---|---|
| Band compact | Details | Band details | lateral | J6, A6 | Band compact (Compact) | nothing to restore |
| Band details | Compact | Band compact | lateral | J5, A4, A6 | Band details (Details) | nothing to restore |
| Band (either) | Pane | Pane Home | forward | J6, A8, A9 | close the pane | prompt focus and draft |
| Prompt | `/tracker` | Pane Home | forward | J6, A8 | close the pane | prompt focus and draft |
| Pane Home | session row | Pane Session | forward | J2, J6 | Pane Home | selected row, scroll |
| Pane Home | repo heading | Pane Repo | forward | J11, A8 | Pane Home | selected heading, scroll |
| Pane Repo | session row | Pane Session | forward | J6 | Pane Repo | selected row, scroll |
| Pane Session | repo line in the header | Pane Repo | lateral | J11 | Pane Session | selected row, scroll |
| Pane (any page but Home) | Back button | previous pane page | back | every forward move | | the previous page's focused row and scroll |
| Pane (any page) | Close button, `ctrl+x x`, or Escape at an empty prompt | prompt | up | return to work | | prompt focus and draft |

The pane has no raw key handler (the mod API gives Buttons, Tab, Enter and one-character hotkeys only), so every move is a Button: rows are Buttons, Back and Close are Buttons with hotkeys.

## Decisions Taken Here

- **Default band view:** compact. A new session, or one with nothing stored, starts compact. The choice is kept machine-wide in `~/.claude/agent-tracker/settings.json` (inside the one folder the tracker writes), so every session's band follows on its next redraw (one band everywhere, A6). Conformance F013.
- **Band order, count first:** the compact line starts with the needs-you count, then running, PRs, and this session's work last. The owner's own sketch in the design file reads `● 2 need you ◐3 … PRs 1✗` with the session after it. Conformance F016.
- **This session waiting:** it counts, and the band names it "this session" instead of its title; the oldest other waiting session follows when there is one. Conformance F008.
- **Pane entry:** the Pane button and `/tracker` always open Home, the triage queue (scene S2). `/tracker repo <name>` and `/tracker session <text>` open those pages. Conformance F006.
- **Route to a waiting session (J1):** the tracker cannot switch sessions (observe only). The band and Home name the session by its title, which is the title of its Claude Code tab. An ended session's page offers "Copy resume command" (`cd <folder> && claude --resume <id>`); a live session's page does not, because resuming a live session starts a second process on it. Conformance F005.
- **Every repo has a way in from Home:** Home ends with a "Repos" line listing every repo with a session in the last 7 days, each a button to its Repo page with its PR count. Conformance F009.
- **Next to ponytail's band:** the tracker draws its own row above the rows of other mods (`next(e)` below), shares no hotkey with them (ponytail's buttons have none), and `/tracker band off` hides it, `/tracker band on` shows it again. Conformance F011.
- **Feature states:** shown as "to do", "building", "complete", "merged", "blocked"; "done" stays the word for a session whose turn ended. Conformance F009 note.
- **Breadcrumb root:** "Home", as in the sitemap; the pane's title row says "Tracker". The breadcrumb is text; the repo button in the Session header is the control. Conformance F004.
- **Ended sessions:** not on Home (the queue stays live). The Repo page lists them under "Ended", newest first, the last 7 days.
- **Repo identity:** the git top-level path; the label is its folder name. Two repos with the same folder name get the parent folder added to both labels (`work/web-app`, `oss/web-app`). Sitemap finding SM-6.
- **Page ids singular** (`repo/<repo>`, `session/<id>`): kept to match the alias table and milestone 2's `#/repo/…` routes. Sitemap finding SM-10, recorded for conformance.
- **One entry, three names** (`/tracker`, the Pane button, the Home page): the pane's title is "Tracker", the band button says "Pane" (the design file's button set; ponytail's band has Board where this has Pane), the first page is Home. Sitemap finding SM-4, put to the owner in the validation pass.

## Open Questions

| Question | Recommended answer | Why it matters |
|---|---|---|
| Does a session that finished its turn (engine `idle`) count as needs you? | No: it is "done", shown below running. Needs you is only a permission prompt or a question the session asked. | Counting every idle session would make the band's main number always high and meaningless. |
| Is the band also shown in the session that needs the owner? | Yes, the same band in every session; the session's own state is in its header. | One band everywhere is predictable. |
