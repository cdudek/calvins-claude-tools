## Purpose

Guide product managers in choosing the right prioritization framework by asking adaptive questions about product stage, team context, decision-making needs, and stakeholder dynamics. Use this to avoid "framework whiplash" (switching frameworks constantly) or applying the wrong framework. Outputs a recommended framework with implementation guidance tailored to your context.

This is not a scoring calculator -- it's a decision guide that matches prioritization frameworks to your specific situation.

## Key Concepts

### Why This Works
- **Context-aware:** Matches framework to product stage, team maturity, data availability
- **Anti-dogmatic:** No single "best" framework -- it depends on your situation
- **Actionable:** Provides implementation steps, not just framework names

### When to Use / When NOT to Use

**Use when:** Choosing a framework for the first time, switching frameworks, aligning stakeholders, or onboarding new PMs.

**Don't use when:** Current framework works fine, for one-off decisions, or as a substitute for strategic vision.

> See `references/advise-prioritization/references/frameworks-and-scoring.md` for the full landscape of scoring, strategic, and contextual frameworks.

---

## Process

This interactive skill asks **up to 4 adaptive questions**, offering **3-4 enumerated options** at each step.

### Question 1: Product Stage

1. **Pre-product/market fit** — Searching for PMF; high uncertainty, need speed
2. **Early PMF, scaling** — Found initial PMF; growing fast; balancing speed + quality
3. **Mature product, optimization** — Established market; data-driven decisions
4. **Multiple products/platform** — Portfolio; cross-product dependencies; coordination complexity

### Question 2: Team Context

1. **Small team, limited resources** — 3-5 engineers, 1 PM; need simple/fast framework
2. **Cross-functional team, aligned** — Clear goals, good collaboration; can use data-driven frameworks
3. **Multiple stakeholders, misaligned** — Need transparent, consensus-building framework
4. **Large org, complex dependencies** — Need coordination framework

### Question 3: Decision-Making Needs

1. **Too many ideas, unclear which to pursue** — Need filtering framework
2. **Stakeholders disagree on priorities** — Need alignment framework
3. **Lack of data-driven decisions** — Need scoring framework
4. **Hard tradeoffs between strategic bets vs. quick wins** — Need value/effort framework

### Question 4: Data Availability

1. **Minimal data** — New product, no usage metrics (gut-based frameworks)
2. **Some data** — Basic analytics, customer feedback (lightweight scoring)
3. **Rich data** — Usage metrics, A/B tests, clear success metrics (data-driven frameworks)

### Output: Recommended Framework

Deliver a recommendation with: rationale tied to Q1-Q4 answers, implementation steps, example scoring template, alternative framework, common pitfalls for the recommended framework, and reassessment triggers.

> See `references/advise-prioritization/references/frameworks-and-scoring.md` for the full output template with scoring examples.

---

## Key Principles

- **Match framework to stage** — Pre-PMF = ICE or Value/Effort; Scaling = RICE; Mature = Opportunity Scoring or Kano
- **Stick with one framework 6-12 months** — switching every quarter causes confusion and lost time
- **Scores are input, not automation** — PM judgment overrides scores when strategic context demands it
- **Score collaboratively** — PM, design, and engineering score together for buy-in and accuracy
- **Any framework beats no framework** — even imperfect structure beats HiPPO-driven chaos

> See `references/advise-prioritization/references/examples-and-pitfalls.md` for worked examples (early PMF + RICE, pre-PMF + RICE mismatch) and 5 common pitfalls.

---

## References

### Related Skills
- `cct:product-epic-analyze` — prioritized epics are split into vertical slices
- `cct:product-workitem-write` — prioritized items become work items
- `cct:product-roadmap-write` — sequences the prioritized items

### External Frameworks
- Intercom, *RICE Prioritization* (2016) — Origin of RICE framework
- Sean McBride, *ICE Scoring* (2012) — Lightweight prioritization
- Luke Hohmann, *Innovation Games* (2006) — Buy-a-Feature and other collaborative methods
- Noriaki Kano, *Kano Model* (1984) — Customer satisfaction framework

---

## Sources

| Source | Origin |
|--------|--------|
| [deanpeters/Product-Manager-Skills](https://github.com/deanpeters/Product-Manager-Skills) — skills/prioritization-advisor | Original skill |
