# Ecosystem: RSpec

## Test Commands

| Action | Command |
|---|---|
| Run single test | `bundle exec rspec <file>:<line>` |
| Run with seed | `bundle exec rspec <file>:<line> --seed <seed>` |
| Run full file | `bundle exec rspec <file>` |
| Run full suite | `bundle exec rspec` or `make test` |

## Seed Handling

- **Seed output regex:** `Randomized with seed (\d+)`
- **Seed displayed by default:** Yes, always shown when running in random order
- Capture the seed from the first failing run's output to use in subsequent reproduction and bisect

## Bisect

**Built-in** since RSpec 3.3. No plugin needed.

### When to use
The test passes in isolation (`rspec <file>:<line>`) but fails in the full suite — indicating order-dependence.

### Command
```
bundle exec rspec --bisect --seed <seed>
```

- You **must** provide `--seed` matching the failing run
- Use `--bisect=verbose` for detailed output
- Ctrl-C during bisect gives the best result found so far
- Output is a copy-pasteable `rspec` command with the minimal reproducing set

### After bisect
The output identifies the minimal set of tests that cause the failure. Read those tests to find shared state pollution, then fix the setup/teardown.

## Common Flaky Patterns

- `let!` leaking across contexts — use `let` or explicit cleanup
- `before(:all)` / `before(:suite)` with mutable state
- Missing `DatabaseCleaner` strategy for specific test types
- `Timecop` or `travel_to` not restored in `after` block
- Shared connection pool in threaded tests (system specs)
