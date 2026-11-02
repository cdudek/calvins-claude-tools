---
name: product-playbook
description: >-
  Product-management playbooks: strategy, discovery, prioritisation, pricing, competition and
  workshops. Covers OKRs, product strategy, ICP and personas, opportunity solution trees, problem
  framing and reframing, discovery processes, customer interviews and their scripts, interview
  summaries, sentiment analysis, customer journey maps, stakeholder maps, competitor analysis,
  battlecards, positioning workshops, story-mapping and journey workshops, strategy sessions,
  workshop facilitation, prioritisation frameworks, feature-investment cases, unit economics,
  finance metrics, monetisation and pricing advice, go-to-market plans, and feature-request triage.
  Use when someone asks for any of those by name, says "help me prioritise", "what should we build",
  "run a workshop with me", "what is our ICP", "should we raise prices", or wants a PM framework
  applied to a decision. Each topic is one file in references/ — read the index, then load only the
  one you need.
user_invocable: true
metadata:
  version: 1.0.0
  author: OMR Product
---

# Product playbook

Twenty-seven product-management playbooks, one file each. **Read this index, then load exactly one
reference.** Loading the folder costs more than the answer is worth.

These are general craft, adapted from two public MIT-licensed libraries (attribution in each file).
They carry no OMR facts. For anything that must be true about OMR — positioning, pricing, ICP,
proof points — load `omr-context` (OMR AI Kit only, OMR's GTM knowledge; not in cct) alongside, and let it win on every fact.

## Strategy and framing

| Ask | File |
|---|---|
| Set or review OKRs | `references/brainstorm-okrs.md` |
| Define a product strategy | `references/define-product-strategy.md` |
| Run a strategy session | `references/run-strategy-session.md` |
| State the problem precisely | `references/frame-problem.md` |
| The framing feels wrong, try another | `references/reframe-problem.md` |
| Plan go-to-market | `references/plan-go-to-market.md` |

## Customers and discovery

| Ask | File |
|---|---|
| Define the ideal customer profile | `references/define-ideal-customer.md` |
| Run a discovery process | `references/run-discovery-process.md` |
| Prepare a discovery interview | `references/prep-discovery-interview.md` |
| Write the interview script | `references/write-interview-script.md` |
| Summarise an interview | `references/summarize-interview.md` |
| Score sentiment from reviews or tickets | `references/analyze-sentiment.md` |
| Map the customer journey | `references/map-customer-journey.md` |
| Run a journey workshop | `references/run-journey-workshop.md` |
| Build an opportunity solution tree | `references/build-opportunity-tree.md` |

## Prioritisation and money

| Ask | File |
|---|---|
| Choose between competing items | `references/advise-prioritization.md` |
| Triage incoming feature requests | `references/triage-feature-requests.md` |
| Build the case for one feature | `references/evaluate-feature-investment.md` |
| Work out unit economics | `references/calculate-unit-economics.md` |
| Look up a finance metric definition | `references/lookup-finance-metrics.md` |
| Plan monetisation | `references/plan-monetization.md` |
| Advise on a pricing change | `references/advise-pricing.md` |

## Competition and positioning

| Ask | File |
|---|---|
| Analyse competitors | `references/analyze-competitors.md` |
| Write a battlecard | `references/create-battlecard.md` |
| Run a positioning workshop | `references/run-positioning-workshop.md` |

## Workshops and stakeholders

| Ask | File |
|---|---|
| Facilitate any workshop | `references/facilitate-workshop.md` |
| Map stakeholders | `references/map-stakeholders.md` |

`facilitate-workshop` is the interaction protocol the other workshop files build on — session entry
modes, one question per turn, numbered response options. Load it with any of them.

## What did not fold in here

These stayed as their own skills because they carry OMR specifics or a working tool, not general
craft: `cct:ai-ready-issues`, `write-ticket`, `develop-prd`, `break-down-epics`,
`run-story-mapping`, `plan-roadmap`, `analyze-cohorts`, and in `omr-dev`
`posthog-ab-test-setup` and `posthog-ab-test-analyze`.

## Why one skill instead of twenty-seven

Every skill description sits in the context window of every colleague, on every prompt, whether or
not they ever do a story mapping. Twenty-seven descriptions cost about 13,700 characters
permanently; this one costs roughly 900. Nothing was deleted — each playbook is a file above, read
on demand by whoever needs it.
