# Common Pitfalls

## Pitfall 1: Celebrating High LTV Without Checking Payback
**Symptom:** "Our LTV:CAC is 6:1, amazing!"

**Consequence:** 6:1 ratio with 48-month payback is a cash trap. You'll run out of money before recovering CAC.

**Fix:** Always pair LTV:CAC with payback period. 3:1 with 10-month payback beats 6:1 with 36-month payback.

---

## Pitfall 2: Ignoring Gross Margin When Calculating LTV
**Symptom:** "LTV = $100/month x 36 months = $3,600"

**Consequence:** You're using revenue, not profit. Actual LTV after 30% COGS = $2,520, not $3,600.

**Fix:** Always include gross margin in LTV calculations. `LTV = ARPU x Margin % / Churn Rate`.

---

## Pitfall 3: Scaling S&M with Low Magic Number
**Symptom:** "We need to grow faster—let's double S&M spend!" (Magic Number = 0.3)

**Consequence:** You're pouring gas on a broken engine. Doubling spend will just accelerate cash burn without proportional revenue growth.

**Fix:** Only scale S&M when magic number >0.75. If <0.5, fix GTM efficiency first.

---

## Pitfall 4: Using Simplistic LTV Formulas
**Symptom:** "LTV = ARPU x Lifetime" (ignoring expansion, discount rates, cohort variance)

**Consequence:** Overstating LTV for decision-making. Reality: expansion boosts LTV; discounting reduces it; cohorts vary.

**Fix:** Use sophisticated LTV models for big decisions. Simple LTV ok for directional guidance only.

---

## Pitfall 5: Forgetting Time Value of Money
**Symptom:** "$10K revenue today = $10K revenue in 5 years"

**Consequence:** Overstating LTV for long-payback businesses. $10K in 5 years is worth ~$7.8K today (at 5% discount rate).

**Fix:** Discount future cash flows for LTV periods >24 months. Use NPV (net present value).

---

## Pitfall 6: Comparing CAC Across Different Payback Periods
**Symptom:** "Channel A has $5K CAC, Channel B has $8K CAC—Channel A is better!"

**Consequence:** If Channel A has 24-month payback and Channel B has 8-month payback, Channel B is actually better (faster cash recovery).

**Fix:** Compare CAC + payback together, not CAC in isolation.

---

## Pitfall 7: Celebrating Rule of 40 >40 with Negative Cash Flow
**Symptom:** "Rule of 40 = 50, we're crushing it!" (60% growth, -10% margin, burning $5M/month)

**Consequence:** Rule of 40 doesn't account for absolute burn. You might have great balance but only 3 months runway.

**Fix:** Pair Rule of 40 with burn rate and runway. Balance matters, but survival matters more.

---

## Pitfall 8: Ignoring Segment-Specific Unit Economics
**Symptom:** "Blended CAC is $2K, blended LTV is $10K, we're good!"

**Consequence:** SMB segment might have $500 CAC / $2K LTV (great), while Enterprise has $20K CAC / $15K LTV (terrible). Blended metrics hide the problem.

**Fix:** Calculate unit economics by segment. Optimize each independently.

---

## Pitfall 9: Confusing Gross Margin with Contribution Margin
**Symptom:** "Gross margin is 80%, our margins are great!"

**Consequence:** After variable support costs (10%) and payment processing (3%), contribution margin might be 67%—not 80%.

**Fix:** Track both gross margin (COGS only) AND contribution margin (all variable costs). Use contribution margin for unit economics.

---

## Pitfall 10: Forgetting Working Capital Timing
**Symptom:** "We have 12 months runway based on burn rate" (but all contracts are paid monthly)

**Consequence:** Annual contracts paid upfront boost cash temporarily. Monthly contracts delay cash collection. Runway is longer/shorter than burn rate suggests.

**Fix:** Account for working capital when calculating runway. Cash-based runway is not the same as revenue-based runway.
