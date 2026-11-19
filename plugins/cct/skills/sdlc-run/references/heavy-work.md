# Heavy work: one queue, local test databases, a few guards

In one large change, helpers waited for hours on builds and browsers, and one usage limit stopped 13
of them at once and killed their queued jobs. Capacity was never the number of helpers; it was the
number of builds, app servers and browsers a machine can run. This file is the kit's answer. Scripts:
`scripts/heavy.py`, `scripts/db.py`, `scripts/evidence.py`, `scripts/preflight.py` (installed by
`adopt`, stdlib only, so they run in CI and inside `/goal` where no plugin is installed).

## Heavy and light

| Heavy: takes a slot | Light: never waits |
|---|---|
| builds, app servers (`dev`, `start`), browser tests, screenshot captures, the full test suite, `verify_gate.py milestone` | format, lint, typecheck, architecture checks, unit tests of touched files, database tests against the local container, git |

`heavy.py classify -- <cmd>` answers heavy or light. `heavy.py run --auto -- <cmd>` takes a slot only
for a heavy command. The built-in patterns cover builds, servers, browsers and captures; list the repo's
full-suite commands (the `checks.milestone` commands) in `sdlc.json` `heavy.patterns`.

## The queue

```bash
python3 scripts/heavy.py run -- pnpm build               # wait for a slot, run, release
python3 scripts/heavy.py submit -- pnpm exec playwright test   # detached: prints a job id, returns
python3 scripts/heavy.py wait <job>                      # exit code of the job; 75 on the deadline
python3 scripts/heavy.py status                          # who holds a slot, who waits
```

- **One heavy job at a time per machine** by default. `sdlc.json` `heavy.slots` (or env
  `SDLC_HEAVY_SLOTS`) raises it for a machine that has the cores and the memory.
- **First come, first served.** Tickets are files in `<git common dir>/sdlc-heavy/`, so every worktree of
  a repo shares one queue. A ticket whose process is dead is dropped, whether it held a slot or waited:
  a killed helper never blocks the line.
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

The Codex sandbox keeps every `.git` read-only, and the queue's tickets live in the git common dir, so
a Codex run cannot take a slot. Decision: a Codex builder runs **light checks only** (lint, types,
touched unit tests). Its touched E2E specs, builds and captures run afterwards from the supervisor's
side, outside the sandbox, through `heavy.py run`, on the worker branch before it is merged.

## Databases: cloud for working data, local for tests

`python3 scripts/db.py` has two halves. Both read `sdlc.json` `db`; `--print` shows the commands and
runs nothing.

**`test`**: one local Postgres container with a migrated template database, and a private copy per job
in under a second (`CREATE DATABASE ... TEMPLATE`).

```bash
python3 scripts/db.py test prepare          # container up, template built (rebuilt when a migration changes)
python3 scripts/db.py test run -- pytest    # a private copy, DATABASE_URL set, dropped afterwards
```

`db.test`: `container`, `port`, `template`, `migrate` (a command that reads `DATABASE_URL`),
`migrations` (globs: their hash is stored on the template, so a stale template never serves tests),
optional `image`, `user`. The container listens on 127.0.0.1 with trust auth: a throwaway with no
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

- **A helper's heavy command goes through the queue.** `heavy.py guard-main` exits 3 in the main
  working folder. As the PreToolUse hook `helper-guard.sh` (`heavy.py guard-main --hook`) it refuses
  only a subagent's heavy command that does not run as `heavy.py run|submit`: the payload carries
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
