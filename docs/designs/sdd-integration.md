---
title: sdlc-run spec-driven build, integration points
type: note
status: active
created: 2026-11-19
tags: [sdlc-run, spec]
read_when: you wire the gate, status or the hooks to the three-document layout and the living spec
---

# Integration points for the gate stream

The spec stream added `templates/scripts/spec.py` (stdlib, no import side effects) and touched none
of `verify_gate.py`, `sdlc_status.py`, `marks.py`, `pr-gate.sh`, `pass_proof.py`. Everything below
is for the integrator. A change is on layout 4 when `spec.applies(change_dir)` is true; every call
below is wrapped in that test, so the old layout is never affected.

## Calls

```python
import spec  # scripts/spec.py, same folder as verify_gate.py

spec.applies(change)            # bool: decisions.json {"layout": 4}, or spec.md without facts.md
spec.documents(change)          # what lint and the readability checks read (OWNER_FILES)
spec.lock_inputs(change)        # {file: text}: what `approve` hashes. State column and handover excluded
spec.consistency(change, "approve", root=ROOT, base=parent_ref)   # list[str], [] is clean
spec.check(ROOT, base=parent_ref)                                 # list[str], the drift check
spec.change_rules(change)       # {n: {change, capability, asks}} to generate done.json
spec.task_states(change)        # [(task, state, milestone)] for status, replaces milestone.md rows
spec.qa_applicability(change)   # (True | False | None, reason); None = unrecorded, never a skip
```

- **`verify_gate.py approve`** (after lint, before writing `lock.json`): if `spec.applies`, refuse on
  `spec.consistency(change, "approve", ROOT, base)` and `spec.check(ROOT, base)`; lock
  `spec.lock_inputs(change)` instead of facts and plan; generate `done.json` facts from
  `spec.change_rules` (id `R<n>`, tag `@R<n>`; screen and states from the UX table).
- **`verify_gate.py milestone`**: `spec.check(ROOT, base)` with `base` the milestone's parent. Pass
  `base` explicitly: that makes an unresolvable base a failure instead of a skip, as does `CI`.
- **`verify_gate.py lint`**: read `spec.documents(change)`. The family letter `R` means a review
  finding in `verify_gate.py` lint and `change_docs.py` FAMILIES, and a rule id in layout 4: the
  lint and `sdlc_status.py ids` must pin the meaning per layout, or a rule id reads as a bare
  finding id.
- **`sdlc_status.py`**: for layout 4 read task state from `spec.task_states` instead of `milestone.md`.
  `change_docs.py readme` is not needed in layout 4 (three documents need no map).
- **`chain-gate.sh`**: protect `specs/**` rule files and `.sdlc/last-rule-id` from direct Edit after
  approval (script and git writes only); refuse the old `facts.md`/`spec/` ordering rules only on
  the old layout; the plan gate for layout 4 is `status: approved` on the three documents.
- **CI step.** `spec.py check` is strict in CI: an unresolvable base is a failure. GitHub's default
  checkout is shallow with no `origin/<default>`, so the job needs `fetch-depth: 0` (or an explicit
  fetch of the base) and `spec.py check --base origin/<base ref>`. `defaultBranch` from `sdlc.json`
  is tried after an explicit `--base`. Without that the check is always red.
- **UX skills** (not in this stream's file area): `cct:ux-spec-validate` single-pass draft mode with
  no nested goal (D1); `cct:ux-build-validate` runs `python3 scripts/spec.py qa <change>` before checking readiness (exit 0 run, 3 skip, 2 stop)
  (S1). The wording is in `references/stages.md`, "Layout 4".
- **Close**: after the merge, `spec.outcome_write(ROOT, folder)` then `git rm -r` of the folder in a
  records-only PR. The tracker comment and the scheduled read call `spec.outcome_record`;
  `spec.outcome_due(ROOT)` lists the waiting ones (S3). Never remove the folder before the merge.
  Existing `changes/archive/` is untouched here; removal once its changes are complete is the
  integrator's step, and the status, audit and pr-gate readers still scan it.

## Blockers and hazards to know

- **BLOCKER to enabling layout 4 in any repo: `adopt.py` (the `specs/` to `designs_dir` migration, near line 945)** moves a root `specs/` folder into
  `docs/designs/` when that folder does not exist yet. With living specs that moves the user's
  rules. This stream was told to add only install lines, so it is not fixed: guard it (skip when
  `specs/` holds a `rules/` folder or a `manifest.yaml`) before any repo enables layout 4.
- **`sdlc.json` keys.** `layout: 4` opts a repo in (adopt never sets it); `livingSpecs` renames the
  folder. `specsDir` is the old key for designs and is not reused.
- **Pass records are not touched.** `spec.py` reads no receipt. The `.sdlc/outcomes/` folder is new
  and records-only; add it to the records-only allow-list of the push hook and status.
- **`.sdlc/last-rule-id`** is a floor, written by `spec.py last-id --write` at milestone close only.
- **`kitTemplates`** in `sdlc.json` changes with these templates; the three streams will collide on
  that line. Recompute with `python3 plugins/cct/skills/sdlc-run/scripts/adopt.py --templates-hash`
  after merging them.
- **Not built:** the `state/` folder move, `intake.json` rename, capability `decisions/` folders
  (`marks.py` and `design_index.py` still read only the designs folder), the 100-case recall
  fixture (the script and a two-case example exist; the fixture needs real past changes of a repo),
  back-fill of `specs/`, related-capability expansion in `find`.
