# Report Format

Present a concise summary after verification:

```
## Fix Summary

**Issue**: <ticket ID or spec path>
**Test**: <file>:<line>
**Ecosystem**: <RSpec/Minitest/Pytest/Jest/Vitest>
**Root cause**: <1-2 sentence explanation>
**Pattern**: <flaky pattern from references/flaky-patterns.md>
**Fix**: <what was changed and why>

### Reproduction
- Reproduction rate: <X/N runs failed>
- Test duration: <Xs per run>

### Verification
- Without fix: FAIL (seed: <seed>)
- With fix: PASS (seed: <seed>)
- Full file: PASS (<n> examples, 0 failures)

### Files changed
- <file>: <brief description of change>
```

If bisect was used, add:

```
### Bisect
- Method: <rspec --bisect / minitest_bisect / detect-test-pollution>
- Polluting test: <file>:<line> (if order-dependent)
```

Do not commit or push. Wait for the user's instructions.
