# Formulas, Calculations & Examples

## Step 1: Calculate Unit Economics

Use the templates in `template.md` to calculate your unit economics metrics.

### Gross Margin
```
Gross Margin = (Revenue - COGS) / Revenue × 100

COGS includes:
- Hosting & infrastructure costs
- Payment processing fees
- Customer onboarding costs
- Direct delivery costs
```

**Example:**
- Revenue: $1,000,000
- COGS: $200,000 (hosting $120K, processing $50K, onboarding $30K)
- Gross Margin = ($1M - $200K) / $1M = 80%

**Quality checks:**
- Is gross margin improving as you scale? (Should benefit from economies of scale)
- Which products/features have highest margins? (Prioritize those)
- Are margins >70%? (SaaS should be high-margin)

---

### CAC (Customer Acquisition Cost)
```
CAC = Total Sales & Marketing Spend / New Customers Acquired

Include in S&M spend:
- Marketing salaries & tools
- Sales salaries & commissions
- Advertising & paid channels
- SDR/BDR team costs
```

**Example:**
- Sales & Marketing Spend: $500,000/month
- New Customers: 100/month
- CAC = $500,000 / 100 = $5,000

**Quality checks:**
- Is CAC consistent across channels? (Calculate by channel)
- Is CAC increasing or decreasing over time? (Should decrease with scale)
- Does CAC vary by customer segment? (SMB vs. Enterprise)

---

### LTV (Lifetime Value)
```
LTV (Simple) = ARPU × Average Customer Lifetime (months)

LTV (Better) = ARPU × Gross Margin % / Monthly Churn Rate

LTV (Advanced) = Account for expansion, cohort-specific retention, discount rate
```

**Example (Simple):**
- ARPU: $500/month
- Average Lifetime: 36 months
- LTV = $500 × 36 = $18,000

**Example (Better):**
- ARPU: $500/month
- Gross Margin: 80%
- Monthly Churn: 2%
- LTV = ($500 × 80%) / 2% = $400 / 0.02 = $20,000

**Quality checks:**
- Is LTV growing over time? (From expansion, improved retention)
- Does LTV vary by cohort? (Are new customers more/less valuable?)
- Does LTV vary by segment? (Enterprise vs. SMB)

---

### LTV:CAC Ratio
```
LTV:CAC Ratio = LTV / CAC
```

**Example:**
- LTV: $20,000
- CAC: $5,000
- LTV:CAC = $20,000 / $5,000 = 4:1

**Quality checks:**
- Is ratio >3:1? (Minimum for sustainable growth)
- Is ratio >5:1? (Might be underinvesting in growth)
- Is ratio improving or degrading over time?

**Interpretation:**
- **<1:1** = Losing money on every customer (unsustainable)
- **1-3:1** = Marginal economics (optimize before scaling)
- **3-5:1** = Healthy (scale confidently)
- **>5:1** = Potentially underinvesting (could grow faster)

---

### Payback Period
```
Payback Period (months) = CAC / (Monthly ARPU × Gross Margin %)
```

**Example:**
- CAC: $5,000
- Monthly ARPU: $500
- Gross Margin: 80%
- Payback = $5,000 / ($500 × 80%) = $5,000 / $400 = 12.5 months

**Quality checks:**
- Is payback <12 months? (Excellent)
- Is payback <18 months? (Acceptable)
- Do you have cash runway to sustain payback period?

**Critical insight:** 4:1 LTV:CAC with 36-month payback is a cash trap. 3:1 LTV:CAC with 8-month payback is better for growth.

---

### Contribution Margin
```
Contribution Margin = (Revenue - All Variable Costs) / Revenue × 100

Variable Costs include:
- COGS
- Support costs (variable component)
- Payment processing
- Variable customer success costs
```

**Example:**
- Revenue: $1,000,000
- COGS: $200,000
- Variable Support: $50,000
- Payment Processing: $30,000
- Contribution Margin = ($1M - $280K) / $1M = 72%

**Quality checks:**
- Is contribution margin >60%? (Good for SaaS)
- Are certain products/segments lower margin? (Consider sunsetting)
- Does margin improve with scale?

---

## Step 2: Calculate Capital Efficiency

### Burn Rate
```
Gross Burn Rate = Total Monthly Cash Spent
Net Burn Rate = Total Monthly Cash Spent - Monthly Revenue
```

**Example:**
- Monthly Expenses: $800,000
- Monthly Revenue: $400,000
- Gross Burn: $800,000/month
- Net Burn: $400,000/month

**Quality checks:**
- Is net burn decreasing over time? (Path to profitability)
- Is burn rate sustainable given runway?
- What's the burn rate relative to revenue? (Burn multiple)

---

### Runway
```
Runway (months) = Cash Balance / Monthly Net Burn
```

**Example:**
- Cash Balance: $6,000,000
- Net Burn: $400,000/month
- Runway = $6M / $400K = 15 months

**Quality checks:**
- Do you have >12 months runway? (Healthy)
- Do you have <6 months runway? (Crisis—raise now or cut burn)
- Can you reach next milestone before runway ends?

**Rule:** Start fundraising at 6-9 months runway, not 3 months.

---

### Operating Expenses (OpEx)
```
OpEx = Sales & Marketing + R&D + General & Administrative

Track as % of Revenue:
S&M as % of Revenue
R&D as % of Revenue
G&A as % of Revenue
```

**Example:**
- Revenue: $10M/year
- S&M: $5M (50% of revenue)
- R&D: $3M (30% of revenue)
- G&A: $1M (10% of revenue)
- Total OpEx: $9M (90% of revenue)

**Quality checks:**
- Are OpEx categories growing slower than revenue? (Operating leverage)
- Is S&M spend efficient? (Check magic number)
- Is G&A <15% of revenue? (Should stay low)

---

### Net Income (Profit Margin)
```
Net Income = Revenue - COGS - OpEx
Profit Margin % = Net Income / Revenue × 100
```

**Example:**
- Revenue: $10M
- COGS: $2M
- OpEx: $9M
- Net Income = $10M - $2M - $9M = -$1M (loss)
- Profit Margin = -10%

**Quality checks:**
- Is profit margin improving over time? (Path to profitability)
- At current growth rate, when will you break even?
- Are you investing losses in growth? (Acceptable if LTV:CAC is healthy)

---

## Step 3: Calculate Efficiency Ratios

### Rule of 40
```
Rule of 40 = Revenue Growth Rate % + Profit Margin %
```

**Example 1 (Growth Mode):**
- Revenue Growth: 80% YoY
- Profit Margin: -30%
- Rule of 40 = 80% + (-30%) = 50 (Healthy)

**Example 2 (Mature):**
- Revenue Growth: 25% YoY
- Profit Margin: 20%
- Rule of 40 = 25% + 20% = 45 (Healthy)

**Example 3 (Problem):**
- Revenue Growth: 30% YoY
- Profit Margin: -35%
- Rule of 40 = 30% + (-35%) = -5 (Unhealthy)

**Quality checks:**
- Is Rule of 40 >40? (Healthy balance)
- Is Rule of 40 >25? (Acceptable)
- Is Rule of 40 <25? (Burning cash without sufficient growth)

**Trade-offs:**
- Early stage: Maximize growth, accept losses (60% growth, -20% margin = 40)
- Growth stage: Balance (40% growth, 5% margin = 45)
- Mature: Prioritize profitability (20% growth, 25% margin = 45)

---

### Magic Number
```
Magic Number = (Current Quarter Revenue - Previous Quarter Revenue) × 4 / Previous Quarter S&M Spend
```

**Example:**
- Q2 Revenue: $2.5M
- Q1 Revenue: $2.0M
- Q1 S&M Spend: $800K
- Magic Number = ($2.5M - $2.0M) × 4 / $800K = $2M / $800K = 2.5

**Quality checks:**
- Is magic number >0.75? (Efficient—scale S&M spend)
- Is magic number 0.5-0.75? (Acceptable—optimize before scaling)
- Is magic number <0.5? (Inefficient—fix GTM before spending more)

**Interpretation:**
- **>1.0** = For every $1 in S&M, you get $1+ in new ARR (excellent)
- **0.75-1.0** = Efficient, scale confidently
- **0.5-0.75** = Marginal, optimize before scaling
- **<0.5** = Inefficient, fix before investing more

---

### Operating Leverage
Track over time to see if you're scaling efficiently.

**Example:**
| Quarter | Revenue | YoY Growth | OpEx | YoY Growth | Leverage |
|---------|---------|------------|------|------------|----------|
| Q1 2024 | $8M | - | $6M | - | - |
| Q2 2024 | $10M | 25% | $7M | 17% | Positive |
| Q3 2024 | $12M | 20% | $9M | 29% | Negative |

**Quality checks:**
- Is revenue growing faster than OpEx? (Positive leverage)
- Are you scaling OpEx too fast relative to revenue?
- Which OpEx category is growing fastest? (R&D, S&M, G&A)

---

## Step 4: Analyze by Segment and Channel

**Unit economics vary dramatically by segment:**

| Segment | CAC | LTV | LTV:CAC | Payback | Gross Margin |
|---------|-----|-----|---------|---------|--------------|
| SMB | $500 | $2,000 | 4:1 | 8 months | 75% |
| Mid-Market | $5,000 | $25,000 | 5:1 | 12 months | 80% |
| Enterprise | $50,000 | $300,000 | 6:1 | 24 months | 85% |

**Quality checks:**
- Which segment has best unit economics?
- Which segment has fastest payback? (Prioritize when cash-constrained)
- Which segment has highest LTV? (Invest in retention/expansion)

---

## Scenario Examples

### Example 1: Healthy Unit Economics

**Company:** CloudAnalytics (mid-market analytics SaaS)

**Unit Economics:**
- CAC: $8,000
- LTV: $40,000
- LTV:CAC: 5:1
- Payback Period: 10 months
- Gross Margin: 82%

**Capital Efficiency:**
- Monthly Net Burn: $300K
- Runway: 18 months
- Rule of 40: 55 (40% growth + 15% margin)
- Magic Number: 0.9

**Analysis:**
- Strong unit economics (5:1 LTV:CAC, 10-month payback)
- Efficient GTM (0.9 magic number)
- Healthy balance (Rule of 40 = 55)
- Sufficient runway (18 months)

**Action:** Scale acquisition aggressively. Economics support growth.

---

### Example 2: Good LTV:CAC, Bad Payback (Cash Trap)

**Company:** EnterpriseCRM (enterprise sales motion)

**Unit Economics:**
- CAC: $80,000
- LTV: $400,000
- LTV:CAC: 5:1 (looks great!)
- Payback Period: 36 months (terrible!)
- Gross Margin: 85%

**Capital Efficiency:**
- Monthly Net Burn: $2M
- Runway: 9 months
- Average Customer Lifetime: 48 months
- Average Contract: $100K/year

**Analysis:**
- Great LTV:CAC ratio (5:1) masks cash problem
- 36-month payback with 9-month runway = cash trap
- Takes 3 years to recover CAC, but only 9 months of cash
- Customers stay 4 years, so economics work IF you have cash

**Problem:** You'll run out of cash before recovering acquisition costs.

**Actions:**
1. Negotiate upfront annual payments (reduce payback to 12 months)
2. Raise capital to extend runway (need 36+ months to sustain growth)
3. Reduce CAC (shorten sales cycle, improve conversion)
4. Target smaller deals with faster payback (mid-market vs. enterprise)

---

### Example 3: Scaling Too Fast (Negative Operating Leverage)

**Company:** SocialScheduler (SMB social media tool)

**Quarter-over-Quarter Trend:**
| Quarter | Revenue | OpEx | Net Income | Revenue Growth | OpEx Growth |
|---------|---------|------|------------|----------------|-------------|
| Q1 | $1.0M | $800K | -$800K | - | - |
| Q2 | $1.3M | $1.2M | -$1.2M | 30% | 50% |
| Q3 | $1.6M | $1.8M | -$1.8M | 23% | 50% |

**Analysis:**
- OpEx growing FASTER than revenue (50% vs. 23-30%)
- Losses accelerating ($800K → $1.8M in 2 quarters)
- Negative operating leverage (should be positive)
- Scaling S&M and R&D without corresponding revenue growth

**Problem:** Burning cash faster while revenue growth is slowing.

**Actions:**
1. Freeze headcount until revenue catches up
2. Cut inefficient S&M spend (magic number likely <0.5)
3. Focus on improving unit economics before scaling
4. Aim for OpEx growth <revenue growth
