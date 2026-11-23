# sdlc-run, end to end

Describes sdlc-run 4.2.4.

`/cct:sdlc-run` plans, builds and proves a change across one or more repos. You approve once. The next thing you do is merge. Nothing is installed in the repos: the plugin ships the skill, the agents and the runner.

Verification and every push follow the [local-first contract](../plugins/cct/skills/sdlc-run/references/local-first.md); read it before running checks or preparing a push. The design is `docs/designs/2026-11-23-sdlc-greenfield.md`.

## The flow

- **Plan:** `sdlc plan` reads each repo's own instructions, manifests and CI, probes tools, credentials, browsers and CI jobs, and drafts a plan and a contract.
- **Approve once:** one Plannotator screen shows the plan, the actual checks with expected values, dependency and lockfile changes, destinations and caps. `sdlc gate <id> --by <name>` records the digest of that bundle in the same process that Plannotator approved it.
- **Build:** up to 8 builder subagents (the contract may raise the cap to 10) work in worktrees the runner cuts at the integration SHA. A fresh verifier subagent runs the approved checks on a clean checkout; only the runner writes results.
- **Close:** a milestone that passes its due checks and the full local gate merges into `sdlc/<run-id>` locally. The only PR per repo is that branch into the default branch.
- **Several repos:** `sdlc pack` and `sdlc publish` handle producers with several npm packages, vendor their tarballs into the consumer and let the runner rewrite the lockfile offline. `sdlc boards index` and `sdlc boards rows` turn a design-canvas export into measured check rows.
- **Check:** `sdlc check` is read-only and ends in one line. Exit 0 READY, 1 FAIL, 2 BLOCKED or STOPPED, 3 PENDING.

## Where things live

- **Records:** `~/.sdlc/runs/<run-id>/`, never committed. The run ID is `<date>-<start repo>-<slug>`; every repo uses branch `sdlc/<run-id>`; `~/.sdlc/active/` links the live runs.
- **Runner:** `plugins/cct/skills/sdlc-run/runner/` (plain Python). Hooks block agents from writing under `~/.sdlc/runs/`.
- **Resume:** `sdlc resume <id>` on the same machine; `sdlc stop <id>` cancels jobs and keeps branches and records.

## Moving from 3.x

3.x runs finish on 3.x. `sdlc clean <repo>` lists the copies 3.x installed (exact matches, edited copies, shared-file fragments, unknown files); `--apply` prepares a cleanup branch for review. See the [changelog](../plugins/cct/skills/sdlc-run/references/changelog.md).
