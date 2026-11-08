---
name: test-e2e-policy
description: "The rulebook for end-to-end tests, the automated checks that click through the product like a customer would: which customer journeys deserve one, how a test finds buttons and text so wording or design changes do not break it, how it waits without flaking, which states (empty, error, refused, expired) to cover, and how AI agents may write and repair tests without weakening them. It grounds the E2E planner, generator and healer and runs, writes and installs nothing. Use when someone asks 'what should we e2e test', 'which journeys are critical', 'which locator should this test use', 'how should this test wait', 'why does every copy change break our tests', 'what is journeys.md'. Skip for: writing, running or repairing the tests, owned by cct:test-e2e-coverage-run; installing the harness, owned by cct:test-e2e-setup."
allowed-tools: "Read Grep Glob"
user_invocable: true
metadata:
  version: 3.0.0
  author: calvindudek
---

# The e2e standard

An end-to-end test is the most expensive test we write and the one most likely to fail for
a reason unrelated to the product. It earns its place only by proving something no cheaper
test can: that the real build, database, auth, routing and browser work together for a
person doing something that matters. Everything in this skill follows from that.

This skill is the rulebook and nothing else. The agents `cct:test-e2e-planner`,
`cct:test-e2e-generator` and `cct:test-e2e-healer` read the same files before they write
anything, so an answer given from here and a spec written by an agent agree. Writing,
running and repairing tests belongs to `cct:test-e2e-coverage-run`; installing Playwright,
the lint preset and the assertion guard belongs to `cct:test-e2e-setup`.

## Which file answers which question

Read only the one you need. Each rule lives in exactly one file; a rule in two files is
wrong in one of them within a month.

| The question | Read |
|---|---|
| Is this worth an e2e test? Which journeys are critical? What goes in `e2e/journeys.md`, and what if it is missing? Which states must a journey cover? How big may the suite get? Flaky tests and quarantine? Where tests run? Rules for AI agents? | `references/strategy.md` |
| Which locator? How do I keep copy out of a spec? Personas and sign-in? | `references/locator-policy.md` |
| How do I wait for something? Timers, network, hydration, downloads, polling? | `references/waiting.md` |
| Why is the suite slow or unreliable? Measurement, control runs, fixtures, load, gate repeats, known traps and repair boundaries. The command per stack for touched tests, production target, sharding and one retry | `references/suite-speed-and-reliability.md` |

Installing Playwright, its config, auth setup, CI and debugging are in
`${CLAUDE_SKILL_DIR}/../test-e2e-setup/references/setup-and-tools.md`.

## In one sentence

Test the few journeys that would cost money, consent, access or data if they broke, assert
what the person can perceive rather than how it is built, wait for facts rather than time,
and never let the agent that changes a test decide what the test expects. The reasons are
the five beliefs in `references/strategy.md` section 1.

## Test integrity

These hold for every author, human or agent, and the healer enforces them:

- A spec contains no user-visible string; it resolves one from the copy catalogue.
- A new scenario is seen to fail with its defect put back before it counts.
- Never raise a timeout, add a sleep, loosen an assertion, skip a test or mark it `fixme` to get green.
  A correct failing test is evidence to preserve (`references/suite-speed-and-reliability.md` section J).
- The assertion count may not fall and no `.skip`, `.fixme` or `.only` may appear; the guard
  `${CLAUDE_SKILL_DIR}/../test-e2e-setup/scripts/assertion-guard.sh` checks this mechanically.
- Quarantine is a ticketed, owned, time-boxed exception, never a repair (`references/strategy.md` section 7).

## When the repo has no journey inventory

Treat a missing `e2e/journeys.md` as the first thing to fix, before any new spec. It is
drafted, grouped by audience and persona with a recommended tier and a state list for every
journey, by `cct:test-journeys-write`; a person confirms owners and tiers.
`references/strategy.md` section 2 says how. From then on every feature adds or updates
its journey row in the same PR that changes the behaviour.
