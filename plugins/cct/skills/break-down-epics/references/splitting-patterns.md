# Splitting Patterns — Detailed Instructions

## Step 0: Provide Epic Context

**Agent asks:**

Please share your epic:

- Epic title/ID
- Description or hypothesis
- Acceptance criteria (especially multiple "When/Then" pairs)
- Target persona
- Rough estimate

**You can paste from Jira, Linear, or describe briefly.**

---

## Step 1: Pre-Split Validation (INVEST Check)

**Before splitting, verify your story satisfies INVEST criteria (except "Small"):**

**Agent asks questions sequentially:**

**1. Independent?**
"Can this story be prioritized and developed without hard technical dependencies on other stories?"

**Options:**
- Yes — No blocking dependencies
- No — Requires other work first (flag this)

---

**2. Negotiable?**
"Does this story leave room for the team to discover implementation details collaboratively, rather than prescribing exact solutions?"

**Options:**
- Yes — It's a conversation starter, not a spec
- No — It's too prescriptive (may need reframing)

---

**3. Valuable?**
"Does this story deliver observable value to a user? (If not, combine it with related work rather than splitting.)"

**Options:**
- Yes — Users see/experience something different
- No — It's a technical task (not a user story—don't split, reframe)

**Critical Check:** If story fails "Valuable," STOP. Don't split. Instead, combine with other work to create a meaningful increment.

---

**4. Estimable?**
"Can your team size this story relatively (even if roughly)?"

**Options:**
- Yes — Team can estimate days/points
- No — Too much uncertainty (may need spike first)

---

**5. Testable?**
"Does this story have concrete acceptance criteria that QA can verify?"

**Options:**
- Yes — Clear pass/fail conditions
- No — Needs clearer acceptance criteria (refine before splitting)

---

**If story passes all checks → Proceed to Step 2 (Splitting Patterns)**
**If story fails any check → Fix the issue before splitting**

---

## Step 2: Apply Splitting Patterns Sequentially

Work through patterns in order. For each pattern, ask "Does this apply?"

---

### Pattern 1: Workflow Steps

**Key insight:** Split into **thin end-to-end slices**, not step-by-step. Start with a simple case covering the **full workflow**, then add intermediate steps as separate stories.

**Agent asks:**
"Does your epic involve a multi-step workflow where you could deliver a simple case first, then add intermediate steps later?"

**Example:**
- **Original:** "Publish content (requires editorial review, legal approval, staging)"
- **Wrong split (step-by-step):** Story 1 = Editorial review, Story 2 = Legal approval, Story 3 = Publish
- **Right split (thin end-to-end):**
  - Story 1: Publish content (simple path: author uploads, content goes live immediately—no reviews)
  - Story 2: Add editorial review step (now content waits for editor approval before going live)
  - Story 3: Add legal approval step (content waits for legal + editorial before going live)

**Each story delivers full workflow**, just with increasing sophistication.

**Options:**
1. **Yes, multi-step workflow** → "Describe the workflow steps"
2. **No, single step** → Continue to Pattern 2

**If YES:** Agent generates thin end-to-end slice splits.

---

### Pattern 2: Operations (CRUD)

**Key insight:** The word "manage" signals multiple operations. Split into Create, Read, Update, Delete.

**Agent asks:**
"Does your epic use words like 'manage,' 'handle,' or 'maintain'? If so, it likely bundles multiple operations (CRUD)."

**Example:**
- **Original:** "Manage user accounts"
- **Split:**
  - Story 1: Create user account
  - Story 2: View user account details
  - Story 3: Edit user account info
  - Story 4: Delete user account

**Options:**
1. **Yes, contains multiple operations** → "List the operations (Create/Read/Update/Delete/etc.)"
2. **No, single operation** → Continue to Pattern 3

**If YES:** Agent generates one story per operation.

---

### Pattern 3: Business Rule Variations

**Key insight:** When identical functionality operates under different rules, each rule becomes its own story.

**Agent asks:**
"Does your epic have different business rules for different scenarios (user types, regions, tiers, conditions)?"

**Example:**
- **Original:** "Flight search with flexible dates (date range, specific weekends, date offsets)"
- **Split:**
  - Story 1: Search by date range (+/- N days)
  - Story 2: Search by specific weekends only
  - Story 3: Search by date offsets (N days before/after)

**Options:**
1. **Yes, different rules** → "Describe the rule variations"
2. **No, same rules for all** → Continue to Pattern 4

**If YES:** Agent generates one story per rule variation.

---

### Pattern 4: Data Variations

**Key insight:** Complexity from handling different data types or structures. Add variations **just-in-time** as needed.

**Agent asks:**
"Does your epic handle different data types, formats, or structures (e.g., file types, geographic levels, user attributes)?"

**Example:**
- **Original:** "Geographic search (counties, cities/towns/neighborhoods, custom provider areas)"
- **Split:**
  - Story 1: Search by county
  - Story 2: Add city/town/neighborhood search
  - Story 3: Add custom provider area search

**Options:**
1. **Yes, different data types** → "List the data variations"
2. **No, single data type** → Continue to Pattern 5

**If YES:** Agent generates one story per data variation (deliver simplest first).

---

### Pattern 5: Data Entry Methods

**Key insight:** UI complexity independent of core functionality. Build simplest interface first, then add sophisticated UI as follow-ups.

**Agent asks:**
"Does your epic include fancy UI elements (date pickers, autocomplete, drag-and-drop) that aren't essential to core functionality?"

**Example:**
- **Original:** "Search with calendar date picker"
- **Split:**
  - Story 1: Search by date (basic text input: "YYYY-MM-DD")
  - Story 2: Add visual calendar picker UI

**Options:**
1. **Yes, fancy UI elements** → "Describe the UI enhancements"
2. **No, basic UI only** → Continue to Pattern 6

**If YES:** Agent generates Story 1 = basic input, Story 2+ = UI enhancements.

---

### Pattern 6: Major Effort

**Key insight:** When **initial implementation** carries most complexity, with additions being trivial. Frame as "implement one + add remaining."

**Agent asks:**
"Does your epic involve building infrastructure where the **first implementation** is hard, but adding more is easy?"

**Example:**
- **Original:** "Accept credit card payments (Visa, Mastercard, Amex, Discover)"
- **Split:**
  - Story 1: Accept Visa payments (build full payment infrastructure)
  - Story 2: Add Mastercard, Amex, Discover support (trivial additions)

**Note:** First story does the heavy lift (payment gateway, security, compliance). Subsequent stories are small additions.

**Options:**
1. **Yes, major effort pattern** → "What's the first implementation + what are the additions?"
2. **No, no infrastructure work** → Continue to Pattern 7

**If YES:** Agent generates Story 1 = build infrastructure, Story 2 = add remaining variants.

---

### Pattern 7: Simple/Complex

**Key insight:** Identify story's core by asking "What's the simplest version?" Extract variations into separate stories.

**Agent asks:**
"What's the **simplest version** of this epic that still delivers value? Can you strip away complexity and add it back later?"

**Example:**
- **Original:** "Flight search (with max stops, nearby airports, flexible dates)"
- **Split:**
  - Story 1: Basic flight search (origin, destination, date)
  - Story 2: Add max stops filter
  - Story 3: Add nearby airports option
  - Story 4: Add flexible dates option

**Options:**
1. **Yes, can identify simplest core** → "Describe the simplest version + what variations to defer"
2. **No, it's already simple** → Continue to Pattern 8

**If YES:** Agent generates Story 1 = simplest core, Story 2+ = variations.

---

### Pattern 8: Defer Performance

**Key insight:** Split "make it work" from "make it fast." Non-functional requirements (performance, security, scalability) can follow functional delivery.

**Agent asks:**
"Can you deliver functional value first, then optimize performance/security/scalability later?"

**Example:**
- **Original:** "Real-time search with <100ms response time"
- **Split:**
  - Story 1: Search works (functional, no performance guarantee)
  - Story 2: Optimize search to <100ms (add caching, indexing)

**Options:**
1. **Yes, can defer optimization** → "What's the functional version + what's the optimization?"
2. **No, performance is essential** → Continue to Pattern 9

**If YES:** Agent generates Story 1 = functional, Story 2 = optimize.

---

### Pattern 9: Break Out a Spike

**Key insight:** Last resort when **uncertainty prevents splitting**. Time-box investigation to answer specific questions, then split implementation story with better understanding.

**Agent says:**
"None of patterns 1-8 apply, which suggests **high uncertainty**. Before splitting, run a **spike** to reduce uncertainty."

**A spike is a time-boxed investigation (not a story), answering questions like:**
- Is this technically feasible?
- Which approach performs best?
- What does the API actually return?

**Agent asks:**
"What's the biggest unknown preventing you from splitting this epic?"

**Options:**
1. **Technical feasibility** — "Can we build this with our stack?"
2. **Approach uncertainty** — "Multiple ways to solve it, unclear which is best"
3. **External dependency** — "Don't know what third-party API provides"

**Agent recommends:**
→ "Run a 1-2 day spike to answer [question]. After the spike, come back and we'll split the epic with better understanding."

**Spikes produce learning, not shippable code. After the spike, restart at Pattern 1.**

---

## Step 3: Evaluate Split Quality

**After splitting, evaluate using these criteria:**

**Agent asks:**

**1. Does this split reveal low-value work you can deprioritize or eliminate?**
- Good splits expose the 80/20 principle: most value concentrates in a small portion of functionality
- Example: After splitting "Flight search" into 4 stories, you realize "flexible dates" is rarely used → deprioritize or kill it

**2. Does this split produce more equally-sized stories?**
- Equal-sized stories give Product Owners greater prioritization flexibility
- Example: Instead of one 10-day epic, five 2-day stories allow reordering mid-sprint

**If split doesn't satisfy either criterion, try a different pattern.**

---

## Meta-Pattern Application

**Across all patterns, follow this sequence:**
1. **Identify core complexity** — What makes this epic hard?
2. **List variations** — What are all the different ways/cases/rules?
3. **Reduce to one complete slice** — Pick the simplest variation that still delivers end-to-end value
4. **Make other variations separate stories**

---

## Cynefin Domain Considerations

**Strategy shifts based on complexity domain:**

**Agent asks:**
"How much uncertainty surrounds this epic?"

**Options:**

1. **Low uncertainty (Obvious/Complicated domain)** — "We know what to build; it's just engineering work"
   → Find all stories, prioritize by value/risk

2. **High uncertainty (Complex domain)** — "We're not sure what customers want or what will work"
   → Identify 1-2 **learning stories**; avoid exhaustive enumeration (work itself teaches what matters)

3. **Chaos** — "Everything is on fire; priorities shift daily"
   → **Defer splitting** until stability emerges; focus on stabilization first
