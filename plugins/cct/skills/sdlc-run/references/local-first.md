# Local-first verification and the local CI gate

Owner rule, 2026-11-08. This is the verification contract for builders, milestone close,
review fixes, flaky tests, E2E work, PR creation and copied project instructions.

## Before every push

Never push to "see what CI says". Before the first push of a change, run the repository's
`scripts/ci-local`, or its full local suite if the gate has not been installed. Include
format check, lint, typecheck, tests and the applicable build and guard checks. Run the
repo's required checks before committing as well; targeted checks during development do
not replace the full gate before a push. Batch fixes into one push, not a push per edit.

## When a check fails

1. Read exactly which job or test failed and why, whether the failure was local or remote.
2. Reproduce that test locally with the same relevant seed, configuration and fixture.
3. Fix the cause and rerun only the failing test(s) plus the directly affected suite until
   green. For an E2E change, run that spec and its neighbours locally, not the full pipeline.
4. Run the full local gate once on the final head before pushing the batched fixes.

Never rerun a whole pipeline to retry one flaky or failed test. Never push a speculative
fix. Remote CI, where a repository still has it, is confirmation, not a debugger. Waiting
on GitHub for feedback a local run could give is a defect in the process. If reproduction
needs unavailable cloud access, report the precise blocker; a blind retry is not proof.

## Gate and status publication

The repository-owned `scripts/ci-local` runs the full suite and Decision4 validation,
pushes the verified commit, then posts `local-ci` and `decision4` commit statuses for that
exact SHA. A pre-push hook invokes the same gate, with a recursion guard for the script's
own push. Require both statuses in rulesets for the default branch and protected
`milestone/*` and `project/*` branches. Never post them by hand, copy prior statuses, or
mark skipped or failed validation successful. A dirty or moved head, failed push, failed
check or failed status publication leaves the gate unsuccessful. A new commit, merge or
rebase requires fresh evidence. Decision4 reads the PR body and the boundary map's highest changed-path floor. For an
initial PR, validate the proposed body locally, push the verified branch, create the PR,
and validate the actual body before publishing success. Revalidate when that body or map
changes.

GitHub keeps deploys, previews, cloud Terraform plans, GitHub comments/labels and scheduled
jobs. Skip bot and draft previews; serialize deploy and cleanup work that must finish.
Use PR concurrency with cancel-in-progress and relevant path filters. Do not repeat the
full suite on main after the PR already passed. Keep one job per stack where possible,
sharing installation. Choose the cheapest capable runner; macOS is for tagged or manually
dispatched Apple app releases, never every push or PR. Standard public-repo runners are free.

## Adoption and existing repositories

This is a contract to implement and audit, not evidence that a gate is installed. `adopt`
keeps existing CI and prints the local-gate setup requirement; it does not manufacture
statuses or install a universal gate with guessed stack commands. Supply the repo's full
suite and Decision4 validator, test their failure paths, install the pre-push hook, apply
the rulesets and verify both required statuses before removing an existing required check.
A repository's existing required remote checks remain required until that migration is
complete. See [CI setup](ci-blueprint.md) and [adoption](adopt.md).
