---
type: plan
status: active
created: 2026-11-28T03:00
author: Claude Opus 5.5 with Calvin
project: factory plugin
supersedes: none
---

# Factory: test tiers (fast builders, old tests caught before hand-back)

The owner approved on 2026-11-28 ("agree to all, generalise this into the skill").

## Why (eval round 3, factory 0.5.2, 12 runs)

- **Runs are slow:** each took 52–90 min, and 5 hit the 90-min cap.
- **Vitest is fast:** median 4 s per full run. Of 284 min in test calls over 60 s, vitest ran for 34 min. The rest was waiting on the eval's machine-global `heavy` lock, or the output had been cut by `grep`/`tail`.
- **Serial runs came from the coordinator:** it wrote "run serially" into builder briefs (it is in no plugin or project file). Builders then ran `--fileParallelism=false` 36–50 times per run. Serial runs take 4–6 min; parallel takes about 40 s. HeyDiff already gives each DB suite its own database.
- **Slow structural tests ran on every task:** smoke at 47 s, architecture at 31 s, new-module at 31 s. The default vitest config excludes `test/architecture`, so "the full suite" is more than one command.
- **The main failure:** builders broke old visible tests they never ran, e.g. foreign-keys when tables are added. Each one cost a verifier round plus a gap round (10–20 min each).

## Approach A (generalise first) vs. the project analysis

- **One `unit` command:** HeyDiff's full tier is `npm test` plus `npm run arch`. The full tier is a list of suites.
- **`global` tests on every task:** HeyDiff's are coupled through files the code reads (schema, migrations, `architecture.json`). They run when matching paths change, which keeps hand-back at 15–40 s.
- **Per-worktree DB env:** not needed, since HeyDiff isolates each suite itself. The plugin leaves isolation to the project; it only bans serial flags.
- **Serial flags banned in builder prose:** the cause was the coordinator's brief. The fix goes in the kickoff ("briefs pass the plan's test commands verbatim") plus a guard-hook deny.
- **Research:** Meta predictive test selection catches 95% of failures. The common pattern is affected tests + a safety set triggered by path + the full suite once at merge. TDAD (arXiv 2603.17973) cut agent regressions 70% with a code-to-test map.

## Design

- [x] **Plan key `tests` (optional, top level):**
  - `related`: a command template with `{files}`, e.g. `npx vitest related --run {files}`.
  - `triggers`: `[{paths: [globs], run: cmd, why}]`.
  - `suites`: `[{name, cmd, lock?: bool}]`, the full tier.
  - Without `tests`, the run behaves as today.
- [x] **check-plan.py:** checks the shape. It fails on a command carrying a parallelism-off flag (`--no-file-parallelism`, `--fileParallelism=false`, `--runInBand`, `-p 1`, `-j1`, `--maxWorkers=1`, `--workers=1`), on a trigger without `why`, and on `related` without `{files}`.
- [x] **task-step.py `finish`:** in the task worktree before the merge, it runs `related` on the task's changed files plus every trigger whose glob matches. A failure prints `FINISH FAIL tests: <cmd>` with the last 40 lines.
- [x] **task-step.py `gate`:** it runs every suite once (with `heavy` when `lock` is set and `heavy` is on PATH) and prints `GATE tests OK|FAIL <suite>`.
- [x] **builder.md:**
  - Inner loop: the test file it touched, or `related` on its files.
  - Before reporting: `finish` runs the hand-back set, so the builder needs no full-suite loop.
  - Never: serial flags, edits to the test config.
- [x] **verifier.md:** reads the gate's test lines and does not re-run the full suite.
- [x] **kickoff.md:**
  - Verify step 1 becomes `task-step.py gate`, which runs the suites.
  - Briefs pass the plan's test commands verbatim and add no test-running advice (no "serial").
- [x] **intake / grilling:** discover `tests` from the manifests and CI. Ask which tests guard repo-wide invariants, and on which paths.
- [x] **plan-standard.md and the templates:** document `tests`, with one example.
- [x] **Guard hook:** deny a Bash command with a parallelism-off flag during a factory run.
- [x] **Tests:** check-plan shape cases, finish hand-back pass and fail, gate suites, guard deny.
- [x] **Version:** 0.5.4 to 0.6.0.

## Eval (same PR, tools/factory-eval)

- [ ] **System prompt:** the `heavy` line covers E2E suites and app servers only, not unit runs. The gate takes the lock for `lock: true` suites.
- [ ] **Replay plans T1–T4:** add the HeyDiff `tests` block.
  - `related`: `npx vitest related --run {files}`.
  - Triggers: schema, drizzle and `architecture.json` run the tooling, migrate and foreign-keys tests; access and guest code run the guest-scope tests.
  - Suites: `npm test`, plus `npm run arch` with lock.
  - Re-approve the plans in start.tar.gz the way the mayTouch swap did.
- [ ] **Repin eval-v7** to the merged commit, then rerun the 12 runs.

## Open

- **Postgres connection limit:** the eval Postgres (heydiff-test-pg) has max_connections 100. Unlocked hand-back runs from 12 runs could exceed it. Auto mode refused raising it, so the owner runs the ALTER SYSTEM command.
