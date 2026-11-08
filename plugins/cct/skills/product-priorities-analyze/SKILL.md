---
name: product-priorities-analyze
description: "Returns comparative priorities for roadmap and strategy decisions, writing nothing back: recommends the prioritization framework that fits the product stage, team, decision need and data (ICE, RICE, value/effort, Kano, opportunity scoring) with implementation steps and reassessment triggers, or triages a pile of customer feature requests into themes and a top three by impact, effort, risk and strategic alignment, with assumptions to test. Use when the user says 'which prioritization framework', 'triage feature requests', 'score these with RICE', 'rank these opportunities', 'what should we build first'. Skip for: placing the chosen priorities on a timeline - use cct:product-roadmap-write. Skip for: splitting a prioritized epic into slices - use cct:product-epic-analyze."
allowed-tools: "Read"
user_invocable: true
---

# Analyze priorities

Insight out, nothing written back: return the comparison and recommendation in the reply. Do not create files, edit trackers or change a roadmap; the owner of that job acts on the answer (`cct:product-roadmap-write` sequences it, `cct:product-prd-write` records it, `cct:product-epic-analyze` slices it).

Principle: prioritize opportunities (problems), not features, and never let customers design the solution. Scores are input, not automation; PM judgment overrides a score when strategy demands it.

## Choose the mode

- **Choose a framework** (`references/advise-prioritization.md`): up to four adaptive questions (product stage, team context, decision-making need, data availability), each with 3 to 4 enumerated options. Output a recommended framework with the rationale tied to the answers, implementation steps, an example scoring template, an alternative, the common pitfalls of that framework and when to reassess. Landscape of frameworks and the output template: `references/advise-prioritization/references/frameworks-and-scoring.md`; worked examples and five pitfalls: `references/advise-prioritization/references/examples-and-pitfalls.md`. Match framework to stage (pre-PMF: ICE or value/effort; scaling: RICE; mature: opportunity scoring or Kano), stay with one for 6 to 12 months, score collaboratively.
- **Triage requests** (`references/triage-feature-requests.md`): given a product goal and feature requests (pasted, or a spreadsheet or CSV to read), confirm the goal, group the requests into named themes, assess strategic alignment per theme, and prioritize the top three on impact (value and users affected), effort, risk and strategic alignment. For each: rationale, alternative solutions, high-risk assumptions and the cheapest way to test them. Use the Opportunity Score (importance x (1 - satisfaction), normalized to 0-1) for customer-reported problems.

When the user has both a pile and no framework, choose the framework first, then triage with it.

## Rules

- Ask only what is missing; if the user wants a single-shot answer, skip the multi-turn questions and state the assumptions you made.
- Name the evidence behind every ranking. Without data, say the ranking is judgment and which data would change it.
- Any framework beats no framework, but switching every quarter ("framework whiplash") costs more than a mediocre fit.
