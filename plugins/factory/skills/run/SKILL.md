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
- `/factory:run <slug>`: continue a change, by the same person or another. Read `changes/<slug>/` and the plan's progress log. Reconcile with git and PR state: the merge SHA and PR state come from `gh pr view <n> --json state,mergeCommit` or git, never from the log. Then do the next step only:
  1. `intent.md`, `delta.md` or `plan.md` missing or still open: continue the grill (station 1).
  2. All written but not approved, or changed since the approved SHA: ask for the approval (station 2).
  3. Otherwise launch the first unmet milestone (station 3).
- Auth failure, exhausted credit or context overflow clears a goal: `/factory:run <slug>` starts a new one from the progress log.

## The process, for every size
1. **Grill.** Rounds of at most 5 numbered questions, each with a recommended answer, until no decision is open. Subagents look up facts. Method and question tree: `references/grilling.md` (or `mattpocock-skills:grilling` when installed).
2. **Write.** `intent.md`, `delta.md`, the holdout scenarios and `plan.md`. A bug or small feature is a plan with `kind` and one milestone with one task, from `references/plan-small-template.md`.
3. **Approve once.** The person approves all of it together. The approval is the commit SHA at that moment.
4. **Run one `/goal`.** One milestone, or `--all` for the whole plan. The run stops only for BLOCKED: an owner decision, a credential, money or an irreversible act. A finding inside an approved requirement goes to the gap lane.
5. **Learn.** A BLOCKED that grilling could have prevented becomes a new question in `references/grilling.md`.

## Who uses it
- Product managers, product engineers and UX designers all run this one skill, alone or together. There are no role fields and no file ownership.
- Intake asks what the person brings: an idea, a journey or screen, or a bug. All work is spec-driven: a behaviour change starts as a delta.
- Several people continue one change with `/factory:run <slug>`. The change folder and git are the shared state. Whoever runs the session approves, or names who should.
- The approval is readable without code: intent, requirements, boards and a plain summary of the plan. Engineering detail stays in the plan.

## Files
Specs in `specs/`, one folder per change in `changes/<slug>/` (intent, delta, plan, kickoff, evidence), the plugin's scripts in `.factory/` (copied at session start, commit it), holdout scenarios outside the repo in `~/.factory/scenarios/`.
Layout, spec lifecycle, ADRs and the one-time rename of old repos: `references/files.md`.

## Stations

### 0. Intake
Ask what the person brings and size it. Check the merge gate, the fast commands and, in repos where Actions minutes cost money, set `integration`. The plugin's scripts reach `.factory/` by a SessionStart hook; nobody copies them by hand. Detail: `references/intake.md`.

### 1. Grill and spec
- Grill per `references/grilling.md`. The tree covers test edits, who can see what, deferrals with probes, merge and production gate, holds, design boards and preflight tools.
- Write `intent.md` (`references/intent-template.md`), then `delta.md` with journeys and the design mapping (`references/spec-standard.md`). Every requirement `req-<n>` (the next free number in the repo) cites `[outcome-<n>]` or `[constraint-<n>]`.
- Ids in prose come after an explainer of two to eight words: "guests see only their own comments in mail (req-159)". The check enforces the two; the eight is guidance. No `[NEEDS CLARIFICATION` may remain.
- Draft holdout scenarios with a separate agent that never sees builder output. Each names its `milestone`.
- For a risky milestone, one read-only sweep of the base (an Explore agent) lists every place an actor can see the data. It becomes the plan's `surface`.
- The pattern for how the guarded data is read goes in `guards`; `check-plan.py` fails on any source file that matches it and that no task, surface exposure or probed deferral covers.
- On a milestone with access or privacy requirements, also ask for `mayTouch`, the files a late finding may touch.

### 2. Plan and approval
- Copy `references/plan-template.md` (or `plan-small-template.md`) to `changes/<slug>/plan.md` and fill it per `references/plan-standard.md`, including the `json factory` block.
  - The planner sizes each task by judgement: effort and model default to Sonnet 5.5 medium and are set only where a task needs more.
- Run `python3 .factory/check-plan.py changes/<slug>/plan.md`, with `--all` when the run will be `--all`. It must print `PLAN OK`. Run every `preflight` command now. A project run (`--all`) has no `hold`: settle owner actions during grilling.
- One fresh plan review by Codex `gpt-6.2-astra`, correctness against the intent and delta only. It checks the riskiest step and the options rejected in Risks. Apply `references/review-policy.md`. When `codex` is absent, skip it.
- **PRs: one per milestone, nothing else.** Where Actions minutes cost money there is no plan PR: commit intent, delta, plan, `.factory/` and any new ADRs (as `proposed`) on milestone 1's branch, push it without a PR, and they merge with milestone 1's PR.
  - Elsewhere a plan PR on `plan/<slug>` holds them.
- Check every new ADR number is unused on the base.
- **The approval.** The person approves intent, delta, plan and boards together.
  - Set new ADRs to `accepted` first, so milestone 1 carries the exact approved blobs.
  - Commit, then record the SHA (`git rev-parse HEAD`) as `approved: <sha>` in the plan's first progress entry.
  - Changed scope later means a new revision and a new approval.

### 3 to 6. Build, verify, ship, learn
The launched run is a separate process, never under `/goal` in this session. Per milestone:
`wt switch -c milestone/<slug>-<M>` from a fresh base, then `python3 .factory/goal-brief.py changes/<slug>/plan.md <M> --approved <sha>` (or `--all`). It writes `kickoff-<M>.md` and prints the `/goal` line and the run command.
Never hand-write a goal line. Start the printed RUN command with the Bash tool and `run_in_background: true`, and report the end state line (SHIPPED, HOLD, BLOCKED or INCOMPLETE) when it finishes.

The run, in short:
- The coordinator calls `task-step.py` for worktrees, integrity and merges; every task runs in a `factory:builder` subagent, in the foreground (a hook denies background agents).
- Verify: fast checks, per-task integrity, `factory:verifier`, a security review on a risky milestone, `factory:ux-verifier` on a UI milestone. Each FAIL is labelled `bug` or `gap`, and a builder's report of a file no task owns or a test edit opens a `gap` too; up to `gapRounds` gap rounds per milestone (default 3), inside the owner-approved `mayTouch`.
- Ship: commit, verify that SHA, push it, one PR per milestone. The release PR waits for a human only when a milestone is `risky`, `deployOnMerge` is true or the plan sets `merge: owner`.

Every rule, with the merge matrix, the bug flow and the learn loop: `references/run-stations.md` and `references/goal-briefing.md`.

## Models and effort
One default: Sonnet 5.5 medium for the coordinator and builders; stations 0 to 2 run at high effort. Verifier, advisor and second opinions: Opus 5.5 high. Codex doing work: `gpt-6.2-sol` high; Codex advisory:
`gpt-6.2-astra` high, run as `codex exec -m <model> -c model_reasoning_effort=high -s read-only --ephemeral`. A task's `effort` or `model` and a milestone's `verifier` in the plan override the default.

## The approval
One approval, one SHA. The person sees four short things: intent, requirements, boards, a plain plan summary. Everything else is an exit code or the platform. The gallery is reviewed once, from the release PR, and stops nothing.

## Stop and ask
- An owner decision, credential, approval or destructive migration blocks the work: write BLOCKED with the exact action needed, and stop.
- Scope grows beyond the approved intent and delta, or a fix needs files or tests outside the milestone's `mayTouch` (or a gap past `gapRounds`): `BLOCKED: owner approves plan revision for <finding>`.
- The merge gate is missing or unreadable: the owner merges by hand.
- A CI file, spec, ADR or scenario must change: only the owner decides, and the coordinator makes the change, never a builder.
- Verifier and builder disagree after 3 passes.
- A preflight command fails: `BLOCKED: <tool or credential> missing: <exact fix>`.
- State at any stop is `SHIPPED`, `HOLD`, `INCOMPLETE` or `BLOCKED`, appended to the plan's progress log.

## References (read when the station needs it)
- `references/intake.md`: station 0, script delivery. `references/files.md`: layout, lifecycle, old repos.
- `references/grilling.md`: method, question tree, questions learned from BLOCKED runs. Station 1.
- `references/intent-template.md`, `references/spec-standard.md`: intent file; delta format, EARS, journeys, design mapping, holdouts, bug specs. Station 1.
- `references/plan-standard.md`, `references/plan-template.md`, `references/plan-small-template.md`: every key of the JSON block, a filled plan, a small plan. Station 2.
- `references/run-stations.md`: build, verify, ship, learn, the gap lane, known limit. Stations 3 to 6.
- `references/goal-briefing.md`: goal line, merge rules, `--all`, gap lane, bug flow, max-turns math.
- `references/review-policy.md`, `references/ux-checks.md`: Important versus Nit; per-screen UX checks (the verifier agents carry a copy).
- `references/research.md`: why each rule exists, with sources. Read before changing a rule.

## Scripts
Run from `<repo>/.factory/`, where the SessionStart hook keeps them equal to the plugin's copies:
- `check-plan.py <plan.md> [--all] [--approved <sha>]`: validates the plan, delta and intent, and that the approved files did not change (only appended progress entries may differ).
- `goal-brief.py <plan.md> <M> --approved <sha>` or `<plan.md> --all --approved <sha>`: kickoff file (from `kickoff.md`), `/goal` line, run command. The plan path is repo-relative.
- `task-step.py target|start|pin|finish|gate|status <plan.md> <M> [<T>] --approved <sha>`: the coordinator's per-task mechanics; reads the approved plan and derives checked commits from git.
- `test-integrity.sh <worktree> <base-ref> [plan.md [--task <id> | --milestone <id>] [flags]]`: touched tests, paths outside the task (plus the logged gap rounds inside `mayTouch`), CI, `.github/`, `.factory/`, plan, baselines, spec, skips and added lint suppressions. The flags are in its header.
  Flags are documented in its header.
- `migrate-name.py <repo> | --home`: one-shot rename of a pre-0.3.0 repo or home folder; commits nothing.
