---
name: product-audience-write
description: "Writes the canonical audience definition of a product: the ideal customer profile (firmographics, behaviours, pain points, disqualifiers, the ideal-of-the-ideal), primary versus secondary audiences with a rule for who wins when they conflict, and named personas with role, goals, frustrations and current tools. Built from survey, interview, usage and win/loss data, and marked as draft until checked against real interviews. Use when the user says 'define the ideal customer', 'write the ICP', 'write the personas', 'who is this product for', 'primary and secondary audience'. Skip for: the jobs to be done of each persona - use cct:ux-jobs-write. Skip for: the whole product inception - use cct:project-kickoff-run."
allowed-tools: "Read Write"
user_invocable: true
---

# Write the audience

The one place where a product's audience is defined. Other skills read it: `cct:project-kickoff-run` delegates its audience stage here, `cct:product-problem-write` names its persona from it, `cct:ux-journey-create` maps one journey per persona from it, `cct:ux-setup` records it for the UX work. Do not redefine the audience anywhere else.

## Output

Three kinds of content, kept in the context repo's `audience/` folder (or wherever the project keeps product documents), each starting with frontmatter `type: audience`, `status: draft|decided`, `created`, `author`:

- `audiences.md`: the ICP.
  - **Primary** audiences: designed, priced and marketed for first. For each: who, size, role, who buys, personas.
  - **Secondary** audiences: supported, not designed around.
  - **Why these**: one paragraph.
  - **What this means for decisions**: the conflict rule ("when a choice serves the primary and hurts a secondary audience, the primary wins"), what waits, who marketing speaks to.
  - **Disqualification criteria**: who is not a good fit.
- `personas.md`: a few named personas per audience. Each has role, context, goals, frustrations, current tools and workarounds, and how they appear in the product (buyer, member, guest, admin). One persona is one person, not a segment.
- The jobs each persona hires the product for are not written here: `cct:ux-jobs-write` writes `jobs-to-be-done.md` from these personas.

## Method

Follow `references/define-ideal-customer.md` for the framework (demographics and firmographics, behaviours, jobs to be done, needs and pain points) and its six steps: gather customer data, segment by value, profile demographics, identify behaviours, define the jobs, document pain points. The ICP it produces includes the top 5 to 7 pain points, quantified impact, decision-making process, go-to-market implications, disqualifiers and the high-value segment within the ICP.

Rules:

1. Interview the owner for what only they know (who it is for, why now, what it must never become), research the rest. Quote and date the owner's own words.
2. Use quantitative and qualitative data together; for an existing product, interview 10 or more high-value customers before calling the profile decided.
3. Mark what is a guess. Personas written without interviews are `status: draft` and say so in the first paragraph ("first draft, to be checked against real interviews"). Never present invented demographics or quotes as research.
4. Name a conflict rule. An audience list with no statement of who wins is not usable for decisions.
5. Revisit quarterly as customer data arrives; the ICP drives focus, it does not exclude every other buyer.
6. Gate: the owner confirms the audiences and personas before other documents depend on them.
