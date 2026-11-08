---
name: test-suite-run
description: "Executes a supplied test suite of any layer (unit, integration or E2E), or a path inside it, with the project's own runner or Playwright, and returns the results: pass, fail, skip and flaky counts, each failing test with its error, and the failure context from the run output. It runs and reports; it edits no test and no product code. Use when someone says 'run the test suite', 'run this spec file', 'run the playwright tests', 'what failed in the test run', 'run the touched tests'. Skip for: repairing failing E2E specs, owned by cct:test-e2e-coverage-run; one test that passes and fails at random, owned by cct:test-flake-fix."
allowed-tools: "Bash(npx *) Bash(npm run *) Bash(pnpm *) Bash(make *) Bash(pytest *) Bash(uv run *) Bash(bundle exec *) Bash(ls *) Bash(git diff *) Read Glob Grep"
user_invocable: true
metadata:
  version: 1.0.0
  author: calvindudek
---

# Run a test suite and return the results

No agents and no browser driver. The input is a test path, a directory or nothing (the
whole suite); the output is a results summary.

## Steps

1. Pick the command. Use the project's own runner when it has one (a `package.json` script,
   Makefile target, `sdlc.json` `ciCommands`). Otherwise detect the stack and use its default
   (`pytest`, `bundle exec rspec`, `npx vitest run`, `npx jest`) or, for browser specs:

   ```bash
   npx playwright test [path] --reporter=line
   ```

   Which tests to run, against which target, and how to shard or retry are rules in
   `${CLAUDE_SKILL_DIR}/../test-e2e-policy/references/suite-speed-and-reliability.md`
   section K: touched tests only for a feature PR, a production build as the target for E2E
   (never a server that compiles on demand), one retry, and a pass on retry reported as
   flaky, not green.
2. Run it and keep the full output.
3. For each failure, quote the error and the step that failed. For Playwright, read
   `test-results/**/error-context.md`.
4. Return: total, passed, failed, skipped, flaky (passed on retry); then one entry per
   failing test with its path, title and the error. Say whether the run was scoped or the
   whole suite.

## Do not

- Edit a test, raise a timeout or add a retry to turn a run green.
- Diagnose or fix. Hand failing E2E specs on to `cct:test-e2e-coverage-run` (heal) and a
  test that fails at random to `cct:test-flake-fix`.
