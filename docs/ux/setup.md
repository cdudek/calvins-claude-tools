---
type: ux-setup
updated: 2026-11-13
---

# UX setup: calvins-claude-tools

Every `ux:` skill reads this file first. Keep it short and true.

The repo ships Claude Code plugins. Until the agent tracker, none had an interface: skills, agents and hooks only. The agent tracker (`plugins/agent-tracker/`, not built yet) is the first product with screens: a mod that draws a band above the prompt and a pane, and later a local web page.

## The product

- **What it is:** the agent tracker, a Claude Code mod that shows one owner what every session, repo and worktree is doing and which session needs them.
- **Platform:** desktop. Claude Code's terminal and its desktop app draw the mod (band and pane); milestone 2 adds one self-contained HTML page opened in the browser.
- **Audience file:** none; the audience is one developer, the owner, running several Claude Code sessions at once. Scenes, from `changes/2026-11-13-agent-tracker/intent.md`:
  - **S1 Mid-prompt:** typing in one session while others run elsewhere; glances at the band.
  - **S2 Triage:** several sessions have stopped; decides which to answer first.
  - **S3 Review:** after a run or at the end of the day, reads what was asked, done and decided.
- **Jobs to be done:** the job stories J1 to J11 in `changes/2026-11-13-agent-tracker/intent.md`.
- **Products the audience already uses** (for pattern research): Claude Code (prompt, `claude agents` view, status line), the ponytail band and board, Orca, tmux, GitHub pull requests, Linear, Beads. Others surveyed in `docs/designs/2026-11-13-note-agent-tracker-research.md`.

## The rules it must follow

- **Design system:** none. The mod uses Claude Code's own components (`Box`, `Text`, `Button`, `Svg`) and its theme colours (`success`, `warning`, `error`, `suggestion`, `inactive`, dim). No colours of its own.
- **Glossary:** none yet; `docs/ux/glossary-proposal.md` collects terms.
- **Voice and writing rules:** the shared `writing.md`, plus the repo's style: plain words, short sentences, sentence case, no exclamation marks.
- **Hard rules** that override UX preferences:
  - **Observe only:** the tracker never writes to a session or the agent (no hidden notes, no automatic continue, no queued decisions).
  - **Public repo:** no internal names, private repo names, people, URLs or local paths in anything committed (`tests/test_plugin.py`).
  - **Never publish to claude.ai:** pages are local files.
  - **Cheap model:** every model call pins `haiku`.
  - **Standalone:** works in a repo without sdlc-run; sdlc-run change folders only add detail.
- **Exceptions register:** `docs/ux/exceptions.md` (`EX-<n>`, format in `conflicts.md`)
- **WCAG and EAA scope, one finding per surface:**
  - Band and pane: a developer tool for one business user, so WCAG 2.2 AA is R2. Proposed by the agent 2026-11-13; awaiting the owner.
  - Web page (milestone 2): the same scope. Proposed by the agent 2026-11-13; awaiting the owner.

## The owner's words

- **File:** `docs/ux/owner-words.md`, every request verbatim and dated. Quote from it; never cite a request by number.
- **Feedback folders:** `changes/*/asks/` (screenshots and briefs that came with an ask).

## Design inputs

Read by `cct:ux-design-run` and `cct:ux-spec-validate`; `cct:ux-sitemap-create` reads the route source.

- **Route source:** none in code yet. The mod has no router: its surfaces are the band (always on), the pane's pages (opened by `/tracker` or the band's Pane button) and, from milestone 2, the web page's hash routes (`#/repo/<repo>/…`). The proposed routes are written in the change's `spec/sitemap.md`.
- **Interaction guidelines:** `docs/ux/interaction-guidelines.md`
- **Screen goals:** the screen inventory in the change's `spec/ia.md` until `docs/ux/` grows a screen-goals file.
- **UI components live in:** Claude Code's mod UI (`$.ui.resolve(e)`); the tracker's own pieces will live in `plugins/agent-tracker/`.
- **Component catalogue:** none. The reference implementation is the ponytail band (a public plugin), whose hooks module draws the same kind of band.
- **Screenshot recipe at 100 percent:** BLOCKED: no mod is built yet. Once it is: a terminal at 120 columns and at 80 columns, screenshot of the window.
- **Screenshot recipe at 150 percent:** BLOCKED: no mod is built yet. Once it is: the same terminal with the font at 150 percent (about 80 columns become about 53).
- **Specs without a change folder:** `docs/ux/specs/<YYYY-MM-DD>-<slug>/`

## Where the UX files live

| File | Path |
|---|---|
| Audits | `docs/ux/audits/<YYYY-MM-DD>/` (briefing, evaluator notes, findings, shots) |
| Findings (latest) | `docs/ux/audits/<YYYY-MM-DD>/findings.md` |
| Decision lists (one per round, built by ux:decision) | `docs/ux/decisions-<YYYY-MM-DD>.md` |
| Decisions (one file each, written by ux:decision; listed in `docs/designs/INDEX.md`) | `docs/designs/<YYYY-MM-DD>-adr-<slug>.md` |
| Exceptions register | `docs/ux/exceptions.md` |
| Interaction guidelines | `docs/ux/interaction-guidelines.md` |
| Sitemap, for people (written by `cct:ux-sitemap-create`) | `docs/ux/sitemap.md` |
| Sitemap, for tools: one object per page | `docs/ux/sitemap.json` |
| Glossary proposal | `docs/ux/glossary-proposal.md` |
| Decision page (optional) | none |

## Screens and states

Nothing is built. The proposed screens for milestone 1:

| Screen | Route or entry | States to capture |
|---|---|---|
| Band, compact | above the prompt, every session | empty (no other session) · loading (first poll) · error (poll failed) · something needs you · nothing needs you |
| Band, details | the band's Details button | the same, plus a column with no items |
| Pane, Home | `/tracker`, the band's Pane button | empty · loading · error · needs you · all quiet |
| Pane, Session | a row on Home | live · ended · without the mod (from the transcript) |
| Pane, Repo | a repo heading on Home | with PRs · without gh · without bd |

App-wide parts: the band (always present), the pane's breadcrumb, toasts for Copy.

## How to run it for an audit

- **Build and run:** BLOCKED until milestone 1 builds the mod. Then: `claude plugin validate plugins/agent-tracker`, `tsc -p plugins/agent-tracker`, `claude plugin test plugins/agent-tracker`, and a Claude Code session with the plugin enabled.
- **Test data:** fixture session files and fixture transcripts under `plugins/agent-tracker/` tests; never the owner's real sessions in a committed shot.
- **Screenshots go to:** `docs/ux/audits/<YYYY-MM-DD>/shots/`
- **Window sizes:** terminal 80, 120 and 200 columns; desktop app at its default and narrowest width.
- **Builds to audit:** main, plus the milestone branch while it is open.

## Safety

- **Never write to:** any Claude Code session, transcript or agent; git, gh or bd state (read only).
- **Read only:** `~/.claude/projects/*/*.jsonl`, `claude agents --json`, `git`, `gh`, `bd`.
- **Writes only against:** `~/.claude/agent-tracker/` (one file per session, and the board file from milestone 2).

## Flows for this product

Beyond the minimum in `rule-areas.md` (most of which do not apply, since the tracker edits nothing):

- **F1 Answer the session that waits longest** (S2): band → that session named → switch to it.
- **F2 Read what I asked in a session, in order** (S3): band → Pane → Session → Tasks.
- **F3 Switch the band between compact and details** (S1).
- **F4 Copy the state as Markdown** (S3): band → Copy → paste elsewhere.
- **F5 Find a repo's open PRs and their state** (S3): Pane → Repo → PRs.
