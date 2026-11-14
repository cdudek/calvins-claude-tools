# CI blueprint — GitHub Actions required checks are the gate

Merge protection is the repository's required GitHub checks. Iterate locally per the
[local-first contract](local-first.md); no local script, receipt or hook gates a push.

## Setup

1. Define the full suite from the repo's format, lint, typecheck, test, build and guard
   commands. `sdlc.json` `checks` and `ciCommands` can supply commands; never guess that a
   missing command means success. Keep E2E on a production build with isolated data.
2. Run that suite in GitHub Actions as required checks on the default branch and any
   protected `milestone/*` and `project/*` bases. `templates/ci/github-actions.yml` is a
   starting point; `adopt` never installs it. Confirm the ruleset is active, not just
   documented.
3. Keep deploys, previews, cloud plans, GitHub operations and schedules in GitHub too. Skip
   bot/draft previews. Serialize deploys and cleanup with cancellation off; PR work uses
   cancel-in-progress and applicable path filters.
4. Share installation in one job per stack when possible. Use the cheapest capable runner;
   reserve macOS for Apple release builds on tags or manual dispatch. Standard runners in
   public repositories are free. No full CI rerun on main after a PR already passed.

## The example workflow

`templates/ci/github-actions.yml` has a `changes` job that uses `ciPaths` and jobs that use
`ciCommands` for six stacks, with one required status, `check`. Adapt it, never copy it
blind: do not delete an existing required check before its replacement is applied.

`ciPaths` is the changed-path map for targeted development runs and CI: `docs` is an
optional ignore list, `all` matches lockfiles and workflow config, `code` and `config`
classify runnable paths, and per-step include/exclude lists select affected work. Unknown
code/config paths run every affected check. Do not ignore migrations or a docs folder that
builds into the product. `ciCommands` defaults and the stack command table in
`../../test-e2e-policy/references/suite-speed-and-reliability.md` section K stay useful
locally. These lists never reduce the required checks.

## Scheduled audit

Keep the monthly enforcement audit in GitHub. Run `python3 scripts/verify_gate.py audit`,
record installed, configured, executed, passed and required/applied separately, and verify
that the required checks protect every intended base.
