---
linear: none
type: intent
change: 2026-11-13-kit-internal-names
design: null
author: Calvin Dudek
status: approved
reviewed_by: Calvin Dudek
approved_at: 2026-11-13T21:53
created: 2026-11-13
---

# Intent: Keep internal names out of the sdlc-run kit

> Stop the kit templates from leaking an internal Linear team name, an internal repo name and internal ticket keys into every repo that adopts sdlc-run.

## Asks

| # | Date | Source | Words | Screen | Resources |
|---|---|---|---|---|---|
| A1 | 2026-11-13 | owner, chat | "ok so next" | none | none |

A1 answers the agent's note that the next step is a separate change fixing the kit templates.

## Job stories

| # | When … | I want to … | So I can … | Evidence |
|---|---|---|---|---|
| J1 | I adopt sdlc-run in a repo | the kit to carry no internal names | keep a public repo clean without hand edits | observed — cleaned by hand in the adopt change |
| J2 | I adopt sdlc-run in a new repo | adopt to ask which tracker to use | pick the tracker myself | observed — a preset team made adopt treat the repo as tracked in Linear |

## Success measure

- **Measure:** the name test passes — **read in:** `python3 -m unittest discover -s tests` — **target:** exit 0 on main

## Problem

- **What is wrong or missing:** the presets, one template example and two test files carry internal names. A preset team also made `adopt.py` and `tracker.py` treat every adopted repo as already tracked in Linear.
- **Who feels it:** the owner, and every repo that adopts sdlc-run.
- **Evidence:** A1; found while adopting sdlc-run in this repo, where the adopted copies were cleaned by hand.

## Proposed outcome

- The kit templates and their tests carry no internal names.
- Adopt asks which tracker to use in a repo with no team set.
- The name test fails if the two names return.

## Affected users and systems

| Kind | Name | How |
|------|------|-----|
| users | the owner | adopt asks the tracker question and writes no internal names |
| service | `adopt.py`, `tracker.py` | read an empty team, no code change |

## Constraints

- **Must not change:** `.github/workflows/ci.yml`; the adopted copies in this repo.
- **Deadline:** none
- **Rules that apply:** the public-repo rule in `CLAUDE.md`. No internal names, private repo names, people, URLs or local paths of any employer or client.

## Open questions

none
