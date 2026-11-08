---
linear: {{LINEAR}}
type: plan
change: {{CHANGE}}
design: {{DESIGN}}
author: {{AUTHOR}}
status: draft
reviewed_by: null
approved_at: null
created: {{DATE}}
---

# Plan: {{TITLE}}

> One sentence. What this change does.

A person with no context builds from this file alone. [intent](intent.md) and
[facts](facts.md) are for the gate, not for the build.

## Approach

- **What changes:** <one sentence>
- **What stays the same:** <one sentence>
- **Why this way:** <one sentence>
- **Rejected:** <option> — <why not, one clause>

## Rules check

The rules in `intent.md` → "Rules that apply", checked twice: before the design (can the approach
obey them?) and after it (does the design?). `pass` or the rule ID that fails.

- Before design: <pass | rule IDs>
- After design: <pass | rule IDs>

### Justified violations

One row per rule the plan breaks. A row with an empty cell blocks the gate; `none` when clean.

| Violation | Why needed | Simpler alternative rejected because |
|---|---|---|
| none | | |

## Design changes

<Which sections of `design:` this change edits, or "none". Edit them in the same PR.>

## Where things go

The folder for every new file, so the build cannot invent a place. A file outside these folders
is `scope-growth`.

| New file or kind | Folder |
|---|---|
| <component, route, test> | `<path>/` |

## Feature PRs

In order, grouped under `### Milestone <n> — <what a user can do after it>`. One go (the
default): each row is a commit on `milestone/<slug>-<n>` with touched tests and required pre-commit checks between rows; each
milestone gets the checks and validation once, and one PR that releases it. For E2E, run
the full suite once, ×3 only for changed and flaky specs. Use the committed
`e2e/flaky-specs.txt` list per `cct:test-e2e-policy`, `suite-speed-and-reliability.md`
section G (selection and line format). `delivery: "feature-prs"`: each row is one PR into
`milestone/<slug>` (a hotfix: into the default branch), the next starts when it auto-merges.

| # | Feature | Facts | Branch | State |
|---|---|---|---|---|
| 1 | <what it delivers> | F1, F2 | `<slug>/1-<feature>` | todo |

## Files that change

| File | Change |
|------|--------|
| `path` | <one line> |

## Order of work

Each step has a proof. The proof is a command, a file, or a fact.

- [ ] 1. <step> — proof: `<command>` exits 0
- [ ] 2. <step> — proof: `<file>` exists
- [ ] 3. <step> — proof: F<n> passes

## Milestones

One row per milestone, in order; a change small enough for one has one. Each milestone is cut
from the default branch and merges on its own, unless `needs` names one whose code it calls.
Different files do not prove independence: an API and its caller conflict without a merge
conflict.

| Milestone | Features | needs |
|-----------|----------|-------|
| M1 <name> | F1, F2 | none |
| M2 <name> | F3 | M1 (<what of M1 it calls>) |

## Risks

| Risk | What we do | Where it lands |
|------|------------|----------------|
| <what could break> | <the action> | <step number, test name, or "accepted"> |

## Out of scope

- <what this change does not do, on purpose>

## Done

What must hold, as data in [done.json](done.json) (facts, test tags, pages, states). The goal
below ends on the verify sentinel, so every line here is proven by a check, not by a claim.

- `python3 scripts/verify_gate.py feature {{CHANGE}}` ends `VERIFY PASS` for every feature.
- `python3 scripts/verify_gate.py milestone {{CHANGE}}` ends `VERIFY PASS` once, on the milestone.
- <file> exists / contains `<string>`.
- F1 to F<n> pass by their named check.
- Nothing outside `## Files that change` is edited.
- Stop and report as soon as a step cannot proceed. Never work around a blocker.
- Stop after 40 turns if not met. Report what is missing.

## Goal handover

One go: the single `/goal` from `templates/goal/run.txt`, with `<ID>`, `<slug>`, `<default>` and
`<TURNS>` filled. Feature PRs: one `/goal` per feature from `templates/goal/feature.txt`. Verbatim, so the handover is committed rather than living in one chat message. Fill it
when the gate returns approved; the build only runs inside it.

The guardrail test fails an approved plan whose section is empty. Write `none —
<why>` rather than leaving it blank: an empty section is a skip, a section that
names itself empty is a decision. The usual reason is a document-shaped change,
where the artifact is this PR's diff and there was never a build to hand over.

```
/goal Deliver change {{CHANGE}} in one go per changes/{{CHANGE}}/plan.md ...
```

## Revisions

Only after approval. One line per change: `YYYY-MM-DD — what changed, and why`.

Verification follows the [local-first contract](https://github.com/cdudek/calvins-claude-tools/blob/main/plugins/cct/skills/sdlc-run/references/local-first.md).
