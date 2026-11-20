# Heavy work: one queue, local test databases, a few guards

In one large change, helpers waited for hours on builds and browsers, and one usage limit stopped 13
of them at once and killed their queued jobs. Capacity was never the number of helpers; it was the
number of builds, app servers and browsers a machine can run. This file is the kit's answer. Scripts:
`scripts/heavy.py`, `scripts/db.py`, `scripts/evidence.py`, `scripts/preflight.py` (installed by
`adopt`, stdlib only, so they run in CI and inside `/goal` where no plugin is installed).

## What is wired in (3.22.0)

- **The gate is one job.** What a job is: one command through the queue. The milestone close is one job, not one per check. `verify_gate.py milestone` runs the light checks first (format, lint, typecheck; neighbours that are not `serial` and not `after` one another run side by side, `heavy.lightParallel`, default 4), then takes **one slot** before its first heavy check and holds it to the end, exporting `SDLC_HEAVY_HOLDER` so a nested `heavy.py run` passes straight through. A heavy check that is already cached never takes a slot. A gate started inside a slot (`heavy.py run -- verify_gate.py milestone`) takes no second one. A check's own timeout (`checkTimeout`, per-check `timeout`) still kills its process group, and the slot ticket lists the group of every check that is running (a gate inside a wrapper's slot lists them on the wrapper's ticket), so a cancelled or dead gate's checks are killed before the slot is freed. A SIGTERM, SIGHUP or SIGINT to the gate stops its running checks, drops its database copy and frees the slot. Run the close as `python3 scripts/verify_gate.py milestone <id>`: it takes its own slot, and the helper hook lets it through (wrapping it in `heavy.py run` is not needed). With `preflight` in `sdlc.json`, the preflight is a wall: it runs before everything else. The gate ends with `timing: queue wait Ns, total Ns; <check> Ns, ...` and the report carries `metrics.queue_wait_s`.
- **Waiting.** While the holder is within its own run deadline the gate waits with no deadline. `heavy.waitTimeout` is the cap for a dead queue: it counts only once every holder is past its own `runTimeout` (plus a 60 s grace), then `VERIFY BLOCKED reason=env` names the holder.
- **One database for the close.** With `db.test`, the gate calls `db.py test create` once after taking the slot, exports `DATABASE_URL` to every check, drops and recreates the copy from the template before each heavy check that follows another (set `"resetDb": false` on a check to keep the data, `"resetDb": true` on a light one to reset before it; a `resetDb: true` check is a serial boundary and takes the slot and the copy), and drops it at the end whatever the verdict. Light checks that run before the copy exists get no `DATABASE_URL` (the caller's is removed): database tests belong after the copy. The preparation is bounded by `db.test.prepareTimeout` (default 600 s, also the deadline waiters see for the holder); past it the close ends `VERIFY BLOCKED reason=env`. A failed `--last-failed` rerun of an E2E check runs through the same path as the first run, with the same private `DATABASE_URL`, ports and timeout. A lock approved before 3.18.0 (no `"order": "cost"`) runs every check one at a time in its declared order. A build check (any check named `build`) runs once per tree: a passing check is cached by tree, command and lock.
- **The hooks.** `helper-guard.sh` is registered by `adopt`. A feature-PR repo with local milestones is refused with the two ways out, and a `blocked[]` rule with no message still refuses and names who owns `sdlc.json`.
- **Status.** `sdlc_status.py status` shows who holds or waits for a slot, and a failed stop left in `sdlc-stop-status.json`. It runs the plugin's own `heavy.py`, never a repo copy.

## Heavy and light

| Heavy: takes a slot | Light: never waits |
|---|---|
| builds, app servers (`dev`, `start`), browser tests, screenshot captures, smoke runs, the full test suite (`npm test`), `verify_gate.py milestone` | format, lint, typecheck, architecture checks, unit tests of touched files, database tests against the local container, git |

`heavy.py classify -- <cmd>` answers heavy or light. `heavy.py run --auto -- <cmd>` takes a slot only
for a heavy command. The classifier reads the **program and the script**, never a word anywhere in the
line: `npm|pnpm|yarn|bun test`, `... run build`, `... run smoke:background`, `npx next start`,
`playwright`, `make e2e`, `python3 scripts/capture.py`, `cargo build|test`, `go build|test`, `uv build`, `yarn workspace app run build`, `mvn|gradle` builds and tests and `verify_gate.py milestone` are heavy;
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
  compatibility): a job queued by an older kit is simply not in the line. Ticket order is made under the publication lock, and a group id is signalled only while the leader's start time still matches the one recorded, so a recycled id is never hit. Ports are reserved per slot, not per machine: repos that share a machine should share `heavy.portBase`.
- **The job dies with its wrapper.** A ticket whose wrapper process is dead is dropped, whether it held a
  slot or waited, and its recorded process group is killed first, so a killed helper never blocks the line
  and never leaves a build running behind a free slot. SIGHUP and SIGINT stop a job like SIGTERM.
  Results are written by atomic rename. `heavy.py submit` run inside a slot still queues.
- **Job logs are pruned.** `heavy.py prune` removes job folders older than 7 days and orphans (no result,
  wrapper gone; a job whose wrapper is still running is never removed); the gate calls it at its start.
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
- **A container is never removed.** `pg_isready` is retried; a running one that is not ready yet is
  waited for; a stopped one with the configured image and port is started again; a stopped one that
  differs, or will not start, ends with a message naming it (rename `db.test.container` or remove it
  yourself). Only a name no container has gets a `run`.
- **A job gets one copy; the close is one job and one copy.** Use `test run` once around a whole
  command, not once per test file. The milestone close runs its checks under one copy.
- **Copies have an owner.** `test create --owner-pid PID` (the gate passes its own pid; `test run` uses
  its own) names the copy `sdlc_own_<pid>_<time>_<n>`. `prepare` and `test sweep` drop it only once that
  pid is dead and an hour has passed, and drop templates of other migration sets not used for 7 days
  (last use is kept beside the lock). A copy with no owner (a 3.21 name, or `create` without
  `--owner-pid`) is never swept automatically; `test sweep --all-unowned` drops those on request. A
  template prefix too long for `<prefix>_<hash>` in 63 characters is cut and a short hash of the whole
  prefix is added.
- `test run` streams the command's output as it runs and returns its exit code. `db.py` reads
  `sdlc.json` and the migration globs from the repo root, wherever it is started.

`db.test`: `container`, `port`, `template` (a name prefix), `migrate` (a command that reads `DATABASE_URL`),
`migrations` (globs: their hash names and stamps the template, so a stale template never serves tests),
optional `image`, `user`, `prepareTimeout` (seconds the gate gives the preparation, default 600), `engine` (`docker` or `podman`; default: `SDLC_DB_ENGINE`, else Docker when installed, else Podman). The container listens on 127.0.0.1 with trust auth: a throwaway with no
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
  refuses with exit 2 (the code that blocks) a subagent's heavy command that does not run as
  `heavy.py run|submit` (`verify_gate.py milestone|project` is let through: it queues itself), and any
  subagent command that changes the main working folder: file writes and redirects, mutating git
  (`commit`, `add`, `merge`, `checkout`, `switch`, `reset`, `stash`, `push`, `rebase`, `worktree add`,
  `branch -D`), package installs, builds and tests. Reading, including read-only git, is fine. A `cd`
  moves the check to its resolved destination; only a command that ends up in the main folder is
  refused. A `cd` it cannot resolve (`$VAR`, a backtick, `-`) fails closed: what follows may be in the
  main folder, so a write there is refused until a literal `cd` follows. Inline interpreter code
  (`python3 -c`, `node -e`) is unknown, so it counts as heavy and goes through the queue. The payload carries
  `agent_id` for a subagent, and an absent, empty or unreadable field is the owner's own session,
  which is never refused. The command is split into real segments and wrappers (`env`, `timeout`,
  `nice`, `xargs`, `sh -c`, `find -exec`) are read by their inner command. It stops a careless
  agent; it is not a sandbox.
- **Screen evidence** (one file per screen, "changed since capture" per text key): [visual work](visual-work.md).

## Preflight

`python3 scripts/preflight.py` checks, once, what this change will need: the tools (`git`, the first
word of `verify`, `preflight.tools`), sign-in (`preflight.auth`: `{name, check, fix}`), the container engine
(the one `db.py` picks: `db.test.engine`, `SDLC_DB_ENGINE`, Docker, else Podman) when `db.test` exists, and one config conflict: a `blocked[]` rule
with no message. It prints one `FAIL <what>: <fix>` line per failure and ends with `PREFLIGHT OK` or
`PREFLIGHT FAIL <n>`. Run it at plan approval, and `--config` in CI.

**Free disk.** It also checks the free space on the repo's volume: a `FAIL disk` line with the free GB
below `preflight.minFreeGB` (default 15), a `WARN disk` line below twice that (a warning does not fail
the run). Worktrees, installed dependencies, containers and browser caches fill a disk during a long
run, and a full disk fails a build in a way that reads like a code bug.
