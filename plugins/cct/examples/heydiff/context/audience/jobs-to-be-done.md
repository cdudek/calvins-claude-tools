---
type: audience
status: draft
created: 2026-10-27
author: Calvin Dudek
---

# Jobs to be done

The jobs across all roles, ordered along one piece of feedback. Per-persona jobs are in [personas.md](personas.md); who matters most is in [audiences.md](audiences.md). Draft by Claude from the owner's description, to check against interviews.

## The main job

**Get what is built to match what we meant, together and with AI agents, without losing why we decided it.**

## The job, step by step

Written as: _When … I want to … so I can …_ The role in brackets is who does it most.

1. **Notice** (PM, designer, founder, client, QA)
   - When I click through a build, I want to flag anything that is off in seconds, so I keep reviewing instead of writing tickets.
2. **Point** (all reviewers)
   - When something is off, I want to point at the exact element and draw what I mean, so nobody guesses which button or which pixel.
   - When I give feedback, I want it to remember the page, region, module and version on its own, so I do not have to explain where and when.
3. **Explain** (all reviewers)
   - When I request a change, I want to say what I expect, not just what is wrong, so the result matches the first time.
4. **Discuss and decide** (PM, designer, founder, agency lead)
   - When there are several ways to fix it, I want to compare versions side by side, comment and vote, so we decide once and on facts.
   - When the agent or a developer is unsure, I want their question to reach me where I am, so work does not stall.
5. **Hand off** (product engineer, solo builder)
   - When I start working, I want my agent to fetch every open, decided request for this repo and branch, so I never copy feedback by hand.
   - When I hand work to the agent, I want it to see the screenshot, the anchor and the version, so it finds the right code.
6. **Implement** (product engineer and their agent)
   - When the fix is in, I want it reported with the pull request and an after-screenshot, so the reviewer can check without asking me.
7. **Verify** (whoever asked, or anyone on the team)
   - When a fix comes back, I want before and after side by side, so I approve or object in seconds.
8. **Remember** (PM, founder, agency lead, client)
   - When someone asks "why is it like this?", I want the request, the decision, who made it and the pull request, so I do not dig through chat.
   - When a client disputes a change, I want the approval with version and date, so the discussion ends.

## Emotional and social jobs

- Feel sure that what ships is what was agreed.
- Not be the annoying reviewer who sends vague screenshots in chat.
- Be seen as deciding on facts, not on who shouts loudest.
- For agencies: look professional and in control in front of the client.
- For engineers: stay in flow with the agent instead of chasing context.

## Signs the job is done well (to measure)

- Time from noticing a problem to the agent having full context.
- Feedback rounds per change (target: one).
- Share of feedback that names element, version and expected result.
- Time to answer "why is it like this?" (target: one click).
- Share of implemented requests approved on the first review.
