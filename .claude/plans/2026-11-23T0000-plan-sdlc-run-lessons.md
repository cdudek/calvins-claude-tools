---
type: plan
status: in-progress
created: 2026-11-23
author: claude
project: calvins-claude-tools
supersedes: none
---

# sdlc-run 3.27.0: lessons from a large multi-repo project

Path used: sdlc.json says changes run through sdlc-run. This is a docs-and-scripts change to the
skill itself, so the lightest path: no change folder, one branch, one PR, local checks
(`python3 -m unittest discover -s tests`, `scripts/run-plugin-tests.sh`), no milestone branch.

## Calls made
- Kit scripts are edited under `templates/scripts/` and copied byte-identical to `scripts/` and the blueprint.
- Owner change (coordinator): NO owner screenshot approval. The gate records a baseline after an agent comparison matches; `visual.approve` is not added. The design-inventory confirmation (a board list, not a screenshot) stays.

## Checklist
- [ ] 1 `templates/scripts/e2e-repeat.sh`, adopt installs it, presets use it, E2E guidance, test
- [ ] 2 `preflight.py doctor` with one test per gap; run in adopt, Stage 1.0, before the plan gate
- [ ] 3 `references/multi-repo.md`, linked; `sdlc_status.py repo-records` writes per-repo records; test
- [ ] 4 Milestones start at 1: plan template + `verify_gate.py lint` flags 0; test
- [ ] 5 Plan template "Dependency changes (owner paste blocks)"; lint flags a package-adding feature row without it; tarball pattern doc; test
- [ ] 6 Comparison-based baselines, no owner screen approval (capture.py, evidence.py, verify_gate.py, docs, tests)
- [ ] 7 Models are an orchestrator choice: kickoff block, docs
- [ ] 8 `maxBuilders` (default 4)
- [ ] Version 3.27.0, one changelog entry (Mechanical, Manual), kit hashes
- [ ] Checks, commits, push, one PR (not auto-merged)
