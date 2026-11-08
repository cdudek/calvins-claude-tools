# Reproduction (Flaky-Specific)

For universal reproduction principles, see `references/fix-discipline.md` section 1.

This file covers flaky-specific calibration: seed handling, reproduction rates, and timing for bisect decisions.

## Calibration Run

Before attempting a fix, establish the reproduction rate.

### 1. Run the test in isolation

Use the ecosystem-specific command from the loaded ecosystem reference. If a seed was provided, use it.

### 2. If it passes in isolation, run the full file

A test that passes alone but fails in the suite is **order-dependent** — proceed to the bisect step.

### 3. Seed handling and calibration

Flaky tests don't fail every time. Run 3-5 times — let the runner generate random seeds each time. Capture the seed from each run's output using the ecosystem-specific seed regex (see ecosystem reference). Count pass/fail.

When a run fails, record that seed — use it for all subsequent reproduction and verification.

**Reproduction rate:**
- 80%+ failure → highly reproducible, straightforward to fix and verify
- 40-80% failure → moderately reproducible, may need multiple verify runs
- < 40% failure → hard to reproduce, note this for the user
- 0% failure after 5 runs → cannot reproduce, report to user and ask for guidance

### 4. Time the test

Note the wall-clock duration of a single run. This informs bisect strategy:
- < 10s → fast feedback, iterate freely
- 10s-60s → moderate, be deliberate with runs
- > 60s → slow, minimize unnecessary runs, prioritize bisect for order-dependent issues
