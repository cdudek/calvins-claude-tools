---
linear: none
type: intent
change: 2026-11-14-tracker-session-cleanup
design: docs/designs/agent-tracker.md
author: Calvin Dudek
status: draft
reviewed_by: null
approved_at: null
created: 2026-11-14
---

# Intent: Tracker shows only live sessions and clears dead ones

> Let the owner trust the tracker's needs-you list and clear dead sessions and their merged worktrees from the tracker, one at a time or in one tidy pass.

This change is milestone agent-tracker-4 of project agent-tracker (Beads cct-83h.4). It builds on milestone 1, which reached `main` on 2026-11-14.

## Asks

| # | Date | Source | Words | Screen | Resources |
|---|---|---|---|---|---|
| A1 | 2026-11-14 | owner, chat | "can we check which worktrees and open sessions we no longer need e.g. something that might happend over a month ago" | none | none |
| A2 | 2026-11-14 | owner, chat | "if you look at the agent tracker as well" | none | none |
| A3 | 2026-11-14 | owner, chat | "I also want to close this sessions. is this something I can do?" | band, "Your tasks not done" | an inline screenshot of the band, not saved as a file |
| A4 | 2026-11-14 | owner, chat | "I wonder if there's also a way to, maybe from the panel, close a session and delete a work tree or ask to do that. Or maybe there's something more meta: as a supervisor I can launch a supervisor agent that launches subagents for the specific sessions and the sessions in question can be resolved gracefully (the ones that are not running, at least)." | pane, session page | [session page](asks/2026-11-14/find-this-track-session-page.png) |
| A5 | 2026-11-14 | owner, chat | "Something is running and it's more about sessions that are old. Once I see this, like the Spotify sessions (which I don't know when I ever touched) or an SES email session, I don't think that's relevant anymore. For some weird reason your task is not done. It's breathing there, popping up new and old ones but they are actually old. Not 100% sure here" | band, session page | [session page](asks/2026-11-14/find-this-track-session-page.png) |
| A6 | 2026-11-14 | owner, dialog | "Fix the cause (Recommended), Clear button, Supervisor /tracker tidy" | band, pane | none |

## Job stories

| # | When … | I want to … | So I can … | Evidence |
|---|---|---|---|---|
| J1 | a background session has exited but Claude Code still lists it as blocked | have the tracker count it as ended, not as needing me | trust that every needs-you row is real | observed — sessions ef0cad07 (88 days), c5bbc5ff (63 days) and 4b369489 (13 days) showed as waiting with no process on 2026-11-14; A5 |
| J2 | I open the page of an old session | see when it last did anything, not when the tracker first saw it | judge at a glance whether it still matters | observed — the session page said "since 16:13" for a session idle 63 days; A5 |
| J3 | a session has ended but its asks still sit in "Your tasks not done" | clear the session and its open asks in one step from its page | stop the list from bringing back old work | observed — the samplewerk ask stayed after its session ended; reported — A3, A4 |
| J4 | a cleared session's worktree is clean and merged | remove that worktree from the same page after one confirm | clean up without opening a terminal | reported — A4 |
| J5 | many sessions and worktrees have gone stale | start one tidy pass that checks each and asks me once per batch | resolve them together without losing work | reported — A1, A4; observed — 72 worktrees and 6 sessions cleared by hand on 2026-11-14 |
| J6 | a session is still running | have Clear and tidy leave it alone | never stop work in progress by accident | reported — A4 ("the ones that are not running, at least") |

## Success measure

How we know after release that it worked. One number, where it is read, and the target.

- **Measure:** needs-you rows with no running process — **read in:** spot checks — **target:** 0 in 5 of 5 by 2026-12-05.
- **Spot check:** compare the band with `claude agents --json`.
- **No running process means:** the session's row in `claude agents --json` has no `pid`.

## Problem

- **What is wrong or missing:** exited background sessions show as waiting forever. Their age is when the tracker first saw them, and nothing clears them.
- **Who feels it:** the owner, who stops trusting the needs-you list.
- **Evidence:** on 2026-11-14 three dead background sessions (88, 63 and 13 days old) showed as waiting; the owner called the list "breathing" (A5).

## Proposed outcome

- The needs-you list holds only sessions that are alive and waiting.
- A session page shows how long the session has really been idle.
- From a session page, the owner can clear an ended or dead session and its open asks.
- When that session's worktree is clean and merged, the owner can remove it after one confirm.
- One tidy command checks every stale session and worktree and asks the owner once per batch.
- Nothing that is running, holds uncommitted work or holds unpushed commits is ever removed.

## Affected users and systems

| Kind | Name | How |
|------|------|-----|
| users | the owner | trusts the needs-you list; clears dead sessions from the tracker |
| service | `plugins/agent-tracker` | state rules, the session page, a new command |
| data | `~/.claude/agent-tracker/` session records and asks | asks can be dismissed; dead sessions stop counting |
| system | Claude Code background session list | `claude rm` removes a dead session from it; the conversation is kept |
| system | git worktrees in the owner's repos | a clean, merged worktree can be removed; its branch is kept |

## Constraints

- **Must not change:** a running session is never stopped or removed. Nothing is force-removed: no `--force`, no `-D`, no discarded changes or unpushed commits.
- **Changes an earlier rule:** the owner's words of 2026-11-13 made the tracker observe only ("ok never mind lets remove this intervention rules"). This change adds acting, but only on the owner's explicit action, with a confirm before anything that cannot be undone, and never on its own.
- **Deadline:** none.
- **Rules that apply:**
  - CLAUDE.md, public repo rule: no internal names, private repo names, people, URLs or local paths in the plugin.
  - CLAUDE.md, never publish to claude.ai: tidy output stays local.
  - CLAUDE.md, naming: any new skill or agent follows `docs/adr/0001-skill-taxonomy.md`.
  - Design decision, every model call uses `haiku`: applies to the mod's own model calls.
  - Design decision, data layer standalone: only the mod's events, transcripts, git, gh, bd and `claude` CLI.
  - Owner's worktree rule: removal never forces and keeps the branch.

## Open questions

None. The tidy pass uses Claude subagents per stale session; their model is set in the plan.
