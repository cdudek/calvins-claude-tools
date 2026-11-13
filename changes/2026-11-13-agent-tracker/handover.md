---
type: handover
change: 2026-11-13-agent-tracker
created: 2026-11-13
author: Claude (session with Calvin Dudek)
---

# Handover: agent tracker, Stage 1

## Where things stand

- **Repo:** sdlc-run adopted (merged), kit templates cleaned of internal names (merged). Tracker is Beads, local, `.beads/` gitignored; the database sits in the main checkout and all worktrees share it.
- **Branch:** `milestone/agent-tracker-1`, cut from `origin/main`, local only. It lives in the current worktree, not under `<repo>/.worktrees/`, because the session runs in a workspace-manager worktree.
- **Beads:** project epic `cct-83h` "agent tracker" (in progress); milestones `cct-83h.1` usable inside Claude (in progress), `cct-83h.2` web page, `cct-83h.3` insights and links.
- **Design:** `docs/designs/agent-tracker.md` (the plan, with a Milestones section) and `docs/designs/2026-11-13-note-agent-tracker-research.md`; `INDEX.md` written.
- **This change:** `decisions.json` (L, feature, milestone new `agent-tracker-1`, project new `agent-tracker`, no project branch), `asks/2026-11-13/` (the owner's brief and two ponytail band screenshots). `intent.md` and `milestone.md` were being drafted when this was written.

## Decisions the owner made

- **Surfaces:** a mod with a band like ponytail's (details and compact views; Copy, Pane, Board buttons) and a drill-in pane, plus a web page instead of a terminal UI. The page is one self-contained HTML file the mod writes and opens, like ponytail's board, kept live by rewrites and a self-reload.
- **Data:** fully standalone. Live sessions from `claude agents --json`; the mod adds asks, usage, errors and retries per session.
- **Model calls:** always `haiku`.
- **Observe, never steer:** the intervention rules (hidden notes, automatic continue, queue decisions) were added, then removed by the owner.
- **Layout:** the triage queue (needs you first) is the favourite.
- **Also in scope:** "you should know" and "decided without you" items; a compact view; a band header naming the repo, the work and what runs in the session (a `/goal`, subagents, background tasks).
- **Works without sdlc-run:** sdlc-run change folders only add detail.

## Next

1. Confirm `intent.md` with the owner (touchpoint one), commit `changes(2026-11-13-agent-tracker): intent confirmed by Calvin Dudek`.
2. Stage 2 UX plan (size L), Stage 3 facts, Stage 4 plan, then the one gate.
3. `/goal` builds milestone 1.

## Open, not verified

- Which of the `claude agents --json` states `blocked` and `waiting` means a permission prompt.
- When a `/goal` ends, as a mod sees it.
- Whether a mod can call a connected MCP tool (needed for Linear state in milestone 3).
- The local CI gate (`scripts/ci-local` and its pre-push hook) is not installed in this repo yet.
