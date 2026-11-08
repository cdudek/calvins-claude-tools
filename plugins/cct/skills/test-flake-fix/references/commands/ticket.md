---
description: Fix a flaky test from a Linear ticket or GitHub issue
---

The user input is: $ARGUMENTS

Parse the input as: `<ticket_id> [seed]`

- `ticket_id` — a Linear ticket ID (e.g. `ENG-1234`) or GitHub issue URL/number
- `seed` — optional randomization seed for reproduction

## Step 1: Fetch Ticket Context

### Linear ticket
Use the Linear MCP tools to get the ticket title, description, and comments.

### GitHub issue
`gh issue view <number> --json title,body,comments`

Extract from the ticket:
- The failing test file and line number
- The error message or assertion failure
- The seed (if mentioned and not provided as argument)
- Reproduction hints (e.g. "only fails on CI", "order-dependent")

Present a brief summary of the issue before proceeding.

## Step 2: Enter Worktree

Use the EnterWorktree tool: `fix-flaky-<short_identifier>`

Where `<short_identifier>` is derived from the ticket ID (e.g. `fix-flaky-eng-1234`).

After entering, verify you're on a clean branch:
```
git status
git log --oneline -3
```

## Steps 3–8: Fix

Follow `references/fix-workflow.md` with the test file/line and seed extracted above.
