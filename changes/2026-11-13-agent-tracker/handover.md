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
- **This change:** `decisions.json` (L, feature, milestone new `agent-tracker-1`, project new `agent-tracker`, no project branch), `asks/2026-11-13/` (the owner's brief and two ponytail band screenshots). `intent.md` approved by Calvin Dudek and committed; `milestone.md` lists features 0 to 4 (sync, collector, backfill and scans, band, pane); `facts.md` and `plan.md` are template drafts so the guardrail test passes.

## Decisions the owner made

- **Surfaces:** a mod with a band like ponytail's (details and compact views; Copy, Pane, Board buttons) and a drill-in pane, plus a web page instead of a terminal UI. The page is one self-contained HTML file the mod writes and opens, like ponytail's board, kept live by rewrites and a self-reload.
- **Data:** fully standalone. Live sessions from `claude agents --json`; the mod adds asks, usage, errors and retries per session.
- **Model calls:** always `haiku`.
- **Observe, never steer:** the intervention rules (hidden notes, automatic continue, queue decisions) were added, then removed by the owner.
- **Layout:** the triage queue (needs you first) is the favourite.
- **Also in scope:** "you should know" and "decided without you" items; a compact view; a band header naming the repo, the work and what runs in the session (a `/goal`, subagents, background tasks).
- **Works without sdlc-run:** sdlc-run change folders only add detail.

## Next

1. Stage 2 UX plan (size L), Stage 3 facts, Stage 4 plan, then the one gate.
2. `/goal` builds milestone 1.

## Open, not verified

- Which of the `claude agents --json` states `blocked` and `waiting` means a permission prompt.
- When a `/goal` ends, as a mod sees it.
- Whether a mod can call a connected MCP tool (needed for Linear state in milestone 3).
- The local CI gate (`scripts/ci-local` and its pre-push hook) is not installed in this repo yet.

## Design references

- **Board mockups:** the owner reviewed terminal mockups of the triage layout, the band (details and compact), the drill-in pages and the you-should-know section. They were local HTML, not in the repo; Stage 2 redraws what it needs into `spec/`.
- **Ponytail's band:** its hooks module is the pattern for the band and the board file (a `ui.render` hook on `AbovePrompt`, a `details` toggle in `$.store`, an SVG on desktop, `board.html` written with `$.fs.write` and opened with `open`).
