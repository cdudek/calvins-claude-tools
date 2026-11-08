---
name: project-report-write
description: "Authors a status report or an investigation report strictly from evidence the user supplies: progress, metrics, risks, decisions needed, health; or questions, findings, confidence and recommendations. Use when the user says 'write a status update', 'write the project report', 'write up the spike findings', 'draft the initiative status'. Skip for: the plan being reported on (use cct:project-plan-write), posting it to Linear (use cct:linear-manage), analysing raw data (use cct:data-cohorts-analyze)."
allowed-tools: "Read Grep Glob Write"
user_invocable: true
metadata:
  version: 1.0.0
  author: calvindudek
---

# Write a status or investigation report

Turns supplied evidence into a report. It reports; it does not gather new data, run analyses or
change the project. If a needed fact is not in the evidence, write "not reported" and list it
under open items. Never invent numbers, dates or owners.

## Choose the report

- **Project status update**: `${CLAUDE_PLUGIN_ROOT}/skills/linear-manage/references/project-status-update-template.md`. Summary, progress,
  key metrics (last period, this period, target), risks and blockers, next period, decisions
  needed. Pick a health value with the guide in that file: `onTrack`, `atRisk` or `offTrack`.
- **Initiative status update**: `${CLAUDE_PLUGIN_ROOT}/skills/linear-manage/references/initiative-status-update-template.md`. Adds key
  results progress (baseline, current, target), project health and strategic changes.
- **Investigation or spike report**: `${CLAUDE_PLUGIN_ROOT}/skills/linear-manage/references/spike-research-template.md`. Summary, questions,
  approach, findings with evidence, data, conclusions, recommendations.

## Rules

1. **Evidence first.** Every metric, finding and health claim cites its source (ticket, query,
   commit, link). Evidence, not impressions. Links must be reachable by the reader, never a local
   path.
2. **Health follows facts.** Missed milestones or an unresolved blocker is `offTrack`; blockers
   with a mitigation in progress is `atRisk`; otherwise `onTrack`. State the fact that set it.
3. **Confidence block for investigations.** Split conclusions into high, medium and low
   confidence, and list what is still not known. A finding presented without confidence is
   unfinished.
4. **Few findings.** Two strong findings beat six thin ones; do not pad to the template.
5. **Decisions needed** are explicit, each with context and options, so the reader can act.
6. A conclusion that is a decision becomes an ADR (`cct:arch-decision-log`); a proposed solution
   becomes an RFC (`cct:arch-plan-write`). This report does not stand in for them.

Posting a status update or attaching the research document in Linear is `cct:linear-manage`;
hand it the finished text and the health value.
