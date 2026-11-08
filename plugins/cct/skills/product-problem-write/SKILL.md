---
name: product-problem-write
description: "Writes the problem statement that briefs and PRDs reuse, from the user's side: persona, desired outcome, barrier, root cause, felt impact, constraints, then one sentence. Two methods: frame a problem from existing research, or reframe a stuck one with the MITRE Problem Framing Canvas (look inward at assumptions, look outward at who is affected and left out, then a problem statement and a How Might We question). Use when the user says 'write the problem statement', 'frame this user problem', 'reframe the problem', 'problem framing canvas', 'how might we statement'. Skip for: the design brief with audience, constraints and success criteria - use cct:ux-brief-write. Skip for: the full requirements document - use cct:product-prd-write."
allowed-tools: "Read Write"
user_invocable: true
---

# Write the problem statement

Produce the problem statement that `cct:ux-brief-write` and `cct:product-prd-write` reuse. It is a human-centred narrative, not a requirements document and not a solution. The PRD defines the solution; this skill makes sure the problem is worth solving and agreed before anyone solves it.

## Pick the method

- **Frame** (`references/frame-problem.md`): you have user research, quotes or observed behaviour and need a crisp statement to align stakeholders. Output: I am / Trying to / But / Because / Which makes me feel, context and constraints, and one final sentence (`[Persona] needs a way to [outcome] because [root cause], which currently [impact]`). Template: `references/frame-problem/template.md`; examples, good and bad: `references/frame-problem/examples/sample.md`.
- **Reframe** (`references/reframe-problem.md`): the problem is stuck, politically loaded or arrived as a solution ("we need a dashboard"). Output: the MITRE canvas, a refined problem statement (`[Who] struggles to [what] because [root cause], leading to [consequence]`) and a HMW statement (`How might we [action] as we aim to [objective]?`). It is interactive and works best with several people; it follows the facilitation protocol in `${CLAUDE_SKILL_DIR}/../product-playbook/references/facilitate-workshop.md`. Template and examples are under `references/reframe-problem/`.

Often both: reframe first, then frame the result into the formal statement.

## Rules for either method

- Do not fabricate. If there is no user research, say so and run interviews first (`cct:product-discovery-run` coordinates them); do not guess the persona, the barriers or the emotions.
- Reject solution smuggling ("the problem is we lack X"), company problems dressed as user problems ("churn is high"), generic personas, symptoms instead of root causes (keep asking why) and invented emotions (use real quotes: frustrated, stuck, anxious).
- The statement is one sentence, measurable (you can tell if it is solved) and could be said in a meeting so that stakeholders nod.
- Validate before handing over: read it to people who have the problem and to the stakeholders; if anyone says "that is not the real problem", dig further.
- Save the result where the project keeps product documents (for a new product, the context repo's `PRODUCT.md` problem section, see `cct:project-kickoff-run`) or return it in the reply when the user wants no file.

## Neighbours

- The audience and personas the statement names: `cct:product-audience-write`.
- Pain points found across a journey: `cct:ux-journey-create`.
- Choosing among the opportunities the statement exposes: `cct:product-priorities-analyze`.
