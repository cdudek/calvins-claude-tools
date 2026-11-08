---
description: Fix a flaky test from a spec file path
---

The user input is: $ARGUMENTS

Parse the input as: `<spec_path> [seed]`

- `spec_path` — a test file path, optionally with line number (e.g. `spec/models/user_spec.rb:42`, `tests/test_api.py::test_create`)
- `seed` — optional randomization seed for reproduction

## Step 1: Understand the Test

Read the test file to understand what it tests and what it exercises.

If no seed was provided, note that you'll capture it from the first test run's output.

Present a brief summary before proceeding.

## Step 2: Enter Worktree

Use the EnterWorktree tool: `fix-flaky-<short_name>`

Where `<short_name>` is derived from the test file path — include a parent directory to avoid collisions (e.g. `fix-flaky-models-user-spec` for `spec/models/user_spec.rb`).

After entering, verify you're on a clean branch:
```
git status
git log --oneline -3
```

## Steps 3–8: Fix

Follow `references/fix-workflow.md` with the spec path and seed provided above.
