@@ top
# Kickoff: {{title}}

You coordinate factory change {{change}}, {{scope}}. The approved plan and delta are on `{{tgt}}`, or on this branch for milestone 1 in a repo without a plan PR. Read {{P}}plan.md and {{P}}delta.md first. The owner approved revision `{{sha}}`; every integrity and plan check below passes it.
Do reversible steps yourself and keep going: create a missing branch, rerun a check, recreate a worktree. Stop only for a decision the plan does not cover or an irreversible step.
Resume rule: read the progress log in plan.md, reconcile it with git and PR state, skip what is already done. Read a PR's state and merge SHA from `gh pr view <n> --json state,mergeCommit` or git, never from the log. `python3 .factory/task-step.py status {{P}}plan.md <M> --approved {{sha}}` prints the recorded <target SHA> and the <checked SHA>s, which it derives from the `factory-merge:` merges in git. If the target is missing, re-record it with `python3 .factory/task-step.py target {{P}}plan.md <M> --approved {{sha}} --resume`.
{{standing}}
{{all_start}}
{{milestones}}

## Stop
End with exactly one state: {{end_state}}, INCOMPLETE or BLOCKED.
{{hold_stop}}
BLOCKED: an owner decision, credential, approval or destructive migration. Write the exact action needed and stop.
A test already red on the base (`FINISH tests PRE-EXISTING` or `GATE tests PRE-EXISTING` lines) is never a reason for BLOCKED: list those lines as a note in the {{end_state}} or BLOCKED report.
Scope beyond the delta, or a test, CI file or spec that must change and is not a gap-lane fix: BLOCKED, the owner decides.
@@ all_start
At the start of each milestone, re-read the pinned plan (`git show {{sha}}:{{P}}plan.md`, its json block) and the progress log in plan.md, and reconcile with git and PR state. Start a milestone only after the previous one is merged. A later milestone gets its own worktree: `git fetch origin`, record `git rev-parse origin/{{tgt}}` as that milestone's <target SHA>, `git branch milestone/{{change}}-<M> <target SHA>`, `wt switch milestone/{{change}}-<M> --no-cd --yes`, then run `python3 .factory/task-step.py target {{P}}plan.md <M> --approved {{sha}}` inside it.
{{preflight}}
{{hold_note}}
@@ hold_merge
4. The owner action `{{hold}}` comes after the run: open no PR. Push `{{branch}}`, which is the <final SHA>, and print it with the verifier PASS for that SHA. Then merge it into `{{tgt}}` yourself, committing nothing else on the milestone branch:
   - `git fetch origin`, `git switch --detach origin/{{tgt}}`, `git merge --no-ff {{branch}} -m "Merge {{branch}}"`, then `git push origin HEAD:refs/heads/{{tgt}}`.
   - Append `HOLD-MERGED {{mid}} <merge SHA>` to the progress log in plan.md, commit it and push the same way.
   - {{after}}
@@ milestone
{{h}} Build
{{preflight}}
{{target_step}}
One worktree per task, created by you with `python3 .factory/task-step.py start {{P}}plan.md {{mid}} <task id> --approved {{sha}}`, never by the Agent tool's worktree isolation. It cuts the task branch and worktree at the milestone head, runs the plan's `setup` in it and prints `START OK <task id> <worktree path> <sha>`; use that path.
{{task_lines}}
Every task runs in a factory:builder subagent (Sonnet 5.5, at the task's builder effort), even a one-line fix; you only start worktrees, run checks, merge and log. Run 2 or 3 at a time, in the foreground, each given its worktree path, owned files, requirement ids and check. Never give a builder the scenarios path. Brief builders with the plan's test commands verbatim and add no test-running advice: never "serial", never a parallelism-off flag.{{model_note}}
Every agent you start (builders, verifiers, reviews) runs in the foreground, never with run_in_background: a background agent pauses the goal check, and an unattended run exits under it.
Unfinished work stays in its task worktree and the next pass gets the same path. Never patch files (no `git apply`, no copied diffs). To read a diff: `rtk proxy git diff`.
{{bug_flow}}

{{h}} Verify, in this order, pasting each output into the transcript
1. The plan's `tests` (rules: the factory plugin's references/test-strategy.md): the suites run once in the Ship gate below (`GATE tests OK|FAIL <suite>`), the hand-back tests in step 2. A plan without `tests`: the repo's fast checks (lint, typecheck, unit). No local CI.
2. Per task, before merging it into `{{branch}}`: `python3 .factory/task-step.py finish {{P}}plan.md {{mid}} <task id> --approved {{sha}}` runs the task's integrity check and the plan's hand-back `tests` in its worktree, records its HEAD as a <checked SHA> (every INTEGRITY OK commit, also an earlier pass's) and merges exactly that commit into `{{branch}}`. It must print `FINISH OK`.
{{ux_step}}
Failures go back to the builder of that task, at most 3 passes. Stop after 2 attempts at the same failure with no new evidence.
{{gap_line}}

{{h}} Ship, in this order
Commit first, verify that final commit, push that same SHA. Nothing is committed after the verifier: a later commit is a different SHA and needs the verifier again. A risky milestone's `task-step.py review` records its round in the git-ignored state file, not in plan.md, so copy its printed `SECURITY-REVIEW` line into the next progress entry or the HOLD/SHIPPED message.
1. Commit on `{{branch}}`: {{commit_what}}the progress entry to plan.md (time, milestone, requirement ids, done and remaining, check result, next action; no PR number or merge SHA, they are not known yet and `gh pr view` has them).
{{gate_verify}}
{{ship_tail}}
