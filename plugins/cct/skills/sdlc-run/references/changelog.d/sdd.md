# sdd fragment (the integrator turns this into one version entry)

Spec-driven restructure and the living spec.

- **Three documents per change.** A change on layout 4 has `spec.md` (why and what), `design.md` (how) and `tasks.md` (in what order) instead of intent, facts, plan, checklist, analyze, challenge, milestone and the reading map. Scope S needs only the spec, M the spec and tasks, L all three; scope is chosen by risk, not by UX size. Machine files keep their paths. A repo opts in with `"layout": 4` in `sdlc.json`; a change already on the old layout finishes on it and is never blocked.
- **The living spec.** What the product does is one file per rule: `specs/<capability>/rules/R123.md`, with a `manifest.yaml` per capability and a generated `specs/CAPABILITIES.md`. The PR's git diff is the delta: no delta format, no apply script, no hashes. Rule ids are `R` and a number, never reused; `spec renumber` gives the later of two colliding PRs the next free number and retags only its own tests.
- **`scripts/spec.py`, installed by adopt.** `find` (ranked rules for a request, with stale and open-PR warnings), `show`, `new`, `next`, `renumber`, `index` (a local index inside `.git`, never committed), `capabilities`, `check`, `eval`, `consistency`, `outcome`. `check` makes a changed rule need a changed test and does not count skipped tagged tests (including file-, describe- and class-level skips). `eval` measures recall@10 against a grep over a fixture of past changes before a repo turns blocking on.
- **No archive.** Change folders are removed after the merge in a records-only close PR. The success measure is copied to `.sdlc/outcomes/<id>.json` first, so a final change with no tracker and no later PR still has a place to record its result.
- **Three deadlocks closed.** D1: the UX validation runs once as a draft and an ask may be `pending` until the owner gate. S1: `prototype: required|none` is recorded at Stage 2 and build QA decides whether it applies before it asks for readiness. S3: the outcome record outlives the folder.
- **Planning content in `design.md`.** Ground truth with `file:line`, a proof before build for every risk, rollout and rollback, the architecture checklists as a trigger, a test strategy per rule, and a cold-read question in the single reviewer's brief.
- **Safety.** `livingSpecs` must be one plain folder name inside the repo; manifest test roots may not leave the repo; in CI or with an explicit `--base`, an unresolvable base or a failed git call is a failure, never a silent skip.

Migration: nothing. Existing changes, archives and repos keep working; see `docs/designs/sdd-integration.md` for what the gate, status and hooks still have to read.

Second wave.

- **Recall fixture from the repo's own changes.** `scripts/eval_corpus.py` turns a repo's facts into rules and its asks into labelled cases; this repo's run is in `tests/eval/` (233 rules, 57 cases). `spec.py eval --root` evaluates against it: recall@10 is 0.24 for `find` and 0.13 for a grep.
- **`find` pulls in related capabilities** (manifest `related`), below every direct hit and marked `via <capability>`.
- **UX skills.** `ux-spec-validate` runs once as a draft pass in sdlc mode (an ask may be `pending`, no nested goal); `ux-design-run` calls it that way and records `prototype`; `ux-build-validate` runs `spec.py qa` before it asks for any readiness file.
- **The letter R, pinned per layout.** In layout 4 `R<n>` is only a rule and a review finding is `V<n>`; `spec.id_families` is the one definition and `sdlc_status.py ids` reads it.
