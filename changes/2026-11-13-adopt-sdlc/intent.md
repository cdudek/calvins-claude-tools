---
linear: none
type: intent
change: 2026-11-13-adopt-sdlc
design: null
author: Calvin Dudek
status: approved
reviewed_by: Calvin Dudek
approved_at: 2026-11-13T21:24
created: 2026-11-13
---

# Intent: Adopt the AI-native SDLC in calvins-claude-tools

> Run this repo's own changes through sdlc-run, so the next change (an agent tracker) has change folders to read.

## Asks

| # | Date | Source | Words | Screen | Resources |
|---|---|---|---|---|---|
| A1 | 2026-11-13 | owner, chat | "go and adopt" | none | none |
| A2 | 2026-11-13 | owner, chat | "also do .gitignore beads" | none | none |

## Job stories

| # | When … | I want to … | So I can … | Evidence |
|---|---|---|---|---|
| J1 | I start the next change, a local agent-tracker mod for Claude Code | this repo to run changes through sdlc-run | have the tracker read real change folders | reported — A1 |
| J2 | I use Beads to track work in several worktrees | the Beads database kept out of git | never commit local tracker state | reported — A2 |

## Success measure

- **Measure:** adopted files pass the guardrail test — **read in:** `python3 -m pytest -q tests/test_sdlc.py` — **target:** exit 0 on the merge commit

## Problem

- **What is wrong or missing:** this repo is the source of sdlc-run but has not adopted it. It has no sdlc.json, hooks, gate scripts or change folders.
- **Who feels it:** the owner, who builds the agent tracker next, and the tracker, which reads change folders.
- **Evidence:** A1 and A2; the repo root has no `sdlc.json` before this change.

## Proposed outcome

- Changes here follow the sdlc-run chain, with its hooks and gate scripts present.
- `.beads/` never shows up in `git status`.
- The existing CI workflow and the repo's own checks keep working as before.

## Affected users and systems

| Kind | Name | How |
|------|------|-----|
| users | the owner | works through change folders and the verify gate |
| service | `.github/workflows/ci.yml` | none, stays as it is |
| data | `.beads/` | local Beads database in the main checkout, shared by worktrees, git-ignored |

## Constraints

- **Must not change:** `.github/workflows/ci.yml`; the kit templates under `plugins/cct/skills/sdlc-run/templates/`.
- **Deadline:** none
- **Rules that apply:** the public-repo rule in `CLAUDE.md`. No employer or client names, private repo names, other people, emails, URLs or local paths.

## Open questions

none
