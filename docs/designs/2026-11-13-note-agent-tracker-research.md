---
title: How developers keep track of many parallel coding agents
type: note
status: active
created: 2026-11-13
tags: [agent-tracker, research]
---

# How developers keep track of many parallel coding agents

Sources were checked on 2026-11-13. Vendor blogs are marked. `claude agents --json` was confirmed locally on Claude Code 2.1.323.

## Tools

- **Claude Code agent view** (`claude agents`, research preview): one screen for sessions. `--json` prints every interactive and background session with its state. https://code.claude.com/docs/en/agent-view
- **Claude Squad:** terminal UI over tmux with a worktree per session, and preview and diff tabs. No documented attention signal. https://github.com/smtg-ai/claude-squad
- **Conductor:** Mac app with a workspace, branch, terminal and diff per task, then PR, merge and archive. https://www.conductor.build/docs/
- **Crystal:** parallel worktrees in a desktop app. Deprecated in Feb 2026 for Nimbalyst. https://github.com/stravu/crystal
- **Vibe Kanban:** kanban board with a workspace per issue and inline diff review. Being sunset. https://github.com/BloopAI/vibe-kanban
- **Sculptor:** isolated workspace per agent, with Changes and Pull Requests tabs. Research preview. https://github.com/imbue-ai/sculptor
- **Orca:** desktop and mobile app with a worktree per task and GitHub and Linear tasks in one place. Sends a phone alert when an agent needs input. https://github.com/stablyai/orca
- **Beads:** dependency-graph issue tracker for agents. `bd ready` lists unblocked work. It tracks work, not sessions. https://github.com/gastownhall/beads
- **workmux dashboard:** tmux and worktree TUI with status icons fed by hooks. https://workmux.dev/guide/dashboard/
- **cmux:** macOS terminal with a sidebar per workspace. https://github.com/manaflow-ai/cmux
- **Agent of Empires:** terminal dashboard with live preview, worktree cleanup and grouping by project. https://betterstack.com/community/guides/ai/agent-of-empires.md
- **ccusage:** token and cost reports per day, session and 5-hour block, plus a status line. https://github.com/ryoppippi/ccusage
- **Copilot Agent HQ and the repo agents tab:** sessions shown beside code, PRs and issues. https://github.blog/changelog/2026-01-26-introducing-the-agents-tab-in-your-repository
- **Cursor background agents:** states RUNNING, FINISHED, ERROR, CREATING and EXPIRED, with a Slack ping on completion. https://docs.cursor.com/background-agent/web-and-mobile
- **Warp:** a notification mailbox with tab badges. https://docs.warp.dev/agents/capabilities/agent-notifications/
- **Zed:** a threads sidebar, grouped by project. https://zed.dev/docs/ai/parallel-agents

## UI patterns

- **Agent view groups:** Pinned, Ready for review, Needs input, Working, Completed. It can regroup by directory. Space opens a peek-and-reply panel, and the tab title shows the count awaiting input.
- **workmux:** states working, waiting, done and stale. Waiting sorts first, and `R` sweeps merged worktrees.
- **cmux:** a coloured ring on the pane that needs input, jump to the latest unread, and a sidebar with branch, PR status and last notification.
- **Warp:** a bell mailbox with filters by source, day and status.
- **Unit of work:** most tools treat the worktree or workspace as the unit. Kanban (Vibe Kanban) is the minority; lists dominate.

## Practices

- **Not missing a waiting agent:** use push signals (Notification hook on `permission_prompt|idle_prompt`, plus sound or tab title) instead of polling. https://contextbolt.com/blog/claude-code-notifications/
- **What breaks with tmux alone:** one person missed permission prompts for 10+ minutes because tmux gives no blocked-pane signal. https://www.producthunt.com/p/vibecoding/running-3-4-claude-code-codex-sessions-at-once-what-breaks-first-for-you
- **How many at once:** reports range from 2-3 to start, to 4 as one person's ceiling, to 4-5 low-touch plus 3-5 high-touch. https://www.agentpatterns.ai/human/attention-management-parallel-agents/
- **Tracking asks:** a markdown file per task, rules in CLAUDE.md, a personal board. Some classify tasks before dispatch (delegated, checkpoint, human only).
- **Tracker links:** the issue key in the branch name, and "Fixes KEY" in the PR to close it on merge.
- **Redundant tasks:** no source describes a practice. Only stop, remove and archive actions exist.

## Pitfalls

- **Too many sessions:** review quality drops faster than output rises.
- **Completion pings:** they fragment focus, and forgotten tabs sit idle for days. https://dev.to/xwero/ai-agent-attention-shattering-35jn
- **Lost context:** an agent rebuilt an existing helper under a new name; one agent committed another's half-done work.
- **Stale worktrees:** about 20 after three weeks, plus their disk cost. https://understandingdata.com/posts/keeping-parallel-agentic-development-tidy-and-clean/
- **Cleanup gone wrong:** an agent told to "clean up" force-removed about 29 active worktrees with uncommitted work. https://mergify.com/blog/the-day-my-ai-agent-deleted-29-git-worktrees
- **Status flicker:** agent view "needs input" rows flipped back to working (reported fixed in 2.1.203 and 2.1.205).

## Five patterns that recur

1. One worktree per session, so the worktree is the unit you group by.
2. A small fixed set of states with "needs input" ranked first.
3. Push attention (tab count, ring, sound, phone) instead of polling, with peek-and-reply without attaching.
4. A cap of about 3-5 active agents, because attention runs out before compute does.
5. Group by repo with branch, PR state and ticket on each row, plus an explicit sweep of merged and stale worktrees.
