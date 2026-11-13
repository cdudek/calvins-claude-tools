---
title: Agent tracker: one view of every repo, worktree, session and task
type: design
status: active
created: 2026-11-13
tags: [agent-tracker, mod, claude-code]
---

# Agent tracker: one view of every repo, worktree, session and task

## Goal

See, from any Claude Code session or one terminal tab, what is happening across every repo and worktree: which sessions run, which need attention, what was asked (tasks, in order, apart from questions), plan progress, tokens, struggles, and open PRs with their state.

## Decisions

- **Surfaces:** a Claude Code mod (a band above the prompt, built like ponytail's, and a pane to drill in) and a local web page. Both read one store. The web page replaced the terminal UI. (Owner, 2026-11-13.)
- **Data layer:** fully standalone. No dependency on any other memory or workspace tool; everything comes from the mod's own events, transcripts, git, gh and bd. (Owner, 2026-11-13.)
- **Live sessions come from `claude agents --json`** (Claude Code 2.1.323): every interactive and background session with `sessionId`, `cwd`, `name`, `startedAt` and `kind`. Interactive sessions carry `status` (`idle`, `busy`, `waiting`, plus a `waitingFor` string); background sessions carry `state` (`working`, `blocked`, `done`, the last only with `--all`). `waiting` and `blocked` are needs you, `busy` and `working` are running, `idle` is done. That covers sessions without the mod, so the mod's hooks only add what the engine does not list: asks classified task or question, retries and tool errors. (2026-11-13, checked on 2.1.323.)
- **Every model call uses `haiku`:** task-or-question (`$.model.classify(text, labels, { model: "haiku" })`) and the superseded check (`$.model.complete({ model: "haiku", ... })`). One constant `MODEL` in the shared file, used by the mod's two calls. The backfill makes no model call: it marks each ask "not classified". The classify default is already the engine's small fast model, but it is pinned so a settings change cannot raise the cost. (Owner, 2026-11-13.)
- **Store:** one JSON file per session under `~/.claude/agent-tracker/sessions/<sessionId>.json`, written only by that session's mod, so no write races. The mod API has no append and no rename, so the file is rewritten whole, with the asks capped at 200. SQLite only if queries outgrow a folder scan. The folder also holds `transcripts/<sessionId>.json` (backfill, only when no `sessions/` file exists), `settings.json` (the band view and the hidden flag, one for every session), and the lease pair `poller.json` and `agents.json`. The git and gh scan of a session's own repo sits inside that session's file, as its `scan` block.
- **Collector:** one poller does the polling, by lease. A session's mod takes `poller.json` when none is fresh (heartbeat under 15 seconds), runs `claude agents --json` every 5 seconds and writes `agents.json`; every other session reads `agents.json`. A failed or old read shows the stale state, never "ended".
- **Code layout:** pure aggregation (parse transcripts, fold events, rank attention) in one shared module, `plugins/agent-tracker/hooks/tracker/core/`, with no I/O: it imports only itself and types, and takes time as a parameter. The I/O files beside it (`store.ts`, `collector.ts`, `asks.ts`, then `backfill.ts`, `scan.ts`, `band.tsx`, `pane.tsx`) feed it through `$.process.run` and `$.fs`, and the mod builds the page from it too. Repo home: `plugins/agent-tracker/`; CLAUDE.md names both plugins.
- **Needs you includes a question in text:** a turn that ends with a plain-text question to the owner counts as needs you. The mod checks with `haiku` at `turn.complete`, reading the last assistant message from the session's transcript; never from the classic `Stop` hook, which managed machines skip. Sessions without the mod stay done. (Owner, 2026-11-13.)
- **Page ids are singular** (`repo/<repo>`, `session/<id>`), in the pane and in the web page's `#/…` routes: exception EX-1 in `docs/ux/exceptions.md`. (Owner, 2026-11-13.)
- **Accessibility:** WCAG 2.2 AA as a target, not a legal floor; the EAA does not apply. (Owner, 2026-11-13.)
- **Band, milestone 1:** the view and the hidden flag are kept in `settings.json`, not `$.store`, so every session follows. The Board button belongs to milestone 2 and the you-should-know columns to milestone 3.
- **Milestone 1's band and pane are specified** in `changes/2026-11-13-agent-tracker/spec/` (screens, states, words). Where step 3 and 3a below differ, the spec wins: the needs-you count goes first, a done count shows, no Board button before milestone 2, and no you-should-know columns before milestone 3.
- **Web page, the way ponytail's board works:** no server and no port. The mod writes one self-contained `~/.claude/agent-tracker/board.html` (inline CSS and script, the data as an inline JSON block, names set as text, never as HTML) with `$.fs.write` and opens it with `open`. `/tracker web` builds it fresh and opens it. Unlike ponytail's snapshot, it stays live: every running mod rewrites it on its timer and the page reloads itself every few seconds, keeping its `#/…` route. With no session open the page shows its last build and its age.

## What the mod can reach (verified against the 2.1.322 types)

- **Hooks:** `prompt.submit`, `turn.start`, `turn.complete`, `tool.call` (results and errors), `agent.spawn`, `session.start`, `session.end`, and every classic hook as `classic.<Name>` (`PermissionRequest`, `Notification`, `Stop`, `SubagentStop`).
- **Calls:** `$.session.usage()` (context %, cost, rate limits), `$.agent.list()` (subagents and status), `$.model.classify(text, labels)`, `$.process.run` (git, gh, bd; 30 s default), `$.fs.read/write/list/stat` (4 MiB per read), `$.clock.every`, `$.ui.open/status/toast/notify`.
- **Limit:** a mod sees its own session live. Sessions without the mod appear only through their transcripts.

## Milestones

- **agent-tracker-1, usable inside Claude:** steps 1, 2, 3 and 3a. Change `changes/2026-11-13-agent-tracker/`, Beads `cct-83h.1`.
- **agent-tracker-2, the web page:** step 4. Beads `cct-83h.2`.
- **agent-tracker-3, insights and links:** steps 5 to 8. Beads `cct-83h.3`.

## Work

- [ ] **1. Collector.** Poll `claude agents --json` for live sessions and their state. The mod adds per session: asks, usage, tool error and retry counts, subagents. Each ask is classified `task` or `question` with `$.model.classify`; tasks keep their order. Test: a `*.test.ts` seeding events and checking the file.
- [ ] **2. Backfill and scan.** Read `~/.claude/projects/*/*.jsonl` for sessions without the mod (tokens per message, branch, cwd, title, tool errors). Scan the session's own repo with `git worktree list` and `gh pr list --json` (state, checks, reviews, mergeable). No `bd` scan in milestone 1: nothing from `bd` shows. Test: fixture transcripts.
- [ ] **3. Pane.** Sections: Attention (waiting sessions first), Active sessions by repo and worktree, Tasks in order with status, PRs with state. `/tracker` opens the pane.
- [ ] **3a. Band, like ponytail's.** A `ui.render` hook on `AbovePrompt` in every session, with two views switched by a button and kept in `$.store` (ponytail's `details` toggle). *Details*: columns needs you, running, you should know, decided without you, PRs; each a label, a bold count and one dim line (the oldest waiting session, the top item); on the desktop surface the columns are an SVG, as ponytail draws them. Buttons on the right: Copy (the state as Markdown), Pane, Board (builds and opens the web page), Compact. *Compact*: one line, `● 2 need you ◐3 !2 ◆2 PRs 1✗ 1↓` plus the oldest waiting session, then Pane, Board, Details. A header row names this session's work: the repo (`$.session.repo().name`), the project and milestone when the session works in an sdlc-run change (its slug, the one sentence at the top of `milestone.md`, feature progress), otherwise the session title from `claude agents --json` and the branch; then what runs in it: a `/goal` and its age (seen at the `/goal` command or the `ProposeGoal` tool call; when a goal ends is not verified yet), the subagents (`$.agent.list()`), and the background tasks and wake-ups the classic `Stop` hook lists (`background_tasks`, scheduled crons); on machines that skip classic hooks these come from `$.agent.list()` and the transcript instead, or are not shown. It stacks with other bands (ponytail's) by rendering `next(e)` below its own row. No status line entry: the compact band is the always-on line. The web page has its own compact toggle.
- [ ] **4. Web page.** The same screens as the pane (Home, Repo, Milestone, Feature, the item views), with links instead of keys, the breadcrumb as the URL (`#/repo/web-app/milestone/design-tokens-1`), a compact toggle, and the tab title showing the count that needs you. Reloads itself every few seconds from the file the mods rewrite. Test: the built HTML against fixtures (data present, names escaped), and one load in a browser.
- [ ] **5. Plan progress.** Find the plan file a session works from (a `/goal` or plan path in its asks, or `.claude/plans/*.md` in its worktree) and count checked against open boxes.
- [ ] **6. Ticket links.** Extract ticket keys from branch names, PR bodies and asks (Linear-style `ABC-123`, Beads ids, GitHub issue URLs) and show them on the session, task and PR.
- [ ] **7. Superseded tasks.** At `turn.complete`, one model pass over open tasks proposes "superseded by <later ask>". Shown as a proposal; only the owner closes a task.

## Research

What other tools do and the pitfalls people report: [the research note](2026-11-13-note-agent-tracker-research.md). What it changes here: rank `needs input` first in a small fixed set of states, push attention (tab title count, one notification) instead of making you poll, peek at a session without attaching, show branch, PR and ticket on every row, and offer an explicit sweep of merged and stale worktrees that never force-removes.

- [ ] **8. You should know, and decided without you.** Two kinds of item, collected without asking the agent anything. *You should know*: side effects, risks, odd findings, skipped steps. *Decided without you*: calls the agent made itself (a library, a default taken, a change to the plan's order). Sources: at the classic `Stop` hook, `haiku` reads `last_assistant_message` and returns items of both kinds or none; in sdlc-run repos, `questions.md` (each open question with the default taken) and the plan's `## Revisions`, read as files. Each item keeps repo, session, time, kind, one line of text and `unseen` or `seen`. Shown under "Needs you" on Home (unseen first), filtered on the repo and milestone pages, and counted in the band. Keys: mark seen; copy a reply to paste into that session to overrule. Test: fixture turns with and without items, and a `questions.md` fixture.

## Open questions

- Linear state (not only the key) needs the Linear API or MCP. Whether a mod can call a connected MCP tool is unverified; check before step 6.
- Answered 2026-11-13: a pane the mod opens on its own is placed only from 144 columns (110 for one the owner opened before); milestone 1 opens it only on `/tracker` or the Pane button, which places it at any width.

## Checks

- `claude plugin validate --strict plugins/agent-tracker` (it type-checks the hooks module, its imports and the `*.test.ts` files) and `claude plugin test plugins/agent-tracker` (it runs each test file and does not type-check).
- `python3 -m unittest discover -s tests` and `scripts/run-plugin-tests.sh` (repo rules: naming, public repo, no hosted publishing).
