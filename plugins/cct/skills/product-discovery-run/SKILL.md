---
name: product-discovery-run
description: "Coordinates a product discovery cycle over 2 to 4 weeks: frame the problem, plan and conduct customer interviews, synthesise insights, design and run experiments, then decide GO, PIVOT or KILL. Delegates problem framing to cct:product-problem-write, journeys to cct:ux-journey-create and ranking of pain points to cct:product-priorities-analyze; runs interview, synthesis and opportunity-tree methods from cct:product-playbook itself. Use when someone says 'run a discovery cycle', 'run the discovery process', 'validate this problem with customers', 'plan discovery interviews and experiments', 'decide go or kill on this idea'. Skip for: one interview script or summary (cct:product-playbook), the strategy cycle (cct:product-strategy-run), analysing an A/B test (cct:posthog-manage)."
user_invocable: true
metadata:
  version: 2.0.0
---

# Product discovery run

A complete discovery cycle from problem hypothesis to validated solution, so teams do not build before they know the problem is real. It coordinates research, synthesis, experimentation and the evidence decision. It is a continuous practice, 1-2 cycles per quarter, running alongside delivery. Needs access to 5-10 customers per cycle and a PM, designer and engineering lead.

When run as a guided conversation, follow `${CLAUDE_SKILL_DIR}/../product-playbook/references/facilitate-workshop.md` (entry modes, one question per turn, numbered options). If it conflicts with this file's workflow, this file wins.

## Delegation

Do not restate the owners' methods.

- **Problem statement, How Might We, reframing:** `cct:product-problem-write`
- **Journey map from pain points that span phases:** `cct:ux-journey-create`
- **Ranking pain points and solutions:** `cct:product-priorities-analyze`
- **Audience when the segment is unclear:** `cct:product-audience-write`; **jobs:** `cct:ux-jobs-write`
- **Experiment tooling and analysis:** `cct:posthog-manage`
- **PRD and epics after GO:** `cct:product-prd-write`, `cct:product-epic-analyze`

Private methods, read from `${CLAUDE_SKILL_DIR}/../product-playbook/references/<method>.md`:

- `prep-discovery-interview.md` (method, biases to avoid, interview plan)
- `write-interview-script.md` (script)
- `summarize-interview.md` (per-interview synthesis)
- `analyze-sentiment.md` (tickets, reviews, NPS comments)
- `build-opportunity-tree.md` (opportunity solution tree)

## Phases

Full activity lists, participants, durations and outputs per phase are in `references/phase-details.md`; the week-by-week timeline is `references/workflow-timeline.md`.

| Phase | Timing | Key activity | Owner |
|---|---|---|---|
| 1. Frame the problem | Day 1-2 | Framing canvas, formal statement, research questions | `cct:product-problem-write` |
| 2. Research planning | Day 3 | Interview plan, recruiting, scheduling | `prep-discovery-interview.md` |
| 3. Conduct research | Week 1-2 | 5-10 interviews plus tickets and analytics | `write-interview-script.md` |
| 4. Synthesise | End week 2 | Affinity map, pain-point scoring, updated statement | `summarize-interview.md`, `cct:product-priorities-analyze` |
| 5. Generate and validate | Week 3 | Opportunity tree, experiments | `build-opportunity-tree.md` |
| 6. Decide and document | Week 3-4 | GO / PIVOT / KILL, readout | this skill |

### Decision points

- **After phase 1:** enough context to start research? If not, review tickets, churn surveys, NPS and analytics first (+2-3 days).
- **After phase 3:** saturation (same pain points across 3+ interviews)? If not, schedule 3-5 more interviews (+1 week).
- **After phase 5:** did experiments validate the solution? If not, pivot to the next option (+1-2 weeks).

### Phase 6 decision

Weigh problem validated (phases 3-4), solution validated (phase 5), strategic fit and feasibility. GO moves to epics and a PRD, PIVOT explores another solution, KILL de-prioritises. Give execs a 30-minute readout: problem evidence, experiment results, recommendation.

## Rules

- Interview 5-10 customers per cycle; never rely on analytics alone.
- Ask about past behaviour, not hypotheticals (Mom Test).
- Continue until saturation, but time-box the cycle to 3-4 weeks.
- Aim for one customer interview a week on an ongoing basis.
- Every solution maps to an experiment before the build commitment.

## Output

Capture the cycle in `references/template.md`; `references/sample.md` is a worked example; `references/examples-and-pitfalls.md` lists five common pitfalls.

## Sources

Adapted from deanpeters/Product-Manager-Skills (`skills/discovery-process`), MIT. External frameworks: Teresa Torres, Continuous Discovery Habits; Rob Fitzpatrick, The Mom Test; Marty Cagan, Inspired.
