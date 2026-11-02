# Feature Investment Examples and Common Pitfalls

## Examples

### Example 1: Direct Monetization (Time Tracking Add-On)

**User:** "We're considering building time tracking as a paid add-on."

**Agent:** [Gathers context]

**User provides:**
- Current: 1,000 customers, $500 ARPU, 80% gross margin
- Feature: Time tracking add-on, $10/user/month
- Dev cost: $100K (2 engineers x 3 months)
- Adoption estimate: 20% of customers

**Agent calculates:**
- Customers with 10 users/account avg = 1,000 accounts x 10 users = 10,000 users
- Adoption: 20% of users = 2,000 users
- Revenue: 2,000 x $10 = $20K/month = $240K/year
- Margin: $240K x 80% = $192K gross profit/year
- ROI: $192K / $100K = 1.92:1 in year 1
- Payback: $100K / $20K = 5 months

**Agent recommends:**

"**Build now** — Positive ROI with fast payback

**Revenue Impact:** $240K/year (conservative 20% adoption)
**ROI:** 1.92:1 in year 1, 3.8:1 in year 2
**Payback:** 5 months

**Why this works:**
- Fast payback (5 months) means low risk
- 80% gross margin on add-on revenue
- 20% adoption is conservative (test willingness-to-pay)

**Next steps:**
1. Survey customers: who would pay $10/user for time tracking?
2. Build MVP with core time tracking only
3. Beta with 50 customers before broad launch
4. Track adoption rate vs. 20% target"

---

### Example 2: Retention Feature (Data Export)

**User:** "We're losing customers because they can't export their data easily. Should we build a comprehensive export feature?"

**Agent:** [Gathers context]

**User provides:**
- Current: $2M MRR, 500 customers, $4K ARPA, 5% monthly churn
- Feature: Full data export (CSV, API, scheduled exports)
- Dev cost: $150K (3 engineers x 2 months)
- Churn context: 30% of churned customers cited data export as a reason

**Agent calculates:**
- Current annual churn: ~46% (5% monthly compounded)
- Customers churned annually: 500 x 46% = 230 customers
- Customers churned due to export issue: 230 x 30% = 69 customers
- MRR lost: 69 x $4K = $276K MRR lost/year = $3.3M ARR

**If feature reduces this by 50%:**
- Churn prevented: 35 customers/year
- MRR saved: $140K/year
- LTV impact (assuming 24-month lifetime): $140K x 24 = $3.36M

**Agent calculates ROI:**
- Investment: $150K
- LTV saved: $3.36M (conservative 50% reduction)
- ROI: $3.36M / $150K = 22.4:1

**Agent recommends:**

"**Build immediately** — Exceptional ROI on retention

**Impact:**
- Prevents ~35 customer churns/year
- Saves $140K MRR annually
- LTV impact: $3.36M over customer lifetime
- ROI: 22:1 (exceptional)

**Why this is a no-brainer:**
- 30% of churn cites this gap (validated problem)
- Even if you only prevent 25% (not 50%), ROI is still 11:1
- Retention improvements compound (reduces future churn too)

**Next steps:**
1. Interview churned customers to validate export was primary reason
2. Build core export (CSV, API) first
3. Measure churn rate change after launch (target: 5% to 4.5%)
4. Add scheduled exports if adoption is high"

---

### Example 3: Poor ROI Feature (Dark Mode)

**User:** "Users are requesting dark mode. Should we prioritize it?"

**Agent:** [Gathers context]

**User provides:**
- Current: $500K MRR, 2,000 customers, $250 ARPA, 3% monthly churn, 75% gross margin
- Feature: Full dark mode across product
- Dev cost: $80K (2 designers + 2 engineers x 1 month)
- Revenue connection: Indirect — may improve retention slightly

**Agent asks:** "What evidence do you have that dark mode will reduce churn?"

**User:** "Feature requests from 50 users. No data on churn impact."

**Agent calculates:**
- 50 feature requests out of 2,000 customers = 2.5% of base
- No validated churn impact
- Dev cost: $80K
- Optimistic scenario: Prevents 5 churns/year (2.5% of base)
- MRR saved: 5 x $250 = $1,250/month = $15K/year
- LTV impact (24-month lifetime): $15K x 24 = $360K

**ROI: $360K / $80K = 4.5:1** (looks okay, but based on weak assumptions)

**Agent recommends:**

"**Build later** — Weak evidence for ROI

**Current case:**
- Revenue impact: $15K/year (optimistic)
- Development cost: $80K
- ROI: 4.5:1 (assumes dark mode prevents churn)

**Problem:**
- Only 50 users requested this (2.5% of base)
- No evidence dark mode reduces churn
- Churn interviews don't mention this as a top reason

**Alternative approach:**
1. **Survey churned customers** — Is dark mode in top 5 churn reasons?
2. **Test demand** — Ask trial users: "Would dark mode affect your decision to convert?"
3. **Reduce scope** — Build basic dark mode (20% cost) as experiment

**Better features to consider:**
- If retention is priority: Interview churned customers, find top 3 churn drivers
- If revenue is priority: Focus on expansion features (upsell, add-ons)

**Decision criteria to build:**
- If churn interviews show dark mode is top 3 reason: build
- If conversion research shows 10%+ impact: build
- Otherwise: deprioritize"

---

## Common Pitfalls

### Pitfall 1: Confusing Revenue with Profit
**Symptom:** "This feature will generate $1M in revenue!" (ignoring $800K COGS)

**Consequence:** $1M revenue at 20% margin is worth $200K profit, not $1M. Feature looks great until you factor in costs.

**Fix:** Always calculate contribution margin. Use `Revenue x Margin %`, not just revenue.

---

### Pitfall 2: Ignoring Payback Period
**Symptom:** "ROI is 5:1, let's build!" (but payback is 36 months and customers churn at 24 months)

**Consequence:** You never recover the investment because customers leave before payback.

**Fix:** Check payback period. Must be shorter than average customer lifetime.

---

### Pitfall 3: Overestimating Adoption
**Symptom:** "100% of customers will use this paid add-on!"

**Consequence:** Real adoption is 10-20%. Revenue projections are 5-10x too high.

**Fix:** Use conservative adoption estimates (10-20% for add-ons). Validate with willingness-to-pay research.

---

### Pitfall 4: Building Without Validation
**Symptom:** "We think this will reduce churn" (no customer interviews)

**Consequence:** You build a feature that doesn't address real churn reasons. Churn stays flat.

**Fix:** Interview churned customers first. Validate that this feature addresses top 3 churn reasons.

---

### Pitfall 5: Ignoring Opportunity Cost
**Symptom:** "This feature has 2:1 ROI, let's build!" (other features have 10:1 ROI)

**Consequence:** You build a mediocre feature while better options sit in the backlog.

**Fix:** Compare ROI across features. Build highest-ROI features first (unless strategic value overrides).

---

### Pitfall 6: Strategic Value as Excuse
**Symptom:** "ROI is terrible but it's strategic!" (no clear strategy)

**Consequence:** "Strategic" becomes a catch-all for building low-value features.

**Fix:** Define what "strategic" means (competitive moat, platform enabler, compliance). If it doesn't fit, it's not strategic.

---

### Pitfall 7: Margin Dilution Blindness
**Symptom:** "This feature adds $500K revenue!" (but COGS is $400K)

**Consequence:** Your gross margin drops from 80% to 60%. Feature destroys unit economics.

**Fix:** Calculate contribution margin. If margin is <50%, reconsider or charge a premium.

---

### Pitfall 8: Celebrating Vanity Metrics
**Symptom:** "This feature will increase engagement!" (but not revenue or retention)

**Consequence:** You build features that feel good but don't impact business outcomes.

**Fix:** Tie features to revenue or retention. Engagement is a leading indicator, not an outcome.

---

### Pitfall 9: Forgetting Time Value of Money
**Symptom:** "This feature pays back in 5 years"

**Consequence:** $1 in 5 years is worth ~$0.65 today (at 9% discount rate). ROI is overstated.

**Fix:** For long payback periods (>24 months), use NPV (net present value) to discount future cash flows.

---

### Pitfall 10: Building Features for Loud Minorities
**Symptom:** "50 customers requested this!" (out of 10,000)

**Consequence:** You optimize for 0.5% of your base while ignoring the other 99.5%.

**Fix:** Weight feature requests by revenue impact or customer segment. 10 enterprise customers > 100 SMB customers if enterprise is your strategy.
