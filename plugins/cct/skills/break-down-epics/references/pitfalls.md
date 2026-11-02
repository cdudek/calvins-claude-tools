# Common Pitfalls

## Pitfall 1: Skipping Pre-Split Validation
**Symptom:** Jump straight to splitting without checking INVEST

**Consequence:** Split a story that shouldn't be split (e.g., not Valuable = technical task)

**Fix:** Always run Step 1 (INVEST check) before Step 2 (splitting patterns)

---

## Pitfall 2: Step-by-Step Workflow Splitting (Pattern 1 Done Wrong)
**Symptom:** Story 1 = "Editorial review," Story 2 = "Legal approval"

**Consequence:** Stories don't deliver end-to-end value

**Fix:** Each story should cover **full workflow** (thin end-to-end slice), just with increasing sophistication

---

## Pitfall 3: Horizontal Slicing (Technical Layers)
**Symptom:** "Story 1: Build API. Story 2: Build UI."

**Consequence:** Neither story delivers user value

**Fix:** Vertical slicing—each story includes front-end + back-end to deliver observable user behavior

---

## Pitfall 4: Forcing a Pattern That Doesn't Fit
**Symptom:** "We'll split by workflow even though there's no sequence"

**Consequence:** Arbitrary, meaningless split

**Fix:** If pattern doesn't apply, say NO and continue to next pattern

---

## Pitfall 5: Not Re-Splitting Large Stories
**Symptom:** Split epic into 3 stories, but each is still 5+ days

**Consequence:** Stories too large for sprint

**Fix:** **Restart at Pattern 1** for each large story until all are 1-5 days

---

## Pitfall 6: Ignoring Split Evaluation (Step 3)
**Symptom:** Split but don't evaluate if it reveals low-value work

**Consequence:** Miss opportunity to eliminate waste

**Fix:** After splitting, ask: "Does this reveal work we can kill or defer?"
