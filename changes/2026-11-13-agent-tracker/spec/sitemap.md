# Agent tracker sitemap (milestone 1: band and pane)

Scope of this file: the change `2026-11-13-agent-tracker`, milestone 1. The whole-product file is `docs/ux/sitemap.md`; it stays empty until something is built.

## As built

Nothing. Read from the repo tree on `milestone/agent-tracker-1` at `cfe2db6` (2026-11-13): `plugins/agent-tracker/` does not exist, there is no router and no page. `docs/ux/sitemap.json` has `pages: []`. One locale (`en`, `sdlc.json` `languages`), so no locale prefix and no host.

## E-mail and external links

None, as built or proposed. The tracker sends no mail and no page in milestone 1 is linked from outside Claude Code.

## Proposed

**Status: proposed, 2026-11-13.** Nothing here is accepted until a decision file in `docs/designs/` says so. Items marked **decide** are open choices; the alternative is named in one line.

**What an address is here.** The surfaces are not URL routes. The band sits above the prompt in every session and has two views. The pane has three pages, each addressed by an internal page id: `home`, `repo/<repo>`, `session/<sessionId>`. The "Route" column holds that id. The two band views carry the ids `band/compact` and `band/details` so a tool can name them; they are views, not places you can type. `sitemap.json` writes params as `[repo]` and `[sessionId]`; this file writes `<repo>` and `<sessionId>`. Pane page ids are what follows `#/` in milestone 2's web page, so the same address works in both.

### The principles it rests on

| Principle | What it forces here |
|---|---|
| Observe only (no-go N1; owner: "ok never mind lets remove this intervention rules") | No page has a write action. Every move opens a page, switches a view, copies text or goes back. |
| The most frequent job needs no move (Hick's law; J1, J5) | The count and the oldest waiting session are on `band/compact` itself, not behind a click. |
| One canonical address per object (RC-7) | A session opens at `session/<sessionId>` from Home and from Repo; a repo at `repo/<repo>` from Home and from a session. No second page for either. |
| Back returns to where you were, not to the parent (Jakob's law, as the host app does it) | Back is history-based: Repo's Back goes to Home or to the session you came from, with the row and scroll restored. |
| Every move is a button (the mod API has no raw key handler) | No page is reachable by a keyboard-only gesture; hotkeys only repeat a visible button. |
| Works without sdlc-run (J9, no-go N5) | The Session page has the same address with or without milestones; the Features section is absent, not a different page. |

### Band and pane navigation

| # | Item | Group | Badge | Why here |
|---|---|---|---|---|
| 1 | Details (button on `band/compact`) | band | none | J6, A6: one click from the count to the columns |
| 2 | Compact (button on `band/details`) | band | none | J5, A4, A6: back to one line |
| 3 | Pane (button on both band views) | band | none | J6, A8, A9: opens `home` |
| 4 | `/tracker` (prompt command) | prompt | none | J6, A8: opens `home` without the mouse |
| 5 | Repo heading (on `home`) | pane | PR count per repo | J11, A8 |
| 6 | Session row (on `home` and `repo/<repo>`) | pane | state | J2, J6 |
| 7 | Repo line in the session header | pane | none | J11 |
| 8 | Back (every pane page but `home`) | pane chrome | none | every forward move |
| 9 | Close (every pane page; `x` or `ctrl+x x`) | pane chrome | none | return to work |

**Gone from the navigation, and why:**

- **Board button:** not in milestone 1; the page it opens is milestone 2 (brief, open question 1).
- **"You should know" and "decided without you" columns and the Home section:** milestone 3 (J8); empty columns would cost band width on every prompt.

### Settings

None. Compact or details saves itself as view state (`docs/ux/interaction-guidelines.md`, "Saving and unsaved work"). No page holds a setting.

### Band and pane routes

Tabs: none on any page. "Header primary" names the one action the page's header offers; Back and Close are pane chrome on every pane page and are not repeated.

| Route | Label (en) | Type | Tabs -> header primary | Reached from |
|---|---|---|---|---|
| `band/compact` | Compact | embed | - -> Details | every session, always (default view, decided in ia.md); Compact button on `band/details` |
| `band/details` | Details | embed | - -> Compact | Details button on `band/compact`; remembered view state on a new prompt (not a visible way in) |
| `home` | Home | home | - -> none | Pane button on either band view; `/tracker`; Back from `repo/<repo>` or `session/<sessionId>` |
| `repo/<repo>` | the repo's folder name | record | - -> none | Home repo heading; repo line in a session header; Back from a session opened here |
| `session/<sessionId>` | the session title | record | - -> none (Copy resume command, ended sessions only, is secondary) | Home row; Repo session row; Back from `repo/<repo>` opened from here |

**Query params:** none on any page. Home has no search, filter, sort or named view in milestone 1, so there is no list state to put in an address (RC-9 does not apply; revisit when a filter exists). The one shareable view is the text the band's Copy button produces.

**Breadcrumb and Back.** Breadcrumb shows where the object lives: `Home`; `Home > {repo}`; `Home > {repo} > {title}`. Back goes to the previous pane page; `home` has no Back, only Close.

**Depth.** `home` is level 1, `repo/<repo>` level 2, `session/<sessionId>` level 3 by breadcrumb. No page is deeper than three (SM-5 passes).

**States to capture:**

- **`band/compact`, `band/details`:** empty (no other session); loading (first poll); error (poll failed); something needs you; nothing needs you. Details adds a column with no items.
- **`home`:** empty; loading; error; needs you; all quiet.
- **`repo/<repo>`:** with PRs; without `gh`; not found (assumption).
- **`session/<sessionId>`:** live; ended; without the mod (read from the transcript); not found (assumption).

**Route-convention differences, written once (RC-1, RC-2, RC-3).** The ids are singular (`repo/<repo>`, `session/<sessionId>`), where RC-1 and RC-2 ask for a plural list plus an id. Reason: the ids match the canonical object names in the alias table and the `#/repo/...` hash routes of milestone 2; there is no `repos` or `sessions` list page to be the plural of. Owner, 2026-11-13: "Keep singular"; recorded as EX-1 in `docs/ux/exceptions.md`. RC-3 does not apply: nothing is created.

### Pages whose content changes

None: nothing is built.

## Changes from as built

As built has no page, so every row is an addition.

| # | Change | Why (job story, law, owner's words, finding) | Findings |
|---|---|---|---|
| 1 | Add `band/compact` | J1, J5, J10; A4 ("there should also be a feature to compact it") | SM-4 |
| 2 | Add `band/details` | J5, J6, J7, J11; A6 | SM-3 |
| 3 | Add `home` | J1, J4, J9, J10; A9 | SM-4 |
| 4 | Add `repo/<repo>` | J9, J11; A8 | SM-6, SM-10 |
| 5 | Add `session/<sessionId>` | J2, J3, J4, J7; A8 | SM-10 |

## Redirects

Additive only: every old address keeps working. None: no as-built address exists, so nothing moves or is removed (SM-11 has nothing to run on).

| Old address | New address | Carries |
|---|---|---|
| none | none | none |

## E-mail links that change

None.
