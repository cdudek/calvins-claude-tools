---
name: product-strategy-run
description: "Coordinates a product strategy cycle over 2 to 4 weeks, from positioning and customer context through problem framing, solution options and prioritisation to a stakeholder readout and a roadmap handoff. Delegates problem framing to cct:product-problem-write, audience to cct:product-audience-write, prioritisation to cct:product-priorities-analyze and journeys to cct:ux-journey-create; runs strategy canvas, OKR, go-to-market and positioning methods from cct:product-playbook itself. Use when someone says 'run a strategy session', 'run the product strategy cycle', 'set our product strategy', 'refresh the product strategy', 'take us from vague direction to strategy'. Skip for: a single method such as an OKR set or a canvas (cct:product-playbook), a discovery cycle (cct:product-discovery-run), the roadmap itself (cct:product-roadmap-write)."
user_invocable: true
metadata:
  version: 2.0.0
---

# Product strategy run

A repeatable process that takes a product from strategic ambiguity to validated direction: positioning, a validated problem, prioritised opportunities, a roadmap and stakeholder alignment. Typical span is 2 to 4 weeks with several touchpoints. It is a process, not a workshop: it coordinates, and every artifact is authored by its owner skill.

Use it to launch a product or major initiative, run an annual or quarterly planning cycle, reposition a product, or align a new product lead. Do not use it when strategy is already clear and validated, for tactical feature additions, or without executive sponsorship (the strategy will not stick).

For guided conversations use the protocol in `${CLAUDE_SKILL_DIR}/../product-playbook/references/facilitate-workshop.md`. Company facts (positioning, pricing, ICP) come from the repo's own context docs, not from the methods.

## Delegation

Do not restate the owners' methods; call them and carry their output forward.

- **Problem statement and How Might We:** `cct:product-problem-write`
- **Target customer and personas:** `cct:product-audience-write`
- **Ranking and framework choice:** `cct:product-priorities-analyze`
- **Journey map when the problem spans touchpoints:** `cct:ux-journey-create`
- **Jobs to be done:** `cct:ux-jobs-write`
- **Roadmap, PRD, epics, story map:** `cct:product-roadmap-write`, `cct:product-prd-write`, `cct:product-epic-analyze`, `cct:product-storymap-create`
- **Evidence gaps (interviews, experiments):** `cct:product-discovery-run`

Private methods, read from `${CLAUDE_SKILL_DIR}/../product-playbook/references/<method>.md`:

- `define-product-strategy.md` (9-section strategy canvas)
- `brainstorm-okrs.md` (objectives and key results)
- `plan-go-to-market.md` (channels, messaging, launch)
- `run-positioning-workshop.md` (positioning statement)
- `analyze-competitors.md` and `map-stakeholders.md` (context and alignment)
- `build-opportunity-tree.md` (solution exploration)

## Phases

### 1. Positioning and market context (week 1, days 1-2)

Run `run-positioning-workshop.md` (90 min, PM, leadership, marketing, sales) for a draft positioning statement. Delegate personas to `cct:product-audience-write` and jobs to `cct:ux-jobs-write`.

**Decision 1:** enough customer context? If no, run `cct:product-discovery-run` for 5-10 interviews before continuing (+1 week).

### 2. Problem framing and validation (week 1, days 3-5)

Delegate the problem statement to `cct:product-problem-write` (framing workshop plus formal statement). Delegate a journey map to `cct:ux-journey-create` only when the problem spans several touchpoints.

**Decision 2:** is the problem validated? If no, run `cct:product-discovery-run` and iterate the statement (+1 week).

### 3. Solution exploration (week 2, days 1-3)

Build an opportunity solution tree with `build-opportunity-tree.md` (3 opportunities, 3 solutions each, a proof-of-concept recommendation). Write epic hypotheses for the top 3-5 initiatives. For complex features, delegate a story map to `cct:product-storymap-create`.

**Decision 3:** high uncertainty? If yes, test solutions (prototype, concierge, landing page, 10-20 customers) via `cct:product-discovery-run` (+1-2 weeks); if no, continue.

### 4. Prioritisation and roadmap (week 2, days 4-5)

Delegate framework choice and ranking to `cct:product-priorities-analyze`. Score the epics with engineering and leadership, then sequence by quarter or release and hand the sequence to `cct:product-roadmap-write`. Size the market (TAM/SAM/SOM) only for executive, fundraising or market-sizing needs.

### 5. Alignment (week 3)

Optional press-release style vision for major launches. Present in 60 minutes: positioning, problem, options and priorities, roadmap. Collect feedback and refine for 1-2 days. Schedule this presentation before starting.

### 6. Execution planning (week 4)

Delegate epic splitting to `cct:product-epic-analyze` and work items to `cct:product-workitem-write`; plan the first sprint or release with engineering. Then stop: move to execution.

## Output

Capture the cycle in `references/template.md` (context, target customer, problem, opportunities, hypotheses, prioritisation, roadmap, metrics, next steps). `references/sample.md` is a worked example.

Time: minimum 2 weeks without discovery, typically 3 with one validation round, 4-6 with interviews and experiments.

## Pitfalls

- **Skipping problem validation:** jumping from positioning to solutions. Force Decision 2.
- **Solo PM exercise:** no buy-in. Include design, engineering, sales and customer success in the workshops.
- **No executive sponsorship:** execs miss the alignment session and nothing is resourced. Secure commitment first.
- **Running every phase regardless:** use the decision points to skip discovery or experiments when uncertainty is low.
- **Permanent strategy mode:** time-box to 2-4 weeks, then execute.

## Sources

Adapted from deanpeters/Product-Manager-Skills (`skills/product-strategy-session`), MIT.
