# Problem Framing Question Guide

Detailed facilitation questions and adaptive options for each phase of the MITRE Problem Framing Canvas.

---

## Step 0: Gather Context (Before Questions)

**Agent suggests:**

Before we frame your problem, let's gather context:

**Problem Context:**
- Initial problem statement or stakeholder request
- Symptoms you've observed (support tickets, churn data, user complaints)
- Existing research (user interviews, surveys, analytics)
- Assumptions you're making about the problem

**Stakeholder Context:**
- Who's affected by this problem? (users, customers, internal teams)
- Who's asking for this to be solved? (execs, sales, customers)
- Who might have been overlooked?

**You can paste this content directly, or describe the problem briefly.**

---

## Phase 1: Look Inward

**Goal:** Examine your own assumptions, biases, and how you might be part of the problem.

---

### Question 1: What is the problem? (Describe symptoms)

**Agent asks:**
"What is the problem as you currently understand it? Describe the symptoms."

**Offer 4 enumerated options:**

1. **Customer pain point** — "Customers struggle with [specific task/outcome]" (e.g., "Customers can't find features they need")
2. **Business metric problem** — "We're seeing [metric decline]" (e.g., "Churn increased 15% last quarter")
3. **Stakeholder request** — "Stakeholders say we need [feature/change]" (e.g., "Sales team says we need better reporting")
4. **Observed behavior** — "We've noticed [pattern/trend]" (e.g., "Users abandon onboarding at step 3")

**Or describe your problem/symptoms.**

**User response:** [Selection or custom]

**Agent extracts:**
- **Problem (initial framing):** [Description from user]

---

### Question 2: Why haven't we solved it?

**Agent asks:**
"Why hasn't this problem been solved yet?"

**Offer 6 enumerated options (can select multiple):**

1. **It's new** — "Problem recently emerged"
2. **It's hard** — "Technically complex or resource-intensive"
3. **It's low priority** — "Other initiatives took precedence"
4. **Lack of resources** — "Not enough budget, people, or time"
5. **Lack of authority** — "Can't make the decision or get buy-in"
6. **A systemic inequity** — "Problem disproportionately affects marginalized groups, overlooked"

**Or describe your own reason.**

**User response:** [Selection or custom]

**Agent captures:**
- **Barriers to solving:** [List of reasons]

---

### Question 3: How are we part of the problem? (Assumptions & biases)

**Agent asks:**
"How might you (or your team) be part of the problem? What assumptions or biases are you bringing?"

**Offer 4 enumerated options:**

1. **Assuming we know what customers want** — "We haven't validated with real users" (Confirmation bias)
2. **Optimizing for ourselves, not users** — "Building what's easy for us, not what's valuable for them" (Internal bias)
3. **Overlooking specific user segments** — "Focused on majority users, ignored edge cases or marginalized groups" (Survivorship bias)
4. **Solution-first thinking** — "Jumped to 'we need [feature X]' before understanding root problem" (Premature convergence)

**Or describe your specific assumptions/biases.**

**User response:** [Selection or custom]

**Agent captures:**
- **Assumptions to challenge:** [List of biases]

---

## Phase 2: Look Outward

**Goal:** Understand who experiences the problem, who benefits from it, and who's been left out.

---

### Question 4: Who experiences the problem? (When, where, consequences)

**Agent asks:**
"Who experiences this problem? When and where do they experience it? What consequences do they face?"

**Agent prompts user to describe:**
- **Who:** Specific personas, user segments, or roles
- **When:** Triggering events or contexts (e.g., "during onboarding," "at month-end close")
- **Where:** Physical or digital locations (e.g., "mobile app," "enterprise deployments")
- **Consequences:** Impact on users (e.g., "waste 2 hours/week," "miss deadlines," "churn")

**Adaptation:** Use personas from context (proto-personas, JTBD, customer research)

**User response:** [Detailed description]

**Agent captures:**
- **Who experiences it:** [Personas/segments]
- **When/where:** [Context]
- **Consequences:** [Impact]

---

### Question 5: Who else has this problem? Who doesn't have it?

**Agent asks:**
"Who else has this problem? (Colleagues, competitors, other domains?) And who doesn't have it?"

**Agent prompts:**
- **Who else has it:** Other companies, industries, or domains with similar problems
- **How do they deal with it:** Workarounds, solutions, or adaptations
- **Who doesn't have it:** Users/companies that avoid the problem (what's different about them?)

**User response:** [Detailed description]

**Agent captures:**
- **Who else has it:** [Examples]
- **Who doesn't have it:** [Counter-examples]

---

### Question 6: Who's been left out? Who benefits?

**Agent asks:**
"Who's been left out of the conversation so far? And who benefits when this problem exists or doesn't exist?"

**Agent prompts:**
- **Who's been left out:** Marginalized voices, edge cases, overlooked stakeholders
- **Who benefits when problem exists:** Who gains from the status quo?
- **Who benefits when problem doesn't exist:** Who loses if problem is solved?

**Example:**
- "Who benefits when onboarding is broken?" → "Sales team doesn't have to support complex workflows; engineering doesn't have to build guided flows"
- "Who's been left out?" → "Non-technical users, international customers (onboarding in English only)"

**User response:** [Detailed description]

**Agent captures:**
- **Who's been left out:** [List]
- **Who benefits (problem exists):** [List]
- **Who benefits (problem solved):** [List]

---

## Phase 3: Reframe

**Goal:** Synthesize insights into a clear, actionable problem statement and "How Might We" question.

---

### Question 7: Restate the problem

**Agent says:**
"Based on everything we've explored, let's restate the problem in a new way."

**Agent generates a refined problem statement** using insights from Phases 1-2:

**Template:**
"The problem is: [Who] struggles to [accomplish what] because [root cause], which leads to [consequence]. This affects [specific segments] and has been overlooked because [bias/assumption from Phase 1]."

**Example (SaaS onboarding):**
"The problem is: Non-technical small business owners struggle to activate our product during onboarding because we use jargon-heavy UI and lack guided workflows, which leads to 60% abandonment within 24 hours. This disproportionately affects solopreneurs without technical support, and has been overlooked because our team optimizes for enterprise users who have IT departments."

**Agent asks:**
"Does this restatement capture the core problem? Should we refine it?"

**User response:** [Approve or modify]

---

### Question 8: Create "How Might We" statement

**Agent says:**
"Now let's make it actionable with a 'How Might We' statement."

**Template:**
"How might we [action that addresses the problem] as we aim to [objective/desired condition]?"

**Example (SaaS onboarding):**
"How might we guide non-technical users through onboarding with plain-language prompts as we aim to increase activation from 40% to 70%?"

**Agent asks:**
"Does this HMW statement set up the right solution space? Should we adjust?"

**User response:** [Approve or modify]
