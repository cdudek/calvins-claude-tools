# Discovery Process Phase Details

Detailed instructions for each of the 6 phases in the discovery process.

---

## Phase 1: Frame the Problem (Day 1-2)

**Goal:** Define what you're investigating, who's affected, and success criteria.

### Activities

**1. Run Problem Framing Canvas**
- **Use:** `reframe-problem` (interactive - MITRE)
- **Participants:** PM, design, engineering lead
- **Duration:** 120 minutes
- **Output:** Problem statement + "How Might We" question

**2. Create Formal Problem Statement**
- **Use:** `frame-problem` (component)
- **Participants:** PM
- **Duration:** 30 minutes
- **Output:** Structured problem statement with hypothesis

**3. Define Proto-Personas (If Needed)**
- **When:** If target customer segment is unclear
- **Duration:** 60 minutes
- **Output:** Hypothesis-driven personas

**4. Map Jobs-to-be-Done (If Needed)**
- **When:** If customer motivations are unclear
- **Duration:** 60 minutes
- **Output:** JTBD statements

### Outputs from Phase 1

- **Problem hypothesis:** "We believe [persona] struggles with [problem] because [root cause], leading to [consequence]."
- **Research questions:** 3-5 questions to answer through discovery
- **Success criteria:** What would validate/invalidate the problem?

### Decision Point 1: Do we have enough context to start research?

**If YES:** Proceed to Phase 2 (Research Planning)

**If NO:** Gather existing data first:
- Review support tickets, churn surveys, NPS feedback
- Analyze product analytics (drop-off points, usage patterns)
- Review competitor research, market trends
- **Time impact:** +2-3 days

---

## Phase 2: Research Planning (Day 3)

**Goal:** Design research approach, recruit participants, prepare interview guide.

### Activities

**1. Prep Discovery Interviews**
- **Use:** `prep-discovery-interview` (interactive)
- **Participants:** PM, design
- **Duration:** 90 minutes
- **Output:** Interview plan with methodology, questions, biases to avoid

**2. Recruit Participants**
- **Target:** 5-10 customers per discovery cycle (Teresa Torres: continuous discovery = 1 interview/week)
- **Segment:** Focus on personas from Phase 1
- **Recruitment channels:**
  - Existing customers (email, in-app prompts)
  - Churned customers (exit interviews)
  - Cold outreach (LinkedIn, communities)
- **Incentive:** $50-100 gift card or product credit
- **Duration:** 2-3 days (parallel with Phase 1)

**3. Schedule Interviews**
- **Format:** 45-60 min per interview (30-40 min conversation + buffer)
- **Timeline:** Spread across 1-2 weeks
- **Recording:** Get consent, record for synthesis

### Outputs from Phase 2

- **Interview guide:** 5-7 open-ended questions (Mom Test style)
- **Participant roster:** 5-10 scheduled interviews
- **Synthesis plan:** How you'll capture and analyze insights

---

## Phase 3: Conduct Research (Week 1-2)

**Goal:** Gather qualitative evidence through customer interviews.

### Activities

**1. Conduct Discovery Interviews**
- **Methodology:** From `prep-discovery-interview` (Problem validation, JTBD, switch interviews, etc.)
- **Participants:** PM + optional observer (design, eng)
- **Duration:** 5-10 interviews over 1-2 weeks
- **Focus areas:**
  - Past behavior (not hypotheticals): "Tell me about the last time you [experienced this problem]"
  - Workarounds: "How do you currently handle this?"
  - Alternatives tried: "Have you tried other solutions? Why did you stop?"
  - Pain intensity: "How much time/money does this cost you?"

**2. Take Structured Notes**
- **Template:**
  - Participant: [Name, role, company size]
  - Context: [When/where they experience problem]
  - Actions: [What they do, step-by-step]
  - Pain points: [Frustrations, blockers]
  - Workarounds: [Current solutions]
  - Quotes: [Verbatim customer language]
  - Insights: [Patterns, surprises]

**3. Review Support Tickets & Analytics (Parallel)**
- **Support tickets:** Tag by theme (onboarding, feature confusion, bugs)
- **Analytics:** Identify drop-off points, feature usage, cohort behavior
- **Surveys:** Review NPS comments, exit surveys, feature requests

### Outputs from Phase 3

- **Interview transcripts:** Recorded sessions + detailed notes
- **Support ticket themes:** Top 10 issues by frequency
- **Analytics insights:** Quantitative data on behavior (e.g., "60% abandon onboarding at step 3")

### Decision Point 2: Have we reached saturation?

**Saturation = same pain points emerge across 3+ interviews, no new insights**

**If YES (saturated after 5-7 interviews):** Proceed to Phase 4 (Synthesis)

**If NO (still learning new things):** Schedule 3-5 more interviews
- **Time impact:** +1 week

---

## Phase 4: Synthesize Insights (End of Week 2)

**Goal:** Identify patterns, prioritize pain points, map opportunities.

### Activities

**1. Affinity Mapping (Thematic Analysis)**
- **Method:**
  - Write each insight/quote on sticky note
  - Group by theme (e.g., "onboarding confusion," "pricing objections," "mobile access")
  - Count frequency (how many customers mentioned each theme)
- **Participants:** PM, design, optional eng
- **Duration:** 90-120 minutes
- **Output:** Themed clusters with frequency counts

**2. Create Customer Journey Map (Optional)**
- **Use:** `run-journey-workshop` (interactive)
- **When:** If pain points span multiple phases (discover, try, buy, use, support)
- **Duration:** 90 minutes
- **Output:** Journey map with opportunities ranked by impact

**3. Prioritize Pain Points**
- **Criteria:**
  - **Frequency:** How many customers mentioned this?
  - **Intensity:** How painful is it? (time wasted, money lost, emotional frustration)
  - **Strategic fit:** Does solving this align with business goals?
- **Method:** Score each pain point (1-5) on frequency, intensity, strategic fit
- **Output:** Ranked list of top 3-5 pain points to address

**4. Update Problem Statement**
- **Use:** `frame-problem` (component)
- **Refine based on research:** Did initial hypothesis hold? Adjust if needed.
- **Output:** Validated problem statement

### Outputs from Phase 4

- **Affinity map:** Themes with frequency counts
- **Top 3-5 pain points:** Prioritized by frequency x intensity x strategic fit
- **Customer quotes:** 3-5 verbatim quotes per pain point
- **Validated problem statement:** Refined based on evidence

---

## Phase 5: Generate & Validate Solutions (Week 3)

**Goal:** Explore solution options, design experiments, validate assumptions.

### Activities

**1. Generate Opportunity Solution Tree**
- **Use:** `build-opportunity-tree` (interactive)
- **Input:** Top 3 pain points from Phase 4
- **Participants:** PM, design, engineering lead
- **Duration:** 90 minutes
- **Output:** 3 opportunities, 3 solutions per opportunity, POC recommendation

**2. Design Experiments**
- **For each solution:** Define "What's the least work to learn the next most important thing?"
- **Experiment types:**
  - **Concierge test:** Manually deliver solution to 10 customers, observe
  - **Prototype test:** Clickable mockup, usability test with 10 users
  - **Landing page test:** Fake door test (show feature, measure interest)
  - **A/B test:** Build minimal version, test with 50% of users
- **Success criteria:** What metric/behavior validates hypothesis?

**3. Run Experiments**
- **Timeline:** 1-2 weeks per experiment
- **Participants:** PM + design (for prototypes), eng (for A/B tests)
- **Output:** Quantitative and qualitative validation data

### Outputs from Phase 5

- **Solution options:** 3-9 solutions (3 per opportunity)
- **Experiment results:** Did hypothesis validate or invalidate?
- **Customer feedback:** Qualitative reactions to prototypes/concepts

### Decision Point 3: Did experiments validate solution?

**If YES (validated):** Proceed to Phase 6 (Decide & Document)

**If NO (invalidated):**
- Pivot to next solution option
- Re-run experiments with adjusted approach
- **Time impact:** +1-2 weeks

---

## Phase 6: Decide & Document (End of Week 3-4)

**Goal:** Commit to build, document decision, communicate to stakeholders.

### Activities

**1. Make Go/No-Go Decision**
- **Criteria:**
  - Problem validated? (Phase 3-4)
  - Solution validated? (Phase 5)
  - Strategic fit? (aligns with business goals)
  - Feasible? (engineering capacity, technical complexity)
- **Decision:**
  - **GO:** Move to roadmap, write epics/stories
  - **PIVOT:** Explore alternative solution
  - **KILL:** De-prioritize, not worth solving now

**2. Define Epic Hypotheses (If GO)**
- **Participants:** PM
- **Duration:** 60 minutes per epic
- **Output:** Epic hypothesis statement with success criteria

**3. Write PRD (If GO)**
- **Participants:** PM
- **Duration:** 1-2 days
- **Output:** Structured PRD with problem, solution, success metrics

**4. Communicate Findings**
- **Format:** 30-min readout covering:
  - Problem validation (Phase 3-4 insights)
  - Solution validation (Phase 5 experiments)
  - Recommendation (GO/PIVOT/KILL)
- **Participants:** Execs, product leadership, key stakeholders
- **Output:** Alignment on next steps

### Outputs from Phase 6

- **Decision:** GO, PIVOT, or KILL
- **Epic hypotheses:** (if GO) Testable epic statements
- **PRD:** (if GO) Formal product requirements document
- **Stakeholder alignment:** Exec buy-in on recommendation
