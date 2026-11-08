---
name: product-playbook
description: "Index of product-management methods and their shared guidance: OKRs, product strategy canvas, go-to-market, discovery interviews and scripts, opportunity solution trees, sentiment analysis, feature-investment cases, unit economics, finance metrics, monetisation, pricing, competitor analysis, battlecards, positioning workshops, workshop facilitation and stakeholder maps. Grounds other product work with general craft and creates nothing itself. Use when someone asks 'which product method fits', 'what is in the product playbook', 'how do we frame a pricing change', 'what does unit economics mean here' or needs a PM framework explained before deciding. Skip for: running a strategy cycle (cct:product-strategy-run), running a discovery cycle (cct:product-discovery-run), problem statements (cct:product-problem-write), audience definitions (cct:product-audience-write), priorities (cct:product-priorities-analyze), journey maps (cct:ux-journey-create)."
user_invocable: true
metadata:
  version: 2.0.0
---

# Product playbook

Eighteen product-management methods, one file each, plus the shared rules they follow. This skill is knowledge: it supplies method and vocabulary to other work and does not author an artifact itself. **Read this index, then load exactly one reference.** Loading the folder costs more than the answer is worth.

The methods are general craft, adapted from two public MIT-licensed libraries (attribution in each file). They carry no company facts. For anything that must be true about the company (positioning, pricing, ICP, proof points) use the repo's own context docs and let them win on every fact.

## Who owns what

Process skills coordinate a whole cycle and delegate to the atomic skills; the atomic skills author one artifact. Use them instead of a reference when the job is the artifact or the cycle.

- **Strategy cycle:** `cct:product-strategy-run`
- **Discovery cycle:** `cct:product-discovery-run`
- **Problem statement, framing and reframing:** `cct:product-problem-write`
- **Ideal customer and audience:** `cct:product-audience-write`
- **Choosing between competing items, triaging feature requests:** `cct:product-priorities-analyze`
- **Customer journey map and journey workshop:** `cct:ux-journey-create`

Neighbouring product skills with their own artifacts: `cct:product-prd-write`, `cct:product-roadmap-write`, `cct:product-epic-analyze`, `cct:product-storymap-create`, `cct:product-workitem-write` and `cct:data-cohorts-analyze`; `cct:posthog-manage` for experiments.

## Methods in this playbook

### Strategy and planning

| Ask | File |
|---|---|
| Set or review OKRs | `references/brainstorm-okrs.md` |
| Define a product strategy (9-section canvas) | `references/define-product-strategy.md` |
| Plan go-to-market | `references/plan-go-to-market.md` |

### Discovery and research

| Ask | File |
|---|---|
| Prepare a discovery interview | `references/prep-discovery-interview.md` |
| Write the interview script | `references/write-interview-script.md` |
| Summarise an interview | `references/summarize-interview.md` |
| Score sentiment from reviews or tickets | `references/analyze-sentiment.md` |
| Build an opportunity solution tree | `references/build-opportunity-tree.md` |

### Investment and money

| Ask | File |
|---|---|
| Build the case for one feature | `references/evaluate-feature-investment.md` |
| Work out unit economics | `references/calculate-unit-economics.md` |
| Look up a finance metric definition | `references/lookup-finance-metrics.md` |
| Plan monetisation | `references/plan-monetization.md` |
| Advise on a pricing change | `references/advise-pricing.md` |

### Competition and positioning

| Ask | File |
|---|---|
| Analyse competitors | `references/analyze-competitors.md` |
| Write a battlecard | `references/create-battlecard.md` |
| Run a positioning workshop | `references/run-positioning-workshop.md` |

### Workshops and stakeholders

| Ask | File |
|---|---|
| Facilitate any workshop | `references/facilitate-workshop.md` |
| Map stakeholders | `references/map-stakeholders.md` |

## Shared guidance

- `references/facilitate-workshop.md` is the interaction protocol every workshop-style method builds on: session entry modes (guided, context dump, best guess), one question per turn, numbered response options. Load it together with any workshop method.
- Methods describe how to think and what a good output contains. Put company facts in only from the repo's own context docs; never invent a metric, price or customer quote.
- Name the decision the method serves before applying it. A framework with no decision behind it is analysis for its own sake.

## Why one skill instead of many

Every skill description sits in every colleague's context on every prompt. One index description replaces eighteen method descriptions; each method is a file read on demand.
