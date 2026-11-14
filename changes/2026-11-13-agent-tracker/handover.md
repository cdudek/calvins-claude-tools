---
type: handover
change: 2026-11-13-agent-tracker
created: 2026-11-13
author: Claude (session with Calvin Dudek)
---

# Handover: agent tracker, Stages 1 to 4 (approved)

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

## Stage 2, UX plan (done 2026-11-13)

- **Scope:** the owner chose the full UX chain; `sdlc.json` `ux` is now `on`. `docs/ux/` holds setup, owner words, unresolved guidelines, exceptions (EX-1), glossary proposal and an empty as-built sitemap.
- **Spec:** `spec/` has brief, ia, sitemap, interaction, screens, conformance (16 findings, resolved), and validation (`verdict: ready`, `status: draft`). Reviewer notes are in `spec/review/`.
- **Owner answers, 2026-11-13:** a turn ending in a plain-text question counts as needs you, classified by haiku at turn end; WCAG 2.2 AA as a target (R2); singular page ids (EX-1); the pane's three names stay.
- **No prototype:** none drawn. Stage 4 decides whether the plan marks the UI risky (`cct:design-mockups-create spec`).

## Stage 3, facts (done 2026-11-13)

- **Facts:** `facts.md` has 126 facts (F1 to F126), `status: draft`, lint passes. Five clarify questions were decided as technical calls (Assumptions); no owner question was needed.
- **Checklist:** `checklist.md` has 46 items (gaps, ambiguities, conflicts, assumptions), all answered in the facts and ticked by a fresh reviewer.
- **Scope cuts recorded as Out of scope:** project name in the band header, a Repo-page milestone view, scheduled wake-ups, the `bd` scan.
- **Terms:** "background session" is the one word (not background task).

## Stage 4, plan (approved 2026-11-14)

- **Gate:** the owner approved spec, facts (132) and plan in plannotator; `lock.json` committed.
- **Owner answers:** keep all four features; success measure is needs-you spot checks; the milestone PR edits CLAUDE.md and the owner merges it (`decisions.json` `autoMerge: false`), so the goal ends at `GOAL … OPEN pr-<n>-not-merged-or-armed`.
- **Next:** Stage 5. Paste the kickoff prompt from `plan.md` `## Goal handover`, then its `/goal` line, in a fresh session.

## Next (earlier stages, kept for history)

0. **Stages 1 to 3 are done.** Items 1 and 3 below are done; start at Stage 4.

1. **Stage 3 facts:** every fact cites asks, names its screen or state and its E2E tag; the "Fact" column of `spec/validation.md` fills from it.
2. **Stage 4 plan:** carry the Medium and Low findings from `spec/validation.md` (the last Findings row points into `spec/review/`) into `plan.md` as Risk rows or deferrals. Add these Risks:
   - **Tab title:** a session's title may not match its Claude Code tab.
   - **Classic hooks:** they may be skipped on managed machines (ponytail's code says so), which affects `Stop`-based items.
   - **Haiku question check:** it runs only in sessions with the mod.
3. **Stage 3 must cover:**
   - **A2:** a fact that every model call pins `haiku`.
   - **A5:** an out-of-scope line saying the web page comes in milestone 2.
   - **The question check:** a fact that it runs at `turn.complete` and reads the transcript, never the classic `Stop` hook, which managed machines skip.
4. **The one gate:** `spec/`, `facts.md` and `plan.md` together; on approval set `spec/validation.md` `status: approved`.

## Verified since Stage 1

- **`claude agents --json` (2.1.323):** interactive sessions carry `status` (`idle`, `busy`, `waiting`, plus `waitingFor`); background sessions carry `state` (`working`, `blocked`, `done`). The mapping is in `spec/ia.md`.
- **Mod API:** letter hotkeys fire only while the band or pane has the keyboard. Panes have no raw key handler. `Link` exists on the terminal, `Svg` on desktop only. A pane opened by the mod itself is placed only from 144 columns (110 for one opened before).

## Open, not verified

- What `waitingFor` holds for a permission prompt against a question.
- When a `/goal` ends, as a mod sees it.
- Whether a mod can call a connected MCP tool (needed for Linear state in milestone 3).
- The local CI gate (`scripts/ci-local` and its pre-push hook) is not installed in this repo yet.

## Design references

- **Board mockups:** the owner reviewed terminal mockups of the triage layout, the band (details and compact), the drill-in pages and the you-should-know section. They were local HTML, not in the repo; Stage 2 redraws what it needs into `spec/`.
- **Ponytail's band:** its hooks module is the pattern for the band and the board file (a `ui.render` hook on `AbovePrompt`, a `details` toggle in `$.store`, an SVG on desktop, `board.html` written with `$.fs.write` and opened with `open`).
