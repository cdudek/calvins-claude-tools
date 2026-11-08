## Purpose

Determine whether your SaaS business model is fundamentally viable and capital-efficient. Use this to calculate unit economics, assess profitability, manage cash runway, and decide when to scale vs. optimize. Essential for fundraising, board reporting, and making smart investment trade-offs.

This is not a finance reporting tool -- it is a framework for PMs to understand whether the business can sustain growth, when to prioritize efficiency over growth, and which investments have positive returns.

## Prerequisites

Read `references/metrics.md` for full metric definitions, benchmarks, and when-to-use guidance before proceeding.

## Metric Families (Summary)

**Unit Economics** -- Customer-level profitability: Gross Margin, CAC, LTV, LTV:CAC Ratio, Payback Period, Contribution Margin, Gross Margin Payback, CAC Payback by Channel. See `references/metrics.md` for definitions and benchmarks.

**Capital Efficiency** -- Cash usage efficiency: Burn Rate, Runway, OpEx, Net Income, Working Capital Impact. See `references/metrics.md` for definitions and benchmarks.

**Efficiency Ratios** -- Growth vs. profitability composites: Rule of 40, Magic Number, Operating Leverage, Unit Economics. See `references/metrics.md` for definitions and benchmarks.

## Workflow

### Step 1: Calculate Unit Economics

Calculate Gross Margin, CAC, LTV, LTV:CAC, Payback Period, and Contribution Margin. Use `template.md` for the fill-in structure and `references/formulas-and-examples.md` for detailed formulas, worked examples, and quality checks for each metric.

### Step 2: Calculate Capital Efficiency

Calculate Burn Rate, Runway, OpEx breakdown, and Net Income. See `references/formulas-and-examples.md` for formulas, examples, and quality checks.

### Step 3: Calculate Efficiency Ratios

Calculate Rule of 40, Magic Number, and Operating Leverage. See `references/formulas-and-examples.md` for formulas, interpretation scales, and trade-off guidance by stage.

### Step 4: Analyze by Segment and Channel

Break down unit economics by customer segment (SMB, Mid-Market, Enterprise) and acquisition channel. Identify which segments have the best economics and fastest payback. See `references/formulas-and-examples.md` for segment comparison tables.

## Anti-Patterns

- **Not vanity metrics:** High LTV means nothing if payback takes 4 years and customers churn at 3 years
- **Not static benchmarks:** "Good" CAC varies wildly by business model (PLG vs. enterprise sales)
- **Not isolated numbers:** LTV:CAC ratio without payback period can mislead (great ratio, terrible cash efficiency)
- **Not just finance's problem:** PMs must own unit economics -- every feature decision impacts margins and CAC

## Common Pitfalls

See `references/pitfalls.md` for 10 detailed pitfalls with symptoms, consequences, and fixes. Key ones:

1. Celebrating high LTV:CAC without checking payback period (cash trap)
2. Ignoring gross margin when calculating LTV (overstating by 20-30%)
3. Scaling S&M spend when magic number is below 0.5 (pouring gas on a broken engine)
4. Using blended metrics that hide segment-specific problems
5. Confusing gross margin with contribution margin

## Examples

See `references/formulas-and-examples.md` for three full scenario walkthroughs:
- Healthy unit economics (CloudAnalytics)
- Good LTV:CAC with bad payback / cash trap (EnterpriseCRM)
- Scaling too fast with negative operating leverage (SocialScheduler)

Also see `examples/` folder for additional detailed scenarios.

## References

### External Frameworks
- **David Skok (Matrix Partners):** "SaaS Metrics" blog -- Definitive guide to CAC, LTV, payback
- **Bessemer Venture Partners:** "SaaS Metrics 2.0" -- Rule of 40, magic number benchmarks
- **Ben Murray:** *The SaaS CFO* -- Advanced unit economics modeling
- **Jason Lemkin (SaaStr):** SaaS benchmarking research
- **Brad Feld:** *Venture Deals* -- Understanding investor perspective on unit economics

---

## Sources

| Source | Author | URL |
|--------|--------|-----|
| Product Manager Skills | Dean Peters | https://github.com/deanpeters/Product-Manager-Skills |
