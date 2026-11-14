# Agent tracker sitemap (agent-tracker-4: session cleanup)

Scope of this file: the change `2026-11-14-tracker-session-cleanup`. It lists only the pages and command words this change touches. The pane's other pages (`repo/<repo>`, `milestone/...`, `feature/...`, `note/...`, the not-found page) and the two band views are not touched and are not repeated. Milestone 1's sitemap is [the earlier spec](../../2026-11-13-agent-tracker/spec/sitemap.md). The whole-product `docs/ux/sitemap.md` still says "nothing built"; it is stale and is not edited here.

Written by hand, not by forking `cct:ux-sitemap-create`: the repo has no router (`docs/ux/setup.md`: "Route source: none in code yet"), so the as-built rows come from the pane's own page union and its handlers, each with `file:line`.

## As built

Read from `plugins/agent-tracker/hooks/tracker/` on `milestone/agent-tracker-4` at `935c8d6` (2026-11-14). One locale (`en`). The surfaces are not URLs: the pane has internal page ids, and the prompt has one command, `/tracker`, with words. The Board (`#/...` routes) is a local file and is out of this change's pages (N9 in the brief).

### Pane

**Navigation:** Back and Close on every page but Home (Close on Home); the breadcrumb on each page is a row of Buttons (`pane/view.tsx`); no tabs.

**Command words** (`pane.tsx:115`, `core/words.ts:56`, `:61`): none (Home), `session <text>`, `repo <text>`, `details`, `compact`, `copy`, `web`, `band on`, `band off`. Any other word answers with the help line.

| Route | Label (en) | Type | Tabs -> header primary | Reached from | Source |
|---|---|---|---|---|---|
| `home` | Agent tracker | home | - -> none | Pane button on the band; `/tracker`; Back from any page; the Home crumb | `core/pane-model.ts:20`, `:174`; `pane.tsx:108`; `band.tsx:108` |
| `session/<sessionId>` | the session title | record | - -> none (Copy resume command, shown on every session today, is secondary) | a session row or a task row on Home; a session row on Repo; `/tracker session <text>` | `core/pane-model.ts:21`; `core/session-model.ts:37`; `pane.tsx:90`, `:122` |

**Query params:** none.

**Breadcrumb and Back.** Session: `Home › <repo> › <title>` (`core/session-model.ts:100`); Back goes to the previous page with the focused row restored (`pane.tsx:64`).

**States as built.** `home`: loading; stale; partial; with and without tasks. `session/<sessionId>`: any state (needs you, running, done, ended), without the mod (from the transcript), not found. A session whose row has no `pid` shows as needs you today (`core/states.ts:46`); that is what this change fixes.

**Redirects:** none.

### Error pages

| Where | What it shows | Way back |
|---|---|---|
| `session/<sessionId>` for an id that matches nothing | "No session matches ..." (`core/words.ts`, `sessionNotFound`) | Home crumb |

## E-mail and external links

None. The tracker sends no mail. The only link out is a PR number, which opens GitHub; this change adds none.

## Proposed

**Status: proposed, 2026-11-14.** Nothing here is accepted until a decision file in `docs/designs/` says so. Items marked **decide** are open choices.

### The principles it rests on

| Principle | What it forces here |
|---|---|
| Acting only on the owner's explicit action (N4) | Every new control is a button the owner presses, or a command the owner types. Nothing runs on a timer or on first sight. |
| A running session is never touched (N1) | A live session's page draws no Clear, only a line. The tidy pass collects ended items only. |
| One canonical address per object (RC-7) | No page is added. Clear's result stays on `session/<sessionId>`. |
| Dashboards stay calm; open tasks lead | Home gains one dim line, last. The band gains nothing. |
| The most frequent job needs no move | The needs-you list is fixed at its source (state), so J1 needs no control at all. |

### Pane and prompt navigation

| # | Item | Group | Badge | Why here |
|---|---|---|---|---|
| 1 | Clear (button on `session/<sessionId>`, ended sessions with something left) | page action | none | J3, A3, A4 |
| 2 | Remove worktree, Keep worktree (offer on `session/<sessionId>`, after Clear); Reopen tasks (after Clear, while on the page) | page action | none | J4, A4 |
| 3 | Tidy (button, last line of `home`, only when something is idle 30 days or more) | pane | none | J5, A1, A4 |
| 4 | `/tracker tidy` (prompt command) | prompt | none | J5, A6 |

**Gone from the navigation, and why:**

- **A tidy button on the band:** the compact band is already full (milestone 1: 125 cells needed, 115 available; segments drop from the right) and the owner's rules say spaced buttons and a calm band (N8).
- **`/tracker clear <session>`:** the act should be taken with the session's tasks and worktree in view, so it has no one-shot command (Decisions Taken Here in `ia.md`).
- **Clear on Home rows:** Home stays a list; the act is on the page of the one session.

### Settings

None. No page holds a setting. A closed task is kept in `settings.json` as before (`closed`); that is storage, not a setting the owner edits.

### Pane routes

| Route | Label (en) | Type | Tabs -> header primary | Reached from |
|---|---|---|---|---|
| `home` | Agent tracker | home | - -> none (Tidy, last line, is secondary) | unchanged |
| `session/<sessionId>` | the session title | record | - -> Clear (ended sessions; none for a live one) | unchanged; plus `/tracker session <text>` |

**Query params:** none.

**Depth.** `home` level 1, `session/<sessionId>` level 3 by breadcrumb with its repo, unchanged (SM-5 passes).

**States to capture (the delta):**

- **`home`:** Tidy line absent; Tidy line with sessions; with worktrees; with both; narrow (a dock below 70 columns).
- **`session/<sessionId>`:** live interactive; live background; ended with something to clear; confirm-free Clear result (cleared; partly cleared; failed); worktree offer; worktree stays (each reason); nothing to clear; session list unreadable (Clear withheld).

### Pages whose content changes

| Page | Change | Why |
|---|---|---|
| `home` | NEEDS YOU, the band count and the needs-you task rows stop counting a session with no `pid`. One dim Tidy line at the bottom. | J1, J5 |
| `session/<sessionId>` | First line reads "started <when> · last activity <ago>" (was "since <clock>"). Actions: Clear added; Copy resume command shown for ended sessions only. Worktree line, result lines, worktree offer added. | J2, J3, J4, J6 |

## Changes from as built

| # | Change | Why (job story, law, owner's words, finding) | Findings |
|---|---|---|---|
| 1 | `session/<sessionId>`: add Clear, the worktree offer and their result lines | J3, J4; "Clear button" (A6) | none |
| 2 | `session/<sessionId>`: Copy resume command only for ended sessions | milestone 1 F005; the Board does the same (`core/board-html.ts:144`) | none |
| 3 | `home`: add the Tidy line | J5; "Supervisor /tracker tidy" (A6) | SM-3: Tidy has two ways in (the line and the command) |
| 4 | `/tracker`: add the word `tidy`; the help and hint strings name it | J5 | none |
| 5 | State rule: a row without `pid` is ended | J1; A5 | none |

## Redirects

Additive only. None: no address moves or is removed (SM-11 has nothing to run on).

| Old address | New address | Carries |
|---|---|---|
| none | none | none |

## E-mail links that change

None.

## Checks

SM-1 to SM-12 on the two pages in scope. No finding above Low.

- **SM-3 (Low):** the Session page has two visible ways in (Home rows, Repo rows) and the command; the Clear action has one (the page's button). Accepted: the act should be hard to reach by accident.
- **SM-4:** Home's page id is `home`, its title "Agent tracker"; milestone 1 called the title "Tracker" and the breadcrumb root "Home". One place, two names, already in the built code. Not changed here; listed for the next audit.
- **SM-7 (Low):** the Home crumb reads "Home" on other pages and "Agent tracker" on Home itself. Same cause as SM-4.
