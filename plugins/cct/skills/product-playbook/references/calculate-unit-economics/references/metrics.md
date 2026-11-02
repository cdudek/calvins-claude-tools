# Unit Economics Metrics Reference

## Unit Economics Family

Metrics that measure profitability at the customer level—the foundation of sustainable SaaS.

**Gross Margin** — Percentage of revenue remaining after direct costs (COGS).
- **Why PMs care:** A feature that generates $1M revenue at 80% margin is worth far more than $1M at 30% margin. Margin determines which features to prioritize.
- **Formula:** `(Revenue - COGS) / Revenue × 100`
- **COGS includes:** Hosting, infrastructure, payment processing, customer onboarding costs
- **Benchmark:** SaaS 70-85% good; <60% concerning

**CAC (Customer Acquisition Cost)** — Total cost to acquire one customer.
- **Why PMs care:** Shapes entire go-to-market strategy. Determines which channels are viable and how much you can invest in product-led growth.
- **Formula:** `Total Sales & Marketing Spend / New Customers Acquired`
- **Benchmark:** Varies by model—Enterprise $10K+ ok; SMB <$500 target
- **Include:** Marketing spend, sales salaries, tools, commissions

**LTV (Lifetime Value)** — Total revenue expected from one customer over their lifetime.
- **Why PMs care:** Tells you what you can afford to spend on acquisition. Higher LTV enables premium channels and longer payback periods.
- **Formula (simple):** `ARPU × Average Customer Lifetime (months)`
- **Formula (better):** `ARPU × Gross Margin % / Churn Rate`
- **Formula (advanced):** Account for expansion, discount rates, cohort-specific retention
- **Benchmark:** Must be 3x+ CAC; varies by segment

**LTV:CAC Ratio** — Efficiency of customer acquisition spending.
- **Why PMs care:** Is growth sustainable or are you buying revenue at a loss? Determines when to scale vs. optimize.
- **Formula:** `LTV / CAC`
- **Benchmark:** 3:1 healthy; <1:1 unsustainable; >5:1 might be underinvesting
- **Note:** This ratio alone doesn't tell the full story—also need payback period

**Payback Period** — Months to recover CAC from customer revenue.
- **Why PMs care:** Cash efficiency. Faster payback = reinvest sooner. Slow payback can kill growth even with good LTV:CAC.
- **Formula:** `CAC / (Monthly ARPU × Gross Margin %)`
- **Benchmark:** <12 months great; 12-18 ok; >24 months concerning
- **Critical:** Must have cash to sustain payback period

**Contribution Margin** — Revenue remaining after ALL variable costs (not just COGS).
- **Why PMs care:** True unit profitability. Includes support, processing fees, variable OpEx.
- **Formula:** `(Revenue - All Variable Costs) / Revenue × 100`
- **Variable costs:** COGS + support + payment processing + variable customer success
- **Benchmark:** 60-80% good for SaaS; <40% concerning

**Gross Margin Payback** — Payback period using actual profit, not revenue.
- **Why PMs care:** More accurate than simple payback. Shows true cash recovery time.
- **Formula:** `CAC / (Monthly ARPU × Gross Margin %)`
- **Benchmark:** Typically 1.5-2x longer than simple revenue payback

**CAC Payback by Channel** — Compare payback across acquisition channels.
- **Why PMs care:** Not all channels are created equal. Optimize channel mix based on payback efficiency.
- **Formula:** Calculate CAC and payback separately for each channel
- **Use:** Allocate budget to faster-payback channels when cash-constrained

---

## Capital Efficiency Family

Metrics that measure how efficiently you use cash to grow the business.

**Burn Rate** — Cash consumed per month.
- **Why PMs care:** Determines what you can build and when you need funding. High burn requires aggressive revenue growth.
- **Formula (Gross Burn):** `Monthly Cash Spent (all expenses)`
- **Formula (Net Burn):** `Monthly Cash Spent - Monthly Revenue`
- **Benchmark:** Net burn <$200K manageable for early stage; >$500K needs clear path to revenue

**Runway** — Months until cash runs out.
- **Why PMs care:** Literal survival metric. Dictates timeline for milestones, fundraising, profitability.
- **Formula:** `Cash Balance / Monthly Net Burn`
- **Benchmark:** 12+ months good; 6-12 manageable; <6 months crisis mode
- **Rule:** Raise when you have 6-9 months runway, not 3 months

**OpEx (Operating Expenses)** — Costs to run the business (excluding COGS).
- **Why PMs care:** Your team's salaries live here. Where "efficiency" cuts happen during downturns.
- **Categories:** Sales & Marketing (S&M), Research & Development (R&D), General & Administrative (G&A)
- **Benchmark:** Should grow slower than revenue as you scale (operating leverage)

**Net Income (Profit Margin)** — Actual profit or loss after all expenses.
- **Why PMs care:** True bottom line. Are you making money? Can you self-fund growth?
- **Formula:** `Revenue - All Expenses (COGS + OpEx)`
- **Benchmark:** Early SaaS often negative (growth mode); mature should be 10-20%+ margin

**Working Capital Impact** — Cash timing differences between revenue recognition and cash collection.
- **Why PMs care:** Annual contracts paid upfront boost cash. Monthly billing delays cash. Affects runway calculations.
- **Example:** $1M annual contract paid upfront = $1M cash now, not $83K/month
- **Use:** Understand cash vs. revenue timing when planning runway

---

## Efficiency Ratios Family

Composite metrics that measure growth vs. profitability trade-offs.

**Rule of 40** — Growth rate + profit margin should exceed 40%.
- **Why PMs care:** Framework for balancing growth vs. efficiency. Guides when to prioritize profitability over growth.
- **Formula:** `Revenue Growth Rate % + Profit Margin %`
- **Benchmark:** >40 healthy; 25-40 acceptable; <25 concerning
- **Example:** 60% growth + (-20%) margin = 40 (healthy growth-mode SaaS)
- **Example:** 20% growth + 25% margin = 45 (healthy mature SaaS)

**Magic Number** — Sales & marketing efficiency.
- **Why PMs care:** Is your GTM engine working? Should you scale spend or optimize first?
- **Formula:** `(Current Quarter Revenue - Previous Quarter Revenue) × 4 / Previous Quarter S&M Spend`
- **Benchmark:** >0.75 efficient; 0.5-0.75 ok; <0.5 fix before scaling
- **Note:** "× 4" annualizes quarterly revenue change

**Operating Leverage** — How revenue growth compares to cost growth.
- **Why PMs care:** Are you scaling efficiently? Revenue should grow faster than costs.
- **Measure:** Revenue growth rate vs. OpEx growth rate over time
- **Good:** Revenue growth 50%, OpEx growth 30% (positive leverage)
- **Bad:** Revenue growth 20%, OpEx growth 40% (negative leverage)

**Unit Economics** — General term for profitability of each "unit" (customer, seat, transaction).
- **Why PMs care:** Is the business model fundamentally viable at the unit level?
- **Calculate:** Revenue per unit - Cost per unit
- **Requirement:** Positive contribution required; aim for >$0 after all variable costs

---

## When to Use These Metrics

**Use these when:**
- Evaluating whether to scale acquisition (LTV:CAC, payback, magic number)
- Deciding feature investments (margin impact, contribution to LTV)
- Planning runway and fundraising (burn rate, runway, Rule of 40)
- Comparing customer segments or channels (unit economics by segment)
- Board/investor reporting (Rule of 40, magic number, LTV:CAC)
- Choosing between growth and profitability (Rule of 40 trade-offs)

**Don't use these when:**
- Making decisions without revenue context (pair with revenue growth metrics)
- Comparing across wildly different business models without normalization
- Early product discovery (pre-revenue focus on PMF, not unit economics)
- Short-term tactical decisions (use engagement metrics, not LTV)
