# Story Mapping Examples & Pitfalls

## Example 1: Good Story Map (E-commerce Checkout)

**Q1 Response:** "Major feature area — E-commerce checkout workflow"

**Q2 Response:** "Single persona — Online shopper"

**Q3 - Backbone Generated:**
```
Browse → Add to Cart → Review Cart → Enter Shipping → Enter Payment → Confirm → Receive Confirmation
```

**Q4 - User Tasks Generated:**

```
Browse Products
├─ View product list (R1)
├─ Search/filter (R2)
└─ Product recommendations (R3)

Add to Cart
├─ Add single item (R1)
├─ Adjust quantity (R2)
└─ Save for later (R3)

Review Cart
├─ View line items + total (R1)
├─ Apply promo code (R2)
└─ Estimate shipping cost (R3)

[...etc...]
```

**Q5 - Release Slices:**
- **Release 1:** Walking skeleton — basic flow with no extras
- **Release 2:** Search, quantity adjustment, promo codes
- **Release 3:** Recommendations, guest checkout, gift options

**Why this works:**
- Backbone follows user narrative (not technical layers)
- Walking skeleton delivers end-to-end value
- Incremental releases add sophistication without breaking core flow

---

## Example 2: Bad Story Map (Technical Layers)

**Backbone (WRONG):**
```
UI Layer → API Layer → Database Layer → Deployment
```

**Why this fails:**
- Not user-centric (users don't care about technical architecture)
- Can't deliver end-to-end value incrementally
- Waterfall thinking disguised as story mapping

**Fix:**
- Map by user workflow: "Sign Up → Configure Settings → Invite Team → Start Project"
- Each release delivers full workflow, not a single layer

---

## Common Pitfalls

### Pitfall 1: Flat Backlog in Disguise
**Symptom:** Story map is just a vertical list, no horizontal narrative
**Consequence:** Loses communication benefit; still "context-free mulch"
**Fix:** Force horizontal structure — activities across top, tasks descending vertically

### Pitfall 2: Technical Architecture as Backbone
**Symptom:** Backbone = "Frontend → Backend → Database"
**Consequence:** Not user-centric, can't deliver value incrementally
**Fix:** Backbone should follow user workflow, not system layers

### Pitfall 3: Feature-Complete Waterfall
**Symptom:** Release 1 = "Build Activity 1 fully," Release 2 = "Build Activity 2 fully"
**Consequence:** No end-to-end value until all activities complete
**Fix:** Walking skeleton = thin slice across ALL activities, incrementally enhanced

### Pitfall 4: Too Much Detail Too Soon
**Symptom:** Trying to map every edge case and acceptance criterion upfront
**Consequence:** Analysis paralysis, lost big picture
**Fix:** Start with backbone + high-level tasks, refine later

### Pitfall 5: Map Hidden in a Tool
**Symptom:** Story map lives in Jira/Miro, never displayed
**Consequence:** Loses value as information radiator
**Fix:** Print/post map physically; make it visible to team daily
