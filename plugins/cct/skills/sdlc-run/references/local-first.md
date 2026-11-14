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
