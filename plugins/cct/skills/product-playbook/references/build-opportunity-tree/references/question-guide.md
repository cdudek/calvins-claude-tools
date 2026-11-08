# Opportunity Tree Question Guide

Detailed facilitation questions and adaptive options for building an Opportunity Solution Tree.

---

## Step 0: Gather Context (Before Questions)

**Agent suggests:**

Before we create your Opportunity Solution Tree, let's gather context:

**Stakeholder Request or Product Initiative:**
- What did the stakeholder ask for? (Feature request, product idea, strategic goal)
- Any existing materials: PRD drafts, OKR documents, strategy memos, meeting notes
- Problem statements, customer complaints, or research findings

**Product Context (if available):**
- Website copy, positioning statements, product descriptions
- Competitor materials, customer reviews (G2, Capterra), community discussions
- Usage data, support tickets, churn reasons

**You can paste this content directly, or describe the request briefly.**

---

## Phase 1: Generate Opportunity Solution Tree

### Question 1: Extract Desired Outcome

**Agent asks:**
"What's the desired outcome for this initiative? (What business or product metric are you trying to move?)"

**Offer 4 enumerated options:**

1. **Revenue growth** — "Increase ARR, expand revenue from existing customers, new revenue streams" (Common for scaling products)
2. **Customer retention** — "Reduce churn, increase activation, improve engagement/stickiness" (Common for established products with retention issues)
3. **Customer acquisition** — "Increase sign-ups, trial conversions, new user growth" (Common for early-stage or growth products)
4. **Product efficiency** — "Reduce support costs, decrease time-to-value, improve operational metrics" (Common for mature products optimizing operations)

**Or describe your specific desired outcome (be measurable: e.g., "Increase trial-to-paid conversion from 15% to 25%").**

**User response:** [Selection or custom]

**Agent extracts and confirms:**
- **Desired Outcome:** [Specific, measurable outcome]
- **Why it matters:** [Rationale from stakeholder request or context]

---

### Question 2: Identify Opportunities (Problems to Solve)

**Agent generates 3 opportunities** based on the desired outcome and context provided.

**Agent says:**
"Based on your desired outcome ([from Q1]) and the context you provided, here are **3 opportunities** (customer problems or needs) that could drive this outcome:"

**Example (if Outcome = Increase trial-to-paid conversion):**

1. **Opportunity 1: Users don't experience value during trial** — "New users sign up but don't complete onboarding, never reach 'aha moment,' abandon before seeing core value"
   - Evidence: [From context: onboarding analytics, support tickets, exit surveys]

2. **Opportunity 2: Pricing is unclear or misaligned** — "Users unsure if paid plan is worth it; don't understand what they get for the price; pricing page confusing"
   - Evidence: [From context: conversion funnel drop-off at pricing page, sales objections]

3. **Opportunity 3: Free plan is 'good enough'** — "Users stay on free tier indefinitely because it meets their needs; no compelling reason to upgrade"
   - Evidence: [From context: freemium user retention data, support tickets asking for workarounds]

**Agent asks:**
"Which opportunity feels most critical to explore first, or would you like to modify/add opportunities?"

**User response:** [Selection or custom]

---

### Question 3: Generate Solutions for Selected Opportunity

**Agent generates 3 solution ideas** for the selected opportunity.

**Agent says:**
"For **Opportunity [X]: [Name]**, here are **3 potential solutions** to test:"

**Example (if Opportunity 1 selected: Users don't experience value during trial):**

1. **Solution 1: Guided onboarding checklist** — "Interactive checklist that walks users through core workflows step-by-step (e.g., 'Create your first project,' 'Invite a teammate,' 'Complete a task')"
   - Hypothesis: Structured guidance increases completion rate
   - Experiment: A/B test checklist vs. no checklist, measure activation rate

2. **Solution 2: Time-to-value triggers** — "Automatically prompt users when they're stuck (e.g., 'You haven't created a project yet—here's a template to get started')"
   - Hypothesis: Proactive nudges prevent drop-off
   - Experiment: Track engagement with prompts, measure trial-to-paid lift

3. **Solution 3: Human-assisted onboarding** — "Offer 15-min onboarding call with CSM for high-value trial users (enterprise, team plans)"
   - Hypothesis: Personal touch increases conversion for high-intent users
   - Experiment: Offer to 50 trial users, measure conversion vs. control group

**Agent asks:**
"Would you like to explore solutions for another opportunity, or move to POC selection?"

**User response:** [Selection or custom]

---

## Phase 2: Select Proof-of-Concept (POC)

### Question 4: Evaluate Solutions (Feasibility, Impact, Market Fit)

**Agent says:**
"Let's evaluate your solutions to pick the best starting point. I'll score each solution on **Feasibility** (how hard to build), **Impact** (how much it could move the outcome), and **Market Fit** (how well it aligns with customer needs)."

**Agent generates evaluation table:**

| Solution | Feasibility (1-5) | Impact (1-5) | Market Fit (1-5) | Total Score | Rationale |
|----------|-------------------|--------------|------------------|-------------|-----------|
| Solution 1: Guided onboarding checklist | 4 | 4 | 5 | 13 | High feasibility (UI pattern), proven impact (industry standard), strong market fit (users expect onboarding) |
| Solution 2: Time-to-value triggers | 3 | 3 | 4 | 10 | Medium feasibility (requires analytics integration), moderate impact (depends on trigger quality), good market fit |
| Solution 3: Human-assisted onboarding | 5 | 5 | 3 | 13 | High feasibility (no dev work), high impact (personal touch), lower market fit (doesn't scale, high-touch only) |

**Agent recommends:**

**Recommended POC: Solution 1 (Guided onboarding checklist)**

**Why this POC:**
- Balances feasibility (can build in 2-4 weeks) with impact (proven pattern)
- Strong market fit (users expect onboarding guidance)
- Testable hypothesis: "If we guide users through core workflows, activation rate will increase from X% to Y%"

**Alternative POC:** Solution 3 (Human-assisted onboarding)
- If you want to learn fast with no dev work, start here
- Test manually with 20-50 trial users, gather qualitative feedback
- Use learnings to inform automated solution (Solution 1)

**Not recommended for POC:** Solution 2 (Time-to-value triggers)
- Requires more upfront investment
- Impact depends on trigger quality (needs experimentation to get right)
- Better as follow-up after validating core onboarding flow

---

### Question 5: Define Experiment

**Agent asks:**
"How will you test this solution? What's the experiment?"

**Offer 3 enumerated options:**

1. **A/B test** — "Build MVP, show to 50% of trial users, compare conversion vs. control" (Best for: Quantitative validation, requires traffic)
2. **Prototype + usability test** — "Create clickable prototype, watch 10 users attempt onboarding, gather qualitative feedback" (Best for: Early-stage validation, low traffic)
3. **Manual concierge test** — "Run the solution manually with 20 users (e.g., personally walk them through onboarding), measure outcomes" (Best for: Learning fast, no dev work)

**Or describe your experiment approach.**

**User response:** [Selection or custom]
