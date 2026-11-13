---
linear: none
type: facts
change: 2026-11-13-adopt-sdlc
design: null
author: Calvin Dudek
status: approved
reviewed_by: Calvin Dudek
approved_at: 2026-11-13T21:24
created: 2026-11-13
---

# Facts: Adopt the AI-native SDLC in calvins-claude-tools

## Goal

The owner can run changes in this repo through sdlc-run, and the Beads database stays out of git. It is one change because the adopted files only work together and the guardrail test checks them as a set.

## Acceptance criteria

### Adoption

- [ ] **F1** (A1) The system shall keep `python3 -m unittest discover -s tests` and `scripts/run-plugin-tests.sh` passing.
- [ ] **F2** (A1) The system shall pass the adoption guardrail test `tests/test_sdlc.py`.
- [ ] **F3** (A1) The system shall set `tiers` to false and `tracker.kind` to `beads` in `sdlc.json`.
- [ ] **F4** (A1) The system shall leave `.github/workflows/ci.yml` unchanged from `origin/main`.
- [ ] **F5** (A1) The system shall carry no employer, client or private-repo name in any adopted file.

### Beads

- [ ] **F6** (A2) The system shall ignore `.beads/` in git.
- [ ] **F7** (A2) The system shall commit no file under `.beads/`.

<details>
<summary>Verification</summary>

- F1 — `python3 -m unittest discover -s tests` and `scripts/run-plugin-tests.sh` both exit 0
- F2 — `python3 -m pytest -q tests/test_sdlc.py` exits 0
- F3 — `python3 -c "import json;d=json.load(open('sdlc.json'));assert d['tiers'] is False and d['tracker']['kind']=='beads'"` exits 0
- F4 — `git diff origin/main -- .github/workflows/ci.yml` prints nothing
- F5 — `grep -rIiE` with the pattern from `test_no_private_or_internal_names` in `tests/test_plugin.py`, over `sdlc.json docs/sdlc.md AGENTS.md REVIEW.md CLAUDE.md boundary-map.yaml .claude .github scripts changes tests/test_sdlc.py`, finds nothing
- F6 — `git check-ignore .beads/` exits 0
- F7 — `git ls-files .beads` prints nothing

</details>

## Verification

- **Automated:** `python3 -m unittest discover -s tests && scripts/run-plugin-tests.sh` exits 0 (this repo's `verify`).
- **Manual:** none, there is no UI.

## Out of scope

- Local CI gate (`scripts/ci-local`, pre-push hook, `local-ci` status) — its own later change, per `plugins/cct/skills/sdlc-run/references/local-first.md`.
- Default-branch ruleset — its own later change.
- The agent tracker mod — its own later change.
- Fixing the kit templates (`plugins/cct/skills/sdlc-run/templates/presets/*.json`, the AGENTS.md template) that carried the names cleaned here — its own later change.

## Assumptions

- Tiers off: one owner, every PR auto-merges on green.
- Verify and both checks lists use the two existing test commands: the repo has no pyproject, uv or Makefile.
- `lintOnEdit` is empty: the repo has no linter configured.

## Deferred

none

## Open questions

none
