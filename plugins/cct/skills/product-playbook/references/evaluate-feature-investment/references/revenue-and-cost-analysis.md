# Revenue Connection and Cost Structure — Detailed Question Flows

## Step 1: Identify Revenue Connection

**Agent asks:**

"How does this feature impact revenue? Choose the option that best describes the revenue connection:

1. **Direct monetization (new revenue stream)** — We'll charge for this (new pricing tier, paid add-on, usage-based fee)
2. **Retention improvement (reduce churn)** — Addresses key churn reason; keeps customers from leaving
3. **Conversion improvement (trial-to-paid)** — Helps convert free/trial users to paid customers
4. **Expansion enabler (upsell/cross-sell)** — Creates upsell path or drives usage-based expansion
5. **No direct revenue impact** — Table stakes, platform improvement, or strategic value only

Choose a number, or describe a custom revenue connection."

**Based on selection, agent adapts:**

**If 1 (Direct monetization):**
- "What pricing are you considering?"
- "What % of customers do you expect to adopt this?" (conservative, base, optimistic)
- Calculate: `Potential Monthly Revenue = Customer Base x Adoption Rate x Price`

**If 2 (Retention improvement):**
- "What % of churn does this feature address?" (e.g., "30% of churned customers cited this gap")
- "What churn reduction do you expect?" (e.g., "5% to 4% monthly churn")
- Calculate: `LTV Impact = Increase in Customer Lifetime x Customer Base x ARPU x Margin`

**If 3 (Conversion improvement):**
- "Current trial-to-paid conversion rate?"
- "Expected conversion lift?" (e.g., "20% to 25% conversion")
- Calculate: `Additional MRR = Trial Users x Conversion Lift x ARPU`

**If 4 (Expansion enabler):**
- "What expansion opportunity does this create?" (upsell tier, usage growth, add-on)
- "What % of customers will expand?"
- Calculate: `Expansion MRR = Customer Base x Expansion Rate x ARPU Increase`

**If 5 (No direct revenue impact):**
- Skip to strategic value assessment

---

## Step 2: Assess Cost Structure

**Agent asks:**

"What's the cost structure for this feature?

**Development cost (one-time):**
- Team size: ___ engineers
- Time estimate: ___ weeks/months
- Estimated dev cost: $___

**Ongoing costs (if any):**
- COGS impact: $___ /month (hosting, infrastructure, processing)
- OpEx impact: $___ /month (support, maintenance)

If no ongoing costs, enter $0."

**Agent calculates:**
- One-time investment: Development cost
- Ongoing monthly cost: COGS + OpEx
- Contribution margin impact: `(Revenue - COGS) / Revenue`

**Agent flags:**
- If COGS is >20% of projected revenue: "Warning: This feature significantly dilutes margins"
- If ongoing costs are high relative to revenue: "Warning: Consider if this is sustainable"

---

## Step 3: Evaluate Constraints and Timing

**Agent asks:**

"What constraints or timing considerations apply?

1. **Time-sensitive competitive threat** — Competitor launched this; we're losing deals
2. **Limited budget/team capacity** — We can only build one major feature this quarter
3. **Dependencies on other work** — Requires platform improvements or other features first
4. **No major constraints** — We have capacity and flexibility

Choose a number, or describe your constraints."

**Based on selection:**

**If 1 (Competitive threat):**
- Strategic value increases (churn prevention)
- Urgency factor in recommendation

**If 2 (Limited capacity):**
- Compare ROI against other features in backlog
- Recommend stack ranking

**If 3 (Dependencies):**
- Flag dependency risk
- Suggest sequencing

**If 4 (No constraints):**
- Proceed to recommendations

---

## Step 5: Allow Follow-Up Questions

**Agent offers:**

"Do you want to:
1. See the detailed math breakdown
2. Compare this to another feature
3. Adjust assumptions (pricing, adoption, cost)
4. Export recommendation summary

Or, ask any follow-up questions."

**Agent can:**
- Show detailed calculations
- Sensitivity analysis (what if adoption is 2x? 0.5x?)
- Compare multiple features side-by-side
- Export summary for stakeholders
