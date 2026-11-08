---
name: ux-guidelines-write
description: "Writes and maintains the product's interaction guidelines, the shared rules for how the whole app behaves (editing, saving, dialogs and panels, feedback, confirmation and undo, navigation, lists, keyboard, external writes and more), with principles, concrete examples, complete flows, exceptions and an enforcement map. Use when the user says 'write the interaction guidelines', 'how should this behave', 'which interaction do we use for this', 'dialog or panel', 'toast or not'. Skip for: recording a decision the owner made, which belongs to cct:ux-decision-log."
user_invocable: true
metadata:
  version: 1.0.0
  author: calvindudek
---

# cct:ux-guidelines-write

**Arguments:** `[draft | record | answer <question>]`

The guidelines answer "which interaction, when, and why" once, for the whole app. A component
catalogue alone does not do that.

Shared files are in `references/`, two levels up from this skill's base directory. The structure,
the rule areas, the rule format, the flows and the enforcement map are in `rule-areas.md`.

Read `docs/ux/setup.md` first; the guidelines file path is there.

## Modes

### draft — called by cct:ux-assessment-run (agent 1, phase 2), or by hand after an audit

1. Read the latest `findings.md` and the agents' current-behaviour tables.
2. For every area in `rule-areas.md`: what happens today in every build, with the screens where
   it differs; a proposed rule in the format of `rule-areas.md`; exceptions with reasons.
3. Principles first (five to seven), each one a sentence the rules can be traced back to.
4. Write every flow in `rule-areas.md` plus the product's own from `setup.md`, step by step, with
   the keyboard route, set in an audience scene. Annotated current screenshots; proposals clearly
   labelled "Proposal".
5. Every rule `status: proposed`. Link the findings it resolves in its supporting notes.
6. Fill the enforcement map with what would enforce each rule, and whether it exists.

### record — after decisions

Read `docs/designs/INDEX.md` and open the `ux` decisions dated after each rule's last status
(and `docs/ux/decisions.md` where a repo still has the old log). For every decision about a rule:

| Owner's answer | What the rule becomes |
|---|---|
| Accept the recommendation | `accepted` (date, by the owner), text unchanged |
| Choose the alternative | `accepted` (date, by the owner), the alternative becomes the rule text; the old recommendation moves to supporting notes as "rejected option" |
| Own words | `accepted` (date, by the owner), the owner's wording becomes the rule, quoted verbatim; rewrite only the example to match, and show the rewrite at the next round |
| Defer | `deferred` (date), text unchanged |
| No to both, nothing instead | `rejected` (date); the area stays open as `unresolved` |

Never mark a rule accepted without a recorded decision; an existing implementation or an older
document is not acceptance.
Then list which design-system sections and components would have to change. Do not implement.

### answer — during work

When someone asks how something should behave: find the rule, quote it, and name the exception
if one applies. If there is no accepted rule, say so plainly, show the proposed one if any, and
offer to add the question to the next `cct:ux-decision-log` round. Never invent a rule on the spot and
present it as decided.

## Writing

Plain language. Every rule has a concrete example from this product. Never ask or state "modal or
drawer" without showing what each means for the user's task. Codes and file paths go in
supporting notes only. Follow `writing.md` and the project's own voice rules.
