# Ecosystem: Minitest

## Test Commands

| Action | Command |
|---|---|
| Run single file | `bundle exec ruby -Itest <file>` |
| Run single test | `bundle exec ruby -Itest <file> --name <test_name>` |
| Run with seed | `bundle exec ruby -Itest <file> --seed <seed>` |
| Run full suite | `bundle exec rake test` or `make test` |

## Seed Handling

- **Seed output regex:** `--seed (\d+)`
- **Seed displayed by default:** Yes, always shown at the top of every run (`Run options: --seed 12345`)
- Randomization is on by default in Minitest
- Capture the seed from the first failing run's output

## Bisect

**Official gem** — `minitest-bisect` (maintained by the minitest team).

### Setup
Check if `minitest-bisect` is in the Gemfile. If not:
- Bundled projects: add `gem 'minitest-bisect'` to the Gemfile's test group and run `bundle install`
- Otherwise: `gem install minitest-bisect`

### When to use
The test passes alone but fails in the suite — indicating order-dependence.

### Command
```
minitest_bisect --seed <seed> test/
```

- You **must** provide `--seed` matching the failing run
- Set `MTB_VERBOSE=2` for debug output
- Identifies the minimal set of tests that triggers the failure

### After bisect
Read the identified polluting tests to find shared state. Fix setup/teardown.

## Common Flaky Patterns

- `setup`/`teardown` not cleaning global state
- Class-level instance variables shared across test methods
- Missing transaction rollback between tests
- `Minitest::Parallel` with shared database state
