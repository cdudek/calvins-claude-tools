---
linear: none
type: facts
change: 2026-11-13-kit-internal-names
design: null
author: Calvin Dudek
status: approved
reviewed_by: Calvin Dudek
approved_at: 2026-11-13T21:53
created: 2026-11-13
---

# Facts: Keep internal names out of the sdlc-run kit

## Goal

The kit templates and their tests carry no internal names. Adopt asks which tracker to use. It is one hotfix because the empty team and the new test pattern only make sense together.

## Acceptance criteria

- [ ] **F1** (A1) The system shall fail `test_no_private_or_internal_names` if an internal team name, repo name or ticket key returns.
- [ ] **F2** (A1) The system shall keep the adopt and tracker tests passing with the placeholder fixtures.
- [ ] **F3** (A1) The system shall ship both presets with `linear.team` equal to "".
- [ ] **F4** (A1) The system shall keep the plugin test suite passing.

<details>
<summary>Verification</summary>

- F1 — `python3 -m unittest discover -s tests` exits 0 (includes the name test)
- F2 — `python3 -m pytest -q plugins/cct/skills/sdlc-run/scripts/test_adopt.py plugins/cct/skills/sdlc-run/scripts/test_tracker.py` exits 0
- F3 — `python3 -c "import json;[json.load(open(f'plugins/cct/skills/sdlc-run/templates/presets/{p}.json'))['linear']['team']=='' or exit(1) for p in ('node','python')]"` exits 0
- F4 — `scripts/run-plugin-tests.sh` exits 0

</details>

## Verification

- **Automated:** `python3 -m unittest discover -s tests && scripts/run-plugin-tests.sh` exits 0 (this repo's `verify`).
- **Manual:** none, there is no UI.

## Out of scope

- Cleaning the adopted copies in this repo — done by hand in the adopt change.

## Assumptions

- Empty team means untracked: `adopt.py` and `tracker.py` already treat "" as no team, so they need no code change.

## Deferred

none

## Open questions

none
