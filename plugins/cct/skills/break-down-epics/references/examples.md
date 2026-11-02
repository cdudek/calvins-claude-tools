# Epic Breakdown Examples

## Example 1: Pattern 1 Applied (Workflow Steps - Thin End-to-End)

**Epic:** "Publish blog post (requires editorial review, legal approval, staging)"

**Pre-Split Validation:** Passes INVEST

**Pattern 1:** "Does this have workflow steps?" → YES

**Wrong Split (Step-by-Step):**
1. Editorial review story
2. Legal approval story
3. Publish story
→ Problem: Story 1 doesn't deliver value (users see nothing)

**Right Split (Thin End-to-End):**
1. **Publish post (simple path)** — Author uploads, post goes live immediately (no reviews)
2. **Add editorial review** — Post now waits for editor approval before going live
3. **Add legal approval** — Post waits for legal + editorial before going live

**Why this works:** Each story delivers **full workflow**, just with increasing sophistication.

---

## Example 2: Pattern 2 Applied (CRUD Operations)

**Epic:** "Manage user profiles"

**Pattern 2:** "Does this say 'manage'?" → YES (signals CRUD)

**Split:**
1. Create user profile
2. View user profile details
3. Edit user profile info
4. Delete user profile

**Split Evaluation:**
- **Reveals low-value work:** After analysis, "Delete profile" is rarely used → deprioritize
- **Equal-sized stories:** Each 1-2 days

---

## Example 3: Pattern 7 Applied (Simple/Complex)

**Epic:** "Flight search with max stops, nearby airports, flexible dates"

**Pattern 7:** "What's the simplest version?" → Basic search

**Split:**
1. Basic flight search (origin, destination, date) — **Core value**
2. Add max stops filter — **Enhancement**
3. Add nearby airports option — **Enhancement**
4. Add flexible dates option — **Enhancement**

**Split Evaluation:**
- **Reveals low-value work:** User research shows "flexible dates" rarely used → kill or defer
- **Equal-sized stories:** Story 1 = 3 days, others = 1 day each

---

## Example 4: Iterative Splitting (Multiple Patterns)

**Epic:** "Checkout flow with discounts (member, VIP, first-time) and payment (Visa, Mastercard, Amex)"

**First Pass - Pattern 1 (Workflow):** YES
- Story 1: Add items to cart
- Story 2: Apply discount
- Story 3: Complete payment

**Check Story 2 ("Apply discount"):** Still 4 days → Too large, re-split

**Second Pass on Story 2 - Pattern 3 (Business Rules):** YES
- Story 2a: Apply member discount (10%)
- Story 2b: Apply VIP discount (20%)
- Story 2c: Apply first-time discount (5%)

**Check Story 3 ("Complete payment"):** Still 5 days → Too large, re-split

**Third Pass on Story 3 - Pattern 6 (Major Effort):** YES
- Story 3a: Accept Visa payments (build payment infrastructure)
- Story 3b: Add Mastercard, Amex support

**Final Breakdown:** 6 stories, all 1-2 days each
