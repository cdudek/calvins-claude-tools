---
linear: none
type: intent
change: 2026-11-13-agent-tracker
design: docs/designs/agent-tracker.md
author: Calvin Dudek
status: approved
reviewed_by: Calvin Dudek
approved_at: 2026-11-13T22:29
created: 2026-11-13
---

# Intent: Agent tracker, one view of every repo, worktree and session

> Give the owner one local view of what every Claude Code session works on and which one needs them; milestone 1 delivers it inside Claude.

This change is milestone 1 of project agent-tracker, which has three milestones. The intent covers the whole project's outcome. Milestone 1 delivers first: the collector, the backfill, the band and the pane. Milestone 2 (the web page) and milestone 3 (insights and links) follow as their own changes.

## Asks

| # | Date | Source | Words | Screen | Resources |
|---|---|---|---|---|---|
| A1 | 2026-11-13 | owner, chat | "I want more cloud mods. When can we do it? What can we do? What can we do visually? Should we have a TUI ..." (excerpt, full brief linked) | none | [owner-brief](asks/2026-11-13/owner-brief.md) |
| A2 | 2026-11-13 | owner, chat | "we should always use a cheap model for that, can we specify that?" | none | none |
| A3 | 2026-11-13 | owner, chat | "can we also include something like the \"you should know\" mod as well as decisions that were made without me. Does this make sense?" | none | none |
| A4 | 2026-11-13 | owner, chat | "there should also be a feature to compact it" | band | none |
| A5 | 2026-11-13 | owner, chat | "also I think I'd rather have a webpage then a tui" and "like what ponytail has" | web page | none |
| A6 | 2026-11-13 | owner, chat | "ponytail also has this little menu. if you click on compact you ge tthis one liner, and when you click on board you get the web page. we could have something similar for us." | band | [details view](asks/2026-11-13/ponytail-band-details.png), [compact view](asks/2026-11-13/ponytail-band-compact.png) |
| A7 | 2026-11-13 | owner, chat | "I also wonder if it could actually show the repo or project name, and description of what is currently developed. and whether a goal is running or something is running on the current session?" | band | none |
| A8 | 2026-11-13 | owner, chat | "How does the work I asked for per repository work? Can I explore it, dig into one, and navigate inside this app? I suppose I can but what does the detail page look like? What are milestones and this type of milestone, and do milestones have subtasks?" | pane, web page | none |
| A9 | 2026-11-13 | owner, chat | "I like the agent. The triage queue has the cleanest interface in my opinion yet but I am not sure." | pane | none |
| A10 | 2026-11-13 | owner, chat | "it doesnt do this automatically does it? so it can also work without sdlc-run?" | none | none |
| A11 | 2026-11-13 | owner, dialog | "1 and 2" (surfaces: a pane mod and a standalone UI, later replaced by the web page per A5) | none | none |
| A12 | 2026-11-13 | owner, dialog | "Fully standalone" (data layer: no dependency on other memory or workspace tools) | none | none |

A4 was answered by the compact view of the band. A withdrawn ask is recorded under Constraints.

## Job stories

| # | When … | I want to … | So I can … | Evidence |
|---|---|---|---|---|
| J1 | I run sessions across several repos and worktrees | see every session and which ones wait for me | answer the blocked one first | reported — A1 |
| J2 | I type a prompt in a session | have each ask kept in order as a task or a question | see what I asked for, chronologically | reported — A1 |
| J3 | A long loop with a plan runs | see the breakdown of milestones and features and where they stand | know how far the work is | reported — A1, A8 |
| J4 | I want to know how a session is doing | see tokens, tool errors and retries per session | spot where it struggles | reported — A1 |
| J5 | I open the prompt of any session | see a compact line that counts what needs me | stay aware without leaving my work | reported — A4, A6 |
| J6 | I want details | switch the band to details, or open the pane | dig from a count to one item | reported — A6, A8, A9 |
| J7 | I look at a session | see its repo, project, what is being developed, and whether a goal or other work runs | tell sessions apart at a glance | reported — A7 |
| J8 | An agent finishes a turn | see what I should know and what it decided without me | overrule a call before it spreads | reported — A3 |
| J9 | I use a repo without sdlc-run | get the same view from sessions, git, gh and bd alone | not depend on one process | reported — A10, A12 |
| J10 | I forget to check on sessions that waited | get pushed attention, not a list I must poll | not lose time to a blocked agent | assumed |
| J11 | I want one place for open PRs | see each PR's state next to its session | know what is left to merge | reported — A1 |
| J12 | I read tracked work for one repo | follow it from repo to milestone to feature | see what is done and unfinished | reported — A8 |

## Success measure

How we know after release that it worked. One number, where it is read, and the target.

- **Measure:** spot checks where the band's running count equals `claude agents --json` — **read in:** a by-hand check — **target:** 5 of 5 by 2026-12-04

## Problem

- **What is wrong or missing:** no one place shows which sessions run, which wait, what was asked and where the work stands.
- **Who feels it:** the owner, who runs agents across several repos and worktrees at once.
- **Evidence:** A1 in the owner's words; the research note records people missing blocked sessions for ten minutes or more.

## Proposed outcome

What is true when the whole project is done. Milestone 1 delivers the first four.

- Every session on the machine appears, with its repo, work and state, even when it has no mod.
- Each prompt is kept in order as a task or a question, classified with a cheap model.
- A one-line band in every session counts what needs the owner, and a details view and a pane open from it.
- The band's header names the repo, the project and milestone, and what runs: a goal, subagents, background tasks.
- A local web page shows the same screens, with links instead of keys (milestone 2).
- Plan progress, ticket links and superseded tasks show on the page, and "you should know" and "decided without you" items collect there (milestone 3).
- It works in a repo without sdlc-run, and it never writes to the agent.

## Affected users and systems

| Kind | Name | How |
|------|------|-----|
| users | the owner | sees all sessions, work and attention from any session |
| service | the Claude Code session mod | adds a band and a pane, and one per-session file |
| data | `~/.claude/agent-tracker/` | new folder with one file per session, the only store |
| service | `claude agents --json`, git, gh, bd | read only, polled by the collector |
| data | `~/.claude/projects/*/*.jsonl` | read only, for sessions without the mod |

## Constraints

- **Observe only:** the tracker never steers the agent: no hidden notes, no automatic continue.
- **Withdrawn ask:** the owner dropped a rule about continuing a long task after an interruption: "ok never mind lets remove this intervention rules".
- **In scope from that thread:** recording each ask as task or question, in order.
- **Cheap model:** every model call pins `haiku`, from one constant, per A2.
- **Standalone:** no dependency on other memory or workspace tools, per A12.
- **Must not change:** the existing `cct` skills, agents and their naming tests.
- **Deadline:** none
- **Rules that apply:** the public-repo rule and the never-publish-to-claude.ai rule in `CLAUDE.md`. No internal names, emails or local paths.

## Open questions

1. Which of the states `blocked` and `waiting` in `claude agents --json` means a permission prompt? Unverified; the collector needs it to rank attention.
