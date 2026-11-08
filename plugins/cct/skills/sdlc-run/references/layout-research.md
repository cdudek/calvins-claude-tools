# Why `changes/` next to `docs/designs/`, archived on merge

What established tools do (primary sources read 2026-09-06):

| Tool | Per change | Current state | After merge | Plan mandatory |
|---|---|---|---|---|
| GitHub Spec Kit — `specs/NNN-feature/` spec · plan · research · data-model · contracts · tasks; `memory/constitution.md` | all per feature | constitution only | stays | yes (`/speckit.plan`) |
| Kiro — `.kiro/specs/<feature>/` requirements (EARS) · design · tasks; `.kiro/steering/` | all three | steering | stays; "Sync Files" from code | yes (Quick Spec skips gates) |
| OpenSpec — `openspec/specs/<capability>/spec.md` vs `openspec/changes/<id>/` proposal · design? · tasks · spec deltas | proposal + tasks | **specs = source of truth** | `openspec archive` merges deltas into specs, moves the folder to `changes/archive/YYYY-MM-DD-<id>/` | tasks yes, design optional |
| BMAD — `docs/prd.md`, `docs/architecture.md`, `docs/stories/` | stories | PRD + architecture | stays | — |
| superpowers — `docs/superpowers/specs/<date>-design.md`, `plans/<date>-feature.md` | both | none | dated, never archived | yes |
| ADR / RFD — `docs/adr/NNNN`, `rfd/NNNN` | one per decision | the accepted set | numbered, never reused, superseded | — |
| Anthropic playbook — `intent/` + spec.md + plan.md | all | — | "commit the chain" | "nothing without an accepted plan" |
| Claude Code / Cursor plan mode — `~/.claude/plans/`, `.cursor/plans/` | plan | — | swept (30 days) / "save to workspace" | — |

What recurs: a constitution layer (our `CLAUDE.md`); requirements split from plan; a task
checklist; numbering or dating; immutable history; and — only in OpenSpec — the split
between the **current state** and a **proposed change**. Ticket linking is nobody's
built-in; the folder name carrying the key is the cheapest join.

What we took: OpenSpec's specs-vs-changes split (our designs-vs-changes) and archive-on-merge; Spec Kit's
`<id>-<slug>` folder with a creation date plus the ticket key instead of a counter (the date
so the id sorts and survives archiving, the key optional so work without a ticket is not blocked); Kiro's optional design
for small work (our optional `intent.md`); superpowers' "the plan copies the spec's
constraints" (our `Design changes` section and the two-way link test); ADR's supersession
for designs; the playbook's chain and "commit at every stage". Plans never in `.claude/`
— the tools themselves treat that folder as scratch.

Sources: github.com/github/spec-kit (spec-driven.md, templates/plan-template.md) ·
kiro.dev/docs/specs · github.com/Fission-AI/OpenSpec (docs/concepts.md, docs/cli.md) ·
github.com/bmad-code-org/BMAD-METHOD · github.com/obra/superpowers (skills/brainstorming,
skills/writing-plans) · cognitect.com/blog/2011/11/15/documenting-architecture-decisions ·
rfd.shared.oxide.computer/rfd/0001 · claude.com/blog/the-ai-native-sdlc-playbook ·
cursor.com/docs/agent/planning.
