# Local iteration; GitHub's required checks are the gate

This is the verification contract for builders, milestone close, review fixes, flaky tests,
E2E work, PR creation and copied project instructions. Iterate locally; the merge gate is
the repository's required GitHub Actions checks. No local receipt, hook or script stands in
for them, and nothing blocks a push or a PR on a local receipt.

## Before a push

Never push to "see what CI says". Run the repository's format check, lint, typecheck and
tests (the `sdlc.json` `checks`, or
the repo's own full suite) before committing and before the first push of a change.
Targeted checks during development are fine; the full suite on the final head catches what
they miss. Batch fixes into one push, not a push per edit.

## One list: the milestone check is the repo's check

`sdlc.json` `checks.milestone` is the repo's single local check list, the one a CI run also
executes (one script or make target that runs the whole list, or the same commands).
A green milestone close then means ready to push; a second, different gate (a milestone list
with `npm test` and one E2E config next to a CI script with another list and another E2E config) runs the
slow checks twice and still passes one and fails the other. When a script already holds the list,
set `checks.milestone` to just that script. `verify_gate.py` runs the list cheapest first and
stops at the first failure (`--keep-going` runs them all); a check that needs an earlier one's
output declares `"after": ["<check name>"]` (it runs behind that check; codegen before the typecheck) or sets `"serial": true`. An approval made before 3.18.0 keeps the declared order; a new one records `"order": "cost"` in `lock.json`. A check passes the gate cached per tree, so a retry runs only what
failed.

## When a check fails

1. Read exactly which job or test failed and why, whether the failure was local or remote.
2. Reproduce that test locally with the same relevant seed, configuration and fixture.
3. Fix the cause and rerun only the failing test(s) plus the directly affected suite until
   green. For an E2E change, run that spec and its neighbours locally, not the full pipeline.
4. Run the full suite once on the final head before pushing the batched fixes.

Never rerun a whole pipeline to retry one flaky or failed test. Never push a speculative
fix. The required GitHub checks decide whether a PR can merge; read their logs to find the
failure, then debug it locally. If reproduction needs unavailable cloud access, report the
precise blocker; a blind retry is not proof.

## What GitHub runs

GitHub Actions runs the required checks, deploys, previews, cloud Terraform plans, comments,
labels and scheduled jobs. Skip bot and draft previews; serialize deploy and cleanup work
that must finish. Use PR concurrency with cancel-in-progress and relevant path filters. Do
not repeat the full suite on main after the PR already passed. Keep one job per stack where
possible, sharing installation. Choose the cheapest capable runner; macOS is for tagged or
manually dispatched Apple app releases, never every push or PR. Standard public-repo
runners are free. See [CI setup](ci-blueprint.md) and [adoption](adopt.md).

## Local milestones

Opt-in for a team with no GitHub Actions credits: `sdlc.json` `milestones.merge: "local"` (default
`"pr"`; absent means `pr`). Milestone and project branches are created and merged on this machine,
every check runs locally (the full suite), and the only online step is the PR
into the default branch.

1. **Project branch (stage 1.2):** create `project/<slug>` locally from `origin/<defaultBranch>`.
   Do not push it and do not look for it with `git ls-remote`.
2. **Milestone close (stage 5 step 4, stage 6 step 6):** cut each milestone from the local project
   branch. `verify_gate.py milestone` also fails with `check=parent-sync` until the local
   `project/<slug>` is merged in, so a milestone cannot skip an earlier one. After
   `VERIFY PASS milestone` on the head, merge it: `git switch project/<slug> && git merge --no-ff
   milestone/<slug>`. No milestone push, PR or auto-merge. A milestone with no project branch is
   unchanged: one push and one PR into the default branch.
3. **Project close (stage 6p):** with `project/<slug>` checked out and `git merge origin/<defaultBranch>`
   done, run `python3 scripts/verify_gate.py project <slug>` (it runs `checks.milestone` and records
   `VERIFY PASS project <slug> <sha>`; `{id}` in a check is the slug). Then push `project/<slug>`
   once and open one PR into the default branch.
4. **`pr-gate.sh`:** refuses a milestone push when its change has a project branch, and a PR from
   `milestone/*` into `project/*`, naming the merge command; lets `project/*` be pushed only when
   its head carries `VERIFY PASS project`; and, on a `project/*` branch, refuses `git merge` of a
   `milestone/*` ref whose head lacks `VERIFY PASS milestone` (the gate may have run in another worktree).
5. **`/goal`:** a milestone is DONE when its gated head is an ancestor of the local `project/<slug>`
   (`${CLAUDE_SKILL_DIR}/scripts/sdlc_status.py goal <ID>`); the project is DONE when its PR into the default branch is merged
   or armed (`${CLAUDE_SKILL_DIR}/scripts/sdlc_status.py goal <ID> --project`, `templates/goal/project.txt`).
