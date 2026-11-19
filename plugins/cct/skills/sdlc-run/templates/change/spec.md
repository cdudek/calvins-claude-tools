---
linear: {{LINEAR}}
type: spec
change: {{CHANGE}}
design: {{DESIGN}}
author: {{AUTHOR}}
status: draft
reviewed_by: null
approved_at: null
created: {{DATE}}
scope: <S | M | L, chosen by risk: see references/change-folder.md>
ux: <none | S | M | L>
prototype: <required | none, written at Stage 2; leave out when ux is none>
capabilities: [<capability>]
---

# Spec: {{TITLE}}

<!-- Writing rule: plain words first, the id in brackets after ("Retry a failed charge once (R12)", never "per R12"). One idea per sentence, at most 25 words. The requirement text itself lives in specs/<capability>/rules/R<n>.md; this table only lists it, so the PR diff of those files is what the owner reads. -->

> One sentence. What we want, and for whom.

## Asks

Every request this change answers, in the asker's own words. Never paraphrased. `Answered by` is
a rule id from the table below, `out of scope`, or `pending` (allowed only until the gate: the
UX validation may run before every ask has its rule).

| # | Date | Source | Words | Screen | Resources | Answered by |
|---|---|---|---|---|---|---|
| A1 | {{DATE}} | owner, chat | "<exact words>" | <screen or "none"> | [resource](asks/{{DATE}}/<file>) or none | R<n> |

## Job stories

Label every story with its evidence: **observed**, **reported** or **assumed**.

| # | When … | I want to … | So I can … | Evidence |
|---|---|---|---|---|
| J1 | <situation> | <motivation> | <outcome> | reported (A1) |

## Success measure

One number, where it is read, and the target. `spec.py outcome write` copies this out of the
folder before the folder is removed.

- **Measure:** <event or metric> — **read in:** <insight or query> — **target:** <number by date>

## Requirements

One row per rule this change adds, changes or removes. The sentence is the rule file's; the
rule file is created with `python3 scripts/spec.py new <capability> "<summary>"`, which takes the
next free number. Plain words here, the EARS sentence there (`references/requirements-grammar.md`).
`Change` is `new`, `changed` or `removed`. A refactor that keeps behaviour has no row.

| Rule | Change | Capability | Plain words | Asks |
|---|---|---|---|---|
| R<n> | new | <capability> | <what a user can do, in plain words> | A1 |

## UX

Only when `ux` is not `none`. S and M: the state table and the screen list, in this file. L: a
link to `ux/` (brief, information architecture, interaction, screens, prototype). Merge the state
table into the capability's rules before the change closes: the next change on this screen has
nothing else to read.

| Screen | State | What the person sees | Rule |
|---|---|---|---|
| <screen> | <state> | <words> | R<n> |

## Clarifications

Answered questions, one line each, and at most three open `[NEEDS CLARIFICATION: <question>]`
markers, only where a wrong guess changes scope, safety or money. Every marker is answered and
deleted before the gate.

- <question> → <answer>

## Assumptions

Defaults taken instead of asking, one line each: the default and why it is safe.

- <assumption>

## Out of scope

- <what this change does not do, on purpose> — <where it lives instead, if anywhere>
- A<n> — <why this ask is not answered here>
