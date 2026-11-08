# The e2e strategy

**This file is the single source for what an e2e suite tests, how big it may grow, who owns
it, and how it survives copy, token and AI-driven change.** `locator-policy.md` owns how a
spec binds to the page; this file owns everything around that. The three agents read both
before they write anything. If a rule lives in two places, one of them is already wrong.

## The one-sentence version

Test the few journeys that would cost money, consent, access or data if they broke, assert
what the person can perceive rather than how it is built, and never let the agent that
changes a test be the one that decides what the test expects.

## Contents

- 1. Five beliefs
- 2. Choosing what to test: the journey inventory
  - 2.1 Finding the journeys
  - 2.2 Scoring a journey
  - 2.3 What each entry records
  - 2.4 What does not belong at e2e level
  - 2.5 Covering the states
  - 2.6 Forcing a state cheaply
  - 2.7 When the inventory is missing
  - 2.8 Keeping it current
- 3. The budget
- 4. Surviving copy and translation changes
- 5. Surviving design-token changes
- 6. Data and isolation
- 7. Flaky tests and quarantine
- 8. Where it runs
- 9. Working with AI agents
- 10. Ownership
- 11. Done, for a new or changed spec

## 1. Five beliefs

1. **E2E proves the wiring, not the logic.** Routing, auth, permissions, real database,
   real build, real browser. Logic belongs in unit and component tests, which are faster
   and fail closer to the cause. Google, Fowler, GitLab and Shopify agree on this; only the
   exact shape (pyramid, trophy, honeycomb) differs.
2. **A test is a claim someone owns.** A spec says "this journey works". Nobody owning the
   claim means nobody acts when it goes red, which means the suite trains people to ignore
   red.
3. **Correct beats green.** A red test that is right is the most valuable signal the suite
   gives. A green test that cannot fail is worse than no test: it costs run time and buys
   false confidence.
4. **Assert meaning, not mechanics.** Roles, states, values and keys survive a redesign.
   Strings, classes, hex values and DOM order do not.
5. **Writing tests is now cheap; owning them is not.** Agents can produce a hundred specs in
   an afternoon. Every one of them costs CI minutes, review attention and maintenance for as
   long as it exists. Budget the suite like any other cost.

## 2. Choosing what to test: the journey inventory

Every repo with an e2e suite keeps **`e2e/journeys.md`** (template:
`test-e2e-setup/templates/journeys.md`, installed by `test-e2e-setup/scripts/install-lint.sh`). It lists the critical user
journeys, the way Google SRE writes critical user journeys before it writes an SLO: start
from "what do the people using this care about", not from "which screens exist".

It is **grouped by audience**: one section per kind of person who uses the product (a
visitor, a customer, an operator, an integration acting on someone's behalf), and inside
each, the personas with different rights (owner, admin, viewer). A journey belongs to the
audience that starts it. Grouping this way makes the gaps visible: an audience with no T1
journey, or a role nobody signs in as, shows up as an empty section rather than staying
invisible in a flat list of specs.

### 2.1 Finding the journeys

Walk these sources, in this order, and write down every end-to-end path a real person takes:

1. **The money and the law.** Every path that charges, credits, redeems, invoices, records
   consent, withdraws consent, grants or revokes access, or sends mail to a customer.
2. **The front door.** Sign-in, sign-up, double opt-in, the first screen after sign-in for
   each persona.
3. **Usage.** The top paths by traffic from analytics (PostHog, server logs). A journey
   nobody takes is not critical, however complex it is.
4. **Incidents.** Every production incident and every bug that reached a customer in the
   last year. If it broke once, it is a candidate.
5. **Seams.** Every place two systems meet that a unit test cannot reach: an outbox to
   HubSpot, a webhook, a provider callback, a file export someone imports elsewhere.

### 2.2 Scoring a journey

Score each journey on six questions, 0 (no) to 2 (yes, badly):

| Question | 0 | 2 |
|---|---|---|
| Does a failure cost money or create a financial error? | no | yes, silently |
| Does a failure break a legal duty (consent, privacy, deletion)? | no | yes |
| Does a failure expose or lose data, or grant the wrong access? | no | yes |
| How many people take it? | rare | daily, most users |
| Has it broken before? | never | in the last year |
| Can only a browser catch the failure? | no, a unit test can | yes, only wired together |

**Tier by score:**

| Tier | Score | Where it runs | What it gets |
|---|---|---|---|
| **T1** | 8 or more, or any 2 on money, law or access | every PR, blocking | one happy path end to end, plus the one failure path that matters most |
| **T2** | 4 to 7 | milestone gate and nightly | the happy path |
| **T3** | under 4 | not at e2e level | component or unit tests, named in the inventory so the decision is visible |

The last question is a veto: a journey that scores 0 on "only a browser can catch it" is T3
whatever else it scores. Cover it lower down.

### 2.3 What each entry records

`id`, a one-line description, audience and persona, tier, score, **owner**, the
**states** it must cover with the ones covered today (section 2.5), the specs that cover
it, **what the specs prove**, and **what they do not prove**. The last field is the one that
stops a green suite from being read as "everything works".

### 2.4 What does not belong at e2e level

- Field validation, formatting, pluralisation, error copy: component tests.
- Every branch of a state machine: unit tests.
- Every locale: one locale end to end, the rest at component level (section 4).
- Anything you can assert without a browser.

The cheapest flaky test is the one never written.

### 2.5 Covering the states

A journey that only walks its happy path proves the product works on a good day. Most real
failures live in the other states, so every journey lists them, and the inventory shows
which are covered. Two kinds:

**Lifecycle states** of the things the journey changes: a booking pending, active, closed;
a consent requested, confirmed, withdrawn; a link fresh, used, expired. Write the states
and the valid transitions between them. The goal is that **every valid transition is
walked once** somewhere in the suite (state-transition testing calls this 0-switch
coverage), plus the **invalid transitions that matter for money, consent and access**,
whose expected result is a refusal with a named reason: redeeming on a closed booking,
confirming an expired link, a viewer exporting.

**Screen states** of each screen the journey crosses. Use this list, and mark the ones that
cannot happen on that screen as not applicable rather than leaving them out:

| State | What the person sees |
|---|---|
| ideal | the screen with typical data |
| empty | nothing yet, and what to do about it |
| filtered to nothing | no match, and how to clear the filter |
| partial | one row, a long name, a missing optional field |
| loading | the wait, without a jump when it ends |
| error | what failed and what to do now |
| refused | not allowed for this person, and why |
| closed or expired | the thing exists but can no longer be used |
| success | the outcome, on the thing that changed |

Not every cell needs a browser. Decide per cell:

- **E2E**: every lifecycle transition once, every refusal on money, consent or access, and
  any screen state that only appears when real parts are wired (a refusal from the server,
  an expired link, a closed booking).
- **Component level**: presentational variants of one screen (partial, long text, the
  layout of empty and error), because they need no server.
- **Unit or API level**: the full transition table, including invalid transitions that are
  not money, consent or access.

Name each state test `<journey> / <state> / <persona>` so a missing cell is visible in the
report, not just in the inventory.

### 2.6 Forcing a state cheaply

A state you cannot reach on demand becomes a state nobody tests. Reach it deterministically:

- **Data**: create the world in the state you need through a factory (an expired grant, a
  closed booking, a withdrawn consent) instead of walking a person there.
- **Time**: `page.clock` for anything the browser times; a seeded timestamp for anything
  the server times (`waiting.md` section 6).
- **Network**: `page.route` to hold a request (loading) or fail it (error) for the screen
  states only. Never route your own API in a test that claims the wiring works
  (`waiting.md` section 7).

### 2.7 When the inventory is missing

Do not start writing specs. Draft the inventory first, then ask a person to confirm it:

1. **Find the audiences and personas.** Read the product's roles and permissions (the auth
   fixture, the role enum, the permission checks) and any audience or journey document.
   One section per audience; inside it, a row per persona with what they may see and
   change.
2. **Find the journeys per audience** with the five sources in section 2.1. Prefer an
   existing journey or process document over reverse-engineering screens.
3. **Map the existing specs** to journeys by file name and test titles. Every spec lands on
   a journey, in the harness table, or in a "not a journey" list (design-system, layout and
   accessibility checks). A spec that lands nowhere is a deletion candidate.
4. **Score and recommend a tier** for each journey (section 2.2). Mark every score as a
   recommendation; the owner confirms it.
5. **List the states** per journey (section 2.5) and mark which existing specs cover them.
   The uncovered T1 states are the work list.
6. **Leave the owner column for a person.** Propose an owner from the code history if one is
   obvious, marked as a proposal.

### 2.8 Keeping it current

The inventory is only true if every change keeps it true. In the same PR that changes the
behaviour:

- **A new feature adds its journey**, or adds itself to an existing journey's states, with
  a recommended tier and the specs it adds.
- **A changed feature updates** the journey's states, its "proves" and "does not prove".
- **A removed feature removes** its journey and deletes its specs.
- **A fixed production bug** raises the journey's "broke before" score and adds the state
  that broke.

Review checks it like code: a PR that adds or changes a spec without touching
`e2e/journeys.md` needs a reason.

**Who edits it.** The planner and `cct:test-e2e-coverage-run` (ticket mode) propose rows and states, marked as
recommendations. A person confirms owners and tiers and is the only one who edits the
Quarantine table. The healer never edits it: a spec it repairs serves the journey it served
before.

## 3. The budget

A suite without a budget only grows. Set the numbers in `e2e/journeys.md` and check them in
review:

- **The PR gate (T1) finishes in 10 minutes or less** on CI, wall clock. When it does not,
  shard or cut; never raise the job timeout.
- **One spec file per journey**, named for it. A spec that serves no journey id is either a
  harness (section 8) or a candidate for deletion.
- **Adding a T1 spec names what it replaces or why the budget grows.** In the PR body.
- **Harnesses stay out of the gate.** Screenshot capture, state audits, evidence runs and
  proofs are useful, but they are not tests of a journey. Keep them behind an env flag or a
  separate project in the Playwright config, so they never slow or redden the gate.
- **A pruning pass at every milestone.** Delete specs whose journey moved to T3, merge specs
  that walk the same path, and delete any assertion a lower-level test already makes.

## 4. Surviving copy and translation changes

`locator-policy.md` section 2 owns the rule: no user-visible string in a spec, every string
resolved through `t('key')` from the real catalogue, enforced by `no-catalogue-copy`. This
section adds what the policy does not cover:

- **One locale end to end.** The suite runs in the default locale. A second-locale run is a
  T2 smoke of each T1 journey's first screen, not a copy of the suite.
- **Raw keys never render.** One cheap check per locale: no visible text on a T1 screen
  matches the key pattern (`/^[a-z]+(\.[a-zA-Z0-9]+)+$/`, with an allowlist for domain names
  the page shows on purpose). It catches a missing translation the parity test missed
  because the key is built at runtime.
- **Parity lives in unit tests.** "Every key exists in every locale" and "German uses the
  agreed address form" are file checks. They do not need a browser.
- **When the words are the behaviour, say so.** Consent text, a price, a legal notice: here
  a wording change is a product change. The spec still resolves the text by key, and a unit
  test pins the catalogue value, so a change to it is a reviewed diff with a named reviewer,
  not a silent catalogue edit.
- **Renames are a key change, not a copy change.** When a key is renamed, the spec breaks at
  the `t()` call with "missing key". That is the intended failure: fix the key, never retype
  the text.

## 5. Surviving design-token changes

A redesign changes the paint. It should not break a test unless it breaks the meaning. Use
the first rung of this ladder that can express the claim:

1. **State through ARIA.** Selected, current, pressed, expanded, invalid, disabled: assert
   `aria-selected`, `aria-current`, `aria-pressed`, `aria-expanded`, `aria-invalid` or
   `toBeDisabled()`. A screen reader needs these anyway, so the test rides a contract the
   app already owes. This covers most "is it highlighted" questions.
2. **Paint through the token, never the value.** When the look itself is the requirement
   (the selected colour, a focus ring, a danger state), resolve the token in the page and
   compare computed styles. Never a hex literal, never a class name.

   ```ts
   // e2e/tokens.ts, installed from test-e2e-setup/templates/tokens.ts
   import { resolveToken } from './tokens'

   const selected = await resolveToken(page, '--background-color-selected', 'background-color')
   await expect(row).toHaveCSS('background-color', selected)
   ```

   `resolveToken` throws when the token is not defined, so a token rename fails loudly at
   one line; a token value change passes, because the
   claim ("selected rows use the selected token") still holds.
3. **Contrast as a ratio.** Where accessibility is the claim, compute the contrast ratio
   from the two computed colours and assert it is at least 4.5 (text) or 3 (non-text). The
   claim survives any palette that keeps the promise.
4. **Pixels last, and few.** `toHaveScreenshot` only for a handful of surfaces where layout
   is the product, baselines generated in the same pinned container CI uses, volatile parts
   masked, and an owner per baseline. A token change regenerates baselines in its own PR,
   reviewed by a person looking at the images.

Token values themselves (the palette, the scale, a contrast table) are unit-tested against
the token source. The browser test only proves the component uses the token.

**Class names are never asserted.** `toHaveClass(/bg-primary/)` proves the code says what
the code says. It passes when the token is wrong and fails when a refactor renames the
utility.

## 6. Data and isolation

For the default seed, follow `suite-speed-and-reliability.md` section D. It owns the
synthetic fixture rules; the isolation rules below still apply to each worker.

- **Each test makes the world it needs**, through an API or a factory fixture, with names
  unique to the run. Never depend on a row another test made or on the seed staying as it
  was.
- **Self-cleaning or non-destructive**, as the locator policy's personas section and the
  agents already require. Teardown in a fixture or `finally`, so it runs when the body
  throws.
- **Aim for per-worker isolation.** A suite pinned to `workers: 1` because tests share one
  database is a suite that cannot be sharded. Give each worker its own tenant, business unit
  or schema, keyed on `workerInfo.parallelIndex` (`workerIndex` changes when a worker
  restarts after a failure), and parallelism becomes a config change. The fixture is in
  `suite-speed-and-reliability.md` section H.
- **Real everything you own; fake only what you do not.** Your database, your build, your
  auth: real. A third-party provider, a payment gateway, a captcha: a fake at the boundary,
  named in `e2e/personas.md`. A spec that stubs your own API is a component test in a
  slower costume.
- **Control time, do not wait for it.** `page.clock` for countdowns, expiry and scheduled
  sends. A test that sleeps until a timer fires is a test that fails on a slow runner.

## 7. Flaky tests and quarantine

A flaky test is a defect with an owner, not weather.

- **Retries: at most 1 on CI, and a pass on retry is reported.** On a feature PR it goes in
  the job summary and onto the committed flaky list (`suite-speed-and-reliability.md`
  section G) without blocking the merge; on a full run (`FULL=true`, the CI blueprint's A5) a flake fails
  the run (Playwright 1.52+: `failOnFlakyTests: process.env.FULL === 'true'`). The retry
  still records a trace. Commands for other stacks: section K of the same file.
- **Fix first, with `cct:test-flake-fix`:** reproduce with `--repeat-each=20` (`waiting.md` section 11),
  find the cause, fix it, prove it with the same repeat.
- **Quarantine is a human decision, never the healer's.** When a flaky T1 test blocks
  unrelated work and the fix is not quick, a person tags it `@quarantine` and adds a line to
  `e2e/journeys.md` with the owner, a ticket and an expiry no more than 14 days out.
  Quarantined tests still run and still report; they stop blocking. The healer keeps its
  rule: it never skips, fixmes or quarantines anything.
- **Expiry is enforced.** On expiry the test is fixed or deleted, and its journey records
  the coverage gap until it is replaced. A quarantine that only grows is a slow deletion
  without the honesty.
- **Return needs proof:** 20 consecutive green runs on CI hardware, not on a laptop.

Google, Slack, Atlassian and GitLab all run some version of this loop. Slack cut failing
test jobs from 57% to under 5% with automatic detection and suppression
(slack.engineering/handling-flaky-tests-at-scale-auto-detection-suppression).

## 8. Where it runs

| Lane | What | When | Blocks |
|---|---|---|---|
| PR gate | T1 specs against the production build (`next build`, then `next start` or the standalone server) and a freshly migrated, seeded database, sharded over N jobs | every PR into the default branch or `project/*`; a feature PR into `milestone/*` runs only the specs it changed; a docs-only PR runs none (`sdlc-run` `references/ci-blueprint.md`) | yes |
| Milestone gate | T1 and T2; repeat scope per `suite-speed-and-reliability.md` section G | before a milestone PR merges | yes |
| Nightly | T1, T2, quarantine, second-locale smoke, integration evidence against sandboxes | nightly | no, but it pages the owner |
| Preview | T1 read-only journeys against the deployed preview | after each preview deploy | advisory |
| Harnesses | screenshot capture, state audits, proofs | on demand, by env flag | never |

- **Test the production build, not the dev server.** Vercel's Next.js guide says the same:
  dev mode compiles on demand, hides build-only failures and times differently.
- **Preview deployments on Vercel** trigger from `repository_dispatch` with
  `vercel.deployment.success`, check out `client_payload.git.sha`, and pass
  `client_payload.url` as the base URL. Protected previews take the
  `x-vercel-protection-bypass` header from `VERCEL_AUTOMATION_BYPASS_SECRET`; fail fast when
  it is missing. On GKE and Argo, the equivalent is a post-sync smoke job against the
  rolled-out canary.
- **Keep the evidence.** `trace: 'on-first-retry'`, screenshots on failure, the HTML report
  uploaded as an artifact. A red run without a trace is a red run someone reruns instead of
  reads.

## 9. Working with AI agents

Agents are good at the mechanics of a test: finding the locator, writing the fixture call,
reading a trace. They are bad at the one thing a test exists for, which is knowing what the
product should do. Split the work that way.

1. **A person owns the oracle.** The expected behaviour comes from the journey inventory, a
   ticket's acceptance criteria or a spec, confirmed by a person. An agent never derives the
   expected result from what the UI shows today; that only proves the UI shows what it
   shows.
2. **Prove every new test can fail.** Put the defect back: break the one line of product
   code the test exists to protect, run the spec, watch it go red for the right reason,
   restore the line. Record it in the PR ("reverted X, spec failed at line Y"). Meta's
   mutation-guided test generation rests on the same idea: a test that cannot catch a
   fault is not a test.
3. **Triage before healing.** Every red spec is one of three things: a product regression, an
   intentional product change, or test debt (drifted copy key, moved control, data
   assumption). Only the last two change the spec. An intentional change updates the
   journey or ticket first, then the spec, citing it.
4. **The healer never moves an expectation.** Locators, navigation, data setup and keys may
   change. What a test expects may change only for an intentional product change, with the
   source cited. Review any diff that touches an `expect(` separately from the rest.
5. **The gate is mechanical, not a prompt.** `test-e2e-setup/scripts/assertion-guard.sh <base-ref>` fails a
   diff that removes more assertions than it adds, or adds `.skip`, `.fixme` or `.only`.
   Deleting obsolete coverage is legitimate; it passes with
   `E2E_ASSERTION_DROP_REASON="<why>"`, which the script prints so a reviewer sees it.
   Research on coding agents found they add mocks more often than people
   (arxiv.org/abs/2602.00409) and will edit tests to pass (arxiv.org/abs/2511.21654); a rule in a prompt does not stop that, a check does.
6. **The writer is not the grader.** A fresh-context reviewer compares the spec with its
   plan and journey: does each assertion check what the plan says, could it pass with the
   feature broken, does it assert anything the plan did not ask for.
7. **Agent-browser refs stay in exploration.** `@e3` is a handle for one session. The
   committed spec uses roles, labels, test ids and keys.
8. **Evidence with every claim.** "Fixed" comes with the run output, and "regression" comes
   with the trace and the commit that introduced it.
9. **Count what you keep, not what you generate.** Of Meta's LLM-generated tests, 75% built,
   57% passed reliably and 25% added coverage (TestGen-LLM, arxiv.org/abs/2402.09171). Expect the same
   ratio, and do not merge the other three.

## 10. Ownership

- Every journey in `e2e/journeys.md` has an owning person or team, and the owner of the
  journey owns its specs.
- A red T1 spec on the default branch is the owner's first task that day, ahead of feature
  work.
- `CODEOWNERS` maps `e2e/` paths to the same owners, so a change to a journey's specs asks
  the person who owns the claim.

## 11. Done, for a new or changed spec

- [ ] It serves a journey id in `e2e/journeys.md`, and that entry names an owner and a tier.
- [ ] The journey's states list says which states this spec covers.
- [ ] It waits for facts, never for time (`waiting.md`).
- [ ] Its tier justifies e2e level; nothing it asserts is already asserted lower down.
- [ ] It follows `locator-policy.md` and passes the lint preset.
- [ ] State is asserted through ARIA, paint through a resolved token, never a class name.
- [ ] It makes and cleans its own data and runs green twice in a row on a used database.
- [ ] It was seen to fail with the defect put back, and the PR says how.
- [ ] `assertion-guard.sh` passes, or the drop reason is written down.
- [ ] The journey's "what this does not prove" line is still true.
