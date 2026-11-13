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
- **Live sessions come from `claude agents --json`** (Claude Code 2.1.323): every interactive and background session with `sessionId`, `cwd`, `name`, `startedAt` and `state` (`busy`, `idle`, `blocked`, `waiting` seen on 2026-11-13). That covers sessions without the mod, so the mod's hooks only add what the engine does not list: asks classified task or question, retries and tool errors. Which of `blocked` and `waiting` means a permission prompt is not verified yet. (2026-11-13, after the research note.)
- **Every model call uses `haiku`:** task-or-question (`$.model.classify(text, labels, { model: "haiku" })`) and the superseded check (`$.model.complete({ model: "haiku", ... })`). One constant `MODEL` in the shared file; transcript backfill outside a session uses `claude -p --model haiku`. The classify default is already the engine's small fast model, but it is pinned so a settings change cannot raise the cost. (Owner, 2026-11-13.)
- **Store:** one JSON file per session under `~/.claude/agent-tracker/sessions/<sessionId>.json`, written only by that session's mod, so no write races. The mod API has no append, so the file is rewritten whole, with the event list capped. SQLite only if queries outgrow a folder scan.
- **Code layout:** pure aggregation (parse transcripts, fold events, rank attention) in one shared TypeScript file with no I/O. The mod feeds it through `$.process.run` and `$.fs`, and the mod builds the page from it too. Repo home: `plugins/agent-tracker/` (mod and page builder); CLAUDE.md's "one plugin" line gets updated when the mod lands.
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
- [ ] **2. Backfill and scan.** Read `~/.claude/projects/*/*.jsonl` for sessions without the mod (tokens per message, branch, cwd, title, tool errors). Scan repos with `git worktree list`, `gh pr list --json` (state, checks, reviews, mergeable) and `bd list --json` where a `.beads` folder exists. Test: fixture transcripts.
- [ ] **3. Pane.** Sections: Attention (waiting sessions first), Active sessions by repo and worktree, Tasks in order with status, PRs with state. `/tracker` opens the pane.
- [ ] **3a. Band, like ponytail's.** A `ui.render` hook on `AbovePrompt` in every session, with two views switched by a button and kept in `$.store` (ponytail's `details` toggle). *Details*: columns needs you, running, you should know, decided without you, PRs; each a label, a bold count and one dim line (the oldest waiting session, the top item); on the desktop surface the columns are an SVG, as ponytail draws them. Buttons on the right: Copy (the state as Markdown), Pane, Board (builds and opens the web page), Compact. *Compact*: one line, `● 2 need you ◐3 !2 ◆2 PRs 1✗ 1↓` plus the oldest waiting session, then Pane, Board, Details. A header row names this session's work: the repo (`$.session.repo().name`), the project and milestone when the session works in an sdlc-run change (its slug, the one sentence at the top of `milestone.md`, feature progress), otherwise the session title from `claude agents --json` and the branch; then what runs in it: a `/goal` and its age (seen at the `/goal` command or the `ProposeGoal` tool call; when a goal ends is not verified yet), the subagents (`$.agent.list()`), and the background tasks and wake-ups the classic `Stop` hook lists (`background_tasks`, scheduled crons). It stacks with other bands (ponytail's) by rendering `next(e)` below its own row. No status line entry: the compact band is the always-on line. The web page has its own compact toggle.
- [ ] **4. Web page.** The same screens as the pane (Home, Repo, Milestone, Feature, the item views), with links instead of keys, the breadcrumb as the URL (`#/repo/web-app/milestone/design-tokens-1`), a compact toggle, and the tab title showing the count that needs you. Reloads itself every few seconds from the file the mods rewrite. Test: the built HTML against fixtures (data present, names escaped), and one load in a browser.
- [ ] **5. Plan progress.** Find the plan file a session works from (a `/goal` or plan path in its asks, or `.claude/plans/*.md` in its worktree) and count checked against open boxes.
- [ ] **6. Ticket links.** Extract ticket keys from branch names, PR bodies and asks (Linear-style `ABC-123`, Beads ids, GitHub issue URLs) and show them on the session, task and PR.
- [ ] **7. Superseded tasks.** At `turn.complete`, one model pass over open tasks proposes "superseded by <later ask>". Shown as a proposal; only the owner closes a task.

## Research

What other tools do and the pitfalls people report: [the research note](2026-11-13-note-agent-tracker-research.md). What it changes here: rank `needs input` first in a small fixed set of states, push attention (tab title count, one notification) instead of making you poll, peek at a session without attaching, show branch, PR and ticket on every row, and offer an explicit sweep of merged and stale worktrees that never force-removes.

- [ ] **8. You should know, and decided without you.** Two kinds of item, collected without asking the agent anything. *You should know*: side effects, risks, odd findings, skipped steps. *Decided without you*: calls the agent made itself (a library, a default taken, a change to the plan's order). Sources: at the classic `Stop` hook, `haiku` reads `last_assistant_message` and returns items of both kinds or none; in sdlc-run repos, `questions.md` (each open question with the default taken) and the plan's `## Revisions`, read as files. Each item keeps repo, session, time, kind, one line of text and `unseen` or `seen`. Shown under "Needs you" on Home (unseen first), filtered on the repo and milestone pages, and counted in the band. Keys: mark seen; copy a reply to paste into that session to overrule. Test: fixture turns with and without items, and a `questions.md` fixture.

## Open questions

- Linear state (not only the key) needs the Linear API or MCP. Whether a mod can call a connected MCP tool is unverified; check before step 6.
- Whether a pane may open on its own: the mod opens one only at 110+ columns, otherwise it waits for `/tracker`.

## Checks

- `claude plugin validate plugins/agent-tracker`, `tsc -p plugins/agent-tracker`, `claude plugin test plugins/agent-tracker`.
- `python3 -m unittest discover -s tests` and `scripts/run-plugin-tests.sh` (repo rules: naming, public repo, no hosted publishing).
