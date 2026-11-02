---
name: develop-prd
description: "Writes and grows a PRD that people read: problem, segment, success metric and non-goals on page one, no solution until the problem is agreed, then solution, EARS requirements, decisions log, cross-functional launch readiness and a post-launch impact section. Red-teams the draft before stakeholders see it. Use when the user wants the PRD document itself. Triggers on: 'write a PRD', 'create product requirements', 'draft a PRD', 'product requirements document', 'engineering-ready spec', 'update the PRD', 'PRD review', 'red-team my PRD'. Skip for: just the problem statement — use cct:product-playbook. Skip for: splitting work into stories — use break-down-epics."
allowed-tools: "Read Write"
user_invocable: true
metadata:
  version: 2.0.0
  author: Dean Peters
---

## Purpose

Nobody reads a PRD that is written in one go and parked. This skill writes one that is read:
it starts as one page the day the idea hits the backlog, grows one section per product review,
logs every decision so nothing is reopened, and ends with an Impact section that says whether
the metric moved. Twelve well-known templates (Figma, Linear, Intercom, Asana, Amazon, Lenny
Rachitsky, Product Hunt, SeatGeek, Square and more) disagree on shape; the 23 rules below are
what they agree on, and `template.md` is those rules as a document.

Use `template.md` for the structure. It is a mirror of the PRD that `cct:linear-manage`
writes into Linear, so a PRD produced here and one produced from the tracker are the same
document. Requirements go in as EARS sentences with `F`/`N` numbers inside the MoSCoW buckets;
the grammar is in `../ai-ready-issues/references/requirements-grammar.md`.

Never edit `template.md` directly: it is the mirror. Edit
`plugins/cct/skills/linear-manage/references/prd-template.md` and copy it across.
`scripts/check-requirements-grammar.py` fails the build if the two diverge.

## The gate: do you need a PRD at all?

Ask first. **No problem picked yet means no PRD.** Send the user to discovery
(`cct:product-playbook`) and stop. A two-day fix gets page one and nothing more. A PRD is
for work that needs more than one team to agree on what and why.

## The 23 rules

**Before you write a word**

1. Problem first. No solution on page one. (Intercom)
2. No problem picked yet? No PRD. Go and do discovery.
3. Write the success metric before the feature. (Lenny Rachitsky)
4. Say who it is for: a segment, never "users". (Product Hunt)
5. Write the non-goals. The section most teams skip and most need. (Asana)
6. Big launch? Write the press release first. (Amazon PR/FAQ)

**Write it as you go, not in one go**

7. Start the PRD the day the idea hits the backlog.
8. Fill it in at each product review: problem, solution, launch, impact.
9. Order the sections from least likely to change to most. (Nan Yu, Linear)
10. Match the detail to the risk. A two-day fix is not a two-month project.
11. Stay on one page until the problem is agreed. Then grow it. (Intercom, Adam Thomas)

**Make decisions stick**

12. Log every decision: the question, the call, who made it, when. (Adam Waxman, SeatGeek)
13. Write down the options you rejected, so nobody reopens them. (Linear)
14. Name the risks and how you will reduce them. (Steve Morin, Asana)
15. One owner. RACI everyone else.
16. Link everything to it. One link should answer any question.

**Keep it alive**

17. If engineers and designers are not opening it, something has gone wrong.
18. Every section you add, fewer people read it. (Product Hunt)
19. Edit it down every time you touch it. Curate, do not pile up.
20. Changed beyond recognition? Start a new one and link the old.

**Launch, then check**

21. Launch readiness is cross-functional: support, legal, marketing, FAQs. (Figma, Kevin Yien, Square)
22. Get it red-teamed before stakeholders see it. By a person or by Claude.
23. Write the Impact section. Did it move the metric? Almost no template asks.

## Workflow: four visits, not four days

Each visit is one product review. Between visits the document is read, not written.
`references/phases.md` has the questions, examples and outputs for each visit.

### Visit 1: page one (the day it hits the backlog)

Problem with evidence, the segment, the one success metric with its baseline and a guardrail,
the non-goals. Owner, RACI, links. **No solution.** Big launch: the press release and FAQ go
on top, written now. Stop here until the problem is agreed; a two-day fix stops here for good.

### Visit 2: solution and requirements (problem agreed)

Solution in two or three paragraphs at the shape level, design owns the pixels. Requirements
as numbered EARS sentences in MoSCoW buckets, with `[NEEDS CLARIFICATION: ...]` where nobody
may guess. Start the Decisions table with every call made so far and every rejected option.

### Visit 3: launch (build underway)

Target date or decision point, MVP scope, dependencies, the risks table, and the readiness
checklist with a name on every line: support, legal and privacy, marketing, FAQ, rollout.

### Visit 4: impact (the date the metric table names)

Observed value against baseline and target, verdict, what we learned. The document is done
when this section is filled, not when the feature ships.

### Facilitation

When running as a guided conversation, use `cct:product-playbook` →
`../product-playbook/references/facilitate-workshop.md`: one question per turn, progress
labels, numbered options.

## Red team before anyone else reads it

Before a draft goes to stakeholders, run one adversarial pass and fix what it finds. In one
turn, as a sceptical engineer, a sceptical designer and the customer in the segment, answer:

- What on page one is an assumption with no evidence line under it?
- Which requirement has an adjective where a number should be?
- Which non-goal will a stakeholder read as a goal?
- What will support, legal or marketing ask on day one that the document does not answer?
- Which rejected option is not written down, so it will be reopened?
- What would make the metric move without the feature working, or the feature work without
  the metric moving?

Each answer becomes an edit or a Decisions row. Then edit the document down: every sentence
that does not change what someone builds or decides goes.

## Maintenance rules

- On every touch: update **Last updated**, append to Decisions, delete something.
- A question in Slack that the PRD cannot answer with one link means a missing link or a
  missing line. Add it to the PRD, not to the thread.
- A PRD nobody opens for two sprints is either done (fill Impact) or dead (mark it, link the
  successor).
- A PRD changed beyond recognition is a new PRD; the old one keeps its Decisions and a link
  forward.

## Anti-patterns

- **A spec.** The PRD frames problem and solution; it does not specify the UI pixel by pixel.
- **A contract.** It evolves as the team learns; sections are revisited, not frozen.
- **A substitute for the conversation.** It records what was agreed in the room.
- **A pile.** Sections added because a template had them, never read, never removed.

Detailed pitfalls with symptoms and fixes: `references/pitfalls.md`. Examples: `examples/sample.md`.

## References

- Martin Eriksson, "How to Write a Good PRD" (2012)
- Marty Cagan, *Inspired* (2017)
- Amazon, "Working Backwards" (PR/FAQ)
- Nan Yu, Linear, on section ordering; Adam Waxman, SeatGeek, on decision logs

---

## Sources

| Source | Author | URL |
|--------|--------|-----|
| Product Manager Skills | Dean Peters | https://github.com/deanpeters/Product-Manager-Skills |
