# Roadmap Planning — Phase Details

Detailed activities, outputs, and guidance for each of the 5 roadmap planning phases.

---

## Phase 1: Gather Inputs (Day 1-2)

**Goal:** Collect business goals, customer problems, technical constraints, stakeholder requests.

### Activities

**1. Review Business Goals (OKRs, Strategic Initiatives)**
- **Source:** Company OKRs, exec strategy memos, board decks
- **Questions:**
  - What are the company's top 3 priorities this year?
  - What metrics must we move? (revenue, retention, acquisition, efficiency)
  - Are there strategic bets? (new markets, partnerships, product lines)
- **Output:** 3-5 business outcomes to optimize for

**2. Review Customer Problems (Discovery Insights)**
- **Source:** Discovery interviews, support tickets, NPS feedback, churn surveys
- **Use:** Insights from `skills/discovery-process/SKILL.md` (if recently completed)
- **Questions:**
  - What are the top 3-5 customer pain points?
  - Which problems affect the most customers?
  - Which problems have highest intensity?
- **Output:** 3-5 validated customer problems

**3. Review Technical Constraints & Opportunities**
- **Source:** Engineering leadership, tech debt assessments
- **Questions:**
  - Are there technical blockers? (scaling, performance, security)
  - Are there enabling investments? (platform upgrades, API rewrites)
  - What's the technical roadmap? (migrations, deprecations)
- **Output:** List of technical investments required

**4. Review Stakeholder Requests**
- **Source:** Sales, marketing, customer success, execs
- **Questions:**
  - What are sales asking for? (enterprise features, integrations)
  - What's marketing requesting? (growth initiatives, positioning)
  - What's customer success flagging? (churn risks, expansion blockers)
- **Output:** List of stakeholder requests (not yet committed)

### Outputs from Phase 1

- **Business outcomes:** 3-5 OKRs or strategic goals
- **Customer problems:** 3-5 validated pain points
- **Technical investments:** Platform/tech debt items
- **Stakeholder requests:** Feature requests from internal teams

---

## Phase 2: Define Initiatives (Epics) (Day 3-4)

**Goal:** Turn inputs into epics with hypotheses, success metrics, and effort estimates.

### Activities

**1. Define Epic Hypotheses**
- **Use:** `skills/epic-hypothesis/SKILL.md` (component)
- **For each initiative:** Write hypothesis statement
- **Format:** "We believe that [building X] for [persona] will achieve [outcome] because [assumption]."
- **Participants:** PM
- **Duration:** 60 minutes per epic
- **Output:** 10-15 epic hypotheses

**Example Epics (SaaS Product):**

```
Epic 1: Guided Onboarding
Hypothesis: We believe that adding a step-by-step onboarding checklist for non-technical users will increase activation rate from 40% to 60% because users currently drop off due to lack of guidance.

Success Metric: Activation rate (% completing first action within 24 hours)
Target: 40% → 60%

Epic 2: Enterprise SSO
Hypothesis: We believe that adding SSO for enterprise accounts will increase enterprise deals closed from 2/quarter to 5/quarter because enterprise buyers require SSO for security compliance.

Success Metric: Enterprise deals closed per quarter
Target: 2 → 5

Epic 3: Mobile-Optimized Workflows
Hypothesis: We believe that optimizing core workflows for mobile will increase mobile DAU from 5% to 20% because mobile-first users currently can't complete workflows on the go.

Success Metric: Mobile DAU as % of total DAU
Target: 5% → 20%
```

**2. Estimate Effort (T-Shirt Sizing)**
- **Participants:** PM + engineering lead
- **Duration:** 90 minutes
- **Method:**
  - **Small (S):** 1-2 weeks (1-2 engineers)
  - **Medium (M):** 3-4 weeks (2-3 engineers)
  - **Large (L):** 2-3 months (3-5 engineers)
  - **Extra Large (XL):** 3+ months (5+ engineers)
- **Output:** Effort estimate per epic

**3. Map to Business Outcomes**
- **For each epic:** Tag with primary business outcome
- **Example:**
  - Epic 1 (Guided Onboarding) → Retention
  - Epic 2 (Enterprise SSO) → Acquisition (enterprise)
  - Epic 3 (Mobile Workflows) → Engagement

### Outputs from Phase 2

- **10-15 epics:** Each with hypothesis, success metric, effort estimate
- **Business outcome mapping:** Which epics drive which OKRs

---

## Phase 3: Prioritize Initiatives (Day 5)

**Goal:** Rank epics by impact, effort, and strategic fit.

### Activities

**1. Choose Prioritization Framework**
- **Use:** `skills/prioritization-advisor/SKILL.md` (interactive)
- **Participants:** PM
- **Duration:** 30 minutes
- **Output:** Recommended framework (RICE, ICE, Value/Effort, etc.)

**2. Score Epics**
- **Participants:** PM, engineering lead, product leadership
- **Duration:** 120 minutes
- **Method:** Apply framework to all epics
- **Example (RICE scoring):**

| Epic | Reach | Impact | Confidence | Effort | RICE Score |
|------|-------|--------|------------|--------|------------|
| Guided Onboarding | 10,000 users | 3 (massive) | 80% | 1 month | 24,000 |
| Enterprise SSO | 500 users | 3 (massive) | 90% | 2 months | 675 |
| Mobile Workflows | 5,000 users | 2 (high) | 60% | 3 months | 2,000 |
| Advanced Reporting | 2,000 users | 2 (high) | 50% | 2 months | 1,000 |

**3. Adjust for Strategic Fit**
- **Review scores:** Do they align with business goals?
- **Strategic overrides:** Promote epics that align with strategic bets (even if score is lower)
- **Example:** Enterprise SSO scores lower, but it's critical for enterprise expansion strategy → boost priority

### Outputs from Phase 3

- **Ranked backlog:** Epics sorted by priority (RICE score + strategic adjustments)
- **Top 10 epics:** Highest-priority initiatives for roadmap

---

## Phase 4: Sequence Roadmap (Day 6-7)

**Goal:** Organize epics into quarters/releases with logical dependencies.

### Activities

**1. Map Dependencies**
- **Questions:**
  - Does Epic B depend on Epic A? (e.g., "Advanced Reporting" requires "Data Pipeline Upgrade")
  - Are there technical blockers? (e.g., "Mobile App" requires "API Redesign")
- **Output:** Dependency graph (Epic A → Epic B → Epic C)

**2. Sequence by Quarter (or Release)**
- **Now (Q1):** Top 3-5 epics, no dependencies
- **Next (Q2):** Next 3-5 epics, may depend on Q1 completion
- **Later (Q3+):** Remaining epics, lower confidence

**Example Roadmap (Timeline-Based):**

```
Q1 2026 (Now - Committed):
├─ Guided Onboarding (Retention)
├─ Enterprise SSO (Acquisition)
└─ Mobile-Optimized Workflows (Engagement)

Q2 2026 (Next - High Confidence):
├─ Advanced Reporting (depends on Data Pipeline, Q1)
├─ Slack Integration (Engagement)
└─ Pricing Page Redesign (Acquisition)

Q3 2026 (Later - Lower Confidence):
├─ Mobile App (depends on API Redesign)
├─ AI-Powered Recommendations
└─ Multi-Language Support

Q4 2026 (Exploration):
├─ Marketplace/Plugin Ecosystem
└─ Enterprise Onboarding Concierge
```

**Alternative: Now/Next/Later Roadmap**

```
NOW (Current Quarter):
- Guided Onboarding
- Enterprise SSO
- Mobile-Optimized Workflows

NEXT (Following Quarter):
- Advanced Reporting
- Slack Integration
- Pricing Page Redesign

LATER (Future):
- Mobile App
- AI Recommendations
- Multi-Language Support
```

**3. Validate with Engineering**
- **Participants:** PM + engineering lead
- **Questions:**
  - Is sequencing realistic? (capacity, dependencies)
  - Are there hidden technical blockers?
  - Do we need to adjust scope?
- **Output:** Validated roadmap sequence

### Outputs from Phase 4

- **Sequenced roadmap:** Epics organized by Q1, Q2, Q3
- **Dependency map:** What depends on what
- **Capacity check:** Engineering agrees sequence is feasible

---

## Phase 5: Communicate Roadmap (Week 2)

**Goal:** Present roadmap to stakeholders, gather feedback, build alignment.

### Activities

**1. Create Roadmap Presentation**
- **Format:** 30-45 min presentation
- **Structure:**
  - **Slide 1:** Strategic context (business goals, customer problems)
  - **Slide 2-3:** Roadmap overview (Q1, Q2, Q3)
  - **Slide 4-6:** Deep dive per quarter (epics, hypotheses, success metrics)
  - **Slide 7:** What's NOT on roadmap (and why)
  - **Slide 8:** Dependencies and risks
- **Participants:** PM, design
- **Duration:** 2-3 hours to prepare

**2. Present to Stakeholders**
- **Audience:** Execs, product leadership, engineering, sales, marketing, CS
- **Duration:** 45 min presentation + 15 min Q&A
- **Focus:**
  - Strategic narrative: "Here's why we're prioritizing X over Y"
  - Outcome focus: "Each epic drives [business outcome]"
  - Flexibility: "This roadmap is a plan, not a commitment; we'll adjust as we learn"

**3. Gather Feedback**
- **Questions to ask:**
  - Do these priorities align with business goals?
  - Are we missing critical customer problems?
  - Are dependencies clear?
  - What concerns do you have?
- **Output:** List of feedback, concerns, questions

**4. Refine Roadmap**
- **Based on feedback:** Adjust priorities, add missing epics, clarify dependencies
- **Duration:** 1-2 days
- **Output:** Final roadmap v1.0

**5. Publish Roadmap**
- **Internal:** Share with team (Confluence, Notion, Productboard, etc.)
- **External (Optional):** Public roadmap for customers (use Now/Next/Later format)
- **Format:** Visual roadmap + narrative doc

### Outputs from Phase 5

- **Roadmap presentation:** 30-45 min deck
- **Stakeholder alignment:** Feedback incorporated, concerns addressed
- **Published roadmap:** Accessible to team (internal) or customers (external)
