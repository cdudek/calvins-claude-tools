---
name: linear-manage
description: "Persists supplied Linear records through the Linear MCP: creates and updates issues, projects, initiatives, documents, status updates and milestones from text that is already written. Delegates the authored content: work items to cct:product-workitem-write, technical plans and RFCs to cct:arch-plan-write, ADRs to cct:arch-decision-log, project and initiative plans to cct:project-plan-write, status and research reports to cct:project-report-write. Use when the user says 'save this to Linear', 'file the Linear issue', 'create the Linear project', 'post the Linear status update', 'attach the document in Linear'. Skip for: writing the content itself (use the owners above)."
allowed-tools: "mcp__claude_ai_Linear__* mcp__linear__*"
user_invocable: true
metadata:
  version: 1.0.0
  author: calvindudek
effort: low
---

# Linear Workflow Skill

Create structured, AI-native documents and issues in Linear using the connected MCP. All templates follow modern best practices for agent-readable, action-oriented content.


## Routing

The user input is: $ARGUMENTS

Read the first word as the subcommand and route to its file, passing the rest on as arguments.

| Subcommand | Does |
|---|---|
| `create-adr` | Creates an Architecture Decision Record as a Linear Document, optionally attached to a Project → `references/commands/create-adr.md` |
| `create-bug-report` | Creates a structured bug report issue with reproduction steps, impact assessment, and acceptance criteria → `references/commands/create-bug-report.md` |
| `create-initiative-status-update` | Posts a status update on a Linear Initiative, summarizing progress across projects, key results, and strategic → `references/commands/create-initiative-status-update.md` |
| `create-initiative` | Creates a Linear Initiative representing a strategic goal that spans multiple projects → `references/commands/create-initiative.md` |
| `create-issue` | Creates a structured, agent-ready issue in Linear that any developer or AI agent can pick up and execute → `references/commands/create-issue.md` |
| `create-prd` | Creates a Product Requirements Document as a Linear Document attached to a Project → `references/commands/create-prd.md` |
| `create-project-status-update` | Posts a status update on a Linear Project, summarizing progress, risks, and next steps → `references/commands/create-project-status-update.md` |
| `create-project` | Creates a Linear Project with structured description, native milestones, and team assignments → `references/commands/create-project.md` |
| `create-rfc` | Creates an RFC as a Linear Project with an attached Document using the structured RFC template → `references/commands/create-rfc.md` |
| `create-simple-task` | Creates a small, unambiguous issue with no requirement grammar → `references/commands/create-simple-task.md` |
| `create-spike-research` | Creates a research note as a Linear Document attached to the spike issue it came from → `references/commands/create-spike-research.md` |
| `create-spike` | Creates a time-bounded investigation ticket with a clear deliverable (PoC, RFC, ADR, or recommendation) → `references/commands/create-spike.md` |
| `update-initiative` | Updates an existing Linear Initiative's description, status, owner, or target date → `references/commands/update-initiative.md` |
| `update-project` | Updates an existing Linear Project's description, dates, team, priority, or status → `references/commands/update-project.md` |

No subcommand, or one that is not in the table: say
`Usage: /cct:linear-manage <create-adr | create-bug-report | create-initiative-status-update | create-initiative | create-issue | create-prd | create-project-status-update | create-project | create-rfc | create-simple-task | create-spike-research | create-spike | update-initiative | update-project>`
and ask which one they meant. Never guess — the subcommands do different things.

## Core Principles

1. **Agent-ready by default** — every issue uses declarative acceptance criteria, explicit file paths, and the Always/Ask/Never boundary system so AI agents can act on them
2. **Structured over prose** — use tables, checklists, and sections instead of paragraphs
3. **Create minimal, then update** — the Linear MCP is flaky. Create with required fields only, then update with content in a separate call. Retry 2-3 times on 500 errors.
4. **Attach documents to the right parent** — RFCs/ADRs attach to Projects, spike research attaches to Issues. See "Attaching Documents" for the full mapping.
5. **Always provide links** — after creating or retrieving any resource (issue, project, initiative, document), always include the Linear URL in your response so the user can navigate directly to it
6. **Never add timelines or dates** — do not add target dates, durations, or time estimates to phased plans, milestones, issues, or anywhere else. You don't know how long things take or when they'll be worked on. Only add dates if the user explicitly provides them.

## Instructions

### Creating Any Resource

Always follow this pattern with the Linear MCP:

1. **Create** with minimal required fields (name/title + team)
2. **Update** in a separate call to add description, content, priority, dates, etc.
3. If a write fails, **retry 2-3 times** before giving up
4. Keep markdown content concise — long payloads cause 500 errors

### How Linear Organizes Work

```
Initiative (strategic goal, e.g., "Reduce Churn by 20%")
  └── Project (time-bound deliverable, e.g., "Onboarding Flow Redesign")
       ├── Milestones (phases)
       ├── Documents (RFCs, ADRs, PRDs)
       └── Issues (atomic work units)
            └── Sub-Issues
```

#### Definitions

| Level | What it is | Example | Who creates it |
|-------|-----------|---------|----------------|
| **Initiative** | A strategic goal or OKR spanning multiple projects. Tracks progress across all child projects. | "AI-Native Enablement", "Reduce Churn by 20%" | Leadership / PM |
| **Project** | A time-bound deliverable that ships a specific outcome. Contains milestones, documents, and issues. Belongs to one initiative. | "Onboarding Flow Redesign", "Quality Assurance & Testing" | PM / Tech Lead |
| **Milestone** | A phase within a project. Groups issues into logical stages (e.g., "Phase 1: Research", "Phase 2: Implementation"). | "MVP", "Beta", "GA" | PM / Tech Lead |
| **Issue** | An atomic unit of work assigned to one person. Has a status, priority, and acceptance criteria. Belongs to a project (optionally via a milestone). | "Add logout button to nav", "Spike: evaluate CI tools" | Anyone |
| **Sub-Issue** | A smaller task within an issue. Use when an issue has distinct steps that benefit from individual tracking. Inherits the parent's project. | "Write unit tests", "Update API docs" | Developer |

**Rules of thumb:**
- If it takes **one person < 1 week**, it's an **issue**
- If it takes **a team 2-8 weeks**, it's a **project**
- If it spans **multiple projects or quarters**, it's an **initiative**
- Use **sub-issues** sparingly — only when the parent issue has genuinely independent sub-tasks
- **Milestones** are optional — skip them for small projects with < 10 issues

### Using Milestones

**Never write milestones as text in descriptions.** Always use Linear's native milestone feature via `save_milestone`. This makes milestones trackable, filterable, and visible in project progress.

```
save_milestone:
  project: "project-name"
  name: "Phase 1: Research"
  description: "What this phase delivers"
```

- Milestones belong to a project — issues can then be assigned to a milestone
- Use milestones when a project has distinct phases (e.g., Research → Build → Launch)
- Skip milestones for small projects with < 10 issues
- Do not add `targetDate` unless the user explicitly provides one

### Attaching Documents

`create_document` accepts exactly ONE parent: `project`, `issue`, or `initiative`. You cannot specify multiple. Documents cannot be moved between parents after creation.

#### Where to attach each document type

| Document type | Attach to | Why |
|--------------|-----------|-----|
| **RFC** | `project` | Strategic design doc shared across the project team |
| **ADR** | `project` | Architectural decision relevant to the whole project |
| **PRD** | `project` | Product requirements — only when a PM owns "what" separately from engineering's "how". Otherwise fold into the RFC. |
| **Spike Research** | `issue` | Research findings tied to a specific spike ticket — readers find it on the issue |
| **Bug Investigation** | `issue` | Root cause analysis tied to a specific bug report |

#### MCP behavior notes

- `create_document` with `issue` → document appears **directly on the issue** (native embed)
- `create_document` with `project` → document appears in the **project's Documents tab**
- `save_issue` with `links` → creates a **link attachment** on the issue, NOT a native document embed. Use this only for external URLs, not for Linear documents.
- There is no `delete_document` API — archive or rename duplicates instead
- Documents cannot be moved between parents after creation — attach to the right parent the first time

#### Document icons

Use emoji shortcodes for document icons to make them scannable in Linear:

| Document type | Icon |
|--------------|------|
| RFC | `:memo:` |
| ADR | `:scales:` |
| PRD | `:page_facing_up:` |
| Spike Research | `:mag:` |
| Bug Investigation | `:bug:` |
| Status Update | `:bar_chart:` |

## Templates

**This repo is the source for every template.** Write ADR, RFC, PRD, Research Note and Project
bodies from the files under `references/` — never from `get_template`. They carry this kit's own
additions: the EARS grammar and the agent-ready issue body.

Since 2026-09-12 the workspace holds four of them again — `Bug Report`, `Simple Task`,
`Feature Issue` and `Project Template` — typed in from these files so a person filing by hand in
the Linear UI gets a frame. They are copies, not the source: change a template here, then paste it
across. `ADR`, `RFC`, `PRD` and the Research Note have no Linear counterpart at all; they are
created as documents by this skill.

| Document | File |
|---|---|
| Architecture Decision Record | `references/adr-template.md` |
| RFC | `references/rfc-template.md` |
| PRD | `references/prd-template.md` |
| Research Note | `references/spike-research-template.md` |
| Project | `references/project-template.md` |

The three issue templates were always owned here: the agent-ready issue, the bug report and the
spike. Linear's deleted equivalents were written for a human reader and dropped the sections an
agent needs.

**Requirements are EARS, acceptance criteria are optional Gherkin.** One grammar, mirrored into this plugin at
`../sdlc-run/references/requirements-grammar.md` (canonical copy lives in `cct:product-workitem-write`).
Never restate the patterns in a template or a command.

Each template lives in its own file under `references/`. See `references/templates.md` for the full index.

| Template | File | Command |
|----------|------|---------|
| RFC | `references/rfc-template.md` | `/cct:linear-manage create-rfc` |
| ADR | `references/adr-template.md` | `/cct:linear-manage create-adr` |
| Agent-Ready Issue | `references/issue-template.md` | `/cct:linear-manage create-issue` |
| Spike Ticket | `references/spike-template.md` | `/cct:linear-manage create-spike` |
| Spike Research Doc | `references/spike-research-template.md` | `/cct:linear-manage create-spike-research` |
| Bug Report | `references/bug-report-template.md` | `/cct:linear-manage create-bug-report` |
| Simple Task | `references/simple-task-template.md` | `/cct:linear-manage create-simple-task` |
| PRD | `references/prd-template.md` | `/cct:linear-manage create-prd` |
| Project | `references/project-template.md` | `/cct:linear-manage create-project` |
| Initiative | `references/initiative-template.md` | `/cct:linear-manage create-initiative` |
| Project Status Update | `references/project-status-update-template.md` | `/cct:linear-manage create-project-status-update` |
| Initiative Status Update | `references/initiative-status-update-template.md` | `/cct:linear-manage create-initiative-status-update` |

## Moving an issue's state

Creating an issue is half the job. An issue that sits in Backlog while someone works on it makes
Linear useless to everyone who is not in the repo.

| When | State |
|---|---|
| someone starts the work | `In Progress` |
| the PR is open | `In Review` |
| the PR merged, and the repo ships on merge | `Done` |
| the PR merged, and the repo deploys separately | `Ready To Deploy` |

`save_issue` with `state` does it. Resolve the state by **`type`** from `list_issue_statuses`
(`backlog`, `unstarted`, `started`, `completed`, `canceled`) rather than trusting a label — team
names agree today but are not guaranteed to.

**Set the state when you know it changed, and say so in one line.** Do not ask permission for a
transition the user just described ("I'm starting LIN-123" is the instruction). Do ask when the
right state is ambiguous, and never move an issue backwards on your own.

## When the repo runs the SDLC

If the repo has an `sdlc.json` at its root, it uses `cct:sdlc-run`, and the two skills split
the work rather than competing:

| | Lives in | Holds |
|---|---|---|
| **Issue** | Linear | status: state, assignee, cycle, the link to the PR |
| **Change folder** | the repo, `changes/<KEY>-<slug>/` | content: `intent.md`, `facts.md`, `plan.md` |

One change = one folder = one Linear issue = one PR. Create the issue here, then let `sdlc-run`
open the change folder against it — do not paste requirements into both, or they drift within a
sprint and nobody knows which is current. The acceptance criteria live in `facts.md` as numbered
EARS facts; the Linear issue carries the title, the status and the link.

A **design** that outlives one PR is a Linear **project** plus a file in the repo's `designsDir`.
An ADR, RFC or PRD attaches as a document to that project, written from the templates above.

## Error Handling

### MCP 500 errors
Cause: Linear MCP connector is flaky, especially on writes with large payloads.
Solution: Create with minimal fields first, then update. Retry 2-3 times. If reads also fail, the connector is fully down — inform the user.

### "Team not found"
Cause: Team name doesn't match exactly.
Solution: Use `list_teams` first to get exact team names.

### Long content causes failures
Cause: Large markdown payloads in create calls.
Solution: Create the document/issue with a short summary, then update with full content. Or create with a summary and reference a repo file for the full version.
