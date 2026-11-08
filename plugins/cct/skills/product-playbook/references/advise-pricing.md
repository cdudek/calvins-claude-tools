## Purpose

Evaluate the **financial impact** of pricing changes (price increases, new tiers, add-ons, discounts) using ARPU/ARPA analysis, conversion impact, churn risk, NRR effects, and CAC payback implications. Use this to make data-driven go/no-go decisions on proposed pricing changes with supporting math and risk assessment.

**What this is:** Financial impact evaluation for pricing decisions you're already considering.

**What this is NOT:** Comprehensive pricing strategy design, value-based pricing frameworks, willingness-to-pay research, competitive positioning, psychological pricing, packaging architecture, or monetization model selection.

This skill assumes you have a specific pricing change in mind and need to evaluate its financial viability.

## Key Concepts

### The Pricing Impact Framework

A systematic approach to evaluate pricing changes financially:

1. **Revenue Impact** — How does this change ARPU/ARPA? (direct lift vs. loss from reduced conversion/churn)
2. **Conversion Impact** — How does this affect trial-to-paid or sales conversion?
3. **Churn Risk** — Will existing customers leave? (grandfathering, segment sensitivity, elasticity)
4. **Expansion Impact** — Does this create or block upsell/cross-sell opportunities?
5. **CAC Payback Impact** — How does pricing change affect unit economics and LTV:CAC?

### When to Use / When NOT to Use

**Use when:** You have a specific pricing change to evaluate, need to quantify trade-offs, compare options, or present impact to leadership.

**Don't use when:** Designing pricing strategy from scratch, haven't validated WTP, don't have baseline metrics, or change is trivial (<5% price change, <10% of customers).

---

## Process

This interactive skill asks **up to 4 adaptive questions**, offering **3-5 enumerated options** at decision points.

### Step 0: Gather Context

Ask for current pricing (ARPU/ARPA, tiers, churn rate, conversion rate), the proposed change (type, new pricing, affected segment), and business context (total customers/MRR, CAC, NRR). Accept estimates.

### Step 1: Identify Pricing Change Type

Classify into one of 6 types: price increase, new premium tier, paid add-on, usage-based pricing, discount strategy, or packaging change. Ask type-specific follow-up questions.

> See `references/pricing-change-types.md` for detailed question flows per change type.

### Step 2: Assess Expected Impact

Quantify revenue impact (ARPU lift), conversion impact, churn risk, and expansion impact. Gather estimates and model conservative/base/optimistic scenarios.

### Step 3: Evaluate Current State

Collect baseline metrics (MRR/ARR, customers, ARPU, churn, NRR, CAC, LTV) plus growth and competitive context.

### Step 4: Deliver Recommendations

Synthesize all inputs into one of 4 recommendation patterns:

1. **Implement broadly** — Strong financial case (>10% ARPU lift, <5% churn risk)
2. **Test first (A/B)** — Uncertain impact, moderate risk, test with subset
3. **Modify approach** — Original proposal has risks, suggest alternatives
4. **Don't change pricing** — Risks outweigh benefits

> See `references/recommendation-patterns.md` for full recommendation templates.

### Step 5: Sensitivity Analysis (Optional)

Offer what-if scenarios: optimistic/pessimistic cases, breakeven analysis, comparison to alternatives.

---

## Key Principles

- **Always model churn impact** — never evaluate price increases without factoring churn-driven revenue loss
- **Grandfather existing customers by default** — raising prices for everyone simultaneously is almost always wrong
- **Test with statistical power** — 100+ customers per cohort, 60-90 days minimum
- **Tie price changes to value** — customers accept increases tied to improvements, not "we need revenue"
- **Calculate CAC payback** — higher ARPU with lower conversion can make payback worse
- **Communicate 30-60 days in advance** — surprises cause churn and reputation damage

> See `references/examples-and-pitfalls.md` for worked examples and 10 common pitfalls.

---

## References

### Related Skills
- `saas-revenue-growth-metrics` — ARPU, ARPA, churn, NRR metrics used in pricing analysis
- `saas-economics-efficiency-metrics` — CAC payback impact of pricing changes
- `finance-metrics-quickref` — Quick lookup for pricing-related formulas
- `feature-investment-advisor` — Evaluates whether to build features that enable pricing changes
- `business-health-diagnostic` — Broader business context for pricing decisions

### External Frameworks (Comprehensive Pricing Strategy)
These are OUTSIDE the scope of this skill but relevant for broader pricing work:

- **Value-Based Pricing** — Price based on value delivered, not cost
- **Van Westendorp Price Sensitivity** — WTP research methodology
- **Conjoint Analysis** — Feature-to-price trade-off research
- **Good-Better-Best Packaging** — Tier architecture design
- **Price Anchoring & Decoy Pricing** — Psychological pricing tactics
- **Patrick Campbell (ProfitWell):** Pricing research and benchmarks

---

## Sources

| Source | Origin |
|--------|--------|
| [deanpeters/Product-Manager-Skills](https://github.com/deanpeters/Product-Manager-Skills) — skills/finance-based-pricing-advisor | Original skill |
