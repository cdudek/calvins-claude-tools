# Epic Breakdown Output Template

Use this template when generating story breakdowns.

```markdown
# Epic Breakdown Plan

**Epic:** [Original epic]
**Pre-Split Validation:** Passes INVEST (except Small)
**Splitting Pattern Applied:** [Pattern name]
**Rationale:** [Why this pattern fits]

---

## Story Breakdown

### Story 1: [Title] (Simplest Complete Slice)

**Summary:** [User-value-focused title]

**Use Case:**
- **As a** [persona]
- **I want to** [action]
- **so that** [outcome]

**Acceptance Criteria:**
- **Given:** [Preconditions]
- **When:** [Action]
- **Then:** [Outcome]

**Why This First:** [Delivers core value; simpler variations follow]
**Estimated Effort:** [Days/points]

---

### Story 2: [Title] (First Variation)

[Repeat...]

---

### Story 3: [Title] (Second Variation)

[Repeat...]

---

## Split Evaluation

**Does this split reveal low-value work?**
- [Analysis: Which stories could be deprioritized/eliminated?]

**Does this split produce equal-sized stories?**
- [Analysis: Are stories roughly equal in effort?]

---

## INVEST Validation (Each Story)

- **Independent:** Stories can be developed in any order
- **Negotiable:** Implementation details can be discovered collaboratively
- **Valuable:** Each story delivers observable user value
- **Estimable:** Team can size each story
- **Small:** Each story fits in 1-5 days
- **Testable:** Clear acceptance criteria for each

---

## Next Steps

1. **Review with team:** Do PM, design, engineering agree?
2. **Check for further splitting:** Are any stories still >5 days? If yes, **restart at Pattern 1** for that story.
3. **Prioritize:** Which story delivers most value first?
4. **Consider eliminating:** Did split reveal low-value stories? Kill or defer them.

---

**If stories are still too large, re-apply patterns starting at Pattern 1.**
```
