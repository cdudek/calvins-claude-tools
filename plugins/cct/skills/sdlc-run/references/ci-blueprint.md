# CI blueprint — local checks, remote cloud work

Follow the [local-first contract](local-first.md) for all verification and failures.

## Setup

1. Define the full local suite from the repo's format, lint, typecheck, test, build and guard
   commands. `sdlc.json` `checks` and `ciCommands` can supply commands; never guess that a
   missing command means success. Keep E2E on a production build with isolated data.
2. Implement `scripts/ci-local` and its pre-push hook according to the contract: full suite,
   push, then the exact-SHA `local-ci` status.
   Test failing checks, stale heads, hook recursion and publication errors. `adopt` reports
   this setup as manual work; it does not install this repo-specific script.
3. Apply rulesets requiring the status on the default branch and any protected
   `milestone/*` and `project/*` bases. Confirm the ruleset is active, not just documented.
4. Retain remote jobs only for deploys, previews, cloud plans, GitHub operations and
   schedules. Skip bot/draft previews. Serialize deploys and cleanup with cancellation off;
   PR work uses cancel-in-progress and applicable path filters.
5. Share installation in one job per stack when possible. Use the cheapest capable runner;
   reserve macOS for Apple release builds on tags or manual dispatch. Standard runners in
   public repositories are free. No full CI rerun on main after a PR already passed.

## Existing remote CI (migration only)

`templates/ci/github-actions.yml` is a legacy remote-confirmation example, not the default
for new repositories. Its `changes` job uses `ciPaths` and its jobs use `ciCommands` for
six stacks. Existing copies keep running until the replacement local gate and its required
statuses are installed and verified. Do not copy its full remote pipeline into a new repo
or treat `check` as the new merge contract. Do not delete an existing required check before
the ruleset migration is applied. The cct repository itself retains its required `tests`
Actions check; free public minutes do not change the local debugging contract.

`ciPaths` remains the changed-path map for targeted development runs and existing CI:
`docs` is an optional ignore list, `all` matches lockfiles and workflow config, `code` and
`config` classify runnable paths, and per-step include/exclude lists select affected work.
Unknown code/config paths run every affected check. Do not ignore migrations or a docs
folder that builds into the product. `ciCommands` defaults and the stack command table in
`../../test-e2e-policy/references/suite-speed-and-reliability.md` section K remain useful
locally. These lists never reduce the full gate required before a push.

## Scheduled audit

Keep the monthly enforcement audit in GitHub. Run `python3 scripts/verify_gate.py audit`,
record installed, configured, executed, passed and required/applied separately, and verify
that local-ci protects every intended base. A documented gate without its
script, hook and applied ruleset is still unfinished adoption work.
