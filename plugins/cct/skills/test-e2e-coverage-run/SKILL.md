---
name: test-e2e-coverage-run
description: "Coordinates E2E test coverage from planning through generation, execution and healing, taking its source from a journey inventory, a Linear ticket or a live surface: plans scenarios, has them generated as live-verified Playwright specs proven to fail when the feature breaks, runs them, and repairs specs broken by a product change without loosening what they check. It delegates the journey inventory to cct:test-journeys-write, the harness to cct:test-e2e-setup, suite execution to cct:test-suite-run, the rules to cct:test-e2e-policy, and the work to the agents cct:test-e2e-planner, cct:test-e2e-generator and cct:test-e2e-healer. Use when someone says 'write e2e tests for this page', 'cover this feature end to end', 'write e2e for REV-123', 'scaffold e2e tests from a ticket', 'heal the e2e suite', 'the e2e suite is red'. Skip for: a test that fails at random, owned by cct:test-flake-fix."
allowed-tools: "Bash(npx playwright *) Bash(command -v *) Bash(git diff *) Bash(ls *) Bash(gh *) Read Edit Write Glob Grep Agent Skill"
user_invocable: true
metadata:
  version: 3.0.0
  author: calvindudek
---

# Coordinate E2E coverage (plan, generate, run, heal)

Verification and every push follow the [local-first contract](../sdlc-run/references/local-first.md); read it before running checks or preparing a push.

The repeatable E2E workflow: the classic planner, generator, healer concept, where the
browser **driver for exploration is the agent-browser CLI** (not Playwright MCP) and the
committed artifact is **plain deterministic `@playwright/test` with NO runtime LLM**.

This skill is a process. It owns the loop and the sequencing, and delegates every method:

| Job | Owner |
|---|---|
| Journey inventory (`e2e/journeys.md`) | `cct:test-journeys-write` |
| Install lint preset, templates, assertion guard, Playwright config | `cct:test-e2e-setup` |
| Execute a suite and report results | `cct:test-suite-run` |
| Strategy, locator, waiting and integrity rules | `cct:test-e2e-policy` |
| Explore a surface and write the plan | agent `cct:test-e2e-planner` |
| Write and live-verify the spec | agent `cct:test-e2e-generator` |
| Repair failing specs | agent `cct:test-e2e-healer` |

Dispatch on the first word of the argument: `journeys`, `author <surface>`, `ticket <id>`,
`run [path]`, `heal [paths]`. A bare surface or ticket id means `author` or `ticket`.

## Prerequisites

| Variable / Dependency | Required | How to obtain |
|-----------------------|----------|---------------|
| `agent-browser` CLI | For `author`, `ticket` hand-off and `heal` | on PATH: `npm i -g agent-browser && agent-browser install` (Node 24+); usage in `cct:browser-automate` |
| `@playwright/test` | Yes | the target project's package.json |
| Running dev server | For `author` and `heal` | project dev command, seeded/dev DB per project docs |
| Linear MCP | For `ticket` only | connected Linear connector (`get_issue`, `list_comments`), load via ToolSearch |
| `gh` CLI | Only for the ticket PR/shipped-code fallback | `gh auth login` |

## The rules live in the policy skill

`${CLAUDE_SKILL_DIR}/../test-e2e-policy/references/` holds `strategy.md` (what is worth
testing, journeys, states, budget, quarantine, the AI rules), `locator-policy.md` (how a spec
binds to the page), `waiting.md` (how it synchronises) and `suite-speed-and-reliability.md`
(fixtures, suite execution, known traps). The three agents read them before they write
anything. **Resolve that folder to an absolute path once (`ls` it) and put it in every
dispatch prompt**, because an agent's Read tool does not expand the variable. Do not restate
the rules here and do not argue with them in a prompt.

## Before anything

Read the target project's `e2e/journeys.md` (what is worth testing, by whom it is owned),
`e2e/personas.md` (who signs in, via which helper) and its testing docs (`e2e/AGENTS.md`,
`e2e/TESTING.md`, existing specs): spec layout, DB hygiene rules, the auth/persona seam, the
data seam (`testData` fixture or factory), env tags, locale and the copy catalogue are
project-specific and the agents must be told where to find them. If `e2e/personas.md` is
absent, say so and offer to run `cct:test-e2e-setup`.

Hard constraints (every mode):
- No runtime LLM in committed specs; agent-browser for exploration, not Playwright MCP.
- Shared seeded DBs stay clean: mutations are self-cleaning (`finally`) or non-destructive.
- Specs must be re-runnable on a used DB (no emptiness assertions on accumulating data).
- Content-based assertions over HTTP status; web-first assertions; no hard sleeps.
- **No spec contains a user-visible string**; it resolves one from the copy catalogue.
- **Nothing here edits application source.** A missing test id is reported, not added. The
  one exception is the generator's defect check: one line changed, one spec run, reverted
  and verified clean, on a file with no uncommitted work.
- **Every spec serves a journey** in `e2e/journeys.md` with a tier and an owner, and every
  new scenario is seen to fail with its defect put back.
- Committed specs never hardcode entity IDs; every scenario's data needs go through the
  project's data seam.

## `journeys`

Delegate to `cct:test-journeys-write`. Its confirmed inventory is the precondition for
`author` and `ticket`; the uncovered T1 states it lists are the next `author` runs.

## `author <surface>` / `author --plan <path>`

For fixture design and authoring traps, include
`suite-speed-and-reliability.md` sections D and I.1, I.2, I.5 and I.6 in the generator's
dispatch prompt: deterministic data, entrance motion, native shortcut coverage, evidence
output and background sweep completion.

1. Confirm `command -v agent-browser` (else surface the install hint, never silently skip).
2. With `--plan <path>` (a confirmed plan, for example from `ticket`), skip to step 3.
   Otherwise dispatch `cct:test-e2e-planner` on `<surface>`; it explores via agent-browser
   and writes a markdown plan (for example `e2e/plans/<surface>.md`).
   - `INVENTORY MISSING`: run `journeys` first, get the person's confirmation, then start
     `author` again.
   - The path scores T3: stop, recommend the lower-level test and write no spec.
3. Dispatch `cct:test-e2e-generator` with that plan. It live-verifies selectors, writes and
   runs the spec until green, then proves each scenario fails with its defect introduced.
4. Dispatch a **fresh-context reviewer** (a general-purpose agent that did not write the
   spec) with the plan and the spec: does each assertion check what the plan says, could it
   pass with the feature broken, does it assert anything the plan did not ask for. Fix what
   it finds.
5. Report the new spec path, the run result, and the defect each scenario caught.

For several surfaces, run the planner passes in parallel, then dispatch each generator as
its plan lands (no barrier).

## `ticket <id>`

The ticket-driven source: it turns a Linear ticket into a confirmed Markdown plan in the
planner's format, then hands it to generation. It writes the plan, never a `.spec.ts`.

1. **Parse the input**: `REV-123`, a Linear URL or a UUID. Fetch with Linear MCP `get_issue`
   (`includeRelations: true`) and `list_comments`. Retry 2-3 times on transient 500s.
2. **Extract acceptance criteria and user stories.** If the description is thin but a merged
   PR or shipped component exists (the ticket's linked PRs, or `gh` for the branch), use that
   as the source of truth for behaviour.
3. **Detect the target repo and its e2e conventions** (see "Before anything"). Identify the
   persona each scenario needs (logged-out, logged-in, admin) against the project's auth seam.
4. **Map each criterion to a scenario**: persona, steps, expected result (the **copy key**,
   with the resolved string in brackets for a human; the locator policy bans raw copy in a
   spec), **explicit per-scenario data needs** (the hand-off point to the project's
   `testData` seam) and env tags (`@staging` / `@production`).
5. **Place it in a journey.** Name the journey id from `e2e/journeys.md` the ticket changes,
   its tier, owner and states, or score a new one (`strategy.md` section 2). A new feature
   adds its journey row, or its states to an existing journey, in the same PR (section 2.8).
   A T3 result means the ticket gets component or unit tests, not e2e: say so and stop. Plan
   a scenario per new lifecycle transition and per refusal on money, consent or access, and
   name the **defect to put back** per scenario.
6. **Write the plan** at the project's plan location (for example `e2e/plans/<surface>.md`)
   in the format `cct:test-e2e-planner` emits. **Get explicit user confirmation.**
7. **Hand off to generation** with the confirmed plan: run `author --plan <path>`. Red specs
   later go through `heal`.

## `run [path]`

Delegate to `cct:test-suite-run` and return its results.

## `heal [paths]`

Dispatch `cct:test-e2e-healer` (optionally scoped to failing spec paths). It runs the
suite, triages each failure (regression, intentional change, test debt), repairs only test
debt and cited intentional changes, and leaves regressions red. It ends with the assertion
guard from `cct:test-e2e-setup` (`scripts/assertion-guard.sh`), which fails a net drop in
assertions or any new skip, fixme or only.
