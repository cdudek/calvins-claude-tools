---
name: test-journeys-write
description: "Writes the canonical journey coverage inventory (e2e/journeys.md): the list of claims the E2E suite makes, grouped by audience and persona, with a recommended score, tier, owner, lifecycle and screen states per journey, every existing spec mapped to a journey or marked a harness, and the uncovered top-tier states listed. Owners and tiers stay recommendations until a person confirms them. Use when someone says 'draft our journeys.md', 'write the journey inventory', 'list our critical e2e journeys', 'refresh the journey inventory', 'which e2e journeys are uncovered'. Skip for: the rules for scoring and tiering, owned by cct:test-e2e-policy; writing specs for a journey, owned by cct:test-e2e-coverage-run."
allowed-tools: "Bash(ls *) Bash(command -v *) Read Write Glob Grep Agent"
user_invocable: true
metadata:
  version: 1.0.0
  author: calvindudek
---

# Write the journey inventory

Drafts or refreshes `e2e/journeys.md`, the list of claims the suite makes, before any spec
is written. Use it when the file is missing, when a repo first adopts the standard, or at a
milestone to catch drift. It writes the inventory only: no specs, and no edits to
application source.

The method (audiences and personas from the product's roles, scoring, tiers, states, the
specs-to-journeys map) is `references/strategy.md` section 2.7 in `cct:test-e2e-policy`.
This skill applies it and does not restate it.

## Steps

1. Resolve two absolute paths with `ls`, because an agent's Read tool does not expand
   variables: the rules folder `${CLAUDE_SKILL_DIR}/../test-e2e-policy/references/` and the
   template `${CLAUDE_SKILL_DIR}/../test-e2e-setup/templates/journeys.md`.
2. Dispatch the `cct:test-e2e-planner` agent with the task "draft the journey inventory",
   the rules folder and the template path. It follows strategy.md section 2.7: audiences and
   personas from the product's roles, journeys per audience, every existing spec mapped to a
   journey, a harness or "not a journey", a recommended score and tier per journey, and its
   lifecycle and screen states with the covered ones marked. It cannot ask questions; you
   show the draft to a person.
3. Show the person the T1 list, the uncovered T1 states and the specs that landed nowhere.
   Owners and tiers stay marked as recommendations until the person confirms them.
4. Commit the confirmed first draft in its own PR. After that, rows change in the same PR as
   the feature that changes them (strategy.md section 2.8). The uncovered T1 states are the
   next specs to write, through `cct:test-e2e-coverage-run`.
