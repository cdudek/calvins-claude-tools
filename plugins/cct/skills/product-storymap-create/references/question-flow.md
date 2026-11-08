# Story Mapping Question Flow

Detailed adaptive questions with enumerated options for each step.

## Step 0: Gather Context (Before Questions)

**Agent suggests:**

Before we create your story map, let's gather context:

**Product/Feature Context:**
- What system or feature are you mapping?
- Product concept, PRD draft, or existing backlog
- Website copy, positioning materials, or user flows
- Existing user stories (if transitioning from flat backlog)

**User Context:**
- Target personas or user segments
- User research, interviews, or journey maps
- Jobs-to-be-done or problem statements

**You can paste this content directly, or describe the system briefly.**

---

## Question 1: Define Scope

**Agent asks:**
"What are you mapping? (What's the scope?)"

**Offer 4 enumerated options:**

1. **Entire product** — "Full end-to-end system from discovery to completion" (Common for new products or full rewrites)
2. **Major feature area** — "Specific workflow within a larger product (e.g., 'onboarding,' 'checkout,' 'reporting')" (Common for feature launches)
3. **User journey** — "Specific user goal or job-to-be-done (e.g., 'hire a contractor,' 'file taxes')" (Common for JTBD-driven mapping)
4. **Redesign/refactor** — "Existing product/feature being rebuilt or simplified" (Common for legacy system modernization)

**Or describe your specific scope.**

---

## Question 2: Identify Users/Personas

**Agent asks:**
"Who are the primary users for this map? (List personas or user segments.)"

**Offer 4 enumerated options:**

1. **Single persona** — "One primary user type (e.g., 'small business owner')" (Simplifies mapping, good for MVP)
2. **Multiple personas, shared workflow** — "Different user types, same core activities (e.g., 'buyer' and 'seller' both browse listings)" (Common for marketplaces)
3. **Multiple personas, different workflows** — "Different user types with distinct workflows (e.g., 'admin' vs. 'end user')" (Requires separate maps or swim lanes)
4. **Roles within organization** — "Different job functions (e.g., 'PM,' 'designer,' 'engineer')" (Common for internal tools)

**Or describe your users.**

**Adaptation:** Use personas from context provided in Step 0 (proto-personas, JTBD, etc.)

---

## Question 3: Generate Backbone (Activities)

**Agent says:**
"Let's build the backbone—the narrative flow of activities users perform to accomplish their goal."

**Agent generates 5-8 activities** based on scope (Q1) and users (Q2), arranged left-to-right in workflow order.

**Example (if Scope = "E-commerce checkout"):**

```
Backbone Activities (left to right):

1. Browse Products
2. Add to Cart
3. Review Cart
4. Enter Shipping Info
5. Enter Payment Info
6. Confirm Order
7. Receive Confirmation
```

**Agent asks:**
"Does this backbone capture the full workflow? Should we add, remove, or reorder activities?"

---

## Question 4: Generate User Tasks (Under Each Activity)

**Agent says:**
"Now let's add user tasks under each activity, organized by priority (top = must-have, bottom = nice-to-have)."

**Agent generates 3-5 user tasks per activity**, arranged vertically by priority.

**Example (for Activity 2: "Add to Cart"):**

```
Add to Cart (Activity)
├─ Add single item to cart (must-have, walking skeleton)
├─ Adjust quantity (must-have)
├─ Add multiple items at once (should-have)
├─ Save item for later (nice-to-have)
└─ Add gift wrapping (nice-to-have)
```

**Agent repeats for all backbone activities**, showing the full map.

**Agent asks:**
"Does this capture the key tasks? Are priorities correct (top = MVP, bottom = later releases)?"

---

## Question 5: Identify Release Slices (Walking Skeleton + Increments)

**Agent says:**
"Let's define release slices by drawing horizontal lines across the map."

**Agent generates 3 release slices:**

**Release 1 (Walking Skeleton):** Top-priority tasks across all activities — minimal end-to-end functionality

**Release 2 (Next Increment):** Second-priority tasks that enhance the core workflow

**Release 3 (Polish/Expansion):** Third-priority tasks (nice-to-haves, edge cases, optimizations)

**Agent asks:**
"Do these release slices make sense? Should we adjust scope or priorities?"
