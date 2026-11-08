# Ecosystem: Jest / Vitest

## Test Commands — Jest

| Action | Command |
|---|---|
| Run single test | `npx jest <file> -t "<test_name>"` |
| Run with seed | `npx jest <file> --seed=<seed> --showSeed` |
| Run with randomization | `npx jest <file> --randomize --showSeed` |
| Run serially | `npx jest <file> --runInBand` |
| Run full file | `npx jest <file>` |
| Run full suite | `npx jest` or `make test` |

## Test Commands — Vitest

| Action | Command |
|---|---|
| Run single test | `npx vitest run <file> -t "<test_name>"` |
| Run with seed | `npx vitest run <file> --sequence.seed <seed> --sequence.shuffle.files --sequence.shuffle.tests` |
| Run with randomization | `npx vitest run <file> --sequence.shuffle.files --sequence.shuffle.tests` |
| Run full file | `npx vitest run <file>` |
| Run full suite | `npx vitest run` or `make test` |

## Seed Handling

### Jest (28+)
- **Seed flag:** `--seed=<N>`
- **Display seed:** add `--showSeed` (or use `--randomize` which implies it)
- **Seed output regex:** `Seed:\s+(-?\d+)`
- Seed is NOT displayed by default — always pass `--showSeed`

### Vitest
- **Seed flag:** `--sequence.seed <N>`
- **Requires shuffle enabled:** `--sequence.shuffle.files` and/or `--sequence.shuffle.tests`
- **Seed output regex:** `Running tests with seed "(\d+)"`
- Seed defaults to `Date.now()` if not specified
- The `--sequence.seed` flag has **no effect** unless shuffle is enabled

## Bisect

**No bisect support** — neither Jest nor Vitest has built-in or plugin-based test-set bisection.

### Workaround for order-dependent failures

1. Run with `--runInBand` (Jest) or `--pool=forks` (Vitest 1.0+; older versions use `--no-threads`) to force serial execution — confirms order-dependence
2. Manually narrow down by splitting the test suite:
   - Run the first half of the suite + the failing test
   - Binary search by halving until you find the polluting test
3. Use `--verbose` to see test execution order

## Common Flaky Patterns

- `jest.mock()` not restored — missing `jest.restoreAllMocks()` in `afterEach`
- Shared module-level state between test files (Jest's module cache)
- Timer mocks (`jest.useFakeTimers()`) not cleaned up
- Async operations not awaited — missing `await` on assertions
- `setTimeout`/`setInterval` leaking across tests
- DOM state not reset between tests (JSDOM environment)
