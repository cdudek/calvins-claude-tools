---
type: design
change: {{CHANGE}}
author: {{AUTHOR}}
status: draft
approved_at: null
created: {{DATE}}
---

# Design: {{TITLE}}

<!-- Only for scope L. M keeps these sections, shortened, under "## Design notes" in tasks.md. S has none. Plain words first; one idea per sentence. -->

> One sentence. How this change works.

A person with no context builds from this file and `tasks.md` alone.

## Approach

- **What changes:** <one sentence>
- **What stays the same:** <one sentence>
- **Why this way:** <one sentence>
- **Rejected:** <option> — <why not, one clause>

## Ground truth

What already exists, found by one read-only search before this plan was written, with `file:line`
for each: the code this change touches, every caller of it, and the nearest similar feature to
copy. `n/a` for docs and chores. A plan that cites nothing here has not looked.

| What | Where | Why it matters |
|---|---|---|
| <existing code> | `path:line` | <caller, duplicate, or model to copy> |

## Rules check

Checked twice: before the design (can the approach obey the rules in `sdlc.json` `rules`?) and
after it. `pass`, or the rule id that fails.

- Before design: <pass | rule ids>
- After design: <pass | rule ids>

### Justified violations

A row with an empty cell blocks the gate; `none` when clean. A rule this change makes MUST
(for example "module A never imports module B") names the automated check that keeps it true, or `manual`.

| Violation | Why needed | Simpler alternative rejected because | Check that keeps it true |
|---|---|---|---|
| none | | | |

## Where things go

The folder for every new file, so the build cannot invent a place. A file outside these folders is
`scope-growth`.

| New file or kind | Folder |
|---|---|
| <component, route, test> | `<path>/` |

## Interfaces and contracts

Endpoints, events, schemas and component props this change adds or changes. When a schema,
endpoint, new dependency or cross-module boundary appears in "Where things go", paste the
`cct:arch-plan-write` result for it here: a missing one is a High finding.

## Data and migrations

What is stored, what changes, how existing rows get there. `none` when no data is touched.

## Error handling

What fails, what the person sees, what is retried, what is logged. One line each.

## Test strategy

One row per rule (new or changed): the level, what is real and what is faked, and the data it
needs. The test carries the tag `@R<n>` and the change id in its title.

| Rule | Level | Real or faked | Data |
|---|---|---|---|
| R<n> | unit / integration / E2E | <real db, faked gateway> | <fixture> |

## Risks

Each risk has a proof before the build: a command, a ten-line script, or `known`. A risk marked
unknown (a new service call, a data shape, a performance number, a third-party limit) becomes the
first task of milestone 1, a throwaway check capped at ten minutes, its result written here. A
change that touches auth, user data, money, external input or a new dependency adds one risk
line: what can go wrong here, and who can make it.

| Risk | What we do | Proof before build | Lands |
|---|---|---|---|
| <what could break> | <the action> | `<command>` or known | <task id, or "accepted"> |

## Rollout and rollback

Required when data, an API or config changes; `none` otherwise.

- **Reversible by:** <the undo, one line>
- **Data touched and how to undo it:** <one line>
- **Flag or order of deploy:** <one line>

## Open design questions

- <question> — <default taken>
