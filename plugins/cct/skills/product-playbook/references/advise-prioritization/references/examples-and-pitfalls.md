# Prioritization Examples and Common Pitfalls

## Examples

### Example 1: Good Framework Match (Early PMF, RICE)

**Q1 Response:** "Early PMF, scaling — Found initial PMF; growing fast; adding features to retain/expand"

**Q2 Response:** "Cross-functional team, aligned — Product, design, engineering aligned; clear goals"

**Q3 Response:** "Lack of data-driven decisions — Prioritizing by gut feel; want metrics-based process"

**Q4 Response:** "Some data — Basic analytics, customer feedback, but no rigorous data collection"

---

**Recommended Framework: RICE (Reach, Impact, Confidence, Effort)**

**Why this fits:**
- You have some data (analytics, customer feedback) to estimate Reach and Impact
- Cross-functional team alignment means you can agree on scoring criteria
- Transitioning from gut feel to data-driven = RICE provides structure without overwhelming complexity
- Early PMF stage = need speed, but also need to prioritize high-impact features for retention/expansion

**When to use it:**
- Quarterly or monthly roadmap planning
- When backlog exceeds 20-30 items
- When stakeholders debate priorities

**When NOT to use it:**
- For strategic, multi-quarter bets (RICE favors incremental wins)
- When you lack basic metrics (Reach requires usage data)
- For single-feature decisions (overkill)

---

**Implementation:**

#### Step 1: Define Scoring Criteria
- **Reach:** How many users will this feature affect per month/quarter?
- **Impact:** How much will it improve their experience? (1 = minimal, 2 = high, 3 = massive)
- **Confidence:** How confident are you in your Reach/Impact estimates? (50% = low data, 80% = good data, 100% = certain)
- **Effort:** How many person-months to build? (Include design, engineering, QA)

#### Step 2: Score Each Feature
- Use a spreadsheet or Airtable
- Involve PM, design, engineering in scoring (not just PM solo)
- Be honest about Confidence (don't inflate scores)

#### Step 3: Calculate RICE Score
- Formula: `(Reach x Impact x Confidence) / Effort`
- Higher score = higher priority

#### Step 4: Review and Adjust
- Sort by RICE score
- Review top 10-20 with stakeholders
- Adjust for strategic priorities (RICE doesn't capture everything)

---

**Example Scoring:**

| Feature | Reach | Impact | Confidence | Effort | RICE Score |
|---------|-------|--------|------------|--------|------------|
| Email reminders | 5,000 | 2 | 70% | 1 | 7,000 |
| Mobile app | 10,000 | 3 | 60% | 6 | 3,000 |
| Dark mode | 8,000 | 1 | 90% | 0.5 | 14,400 |

**Priority:** Dark mode > Email reminders > Mobile app (despite mobile app having high Reach/Impact, Effort is too high)

---

**Alternative Framework: ICE (Impact, Confidence, Ease)**

**Why this might work:**
- Simpler than RICE (no Reach calculation)
- Faster to score (good if you need quick decisions)

**Tradeoffs:**
- Less data-driven (no Reach metric = can't compare features affecting different user bases)
- More subjective (Impact/Ease are gut-feel, not metrics)

---

**Common Pitfalls:**

1. **Overweighting Effort** — Don't avoid hard problems just because they score low. Some strategic bets require high effort.
2. **Inflating Confidence** — Be honest. 50% confidence is okay if data is scarce.
3. **Ignoring strategy** — RICE doesn't capture strategic importance. Adjust for vision/goals.

---

### Example 2: Bad Framework Match (Pre-PMF + RICE = Wrong Fit)

**Q1 Response:** "Pre-product/market fit — Searching for PMF; experimenting rapidly"

**Q2 Response:** "Small team, limited resources — 3 engineers, 1 PM"

**Q3 Response:** "Too many ideas, unclear which to pursue"

**Q4 Response:** "Minimal data — New product, no usage metrics"

---

**Recommended Framework: ICE (Impact, Confidence, Ease) or Value/Effort Matrix**

**Why NOT RICE:**
- You don't have usage data to estimate Reach
- Pre-PMF = you need speed, not rigorous scoring
- Small team = overhead of RICE scoring is too heavy

**Why ICE instead:**
- Lightweight, gut-check framework
- Can score 20 ideas in 30 minutes
- Good for rapid experimentation phase

**Or Value/Effort Matrix:**
- Visual 2x2 matrix (high value/low effort = quick wins)
- Even faster than ICE
- Good for stakeholder alignment (visual, intuitive)

---

## Common Pitfalls

### Pitfall 1: Using the Wrong Framework for Your Stage
**Symptom:** Pre-PMF startup using weighted scoring with 10 criteria

**Consequence:** Overhead kills speed. You need experiments, not rigorous scoring.

**Fix:** Match framework to stage. Pre-PMF = ICE or Value/Effort. Scaling = RICE. Mature = Opportunity Scoring or Kano.

---

### Pitfall 2: Framework Whiplash
**Symptom:** Switching frameworks every quarter

**Consequence:** Team confusion, lost time, no consistency.

**Fix:** Stick with one framework for 6-12 months. Reassess only when stage/context changes.

---

### Pitfall 3: Treating Scores as Gospel
**Symptom:** "Feature A scored 8,000, Feature B scored 7,999, so A wins"

**Consequence:** Ignores strategic context, judgment, and vision.

**Fix:** Use frameworks as input, not automation. PM judgment overrides scores when needed.

---

### Pitfall 4: Solo PM Scoring
**Symptom:** PM scores features alone, presents to team

**Consequence:** Lack of buy-in, engineering/design don't trust scores.

**Fix:** Collaborative scoring sessions. PM, design, engineering score together.

---

### Pitfall 5: No Framework at All
**Symptom:** "We prioritize by who shouts loudest"

**Consequence:** HiPPO (Highest Paid Person's Opinion) wins, not data or strategy.

**Fix:** Pick *any* framework. Even imperfect structure beats chaos.
