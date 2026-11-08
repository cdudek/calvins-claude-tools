# Suite speed and reliability

Use this before tuning a suite, replacing its data or diagnosing a wave of failures.
Measure the cost, establish a control, then fix the code, harness or fixture responsible.
For fixture failure classification and temporary probes, read
`../../test-flake-fix/references/controlled-diagnosis.md`.

## A. Measure before changing anything

Collect per-test durations from a full run with the list or JSON reporter. Sort them by
duration. Attribute and sum the time spent on app startup, fixed sleeps, tests that exhaust
their timeout and slow assertions. Record launch counts as well as launch duration. Never
guess the bottleneck. Compare the same measurements after each change.

For example, startup can take 5–6 seconds on a production-sized fixture against about one
second on a small one. Across roughly 700 launches, that dominates sleeps totalling less
than three minutes. Yet failing tests that exhaust 90–300 second timeouts can cost more
than either. The largest number in the report decides what to investigate first.

## B. Fail fast first

Triage red tests before tuning passing ones. A timed-out test costs its entire timeout;
20 timeouts can cost more than 500 passing tests. Find why the expected event never arrives.
Use the repair boundaries in section J; a longer wait only makes this sink larger.

## C. Establish a control before diagnosis

When many tests fail the same way, rerun one on a clean checkout of the base branch before
blaming the change. Check environment parity: build output, bundled runtime binaries,
dependencies and required untracked files. A fresh worktree does not inherit all of these.
Record the branch, setup and result of the control run.

For example, 22 send tests can time out because a bundled media runtime binary was not
linked into a new worktree, while all 23 pass on the clean base in four minutes. That is a
harness setup failure. Repair parity before diagnosing product code.

## D. Build a small, deterministic fixture once

Build a synthetic fixture once per run in Playwright `globalSetup`. Derive every row from
what the specs need. Never clone a production-sized dataset or a real user's personal data
for the default fixture. This cuts repeated startup work and makes failures reproducible.

Keep the real-data path behind an opt-in environment variable for comparison runs. Keep
that data out of committed fixtures. Unit-test the synthetic fixture's invariants: every
id the specs address exists, at least one full record exists, and referenced files exist.
Use a short fixture folder path; long temporary paths can themselves cause layout failures.
Keep the generated seed immutable and isolate each worker's mutations as `strategy.md`
section 6 requires. Failure classification belongs in
`../../test-flake-fix/references/controlled-diagnosis.md` section E.

## F. Treat machine load as a test input

Run one e2e suite at a time on a shared machine, behind a machine-wide lock that covers
every worktree and runner. Before starting, require both the 1- and 5-minute load averages
to be below a documented threshold calibrated for that machine. Record load and worker
count with the result. Other work can double durations and turn passes into timeouts;
adding workers on an already loaded machine makes this worse.

Run gates in a quiet window or on a dedicated machine. There, measure higher worker counts:
for example, six workers instead of three on 14 cores can halve wall time. Do not treat
that example as a universal setting. Keep isolated ports, databases and logs even when
the lock serializes suites; isolation and resource capacity solve different problems.

## G. Repeat the risky specs, not the whole suite

For a gate, run the full suite once. Then run only the union of spec files changed in the
diff against the gate's base and a committed flaky list with `--repeat-each=3`. Deduplicate
the paths. An empty union needs no repeat run. Repeating the entire suite triples a long
run without concentrating evidence where risk changed.

Use `e2e/flaky-specs.txt` for the list: one repo-relative spec path per line, followed by
`# reason`. Ignore blank lines and comment-only lines; strip comments before passing paths
to the runner. Each entry explains why it still needs repeats. For example:

```text
e2e/navigation.spec.ts # navigation race under investigation
```

Keep failures visible. Repeats collect reliability evidence; they never turn a failed first
run into a passing gate. Targeted calibration during diagnosis is separate from this gate
policy (`waiting.md` section 11).

## H. Parallel workers with isolated data

One worker is only forced when every test shares one set of data. Give each worker its own
tenant instead. A worker-scoped fixture creates one tenant (or org) per worker, keyed on
`workerInfo.parallelIndex`, which is stable for the worker's life and unique among live
workers. Each test then seeds and reads only inside that tenant.

```ts
export const test = base.extend<{ tenant: Tenant }, { workerTenant: Tenant }>({
  workerTenant: [
    async ({}, use, workerInfo) => {
      const name = `e2e-w${workerInfo.parallelIndex}`
      await api.deleteTenantByName(name) // a crashed run's leftover, if any
      const tenant = await api.createTenant(name)
      await use(tenant)
      await api.deleteTenant(tenant.id)
    },
    { scope: 'worker' },
  ],
  tenant: async ({ workerTenant }, use) => use(workerTenant),
})
```

Name tenants by `parallelIndex`, never by random id, so a crashed run's leftovers are found
and replaced. Seed per test inside `tenant` and clean up what the test made. Once nothing
reads outside its tenant, raise `workers` above 1 and set `fullyParallel: true`. Shared
singletons (one mailbox, one global setting) still need a lock or a serial project.
Tenant names are unique per database, not per machine, so each worktree keeps its own
database (section F). Pick the worker count on a quiet machine, as section F says.

## I. Known traps

1. **Entrance motion breaks “holds still” assertions.** A bounding box sampled mid-transform
   is moving. Fix the motion, for example by fading in place, rather than weakening the
   geometry assertion.
2. **Synthetic keys exercise the renderer path.** Playwright's keyboard sends events over
   the DevTools protocol. In Electron they do not reach native menu accelerators. A shortcut
   bound in both the menu and renderer is tested only through the renderer binding. Record
   that coverage limit; use a native input harness to prove the accelerator path.
3. **Deferred routing leaves commands on the old screen.** A command issued before a deferred
   transition commits can act on the previous route. Commit navigation at once where commands
   depend on the current route. Repair the product race.
4. **Two invocations can overwrite one JSON report.** A script may run parallel tests and
   focus-bound tests separately. Give each Playwright invocation its own reporter output
   name, or the second run destroys the first run's timing and failure evidence.
5. **Tracked evidence files dirty the tree.** Tests that rewrite tracked screenshots can
   break gates requiring a clean tree. Write routine evidence to an ignored folder. Updating
   tracked evidence must be an explicit capture mode.
6. **Background sweeps need observable completion.** Wait on an app-observable signal that
   the sweep is finished before snapshotting device reads. A sleep samples a different
   partial result on each dataset, so its diff cannot be stable.
7. **Request counts must match the designed protocol.** If the app sends counts and then
   options, assert both requests. Counting only the first phase mislabels correct behaviour
   as a duplicate request bug.

## J. Repair boundaries

Never raise a timeout, add a sleep or wait just to pass, loosen an assertion, skip a test,
or add application key handling solely to satisfy a test. These changes hide the cause
and weaken the gate. An assertion on an observable completion signal is synchronization,
not a delay added to get green (`waiting.md`).

Fix the code, the harness or the fixture, and say which one changed and why. If the current
workflow cannot edit product code, file the defect and leave the test red for the authorized
product fix. A correct failing test is evidence to preserve.

## K. Commands per stack

The rules are language-neutral; this table is where the commands live. `sdlc-run`
(`../../sdlc-run/references/ci-blueprint.md`) says when each applies. Fill `sdlc.json`
`checks.feature`, `checks.milestone` and `ciCommands` (what each job of `sdlc-run/templates/ci/github-actions.yml` runs; defaults per stack in `sdlc-run/templates/ci-commands.json`) from the row for the repo's stack.
Which changed paths switch each CI job on is the blueprint's step-to-globs table; the commands below fill those jobs.

- **Touched tests**: what an agent or a feature PR runs; which changed files count as test or code comes from `sdlc.json` `ciPaths`, the same lists the CI `changes` job reads. Never the whole suite; the full suite
  runs once per milestone and on the PRs the blueprint's A5 names.
- **Production target**: what system and E2E tests start. Never a server that compiles or
  reloads on demand: it times differently and hides build-only failures.
- **Shard**: one job per slice, each with its own database service (section H). A suite on
  one shared database cannot be sharded.
- **Retry**: one retry on CI. A pass on retry is reported, not hidden; it fails the run only
  on a full run (`FULL=true`, the blueprint's A5). Each reported flake goes on the committed list (section G).

| Stack | Touched tests | Production target | Shard | Retry |
|---|---|---|---|---|
| TypeScript, JavaScript (Node, Next.js) | `npx vitest related --run <files>`; `npx playwright test <spec files>` | `next build && next start` (or the standalone server); other Node apps: the built `dist/` | `playwright test --shard=i/N` | `retries: 1`; `failOnFlakyTests` on a full run |
| Python (uv, pytest) | `uv run pytest <test files>` | the built wheel installed in a clean env, or the container image | `pytest -n auto` in a job (xdist); `pytest --splits N --group i` across jobs (pytest-split) | `pytest --reruns 1` (pytest-rerunfailures); the JUnit XML names the reruns |
| Rust (cargo, nextest) | `cargo nextest run -p <crate> <filter>` | the built binary: `cargo build --release`, then tests against it (`cargo nextest run --release`) | `cargo nextest run --partition count:i/N` | `--retries 1`; nextest prints `FLAKY` in its summary |
| Ruby, Rails (rspec, parallel_tests, Capybara) | `bundle exec rspec <spec files>` | `RAILS_ENV=test`, `eager_load` on in CI, assets precompiled first (`bin/rails assets:precompile`) | `parallel_rspec -n N` in a job; `parallel_tests --only-group i --group-by runtime` or knapsack across jobs | rspec-retry: `config.default_retry_count = 2` (two attempts) and `verbose_retry` |
| Kotlin (Gradle, JUnit) | `./gradlew :module:test --tests 'pkg.FooTest'` | `./gradlew installDist` or `bootJar`, then run the jar or the container image | `maxParallelForks` in a job; across jobs a matrix of modules or `--tests` lists (Gradle has no job sharding of its own) | the `org.gradle.test-retry` plugin: `maxRetries = 1`, `failOnPassedAfterRetry = false` |
| Scala (sbt, ScalaTest) | `sbt "testOnly pkg.FooSpec"` | `sbt stage` (or `assembly`), then the staged binary or the container image | `Test / testGrouping` with forked JVMs in a job; across jobs `testOnly` lists | ScalaTest `Retries` (`withRetry`) on a listed suite; or rerun failures with `sbt testQuick` |

A PR's changed specs are the files from `git diff --name-only <base>...HEAD` that match the
stack's test globs, plus the tests of any crate, module or package the diff touches. An empty
set runs lint, types and unit tests only.
