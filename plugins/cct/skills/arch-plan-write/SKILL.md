---
name: arch-plan-write
description: "Authors a technical proposal or plan: approach with rejected options, API contract, data model, structural-risk questions, migration, order of work and risks. Output is a plan.md in a change folder or an RFC. Use when the user says 'write a technical plan', 'draft a technical RFC', 'plan the API contract', 'plan the data model', 'assess coupling and scaling risks in the plan'. Skip for: recording one accepted decision (use cct:arch-decision-log), C4 diagrams (use cct:docs-c4-create), saving the RFC in Linear (use cct:linear-manage)."
allowed-tools: "Read Grep Glob Write Bash(git *)"
user_invocable: true
metadata:
  version: 1.0.0
  author: calvindudek
effort: high
---

# Write a technical plan

Authors the plan that says how a change will be built, before it is built. It plans; it does not
audit the running system and it does not build.

## Inputs

Read first: the intent and facts of the change (or the problem statement the user gives), the
repo's `sdlc.json` and design/decision index (`<designsDir>/INDEX.md`) when they exist, and the
code the change touches. Ask only for what you cannot read.

## Choose the output

- **Inside an sdlc-run change** (a `changes/<id>/` folder exists): write `plan.md` in that folder
  and follow "Plan sections" below. `cct:sdlc-run` owns the stages, the approval gate and the
  build; this skill only authors the plan text.
- **A proposal for review by others** (new service, cross-team change, hard to reverse): write an
  RFC from `${CLAUDE_PLUGIN_ROOT}/skills/linear-manage/references/rfc-template.md`. Phases become milestones in the tracker, not prose
  (`cct:project-plan-write` authors them). The RFC is a document; saving it to Linear is
  `cct:linear-manage`.
- Neither: write the plan as a markdown file where the user says.

## Plan sections

1. **Approach**, with what was rejected and why. Each alternative: approach, pros, cons,
   "rejected because".
2. **Where things go**: a folder for every new file. A file outside the listed folders is scope
   growth to be raised, not silently added.
3. **Features / PRs in order**, each with the facts it satisfies and its branch.
4. **Files that change.**
5. **Order of work**, with a proof per step (the test, command or observable result that shows
   the step is done).
6. **Risks**, including findings from earlier validation, each with a mitigation.
7. **Done**: the criteria as checkable statements.
8. **Open questions**, marked `NEEDS CLARIFICATION`, resolved before building starts.

State the biggest risk and your recommendation for it in five lines at the top, for the reviewer.

## Checklists to apply when relevant

Apply a checklist only when the change touches that area; each result lands in the plan.

**API contract** (new or changed endpoint):
- Resources and requirements first, then endpoints: REST methods, status codes, URL patterns; or
  a GraphQL schema with types, queries, mutations, subscriptions.
- OpenAPI 3.1 shape for each endpoint: request, response, auth per endpoint.
- Versioning strategy: URL path, header, or content negotiation; say which and why.
- Error contract: one error shape and a code list used everywhere.
- Pagination, filtering and sorting patterns.

**Data model** (new or changed schema):
- Domain analysis, entities, then relationships.
- Normalization: 1NF to 2NF to 3NF/BCNF, and where you deliberately denormalize, with the
  trade-off.
- A Mermaid ER diagram of the result.
- Migration plan: CREATE/ALTER statements in order, what is reversible, the rollback, and any
  window with a data-loss or outage risk.
- Indexes justified by the query patterns they serve.

**Structural risk** (new service, boundary or dependency):
- Coupling and cohesion: what depends on what after this change, and is any dependency new or
  circular?
- Boundaries: is each service or module too big, too small, or cut in the wrong place?
- Scaling: where does load or data growth first hurt?
- Single points of failure: what does the change introduce, and what is the fallback?
- Each answer is a planning question about the proposed design, answered from the code you read.
  Do not claim to have audited the whole system.

## Hand-offs

- A choice worth its reasons in a year: `cct:arch-decision-log` writes it as an ADR; the plan
  links to it.
- Diagrams of the result: `cct:docs-c4-create`.
- Auth, money or consent in the plan: `cct:review-security-run`. A new package:
  `cct:review-dependency-run`. Success-measure events: `cct:tracking-apply`.

## Do not

- Do not include audit scores, severity tables of the existing system or whole-repo findings.
- Do not invent endpoints, tables or services the facts do not need.
