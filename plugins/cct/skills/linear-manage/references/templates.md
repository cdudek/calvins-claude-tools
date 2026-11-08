# Linear Templates Quick Reference

Each template is in its own file. Commands reference these directly.

**Every template here is the source.** Since 2026-09-12 the workspace holds four of them again — `Bug Report`, `Simple Task`,
`Feature Issue` and `Project Template` — typed in from these files so a person filing by hand in
the Linear UI gets a frame. They are copies, not the source: change a template here, then paste it
across. `ADR`, `RFC`, `PRD` and the Research Note have no Linear counterpart at all; they are
created as documents by this skill.

Requirement grammar for all of them: `../sdlc-run/references/requirements-grammar.md`.

| I want to... | Template | File | Command |
|--------------|----------|------|---------|
| Propose a big technical change | RFC | `references/rfc-template.md` | `/cct:linear-manage create-rfc` |
| Record why we chose X over Y | ADR | `references/adr-template.md` | `/cct:linear-manage create-adr` |
| Create a task for a dev or agent | Agent-Ready Issue | `references/issue-template.md` | `/cct:linear-manage create-issue` |
| Investigate with a time box | Spike | `references/spike-template.md` | `/cct:linear-manage create-spike` |
| Document spike research findings | Spike Research | `references/spike-research-template.md` | `/cct:linear-manage create-spike-research` |
| Report a bug | Bug Report | `references/bug-report-template.md` | `/cct:linear-manage create-bug-report` |
| Do something small and unambiguous | Simple Task | `references/simple-task-template.md` | `/cct:linear-manage create-simple-task` |
| Define what to build and why | PRD | `references/prd-template.md` | `/cct:linear-manage create-prd` |
| Plan a time-bound deliverable | Project | `references/project-template.md` | `/cct:linear-manage create-project` |
| Set a strategic goal | Initiative | `references/initiative-template.md` | `/cct:linear-manage create-initiative` |
| Share project progress | Project Status Update | `references/project-status-update-template.md` | `/cct:linear-manage create-project-status-update` |
| Share initiative progress | Initiative Status Update | `references/initiative-status-update-template.md` | `/cct:linear-manage create-initiative-status-update` |
| Update a project description | Project | `references/project-template.md` | `/cct:linear-manage update-project` |
| Update an initiative description | Initiative | `references/initiative-template.md` | `/cct:linear-manage update-initiative` |
