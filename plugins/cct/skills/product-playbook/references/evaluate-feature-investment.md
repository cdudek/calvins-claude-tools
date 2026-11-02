## Purpose

Guide product managers through evaluating whether to build a feature based on financial impact analysis. Use this to make data-driven prioritization decisions by assessing revenue connection (direct or indirect), cost structure (dev + COGS + OpEx), ROI calculation, and strategic value -- then deliver actionable build/don't build recommendations with supporting math.

This is not a generic prioritization framework -- it's a financial lens for feature decisions that complements other prioritization methods (RICE, value vs. effort, user research). Use when financial impact is a key decision factor.

## Key Concepts

### The Feature Investment Framework

1. **Revenue Connection** — Direct monetization (new tier, add-on, usage) or indirect (retention, conversion, expansion enablement)
2. **Cost Structure** — Development cost (one-time) + COGS impact (ongoing infra) + OpEx impact (ongoing support)
3. **ROI Calculation** — Revenue impact / development cost, factoring gross margin not just revenue
4. **Strategic Value** — Non-financial value that might override pure ROI (competitive moat, platform enabler, market positioning, compliance)

### When to Use / When NOT to Use

**Use when:** Prioritizing features with quantifiable impact, evaluating expensive features (>1 engineer-month), making build/buy/partner decisions, defending prioritization to stakeholders.

**Don't use when:** Feature is table stakes, impact is purely qualitative, problem isn't validated yet, or feature is <1 week of work.

---

## Process

This interactive skill asks **up to 4 adaptive questions**, offering **3-5 enumerated options** at decision points.

### Step 0: Gather Context

Ask for feature description, target segment, business context (MRR/ARR, ARPU, churn, gross margin), and constraints (dev cost estimate, ongoing COGS/OpEx).

### Step 1: Identify Revenue Connection

Classify into one of 5 types: direct monetization, retention improvement, conversion improvement, expansion enabler, or no direct revenue impact. Ask type-specific follow-up questions and calculate projected impact.

> See `references/revenue-and-cost-analysis.md` for detailed question flows and formulas per revenue type.

### Step 2: Assess Cost Structure

Gather development cost (team x time), ongoing COGS, and OpEx. Calculate contribution margin. Flag if COGS >20% of projected revenue or ongoing costs are unsustainable.

### Step 3: Evaluate Constraints and Timing

Classify constraints: competitive threat (adds urgency), limited capacity (compare ROI across backlog), dependencies (flag risk, suggest sequencing), or no constraints.

### Step 4: Deliver Recommendations

Synthesize all inputs into one of 4 recommendation patterns:

1. **Build now** — Strong ROI (>3:1 direct or >10:1 LTV), positive margin, no red flags
2. **Build for strategic reasons** — Marginal ROI (<2:1) but high strategic value
3. **Don't build** — Poor ROI (<1:1), margin-diluting, no strategic case
4. **Build later** — Uncertain assumptions, validate first with research

> See `references/recommendation-patterns.md` for full recommendation templates.

### Step 5: Follow-Up

Offer detailed math breakdown, feature comparison, assumption adjustment, or export.

---

## Key Principles

- **Use contribution margin, not revenue** — $1M revenue at 20% margin is $200K profit, not $1M
- **Check payback vs. customer lifetime** — if payback exceeds average lifetime, you never recover
- **Use conservative adoption estimates** — 10-20% for add-ons, not 100%
- **Validate before building** — interview churned customers, confirm this addresses top churn reasons
- **Compare opportunity cost** — a 2:1 ROI feature is wrong if 10:1 options exist in the backlog
- **Define "strategic" precisely** — competitive moat, platform enabler, or compliance; not a catch-all excuse
- **Weight requests by revenue impact** — 10 enterprise customers > 100 SMB if enterprise is your strategy

> See `references/examples-and-pitfalls.md` for worked examples (time tracking add-on, data export, dark mode) and 10 common pitfalls.

---

## References

### Related Skills
- `saas-revenue-growth-metrics` — Revenue, ARPU, churn, NRR metrics used in impact calculations
- `saas-economics-efficiency-metrics` — ROI, payback, contribution margin calculations
- `finance-metrics-quickref` — Quick lookup for formulas and benchmarks
- `acquisition-channel-advisor` — Similar ROI framework for channel decisions
- `finance-based-pricing-advisor` — Pricing impact analysis for monetization features

### External Frameworks
- **RICE Prioritization** — Combines Reach, Impact, Confidence, Effort (this skill adds financial lens)
- **Value vs. Effort Matrix** — This skill quantifies "value" financially
- **Jobs-to-be-Done** — Understand customer problems before evaluating financial impact
- **Opportunity Solution Tree (Teresa Torres)** — Map opportunities before calculating ROI

---

## Sources

| Source | Origin |
|--------|--------|
| [deanpeters/Product-Manager-Skills](https://github.com/deanpeters/Product-Manager-Skills) — skills/feature-investment-advisor | Original skill |
