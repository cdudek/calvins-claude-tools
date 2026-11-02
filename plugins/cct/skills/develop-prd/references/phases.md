# The four visits

A PRD is written at four product reviews, not in one sitting. Each visit has the questions to
ask, an example of the output, and the state the document is in when the visit ends. Between
visits the document is read and linked, not rewritten.

## Visit 1: page one

**When:** the day the idea hits the backlog. **Who:** the owner, alone is fine.
**Ends with:** Status `Page one`. No solution anywhere in the document.

### Questions

1. Who has this problem? Name the segment and its size, with a source.
2. What happens to them, in their words? One quote, one number, one support theme.
3. What does it cost them, and us? What happens if we do nothing?
4. Why now? What changed?
5. Which one metric must move, from what to what, measured how and when? What must not get worse?
6. What is this not? Which adjacent request will someone assume is included?
7. Who owns it, who is consulted, who is informed?
8. Big launch? Write the press release dated launch day and the FAQ first. Not exciting? Stop.

### Example

```markdown
## Problem

Solo founders (1 person, no IT) sign up, see an empty dashboard and leave. 60% complete no
action in the first 24 hours. "I logged in, saw nothing, and went back to my spreadsheet."

**Evidence:**

- 60% of signups complete 0 actions in 24 h (Mixpanel, Jan 2026)
- 8 of 10 churned users in discovery said "I didn't know what to do first" (Feb 2026)
- "How do I get started?" is the #1 support question, 350 tickets a month (Zendesk, Q4 2025)

**Why now:** churn rose 15% in Q4; first-30-day churn is 60% of it.

**Cost of not solving:** retention OKR (15% → 8%) is unreachable without first-day activation.

## Who it is for

| Segment | Size | Current pain | What they will do with this |
|---|---|---|---|
| Solo founders, no IT | 500k of 5M SaaS-using SMBs (SOM, 2025 survey) | no first step | reach the first project in one session |

## Success metric

| Metric | Current | Target | How measured | When measured |
|---|---|---|---|---|
| Activation: first action within 24 h | 40% | 60% | Mixpanel funnel | 30 days after launch |
| Guardrail: signup conversion | 10% | ≥ 10% | Mixpanel | weekly |

## Non-goals

- Per-persona onboarding variants: prove the one checklist first
- Embedded video tutorials: resource-heavy, validate the checklist concept first
- Gamification: not a guidance problem
```

Stop here until the problem is agreed. A two-day fix stops here for good.

## Visit 2: solution and requirements

**When:** the problem is agreed. **Who:** owner with design and engineering.
**Ends with:** Status `Draft`, red-teamed, and Decisions holds every call so far.

### Questions

1. What are we building, as a shape? Two or three paragraphs. What does design own?
2. Which flows? Link them, never embed a local path.
3. What must be true for launch, as EARS sentences with a number each? What is Should, Could,
   Won't?
4. Where is an adjective standing in for a number?
5. What does nobody know yet? Mark it `[NEEDS CLARIFICATION: ...]` next to the requirement.
6. Which options were rejected on the way here, and why? Into Decisions.

### Example

```markdown
## Solution

A guided checklist on first login: three steps (create a project, invite a teammate, complete
a sample task), dismissible, with a progress bar and a completion message. Design owns the
layout and copy; this document owns the three steps and the dismiss rule.

## Requirements

### Must have (required for launch)

- [ ] **F1** When a user logs in for the first time, the system shall show the checklist within 1 s of the dashboard rendering.
- [ ] **F2** When a user dismisses the checklist, the system shall not show it again on that account.
- [ ] **F3** When a step is completed, the system shall mark it done within 1 s, in any order.
- [ ] **N1** The checklist shall add no more than 100 ms at p95 to dashboard load.

### Should have

- [ ] **F4** When all three steps are done, the system shall show the next three suggested actions.

### Won't have (not this version)

- Per-segment checklists (Non-goals)

## Decisions

| Date | Question | Call | Who | Rejected, and why |
|---|---|---|---|---|
| 2026-02-14 | Mandatory or dismissible? | Dismissible, never re-shown | Sam K. | Mandatory: founders in discovery called forced tours "the reason I leave" |
| 2026-02-14 | Steps in fixed order? | Any order | Sam K. | Fixed: blocks a founder who already has a project |
```

## Visit 3: launch

**When:** build is underway. **Who:** owner with support, marketing, legal where touched.
**Ends with:** a name on every readiness line, or the line struck through.

### Questions

1. Target date, or the decision point that fixes it?
2. What is the smallest v1?
3. Who do we need something from, by when?
4. What can go wrong, how likely, how bad, who is reducing it?
5. What does support answer on day one? What does legal need to see? Who is told first?
6. What are the five questions customers will ask? Answer them now.
7. Flag, cohort, rollback?

## Visit 4: impact

**When:** the date the Success metric table names. **Who:** the owner.
**Ends with:** Status `Measured`. The document is done.

### Questions

1. What is the observed value, from where, on what date?
2. Did it move: yes, no, too early?
3. Did the guardrail hold?
4. What would we do differently? One paragraph, honest.

### Example

```markdown
## Impact

| Metric | Baseline | Target | Observed | Verdict |
|---|---|---|---|---|
| Activation within 24 h | 40% | 60% | 54% (Mixpanel, 2026-04-15, n = 2,310) | moved, short of target |
| Signup conversion | 10% | ≥ 10% | 10.2% | held |

**What we learned:** the third step (sample task) is where 30% stop. The next PRD starts
from that number, not from a new feature idea.
```
