---
name: test-flake-fix
description: "Fixes one flaky test, a test that passes and fails at random: reproduces it and calibrates the failure rate, bisects order-dependent cases, applies the minimal fix and proves it with stash-based confirmation. Works from a spec path or a Linear ticket and a seed, for RSpec, Minitest, Pytest, Jest, Vitest and Playwright. Use when someone says 'fix flaky test', 'flaky spec', 'this test is flaky', 'intermittent test failure', 'fix the flaky test in this ticket'. Skip for: an E2E suite that is red because the product changed, owned by cct:test-e2e-coverage-run (heal); running a suite, owned by cct:test-suite-run."
allowed-tools: "Bash(git *), Bash(make *), Bash(bundle *), Bash(npm *), Bash(npx *), Bash(uv *), Bash(pytest *), Bash(rspec *), Bash(minitest_bisect *), Bash(pip install *), Bash(gem install *), Bash(gh *), Read, Edit, Write, Grep, Glob, Agent, WebSearch, WebFetch, EnterWorktree, ExitWorktree, mcp__claude_ai_Linear__get_issue, mcp__linear__get_issue, mcp__claude_ai_Linear__list_comments, mcp__linear__list_comments, mcp__claude_ai_Linear__get_attachment, mcp__linear__get_attachment"
user_invocable: true
metadata:
  version: 2.0.0
  author: calvindudek
effort: high
---

# Fix a flaky test

Reproduces, diagnoses, and fixes flaky or failing tests with a verified confirmation workflow.


## Routing

The user input is: $ARGUMENTS

Read the first word as the subcommand and route to its file, passing the rest on as arguments.

| Subcommand | Does |
|---|---|
| `local` | The user input is: $ARGUMENTS → `references/commands/local.md` |
| `ticket` | The user input is: $ARGUMENTS → `references/commands/ticket.md` |

No subcommand, or one that is not in the table: say
`Usage: /cct:test-flake-fix <local | ticket>`
and ask which one they meant. Never guess — the subcommands do different things.

## Workflow Overview

1. **Understand** — gather context (from ticket or spec file)
2. **Worktree** — enter isolated worktree
3. **Detect ecosystem** — identify test runner and load ecosystem reference
4. **Reproduce** — confirm the failure, calibrate reproduction rate
5. **Bisect** — if order-dependent, use test runner bisect (ecosystem-dependent)
6. **Diagnose & fix** — identify root cause, apply minimal fix
7. **Verify** — stash-based confirmation (`references/fix-discipline.md` section 4)
8. **Report** — structured summary (`references/report-format.md`)

## Commands

| Command | Description | Arguments |
|---------|-------------|-----------|
| `/cct:test-flake-fix ticket` | Fix a flaky test from a Linear ticket or GitHub issue | `<ticket_id> [seed]` |
| `/cct:test-flake-fix local` | Fix a flaky test from a spec file path | `<spec_path> [seed]` |

## Ecosystem Detection

Inspect the project root for framework markers:

| Marker file | Ecosystem | Reference |
|---|---|---|
| `Gemfile` + `spec/` | RSpec | `references/ecosystem-rspec.md` |
| `Gemfile` + `test/` (no `spec/`) | Minitest | `references/ecosystem-minitest.md` |
| `pyproject.toml` or `requirements.txt` | Pytest | `references/ecosystem-pytest.md` |
| `package.json` + `jest.config.*` | Jest | `references/ecosystem-jest.md` |
| `package.json` + `vitest.config.*` | Vitest | `references/ecosystem-jest.md` |
| `package.json` + `playwright.config.*` | Playwright | `references/ecosystem-playwright.md` |

**Playwright and a unit runner usually both exist.** Route by the failing spec's path, not
by the marker: a spec under the Playwright `testDir` is Playwright, everything else is the
unit runner. Browser flakes and unit flakes have different causes and different fixes.

**Disambiguation:** If both `spec/` and `test/` exist, check `Gemfile` for `rspec-rails` or `rspec` gem. If present → RSpec. Otherwise → Minitest.

Load the matching ecosystem reference before running any test commands.

For e2e reproduction and diagnosis, also read `references/controlled-diagnosis.md`: it
links the control-run and machine-load rules, classifies failures across two fixtures,
and explains temporary probe specs. Use it before attributing failures to product code.

## Principles

1. **Minimal fix** — change only what's necessary. Don't refactor surrounding code, add unrelated improvements, or "clean up" the test file.
2. **Prove causation** — the stash-based verify step is mandatory. A fix that can't be verified this way needs more investigation.
3. **One test at a time** — if a ticket references multiple flaky tests, fix them one at a time. Each gets its own verify cycle.
4. **Respect seeds** — when a seed is provided, always use it for the initial reproduction. Random seeds may mask the flaky behavior.
5. **Shared patterns** — follow the problem-solving workflow in `references/fix-discipline.md`
6. **Quarantine is not a fix** — when a flaky e2e test blocks unrelated work and the fix is not quick, a person may quarantine it with an owner, a ticket and an expiry of at most 14 days (`../test-e2e-policy/references/strategy.md` section 7). This skill never quarantines or skips; it fixes, or it reports.

## Policies

### Worktree
Do NOT exit the worktree — the user exits manually after interactive follow-up.

### Commits
Do NOT commit or push automatically. Present the fix and verification results — the user decides when to commit.

### Error Handling
If reproduction fails (test passes when it should fail), report this clearly and ask the user for guidance. Do not guess at the fix.
