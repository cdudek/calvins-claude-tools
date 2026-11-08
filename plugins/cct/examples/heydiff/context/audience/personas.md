---
type: audience
status: draft
created: 2026-10-27
author: Calvin Dudek
---

# HeyDiff audience: personas, goals and jobs to be done

**Positioning (owner, 2026-10-28, `strategy/2026-10-28-name-heydiff.md`).** "HeyDiff turns team feedback into agent-ready software changes." It replaces the line from 2026-10-27: "Snapmark turns agentic engineering and software factories from a single-player into a multiplayer game. It gives exact tools for exact feedback and leaves a paper trail of decisions."

**Roles (owner):** product manager, UX designer, product engineer, entrepreneur, agency, hobby project developer. The personas, goals and jobs below are a first draft (Claude, 2026-10-27), to be checked against real interviews.

Jobs are written as: _When … I want to … so I can …_

## Product manager: Priya

- **Context:** 8-person product team; two engineers ship most UI with coding agents. Priya reviews on staging and in previews.
- **Goals:** what ships matches what was agreed; decisions are traceable; nothing falls between Slack and Linear.
- **Jobs:**
  - When a preview is ready, I want to point at exactly what is wrong and say what I expect, so the engineer and the agent do not guess.
  - When two options are on the table, I want the team to compare and vote on versions, so we decide once and move on.
  - When someone asks "why is it like this?" weeks later, I want the decision, who made it and the PR, so I do not reconstruct it from chat.
- **Today:** screenshots in Slack, Loom videos, Linear comments; feedback rounds repeat because the agent never saw the context.
- **In HeyDiff:** paid member; requests changes, requests decisions, approves.

## UX designer: Dana

- **Context:** designs in Figma, but what ships is built by agents from prompts; the built UI drifts from the design.
- **Goals:** the built UI meets the design system; small visual details get fixed without a meeting.
- **Jobs:**
  - When I spot a spacing or colour drift, I want to mark the element and draw what I mean, so the fix is exact.
  - When I have an alternative, I want to post a mockup as a version beside the current one, so people compare the real thing.
  - When an implementation comes back, I want before and after side by side, so I can approve in seconds.
- **Today:** annotated screenshots, design QA spreadsheets, redlines nobody reads.
- **In HeyDiff:** paid member, or a guest at an agency's client.

## Product engineer: Ben

- **Context:** drives Claude Code or Codex all day; owns delivery.
- **Goals:** feedback arrives as work the agent can act on; fewer feedback rounds; proof that a request is done.
- **Jobs:**
  - When I start a session, I want my agent to fetch every open request for this repo and branch, so I do not copy feedback by hand.
  - When a request is unclear, I want my agent to ask the requester or propose versions, so we do not build the wrong thing.
  - When the fix is in, I want it marked implemented with the PR and an after-screenshot, so the reviewer can verify without asking me.
- **Today:** pastes screenshots into the agent, chases context in three tools.
- **In HeyDiff:** paid member; the agent acts as Ben's copilot through MCP.

## Entrepreneur: Eva

- **Context:** non-technical or semi-technical founder; builds with one or two engineers or agents; makes the final product calls.
- **Goals:** ship fast without losing control of quality; know what was decided.
- **Jobs:**
  - When I click through the product, I want to leave feedback on anything in seconds, so I keep momentum.
  - When I am unsure, I want options with mockups and a recommendation, so I can decide from my phone.
- **Today:** WhatsApp voice notes and screenshots to the developer.
- **In HeyDiff:** owner of the organisation; pays.

## Agency: Alex (owner or project lead) and Chris (client)

- **Context:** 5 to 20 people building client products with AI; several clients at once; freelancers move between agencies.
- **Goals (Alex):** clean feedback rounds; client sign-off on record; fewer disputes about what was approved; bill for change requests.
- **Goals (Chris, the client):** give feedback without learning a tool; see that it was done.
- **Jobs:**
  - When the client reviews, I want them to comment and approve without a paid seat, so onboarding takes a link.
  - When a client disputes something, I want the approval record with version and date, so the discussion ends.
  - When I work for two agencies, I want to switch organisations without another login.
- **Today:** BugHerd or Marker.io widgets, email threads, PDF sign-offs.
- **In HeyDiff:** Alex pays; Chris is a free guest invited by a paid account.

## Hobby project developer: Hugo

- **Context:** builds side projects with agents, alone or with a friend.
- **Goals:** give the agent precise visual feedback; stay free or nearly free.
- **Jobs:**
  - When the agent's UI is off, I want to mark it and hand it to the agent, so I fix it in one round.
  - When a friend helps, I want to invite them cheaply.
- **Today:** screenshots dragged into the chat.
- **In HeyDiff:** free (solo); the way in for teams later.

## Not a persona: the AI agent

The agent is not a member. It acts for the person driving the work, under that person's name and rights ("Ben via Claude"): it reads requests, asks questions, posts versions and implementations, and never approves.
