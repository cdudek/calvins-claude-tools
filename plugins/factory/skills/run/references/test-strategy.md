# Test strategy (any stack)

The single source for how the factory runs tests. `plan-standard.md` holds the `tests` schema; this file holds the rules.

## Three tiers
- **After an edit:** run only the touched test or the related ones. Never the full suite.
- **Task hand-back:** `task-step.py finish` runs `tests.related` on the changed files, plus every `tests.triggers` entry whose `paths` match a changed file.
- **Milestone close:** `task-step.py gate` runs every `tests.suites` entry once. Nothing else runs the full suite.

## Rules
- **Scripts run the tests, not memory.** `finish` and `gate` are the runners. A task that breaks an old test is not merged.
- **Parallel by default.** Serial flags are banned (`check-plan.py` fails the plan, the guard hook denies the call). Isolation (a database or port per worker) is the project's job. Use `lock: true` only for a truly shared resource: E2E, an app server, a fixed port.
- **Pre-existing failures** are compared by failing test ids against the base, reported as `PRE-EXISTING`, and never BLOCKED. The `PRE-EXISTING` lines are listed as a note in the HOLD or SHIPPED message.
- **Path triggers** cover tests coupled to files they read: schema, migrations, config, directories loaded by glob. A trigger's `edits` names exact test files (a table list, a fixture) that may grow with those paths. The owner approves them once, with the plan.
- **The verifier does not rerun repo checks.** It cites the `FINISH` and `GATE` lines.
- **No related-tests tool on the stack:** `tests.unit` (a command with `{tests}`) runs the test files that sit beside or are named after the changed files, plus the triggers. `discover-tests.py` proposes it for pytest and go, and for vitest or jest when the app is in a subdirectory.

## Defaults per ecosystem
Unverified entries are marked. `discover-tests.py` proposes these from the manifests.

| Stack | `related` | Suite |
|---|---|---|
| vitest | `npx vitest related --run {files}` | `npx vitest run` |
| jest | `npx jest --findRelatedTests {files}` | `npx jest` |
| pytest | none yet (`pytest --testmon` takes no `{files}`, so `related` cannot express it; unverified) | `pytest -n auto` if xdist, else `pytest` |
| go | none (fallback; `go test` takes packages, not files) | `go test ./...` |
| cargo | none (fallback) | `cargo nextest run` if installed, else `cargo test` |
| nx / turbo | `nx affected -t test` / `turbo run test --filter=...[base]` (unverified) | the same without the affected filter |

Lint and typecheck are suites too: they run once at the gate, not per task.
