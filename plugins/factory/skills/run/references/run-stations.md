# Build, verify, ship and learn (stations 3 to 6)

The launched run reads its own kickoff (`kickoff-<M>.md`, from `templates/kickoff.md`); this file is the reference for whoever launches or reviews it.

## 3. Build
- Stations 0 to 2 run in a normal session, never under `/goal`. They end at the approval. The launched run is a separate process.
- Optional integration branch: when the plan sets `"integration": "<branch>"`, milestone branches are cut from it and their PRs target it. `goal-brief.py` creates it on origin from the approved SHA when it is missing and that SHA is on `base`.
- **File refresh at each milestone cut.** Before `goal-brief.py` runs for a milestone, a read-only agent checks each task's `files` and `allowTestEdits` against the current tree: moved or renamed files, files the requirement obviously needs, existing tests the change will break. The coordinator records the result as a plan revision under the standing approval, then cuts the milestone.
- Per milestone: `wt switch -c milestone/<slug>-<M>` from a fresh base (the integration branch when set). Inside it run `python3 .factory/goal-brief.py changes/<slug>/plan.md <M> --approved <sha>`, or `--all --approved <sha>` for the whole plan.
- `goal-brief.py` refuses a plan that fails the check, changed since `<sha>`, or a milestone without tasks. It writes `kickoff-<M>.md` and prints the `/goal` line and the run command. Never hand-write a goal line.
- **Launch.** The session-start hook keeps `.factory/` current; regenerate the kickoff when `.factory/` changed or the kickoff names agents that no longer exist (an old plugin prefix), and commit both.
- Start the RUN command goal-brief prints with the Bash tool and `run_in_background: true` (`claude -p ... "/goal ..."`; print mode honors a goal prompt). When it finishes, report the end state line (SHIPPED, HOLD, BLOCKED or INCOMPLETE) from the run's final result. Details: `references/goal-briefing.md`.
- Every task runs in a `factory:builder` subagent, even a one-line fix. The coordinator only runs `task-step.py` (worktree, integrity, merge), checks and the log.
- The coordinator creates each task worktree with `task-step.py start`, never with the Agent tool's worktree isolation.
- Spawn builders 2 or 3 at a time, in the foreground, each with its worktree path. Each owns disjoint files. Unfinished work stays in its worktree; never patch files.
- A hook denies `run_in_background` on every Agent call in a factory run, so every agent starts in the foreground.
- Builders may add tests and edit exactly the existing test files their own task's `allowTestEdits` lists. Those edits are add-only: `test-integrity.sh` fails a removed or renamed test block, fewer assertions in a block, an added skip, focus marker or early exit, strict matchers traded for loose ones, or a raised timeout (totals are summed per test name; comments and strings do not count as assertions). An edited test file of a type it cannot read fails. It is line-based, a floor: the verifier and the Codex pass are the independent checks behind it.
- Builders never touch CI config, `.github/`, `.factory/`, baselines, specs, deltas or the plan, and never add lint suppressions. They never get the `~/.factory/scenarios` path. `test-integrity.sh` enforces this by exit code.
- A handover file `changes/<slug>/handover-*.md` may be committed on the milestone branch; `test-integrity.sh` does not flag it (it is not a plan, spec or test).
- The milestone's progress entry (with `firstPass`, `planRevisionsAfterApproval`, `diffMatchesPlan`) is committed and pushed before its PR can merge.

## 4. Verify
Run in this order, paste the output into the transcript:
1. Fast checks: lint, typecheck, unit. No local CI.
2. Per task, before merging it: `task-step.py finish` (integrity for the task, then the merge of exactly the checked commit) must print `FINISH OK`.
3. `factory:verifier` with the delta, base, diff and the scenarios for this milestone and earlier ones (all of them on the last milestone). It also runs two neighbouring flows per changed behaviour. Never the builder's reasoning.
4. Risky milestone: also a security review of the diff and delta. Run one Opus 5.5 high advisory agent; when `codex` exists also run the Codex `gpt-6.2-astra` pass, and its absence never blocks. Both fail only on Important findings (`references/review-policy.md`). Each finding names the `rule` it breaks; findings that share a rule are one fix, made at the rule and starting from the `ruleTest` task. Log each review with `task-step.py review <plan> <M> PASS|FAIL <rule> --approved <sha>` and commit the line. A FAIL past `securityRounds` (default 1) ends `BLOCKED: owner decides on <rule>: move it to a later milestone, or accept it as a known limit`.
5. UI milestone: `factory:ux-verifier` against the approved boards, per `references/ux-checks.md`. It writes `evidence/<M>/gallery.md`. No owner stop.

- Failures go back to the builder: at most 3 passes per task. Stop when two consecutive passes fail the same check with the same output.
- The verifier labels each FAIL `bug` (back to the builder) or `gap` (needs files no task owns, or a test that asserts the old behaviour). A `gap` inside an approved requirement, every file matching the milestone's `mayTouch`, gets one fix task `<M>-gap<n>` per round, logged as `GAP-FIX <M> round=<n> files=<a,b> tests=<c,d>` in the progress log, up to the milestone's `gapRounds` (default 3). Anything else ends `BLOCKED: owner approves plan revision for <finding>`. Details: `references/goal-briefing.md`.
- A builder that reports a file no task owns, or an existing test the requirement needs edited, only reports it. The coordinator decides whether it is inside an approved requirement, then writes and commits the `GAP-FIX` line; the rules, log line and `gapRounds` cap are those of a verifier `gap`. Every `tests=` entry must pass the add-only gate, the independent check on test edits.
- A fix for a confirmed High stays inside the task's own files and `allowTestEdits`; otherwise it is a `gap`.
- A bug (`kind: bug`): the builder's first commit holds only the failing test. Show it fails on base and record that SHA with `task-step.py pin`; every later `finish` passes `--pin`.

## 5. Ship
- Before the PR: `task-step.py gate` (integrity `--milestone` with every checked SHA, then `check-plan.py --approved`) must pass.
- One PR per milestone into the base (the integration branch when the plan sets one). Link the delta and the reports.
- With an integration branch, milestone PRs merge on their own after the verify steps; no remote CI there. The release PR into `base` links every milestone's `gallery.md` and runs the full required CI.
- The release PR waits for a human only when a milestone is `risky`, `deployOnMerge` is true or the plan sets `merge: owner`. The run then ends `SHIPPED` with the merge-ready URL. Otherwise it merges on its own after required CI.
- Without integration: `merge: auto` arms auto-merge; `merge: owner` never does, and the run ends at SHIPPED with the merge-ready PR URL.
- Commit everything first (progress entry, gallery, spec changes), then run the verifier on that final SHA, then push that same SHA. Any later commit means verifying again.
- With a `hold`: push the milestone branch, open no PR, end `HOLD` with the pushed SHA and a verifier PASS for that same SHA.
- The delta reaches the specs once, in the PR that ships the change to `base`. Before it, check every MODIFIED or REMOVED entry's prior text still matches the spec on `base` and every ADDED id is unused; a mismatch means the delta is reconciled and re-approved.
- Merge SHA and CI conclusion appear in the transcript. SHIPPED on a release PR also records deploy state: readiness at the serving SHA when the repo deploys on merge, or merge plus CI when deploy is disabled.

## 6. Learn
- Every escaped failure becomes a regression test that fails on the base, or a lint rule with remediation text.
- Every BLOCKED that grilling could have prevented becomes a new question in `references/grilling.md`.
- Every five milestones, tally `firstPass`, `planRevisionsAfterApproval` and `diffMatchesPlan` from the progress logs and re-measure `STEPS_PER_DISPATCH`.
- Optional weekly entropy run opening small cleanup PRs, only after three changes shipped.
- After any change to the factory itself, replay one known-good and one known-bad task with `tools/factory-eval`.

## Known limit
`hooks/guard-scenarios.py` (only `factory:verifier` may read the scenarios) matches tool-input text, with `~`, `$HOME`, `//` and `/./` expanded and `factory` plus `scenarios` in one input. A path assembled at runtime or reached through a symlink can bypass it. It fails closed on a crash or a non-object input that names the folder, and with `FACTORY_EVAL=1` it denies the main session too. The verifier fails when the approved scenario set is missing.

`task-step.py review` logs the coordinator's own report of a security review as a plan line; nothing proves a review agent ran. It catches a forgotten review, an uncommitted round and a task merged after the PASS, not a coordinator that writes a false line. `check-plan.py` compares only backticked paths that contain a `/` in a task's Owns, Edits, Creates or Adds sentence; a root-level file named in prose is not checked.

## Not built
Board, receipts and approval ledgers; local CI; self-policing hooks; one agent per stage; pixel diffs; E2E repeat logic; satisfaction scoring; digital twins; dark no-review mode; a foreman, queue or status page.
