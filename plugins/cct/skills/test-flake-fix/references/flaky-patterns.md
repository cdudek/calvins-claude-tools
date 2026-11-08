# Flaky Test Patterns

Common root causes and their fixes, ordered by frequency.

## Time-Dependence

**Symptoms:** Fails at midnight, month boundaries, DST transitions, or timezone-sensitive environments.

**Look for:** `Time.now`, `Date.today`, `DateTime.current`, `new Date()`, timezone assumptions, relative time comparisons.

**Fixes:**
- Freeze time: `travel_to` (Rails), `freeze_time` (pytest-freezegun), `jest.useFakeTimers()`
- Use explicit timestamps in test data instead of `now`
- Pin timezone in test setup

## Order-Dependence

**Symptoms:** Passes alone, fails in suite. Passes with one seed, fails with another.

**Look for:** Shared state across tests — class variables, global config, database records not cleaned up, memoized values, environment variables set and not restored.

**Fixes:**
- Add proper setup/teardown to reset shared state
- Use database transactions or truncation between tests
- Isolate mutable globals with save/restore wrappers

## Race Conditions

**Symptoms:** Intermittent on CI, hard to reproduce locally. Often in integration/system tests.

**Look for:** Async operations without waits, shared fixtures modified concurrently, background jobs, event-driven assertions.

**Fixes:**
- Add explicit waits/retries for async results
- Use synchronization primitives (mutexes, barriers)
- Assert on settled state, not intermediate state

## External Dependencies

**Symptoms:** Fails when network is slow, external service is down, or rate-limited.

**Look for:** HTTP calls to real services, file system assumptions (tmp paths, disk space), DNS resolution.

**Fixes:**
- Stub/mock external calls (WebMock, responses, nock)
- Use VCR/cassettes for HTTP interactions
- Make file paths configurable and use test-specific directories

## Floating Point

**Symptoms:** Fails on different architectures or Ruby/Python versions.

**Look for:** Exact equality on floats, rounding differences, locale-dependent formatting.

**Fixes:**
- Use approximate matchers: `be_within(0.01).of(expected)`, `pytest.approx()`, `toBeCloseTo()`

## Database State

**Symptoms:** Fails on CI but passes locally, or fails after other tests modify the database.

**Look for:** Missing cleanup, sequence-dependent IDs, transaction leaks, hardcoded IDs.

**Fixes:**
- Use database_cleaner or transaction rollback between tests
- Never rely on specific auto-increment IDs
- Reset sequences in setup if needed
