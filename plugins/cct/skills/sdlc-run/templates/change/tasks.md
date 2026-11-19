---
type: tasks
change: {{CHANGE}}
author: {{AUTHOR}}
status: draft
created: {{DATE}}
---

# Tasks: {{TITLE}}

> One sentence. What a user can do when the first milestone ships.

Derived from `spec.md` and the design. Only the supervisor changes the `State` column, at
integration, after the builders' commits land: builders never edit this file, so parallel
worktrees do not conflict on adjacent lines. Task rows are part of the lock; the `State` column and
the handover below are not.

## Tasks

`Rules` are the rule ids the task satisfies. `Test` is the test that proves it (a name, not a
sentence). `Needs` is `none` or task ids. `[P]` in `Needs` marks a task that can run in parallel
with its neighbours. `State` is `todo`, `building`, `done <sha>` or `blocked: <reason>`.

| # | Rules | Test | Needs | Milestone | State |
|---|---|---|---|---|---|
| T1 | R<n> | <test name, tagged @R<n>> | none | M1 | todo |

## Milestones

| Milestone | Tasks | needs |
|---|---|---|
| M1 <what a user can do after it> | T1 | none |

## Design notes

Scope M only (L has `design.md`): approach and the rejected option, then the risks, each with a
proof before the build, in the same columns as `design.md`.

### Risks

| Risk | What we do | Proof before build | Lands |
|---|---|---|---|
| <what could break> | <the action> | `<command>` or known | <task id, or "accepted"> |

## Handover

Generated at the gate, never written by hand: the kickoff prompt and the `/goal` line, the commands
to run, and the questions taken with their defaults. It is not part of the lock.
