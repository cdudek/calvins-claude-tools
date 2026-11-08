---
name: ux-journey-create
description: "Produces the shared experience map of one persona's journey: stages (awareness to loyalty), customer actions, touchpoints, emotions and quotes, KPIs, business goals, owning teams, pain points and ranked improvement opportunities. Builds it directly from supplied research, or facilitates it as a workshop (actor, scenario and goal, phases, actions and emotions, opportunities). Use when the user says 'map the customer journey', 'build a journey map', 'run a journey workshop', 'touchpoint map', 'experience map'. Skip for: arranging stories into a story map - use cct:product-storymap-create. Skip for: pages, routes and navigation - use cct:ux-sitemap-create."
allowed-tools: "Read Write"
user_invocable: true
---

# Create the journey map

The shared experience and touchpoint map: how one persona moves across every touchpoint, not only the product. Marketing, sales, product and support read the same map. It is a strategic artifact that joins customer empathy to metrics, not a user flow diagram and not a service blueprint.

Prerequisite: the persona. Take it from `cct:product-audience-write`; if none exists, write it first (or run discovery with `cct:product-discovery-run`). One persona per map, never two combined.

## Pick the mode

- **Build** (`references/map-customer-journey.md`): research, personas and a touchpoint inventory are in hand. Steps: prepare prerequisites, set objectives, choose the persona, map each stage (actions, touchpoints, customer experience, KPIs, business goals, teams involved), visualize as a stage-by-row table, analyze and prioritize (impact, feasibility, alignment), refine quarterly. Template: `references/map-customer-journey/template.md`; examples: `references/map-customer-journey/examples/`.
- **Workshop** (`references/run-journey-workshop.md`): the team has no shared picture yet. Up to five adaptive questions (actor, scenario and goal, 4 to 6 phases, actions/thoughts/emotions/pain points, 5 to 7 opportunities ranked HIGH/MEDIUM/LOW with evidence), run one question at a time under the facilitation protocol in `${CLAUDE_SKILL_DIR}/../product-playbook/references/facilitate-workshop.md`. Framework: `references/run-journey-workshop/references/journey-map-framework.md`; questions: `question-guide.md`; output format: `output-template.md`; examples and pitfalls: `examples-and-pitfalls.md` (all in the same folder).

## Rules

- Map from the customer's perspective and what they actually do, validated by research, analytics and support tickets; not what you wish they did.
- Every stage carries emotions and pain points, not only actions. Be specific ("relieved setup took 30 minutes, not the 3 hours feared"), use real quotes, include offline and human touchpoints.
- Stages need KPIs and business goals that are measurable and stage-appropriate; a map without them cannot prioritize.
- Opportunities are ranked with evidence. Turn the top ones into problem statements with `cct:product-problem-write`; rank competing ones with `cct:product-priorities-analyze`.
- Save the map in the repo's `docs/ux/` when it has one (for example `docs/ux/journey-<persona>.md`), otherwise where the user says. The map is a living document: record the date and revisit it quarterly.
