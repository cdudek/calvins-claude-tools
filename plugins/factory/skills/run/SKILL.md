---
name: run
description: Runs a lit software factory for product managers, product engineers and UX designers, alone or together. One command, /factory:run <slug> [intent]: grill, write intent, delta, scenarios and plan, approve once, launch one /goal, learn, and continue a change from where it stands. Use when the user says "factory", "/factory:run", "run the factory on", or "spec this with the factory". Skip for ordinary feature work that does not name the factory.
user_invocable: true
---

# factory

A lit factory. The person approves intent, requirements, plan and design boards once, never raw diffs. One `/goal` then runs without a foreseeable stop. Branch protection and required CI decide the merge. Every escaped failure improves the harness.

## The command
One command, `/factory:run`. The slug starts with the date: `2026-11-24-saved-searches`. Branches, worktrees and folders all use it. If an argument is missing, ask once.
- `/factory:run <slug> <one-line intent>`: a new change. Stations 0 to 2: intake, grill, write, plan, approve.
- `/factory:run <slug>`: continue a change, by the same person or another. Read `changes/<slug>/` and the plan's progress log, reconcile with git and PR state (the merge SHA and PR state come from `gh pr view <n> --json state,mergeCommit` or git, never from the log), then do the next step only:
  1. `intent.md`, `delta.md` or `plan.md` missing or still open: continue the grill (station 1).
  2. All written but not approved, or changed since the approved SHA: ask for the approval (station 2).
  3. Otherwise launch the first unmet milestone (station 3).
- Auth failure, exhausted credit or context overflow clears a goal: `/factory:run <slug>` starts a new one from the progress log.

## The process, for every size
1. **Grill.** Rounds of at most 5 numbered questions, each with a recommended answer, until no decision is open. Subagents look up facts. Method and question tree: `references/grilling.md` (or `mattpocock-skills:grilling` when installed).
2. **Write.** `intent.md`, `delta.md`, the holdout scenarios and `plan.md`. A bug or small feature is a plan with `kind` and one milestone with one task, from `references/plan-small-template.md`.
3. **Approve once.** The person approves all of it together. The approval is the commit SHA at that moment.
4. **Run one `/goal`.** One milestone, or `--all` for the whole plan. Nothing after approval stops the run except a real BLOCKED.
5. **Learn.** A BLOCKED that grilling could have prevented becomes a new question in `references/grilling.md`.

## Who uses it
- Product managers, product engineers and UX designers all run this one skill, alone or together. There are no role fields and no file ownership.
- Intake asks what the person brings: an idea, a journey or screen, or a bug. Every station is open to every person.
- All work is spec-driven: a behaviour change, from anyone, starts as a delta. Code follows the files.
- Several people continue one change with `/factory:run <slug>`. The change folder and git are the shared state. Whoever runs the session approves, or names who should.
- The approval is readable without code: intent, requirements, boards and a plain summary of the plan. Engineering detail stays in the plan.

## Files
```
specs/<YYYY-MM>/<YYYY-MM-DD>__<feature>.md  living spec (requirements as req-<n>, journeys); date = when it was created
specs/adr/NNNN-<words>.md             architecture decisions, numbered; superseded ones stay
changes/<slug>/intent.md              problem, outcome-1.., constraint-1.. (references/intent-template.md)
changes/<slug>/delta.md               ADDED / MODIFIED / REMOVED requirements req-<n>, each citing [outcome-<n>] or [constraint-<n>]
changes/<slug>/plan.md                plan, progress log at the bottom
changes/<slug>/kickoff-<M>.md         run briefing per milestone, written by goal-brief.py
changes/<slug>/evidence/<M>/          screenshots, verifier and UX reports, gallery.md
~/.cfactory/scenarios/<repo>/<slug>/  holdout scenarios, verifier only
```
The folders keep the `cfactory` name: Factory.ai's CLI already uses `.factory/`, and approved plans parse the ```` ```json cfactory ```` fence.

All of it except the scenarios lives in the app's own repository, versioned with the code; a multi-app change writes one delta per repo. The intent stays in the change folder after shipping. When the change merges, the delta goes into `specs/<YYYY-MM>/<YYYY-MM-DD>__<feature>.md` in the same PR. A decision that is expensive to reverse gets an ADR per `references/spec-standard.md`: drafted as `proposed`, set to `accepted` before the approval commit is recorded, never deleted; a later ADR supersedes it.

## Stations

### 0. Intake
- Ask what the person brings (idea, journey or screen, bug) and size it: bug, small feature, milestone or project.
- Check the target branch has a merge gate (branch protection or a ruleset, required CI, no agent bypass). If it is unreadable or absent, tell the person: PRs are then never auto-merged. Record it as the plan's `"merge": "owner"`.
- In repos where Actions minutes cost the owner money (the person says so at intake), a multi-milestone change always sets `"integration"`: milestone PRs merge into it on their own, and the human merge decision applies only to the one release PR into `base`. A single-milestone change or a bug there may target `base` directly.
- Check the repo has fast commands (lint, typecheck, unit). Missing: ask.
- Once per repo, link `specs/` and `specs/adr/` from the README.
- Once per repo, if no git hooks run: set up cheap pre-commit and pre-push hooks per `references/git-hooks.md`, every command through `templates/git-hook-env.sh`. Nobody skips them with `--no-verify`.
- Once per repo, if `<repo>/.cfactory/` is missing: Read `scripts/check-plan.py`, `scripts/goal-brief.py`, `scripts/migrate-ids.py`, `scripts/size-tasks.py` and `scripts/test-integrity.sh` from this skill's folder with the Read tool, Write them to `<repo>/.cfactory/`, and commit them on the first change branch. Refresh them the same way before every launch when the skill's copies differ. Always run them from `.cfactory/`, never by the plugin's install path: another plugin's guard refuses any Bash command that names the plugin cache.

### 1. Grill and spec
- Grill per `references/grilling.md`, for every size. The tree covers test edits, who can see what, deferrals with probes, merge and production gate, holds, design boards and preflight tools.
- Write `intent.md` (`references/intent-template.md`), then `delta.md` with journeys and the design mapping, per `references/spec-standard.md`. Every requirement `req-<n>` (the next free number in the repo) cites `[outcome-<n>]` or `[constraint-<n>]`. Ids in prose come after an explainer of at most eight words ("guests see only their own comments in mail (req-159)"); scheme in `references/spec-standard.md`. No `[NEEDS CLARIFICATION` may remain.
- Draft holdout scenarios with a separate agent that never sees builder output. Each names its `milestone`.
- For a risky milestone, one read-only sweep of the base (an Explore agent) lists every place an actor can see the data. It becomes the plan's `surface`; the pattern for how the guarded data is read goes in `guards`, and `check-plan.py` fails on any source file that matches it and no task, surface exposure or probed deferral covers.

### 2. Plan and approval
- Copy `references/plan-template.md` (or `plan-small-template.md`) to `changes/<slug>/plan.md` and fill it per `references/plan-standard.md`, including the `json cfactory` block.
- A change approved under the old ids (`I1`, `C1`, `<spec>/R<n>`) runs `python3 .cfactory/migrate-ids.py . --slug <slug>` once before its next approval; it rewrites in place and commits nothing.
- Run `python3 .cfactory/check-plan.py changes/<slug>/plan.md`, with `--all` when the run will be `--all` (every milestone then needs tasks). It must print `PLAN OK`. Run every `preflight` command now.
- A project run (`--all`) has no `hold`: settle billing and other owner actions during grilling, before approval.
- One fresh review of the plan by Codex `gpt-6.2-astra`, correctness against the intent and delta only. It checks the riskiest step and the options rejected in Risks. Apply `references/review-policy.md`.
- **PRs: one per milestone, nothing else.** In repos where Actions minutes cost money (the person says so at intake) there is no plan PR: commit intent, delta, plan, `.cfactory/` and any new ADRs (as `proposed`) on milestone 1's branch, push it without a PR, and they merge with milestone 1's PR. Elsewhere a plan PR on `plan/<slug>` holds them.
- Check every new ADR number is unused on the base.
- **The approval.** The person approves intent, delta, plan and boards together. Set new ADRs to `accepted` first, so milestone 1 carries the exact approved blobs; no step changes an ADR's status after approval. Commit, then record the SHA (`git rev-parse HEAD`) as `approved: <sha>` in the plan's first progress entry. Changed scope later means a new revision and a new approval.

### 3. Build
- Stations 0 to 2 run in a normal session, never under `/goal`. They end at the approval. The launched run is a separate process.
- Optional integration branch: when the plan sets `"integration": "<branch>"`, create it from `base`. Milestone branches are cut from it and their PRs target it.
- Per milestone: `wt switch -c milestone/<slug>-<M>` from a fresh base (the integration branch when set), then inside it run `python3 .cfactory/goal-brief.py changes/<slug>/plan.md <M> --approved <sha>`, or `--all --approved <sha>` for the whole plan. It refuses a plan that fails the check, changed since `<sha>`, or a milestone without tasks. It writes `kickoff-<M>.md` and prints the `/goal` line and the run command. Never hand-write a goal line.
- **Launch.** First refresh `<repo>/.cfactory/` from this skill's scripts (Read, then Write, as station 0 says) and regenerate the kickoff when `.cfactory/` changed or the kickoff names agents that no longer exist (an old plugin prefix). Commit both. Then start the RUN command goal-brief prints with the Bash tool and `run_in_background: true` (`claude -p ... "/goal ..."`; print mode honors a goal prompt). When it finishes, report the end state line (SHIPPED, HOLD, BLOCKED or INCOMPLETE) from the run's final result. Details: `references/goal-briefing.md`.
- Every task runs in a `factory:builder` subagent, even a one-line fix. The coordinator only creates worktrees, runs checks, merges and logs.
- Create each task worktree yourself, never with the Agent tool's worktree isolation: `git branch <slug>-<M>-<task> milestone/<slug>-<M>`, then `wt switch <slug>-<M>-<task> --no-cd --yes`, then the plan's `setup`.
- Spawn builders (Sonnet 5.5, medium; low for mechanical replacement, high for complex tasks), 2 or 3 in parallel, each with its worktree path. Each owns disjoint files. Unfinished work stays in its worktree; never patch files.
- A hook denies `run_in_background` on every Agent call in a factory run, so every agent starts in the foreground.
- Builders may add tests and edit exactly the existing test files their own task's `allowTestEdits` lists. They never touch CI config, `.github/`, `.cfactory/`, baselines, specs, deltas or the plan, and never add lint suppressions. They never get the `~/.cfactory/scenarios` path. `test-integrity.sh` enforces this by exit code.
- The milestone's progress entry (with `firstPass`, `planRevisionsAfterApproval`, `diffMatchesPlan`) is committed and pushed before its PR can merge.

### 4. Verify
Run in this order, paste the output into the transcript:
1. Fast checks: lint, typecheck, unit. No local CI.
2. Per task, before merging it: `bash .cfactory/test-integrity.sh <task-worktree> milestone/<slug>-<M> <plan.md> --task <id> --approved <sha>` must print `INTEGRITY OK`.
3. `factory:verifier` with the delta, base, diff and the scenarios for this milestone and earlier ones (all of them on the last milestone). It also runs two neighbouring flows per changed behaviour. Never the builder's reasoning. Risky milestone: also a security review by one Opus 5.5 high agent or the Codex `gpt-6.2-astra` pass. Both fail only on Important findings (`references/review-policy.md`).
4. UI milestone: `factory:ux-verifier` against the approved boards, per `references/ux-checks.md`. It writes `evidence/<M>/gallery.md`. No owner stop.
- Failures go back to the builder: at most 3 passes per task. Stop after 2 attempts at the same failure with no new evidence.
- A fix for a confirmed High stays inside the task's own files and `allowTestEdits`. Anything else ends `BLOCKED: owner approves plan revision for <finding>`.
- A bug (`kind: bug`): the builder's first commit holds only the failing test; show it fails on base and record that SHA; the fix pass runs integrity with `--pin <sha>`.

### 5. Ship
- Before the PR: `test-integrity.sh ... --milestone <M> --approved <sha>` and `check-plan.py <plan.md> --approved <sha>` must pass.
- One PR per milestone into the base (the integration branch when the plan sets one). Link the delta and the reports.
- With an integration branch, milestone PRs merge on their own after the verify steps; no remote CI there. The release PR into `base` links every milestone's `gallery.md` and runs the full required CI.
- The release PR waits for a human only when a milestone is `risky` or `deployOnMerge` is true. The run then ends `SHIPPED` with the merge-ready URL. Otherwise it merges on its own after required CI.
- Without integration: `merge: auto` arms auto-merge; `merge: owner` never does, and the run ends at SHIPPED with the merge-ready PR URL.
- Commit everything first (progress entry, gallery, spec changes), then run the verifier on that final SHA, then push that same SHA. Any later commit means verifying again.
- With a `hold`: push the milestone branch, open no PR, end `HOLD` with the pushed SHA and a verifier PASS for that same SHA.
- The delta reaches the specs once, in the PR that ships the change to `base`. Before it, check every MODIFIED or REMOVED entry's prior text still matches the spec on `base` and every ADDED id is unused; a mismatch means the delta is reconciled and re-approved.
- Merge SHA and CI conclusion appear in the transcript. SHIPPED on a release PR also records deploy state: readiness at the serving SHA when the repo deploys on merge, or merge plus CI when deploy is disabled.

### 6. Learn
- Every escaped failure becomes a regression test that fails on the base, or a lint rule with remediation text.
- Every BLOCKED that grilling could have prevented becomes a new question in `references/grilling.md`.
- Every five milestones, tally `firstPass`, `planRevisionsAfterApproval` and `diffMatchesPlan` from the progress logs and re-measure `STEPS_PER_DISPATCH`.
- Optional weekly entropy run opening small cleanup PRs, only after three changes shipped.
- After any change to the factory itself, replay one known-good and one known-bad task.

Known limit: `hooks/guard-scenarios.py` (only `factory:verifier` may read the scenarios) matches tool-input text (with `~`, `$HOME`, `//` and `/./` expanded, and `cfactory` plus `scenarios` in one input), so a path assembled at runtime or reached through a symlink can bypass it. It fails closed on a crash or a non-object input that names the folder, and with `CFACTORY_EVAL=1` it denies the main session too. The verifier fails when the approved scenario set is missing.

## Models and effort
| Role | Model | Effort |
|---|---|---|
| Coordinator and builders (default work) | Sonnet 5.5 | medium |
| Mechanical code or text replacement tasks | Sonnet 5.5 | low (set in the builder dispatch) |
| Spec, plan, architecture, complex tasks | Sonnet 5.5 | high |
| Advisory: verifier, advisor, second opinion | Opus 5.5 | high |
| Codex doing work or building | `gpt-6.2-sol` | high |
| Codex advisory: plan review, risky-milestone pass | `gpt-6.2-astra` | high |

Stations 0 to 2 run at high effort; the unattended build run uses `--model sonnet --effort medium`. A task marked `"effort"` or `"model"` in the plan overrides the default, and a milestone `"verifier"` overrides Opus high.

The planner sizes every task, then `python3 .cfactory/size-tasks.py <plan> --write` applies the rules from the plan's own data (files per task, milestone `risky`, a `migrat` path):
- small (at most 3 files, not risky, no migration): `model: haiku`, `effort: high`.
- normal: `sonnet`, `medium`.
- large or risky (more than 8 files, a risky milestone, or a migration): `sonnet`, `high`.
- milestone verifier: `sonnet`/`high` when every task in it is small, otherwise `opus`/`high`.

The helper cannot see a task that implements an access, privacy or billing rule inside a non-risky milestone: mark that milestone `risky`, or set the task by hand. A task that implements an access or scope rule lists every read path of the guarded data it found, and the tests that assert the old behaviour are in its `allowTestEdits` (the read-path inventory). Codex advisory runs as `codex exec -m <model> -c model_reasoning_effort=high -s read-only --ephemeral`.

## The approval
One approval, one SHA. The person sees four short things: intent, requirements, boards, a plain plan summary. Everything else is an exit code or the platform. After it, the run stops only for a real BLOCKED. The gallery is reviewed once, from the release PR, and stops nothing.

## Stop and ask
- An owner decision, credential, approval or destructive migration blocks the work: write BLOCKED with the exact action needed, and stop.
- Scope grows beyond the approved intent and delta, or a fix needs a new task, other files or another test edit: `BLOCKED: owner approves plan revision for <finding>`.
- The merge gate is missing or unreadable: the owner merges by hand.
- A CI file, spec, ADR or scenario must change: only the owner decides, and the coordinator makes the change, never a builder.
- Verifier and builder disagree after 3 passes.
- A preflight command fails: `BLOCKED: <tool or credential> missing: <exact fix>`.
- State at any stop is `SHIPPED`, `HOLD`, `INCOMPLETE` or `BLOCKED`, appended to the plan's progress log.

## References (read when the station needs it)
- `references/grilling.md`: method, question tree, questions learned from BLOCKED runs. Station 1.
- `references/intent-template.md`: the intent file. Station 1.
- `references/spec-standard.md`: delta format, EARS, journeys, design mapping, holdouts, bug specs. Station 1.
- `references/plan-standard.md`: plan sections, layers, rules, every key of the JSON block. Station 2.
- `references/plan-template.md`: a filled plan that passes the check. Station 2.
- `references/plan-small-template.md`: a bug or small feature plan. Station 2.
- `references/goal-briefing.md`: goal line, merge rules, `--all`, bug flow, max-turns math. Station 3.
- `references/review-policy.md`: Important versus Nit. Station 4.
- `references/ux-checks.md`: per-screen UX checks and the gallery. Stations 4 and 5.
- `references/research.md`: why each rule exists, with sources. Read before changing a rule.

## Scripts
Copied into `<repo>/.cfactory/` at intake and run from there:
- `check-plan.py <plan.md> [--all] [--approved <sha>]`: dated slug, run caps, layers, needs, disjoint files, at least one requirement, requirement coverage, delta and intent, and that the approved files did not change: the whole plan text up to the json block, intent and delta; only appended progress entries may differ. `--all` also needs every milestone detailed with tasks.
- `size-tasks.py <plan.md> [--write]`: prints per task its model and effort and per milestone the verifier tier from the sizing rules; `--write` sets those fields in the json block, leaving any the plan already sets.
- `migrate-ids.py <repo> [--slug <slug>]`: one-shot rewrite of the old ids (`<spec>/R<n>`, `I<n>`, `C<n>`) in the git-tracked text files to `req-<n>`, `outcome-<n>`, `constraint-<n>`; refuses when two specs share a number; commits nothing.
- `goal-brief.py <plan.md> <M> --approved <sha>` or `<plan.md> --all --approved <sha>`: kickoff file, `/goal` line, run command. The plan path is repo-relative, so it resolves inside any task worktree. At each milestone cut it records `--target <sha>`, the fetched integration or base head, which the integrity checks diff against.
- `test-integrity.sh <worktree> <base-ref> [plan.md [--task <id> | --milestone <id>] [--approved <sha>] [--pin <sha>] [--checked <shas>] [--target <sha>]]`: touched tests, paths outside the task, CI, `.github/`, `.cfactory/`, plan, baselines, spec, skips, added lint suppressions. `--checked` lists the builder commits already checked; implementation changes outside them fail. `--milestone` requires `--approved`, which must be an ancestor of HEAD; the plan scope is read from it. A new test counts as in scope only in a task file's folder or via `allowTestEdits`; every new file gets the skip and suppression scans.

## Not built
Board, receipts and approval ledgers; local CI; self-policing hooks; one agent per stage; pixel diffs; E2E repeat logic; satisfaction scoring; digital twins; dark no-review mode; a foreman, queue or status page.
