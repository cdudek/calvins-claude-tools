# Heavy work: one queue, local test databases, a few guards

In one large change, helpers waited for hours on builds and browsers, and one usage limit stopped 13
of them at once and killed their queued jobs. Capacity was never the number of helpers; it was the
number of builds, app servers and browsers a machine can run. This file is the kit's answer. Scripts:
`scripts/heavy.py`, `scripts/db.py`, `scripts/evidence.py`, `scripts/preflight.py` (installed by
`adopt`, stdlib only, so they run in CI and inside `/goal` where no plugin is installed).

## What is wired in (3.22.0)

- **The gate is one job.** What a job is: one command through the queue. The milestone close is one job, not one per check. `verify_gate.py milestone` runs the light checks first (format, lint, typecheck; neighbours that are not `serial` and not `after` one another run side by side, `heavy.lightParallel`, default 4), then takes **one slot** before its first heavy check and holds it to the end, exporting `SDLC_HEAVY_HOLDER` so a nested `heavy.py run` passes straight through. A heavy check that is already cached never takes a slot. A gate started inside a slot (`heavy.py run -- verify_gate.py milestone`) takes no second one. A check's own timeout (`checkTimeout`, per-check `timeout`) still kills its process group, and the slot ticket records the running check's group, so a dead gate's check is killed. With `preflight` in `sdlc.json`, the preflight is a wall: it runs before everything else. The gate ends with `timing: queue wait Ns, total Ns; <check> Ns, ...` and the report carries `metrics.queue_wait_s`.
- **Waiting.** While the holder is within its own run deadline the gate waits with no deadline. `heavy.waitTimeout` is the cap for a dead queue: it counts only once every holder is past its own `runTimeout` (plus a 60 s grace), then `VERIFY BLOCKED reason=env` names the holder.
- **One database for the close.** With `db.test`, the gate calls `db.py test create` once after taking the slot, exports `DATABASE_URL` to every check, drops and recreates the copy from the template before each heavy check that follows another (set `"resetDb": false` on a check to keep the data, `"resetDb": true` on a light one to reset before it), and drops it at the end whatever the verdict. A build check (any check named `build`) runs once per tree: a passing check is cached by tree, command and lock.
- **The hooks.** `helper-guard.sh` is registered by `adopt`. A feature-PR repo with local milestones is refused with the two ways out, and a `blocked[]` rule with no message still refuses and names who owns `sdlc.json`.
- **Status.** `sdlc_status.py status` shows who holds or waits for a slot, and a failed stop left in `sdlc-stop-status.json`. It runs the plugin's own `heavy.py`, never a repo copy.

## Heavy and light

| Heavy: takes a slot | Light: never waits |
|---|---|
| builds, app servers (`dev`, `start`), browser tests, screenshot captures, smoke runs, the full test suite (`npm test`), `verify_gate.py milestone` | format, lint, typecheck, architecture checks, unit tests of touched files, database tests against the local container, git |

`heavy.py classify -- <cmd>` answers heavy or light. `heavy.py run --auto -- <cmd>` takes a slot only
for a heavy command. The classifier reads the **program and the script**, never a word anywhere in the
line: `npm|pnpm|yarn|bun test`, `... run build`, `... run smoke:background`, `npx next start`,
`playwright`, `make e2e`, `python3 scripts/capture.py` and `verify_gate.py milestone` are heavy;
`prettier --check e2e/a.spec.ts`, `pnpm lint e2e`, `vitest run src/build/x.test.ts` and
`pytest` are light. A suite under another name is the repo's to list in `sdlc.json` `heavy.patterns`
(regexes over the command line, which override the classifier); `adopt` seeds it once from
`checks.milestone` and `ciCommands` and never overwrites it.

## The queue

```bash
python3 scripts/heavy.py run -- pnpm build               # wait for a slot, run, release
python3 scripts/heavy.py submit -- pnpm exec playwright test   # detached: prints a job id, returns
python3 scripts/heavy.py wait <job>                      # exit code of the job; 75 on the deadline
python3 scripts/heavy.py status                          # who holds a slot, who waits
```

- **One heavy job at a time per machine** by default. `sdlc.json` `heavy.slots` (or env
  `SDLC_HEAVY_SLOTS`) raises it for a machine that has the cores and the memory.
- **First come, first served, per machine.** Tickets are files in one per-user folder,
  `${SDLC_HEAVY_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/sdlc/heavy}`, so every worktree of every repo
  on the machine shares one queue, one set of slots and one set of ports. A ticket names its repo,
  worktree and job process group. The old queue in the git dir is ignored (a one-shot move, no
  compatibility): a job queued by an older kit is simply not in the line.
- **The job dies with its wrapper.** A ticket whose wrapper process is dead is dropped, whether it held a
  slot or waited, and its recorded process group is killed first, so a killed helper never blocks the line
  and never leaves a build running behind a free slot. SIGHUP and SIGINT stop a job like SIGTERM.
  Results are written by atomic rename. `heavy.py submit` run inside a slot still queues.
- **Job logs are pruned.** `heavy.py prune` removes job folders older than 7 days and orphans (no result,
  wrapper gone); the gate calls it at its start.
- **A waiter says who is ahead:** pid, command, worktree and age of the holder.
- **Deadlines, never forever:** `heavy.waitTimeout` (default 1800 s) exits 75 naming the holder and
  nothing ran; `heavy.runTimeout` (default 3600 s) kills the job and exits 124. Hand the unchanged
  evidence to its owner instead of waiting again. 0 turns a deadline off.
- **Ports come from the slot.** The job gets `SDLC_HEAVY_SLOT`, `SDLC_APP_PORT` and `SDLC_STUB_PORT`
  (`heavy.portBase`, default 4100, plus 10 per slot, plus 1 for the stub). A repo whose app hard-codes a
  port reads these instead; never derive a port from the worktree path.
- **No self-deadlock.** A heavy command started under a held slot (the env marker
  `SDLC_HEAVY_HOLDER` names a live process) passes straight through, so a gate run inside a slot does not
  queue behind itself.

**Submit and stop.** A builder that must wait for a long browser run submits it and returns its report
with the job id; the supervisor watches it (`Monitor` on the result file, or `heavy.py wait` as a
background command) and wakes the next step on the result. A builder never parks on a queue while other
builders could use its time. Light work keeps running while heavy jobs queue.

## How many helpers

At most **4 builders** run at once (the dispatch limit in `stages.md`), inside **about 6 helpers** in
all: builders plus the reviewer, validator and fix-part agents the supervisor has out at the same
moment. Fewer, longer helpers beat many short ones, because each helper pays its own context cost.
The slot count is separate: six helpers can share one slot, and that is correct.

## Codex builders

The Codex sandbox keeps every `.git` read-only and the queue's folder is outside the workspace, so a
Codex run is assumed unable to take a slot. Decision: a Codex builder runs **light checks only** (lint, types,
touched unit tests). Its touched E2E specs, builds and captures run afterwards from the supervisor's
side, outside the sandbox, through `heavy.py run`, on the worker branch before it is merged.

## Databases: cloud for working data, local for tests

`python3 scripts/db.py` has two halves. Both read `sdlc.json` `db`; `--print` shows the commands and
runs nothing.

**`test`**: one local Postgres container with a migrated template database, and a private copy per job
in under a second (`CREATE DATABASE ... TEMPLATE`).

```bash
python3 scripts/db.py test prepare          # container up, this migration set's template built once
python3 scripts/db.py test run -- pytest    # a private copy, DATABASE_URL set, dropped afterwards
python3 scripts/db.py test sweep            # drop leaked copies and old templates
```

- **A template per migration hash.** The template is `<template>_<hash>`, built once and never
  overwritten or dropped by a checkout with other migrations. Two worktrees on different migrations
  each have their own, side by side in the one container; `create` copies from the template of the
  current checkout's hash.
- **One lock per machine.** `prepare` and `create` hold an exclusive file lock, keyed by the container
  name, in `${SDLC_DB_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/sdlc/db}` while they start the
  container and build a template. A second process waits, then finds the template published (the
  hash comment is stamped last) and only clones. Parallel builders never race to start or rebuild.
- **A running container is never removed on one failed probe.** `pg_isready` is retried; the
  container is removed only when `docker inspect` says it exists and is not running. A running one
  that is not ready yet is waited for.
- **A job gets one copy; the close is one job and one copy.** Use `test run` once around a whole
  command, not once per test file. The milestone close runs its checks under one copy.
- **Sweep.** `prepare` and `test sweep` drop `sdlc_job_<pid>_*` copies whose process is gone (a copy
  from a standalone `test create` is spared for an hour, because that command exits at once) and
  templates of other migration sets not used for 7 days (last use is kept beside the lock).
- `test run` streams the command's output as it runs and returns its exit code. `db.py` reads
  `sdlc.json` and the migration globs from the repo root, wherever it is started.

`db.test`: `container`, `port`, `template` (a name prefix), `migrate` (a command that reads `DATABASE_URL`),
`migrations` (globs: their hash names and stamps the template, so a stale template never serves tests),
optional `image`, `user`, `engine` (`docker` or `podman`; default: `SDLC_DB_ENGINE`, else Docker when installed, else Podman). The container listens on 127.0.0.1 with trust auth: a throwaway with no
password. Database tests are light and need no slot.

**`dev`**: connects a developer to their own cloud database through the provider's auth proxy with
their own identity, no passwords. Every value is a command or pattern for the repo's provider, so the
kit names no vendor.

```bash
python3 scripts/db.py dev ensure            # proxy up, database created once if missing, migrated
```

`db.dev`: `identity` (prints who you are), `name` (default `dev_{identity}`), `proxyCheck`, `proxy`,
`exists`, `create`, `migrate` (all take `{identity}` and `{db}`), `url` (no password).

**Why tests stay local.** A cloud database would not speed them up: the database was never the slow
part (builds, browsers and the memory limit on parallel jobs were), and a local Postgres starts in
seconds. Screen checks reset their data before every screen, so over the network each reset pays the
round trip and a 270-screen batch gets slower. Tests drop and recreate databases, and a shared cloud
instance usually also serves staging or production, which test jobs do not belong next to. If a repo
needs more capacity than a laptop, the lever is a cloud test machine that runs build and capture next to
its own local database, started only for a batch; that costs money each run, so it is a per-repo
decision.

## Guards

- **A helper's heavy command goes through the queue, in its own worktree.** `heavy.py guard-main` exits 3
  in the main working folder. As the PreToolUse hook `helper-guard.sh` (`heavy.py guard-main --hook`) it
  refuses a subagent's heavy command that does not run as `heavy.py run|submit` (exit 2), and any
  subagent command that is not a read-only tool while its working folder is the main one (exit 3; a
  `cd` in the line means it moves to its worktree first): the payload carries
  `agent_id` for a subagent, and an absent, empty or unreadable field is the owner's own session,
  which is never refused. The command is split into real segments and wrappers (`env`, `timeout`,
  `nice`, `xargs`, `sh -c`, `find -exec`) are read by their inner command. It stops a careless
  agent; it is not a sandbox.
- **Evidence is one file per screen.** `evidence.py record` writes `<dir>/<screen>.json` with the shot's
  hash and a hash of each text-catalogue key the screen shows. Parallel helpers never write the same
  file, and a ledger edit conflicts with nothing.
- **"Changed since capture" is checked per text key.** `evidence.py stale` names each screen whose own
  keys changed, so one new button label recaptures the screens that show it, not every screen.

## Preflight

`python3 scripts/preflight.py` checks, once, what this change will need: the tools (`git`, the first
word of `verify`, `preflight.tools`), sign-in (`preflight.auth`: `{name, check, fix}`), Docker when
`db.test` exists, and two config conflicts: feature PRs with local milestones, and a `blocked[]` rule
with no message. It prints one `FAIL <what>: <fix>` line per failure and ends with `PREFLIGHT OK` or
`PREFLIGHT FAIL <n>`. Run it at plan approval, and `--config` in CI.

**Free disk.** It also checks the free space on the repo's volume: a `FAIL disk` line with the free GB
below `preflight.minFreeGB` (default 15), a `WARN disk` line below twice that (a warning does not fail
the run). Worktrees, installed dependencies, containers and browser caches fill a disk during a long
run, and a full disk fails a build in a way that reads like a code bug.
