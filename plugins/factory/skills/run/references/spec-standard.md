# Spec standard

Spec-driven: intent first (`changes/<slug>/intent.md`, see `intent-template.md`), then the delta, then the plan. Code is derived from those files. Any behaviour change, from anyone, starts as a delta. Journeys and design mapping are written in `delta.md` below the requirements.

Spec-anchored: a living spec per feature in `specs/<YYYY-MM>/<YYYY-MM-DD>__<feature>.md` (for example `specs/2026-12/2026-12-20__guest-links.md`), plus one delta per change. The date is the day the spec was created, the folder its month; the file keeps its name when later deltas update it, so the path never changes and links never break. The spec is intent, constraints and acceptance only. No spec for a task you can state in one sentence.

Everything about an app lives in that app's repository, versioned with its code: `specs/` (feature specs in month folders, ADRs in `specs/adr/`) and `changes/`. A change that spans several apps writes one delta per repo, each against that repo's own specs. Only the holdout scenarios live outside, so builders cannot fit them.

## Living spec header
```markdown
---
id: guest-links
summary: Invite a guest to one session with a link that expires.
aliases: [invite links, share links]
adrs: [7, 12]
---
```
- **`id`** never changes, even when the title or file name would read better otherwise. It is the spec's name and slug. It is not part of a requirement id: requirements are `req-<n>`, numbered across the whole repo.
- **Dates are not in the header:** the creation date is in the file name, and the last change comes from git (`git log -1 --format=%as -- <spec>`). File-system dates are useless here: git does not store them and a checkout resets them.
- **`aliases`** carries former names and the words users say, so `grep` finds the spec from a request that uses other words.
- **`adrs`** lists the decisions that govern it, by number (`7` is `adr-7`). Follow `superseded by` to the current one.
- **Retired ids stay reserved:** a REMOVED requirement keeps a one-line `req-3: removed in <slug>` entry at the bottom, and its number is never reused.

## Rename, split, merge
- **Rename:** change the title and add the old name to `aliases`; file name and `id` stay.
- **Split:** the continuing capability keeps its file and ids; each new capability gets a new file dated when it is created. Moved requirements keep their `req-<n>` numbers, so nothing needs "(was ...)"; only a requirement that gets a new number names its old one (`req-31 (was req-4)`).
- **Merge:** the delta names the surviving spec; the other file keeps only its header and one line pointing at the survivor.

## Delta format (`changes/<slug>/delta.md`, slug `YYYY-MM-DD-words`)

```markdown
# <slug>: delta, revision N
## specs/2026-12/2026-12-20__guest-links.md
### ADDED Requirements
- req-159: When the owner revokes a link, the system shall end the guest's session within one minute. [outcome-1]
### MODIFIED Requirements
- req-152: (was) ... (now) While offline, the system shall queue the invite. [outcome-2] [constraint-1]
### REMOVED Requirements
- req-151: reason. [outcome-1]
```

- Every requirement line cites at least one `[outcome-<n>]` or `[constraint-<n>]` from `intent.md`. The check fails a line that cites none, or an id the intent lacks.
- The spec file a requirement belongs to is shown by the heading above it (`## specs/2026-12/2026-12-20__guest-links.md`), not by its id.
- A REMOVED id is covered by a task like any other: the task proves the old behaviour is gone.

- Group entries by the spec file they change; a new spec is listed with its new path. MODIFIED and REMOVED quote the prior text, so a conflict with a change that shipped in between is visible.
- Every requirement has a stable id `req-<n>` and one EARS sentence. The number is unique across the whole repo (all specs and all change deltas): a new requirement takes the next free number, the highest existing plus 1. A number is never reused.
  - Ubiquitous: `The system shall ...`
  - Event: `When <event>, the system shall ...`
  - State: `While <state>, the system shall ...`
  - Unwanted: `If <condition>, the system shall ...`
  - Optional: `Where <feature>, the system shall ...`
  - Combine with care; one behaviour per requirement.
- Mark what nobody may guess: `[NEEDS CLARIFICATION: <question>]` while drafting. The person resolves it in grilling. None may remain at approval; the check fails it in `intent.md` or `delta.md`.
- The plan cites ids. It never restates the requirement.

## What exists versus what changes
Two short lists: existing components, routes, tables and names the change reuses (by path), and what is new. A builder that reads research about existing code must not rebuild it.

## Journeys
Critical and highly important customer journeys only, numbered `journey-<n>`. Each has one success example and one rejection example, concrete (inputs and observable result). These are the only source of E2E tests.

## Design mapping
Table, one row per design board: `board | screen | components | states`, the board column holding `board-<n>`. Every board is either a screen in this change or an owner-approved drop, written as `dropped: <reason>, approved`. An unmapped board blocks approval.

## Holdout scenarios
- 3 to 10 end-to-end scenarios per feature (a bug or small feature: one), numbered `scenario-<n>`, stored in `~/.factory/scenarios/<repo>/<slug>/`.
- Drafted by a separate agent from the intent's outcomes and the journeys; the person sees them once, at the approval.
- Each scenario starts with `milestone: <id>`: the first milestone that can run it. A milestone's verifier runs its own scenarios and earlier ones. The last milestone, or the release candidate, runs all.
- Only the verifier reads them. The plugin hook `hooks/guard-scenarios.py` denies every other subagent any tool call that names the scenarios folder; the coordinator drafts them in the main session (with `FACTORY_EVAL=1`, the eval harness, even the main session is denied).
- Known limit: the guard reads tool-input text, so a path assembled at runtime or reached through a symlink can bypass it. The verifier fails when the approved scenario set is missing.
- A scenario is a user story with steps and an observable end state. No hints about implementation.
- **Who can see what.** For anything that shows data to a role, the scenarios cover every place that role can see it: pages, lists, notifications, mail, queued jobs. They also cover role changes (member to guest) and mail already queued at the time of the change.
- **Tests that assert the old rule.** The same sweep lists every existing unit test and E2E spec that asserts behaviour the delta changes or removes. Each goes into the owning task's `allowTestEdits` with a check that runs it, or the change is re-scoped. The verifier fails an edit that drops the negative case.

## Architecture decisions (ADRs)
- **When:** the delta or plan makes a choice that is expensive to reverse: a new dependency or service, a data model or migration strategy, a boundary between modules or apps, a protocol, an auth or security model. Not for choices a revert undoes.
- **Where:** `specs/adr/NNNN-<words>.md`, next to the specs it explains. The number is the order; it is never reused or renumbered, and the date sits in the file.
- **Shape:** title; `Status: proposed | accepted | superseded by NNNN`; date; Context (the forces, two to five lines); Decision (one paragraph); Consequences (what it commits us to, what gets harder); `Supersedes: NNNN` when it replaces one.
- **Immutable once accepted:** a change of mind is a new ADR that supersedes the old one. The old file stays, and only its status line changes to `superseded by NNNN`. Never delete or rewrite an accepted ADR.
- **Approval:** a new ADR is `proposed` with the plan and becomes `accepted` at the single approval. The plan and the delta cite ADRs as `adr-<n>` (`adr-7` is `0007-<words>.md`), after an explainer: "links expire on their own (adr-7)".
- **Builders never write ADRs:** a builder who needs a new decision stops and reports it.

## Ids and explainers
Things with content get `word-<n>`; positions in the plan get a capital letter and a number.
- `req-<n>`: requirement, unique across the repo. `adr-<n>`: architecture decision (file `specs/adr/NNNN-<words>.md`).
- `outcome-<n>` and `constraint-<n>`: the intent's outcomes and constraints, written `- outcome-1: ...` in `intent.md` and cited as `[outcome-1]`.
- `scenario-<n>`: holdout scenario. `journey-<n>`: journey. `board-<n>`: design board. `deferred-<n>`: deferral. `finding-<n>`: review or verifier finding.
- `M<n>` (milestone) and `T<n>` (task) are positions and keep their form.
- **Explainer first.** A person never meets a bare id: say in two to eight words what it does (`check-plan.py` enforces the two; the eight is guidance), then the id in parentheses, as in "guests see only their own comments in mail (req-159)". The plan check enforces this in the plan prose and in `intent.md`.
- **Bare ids are fine only** in the `json factory` block, in fenced code, as the leading id of a delta requirement line or a defining list item (`- outcome-1: ...`), in headings, and in citation brackets like `[outcome-1]`.
- A change approved under the old forms (`I1`, `C1`, `<spec-id>/R<n>`) is rewritten by hand to the new ids before its next approval; `check-plan.py` names each old id it finds.

## Bug spec
A failing example plus the expected result. Nothing else. The test that encodes it must fail on the base and pass on the fix. It is still four files: a one-line intent, a delta of one to three requirements, one scenario and a plan with `kind: bug` (`plan-small-template.md`).

## Approval
One approval covers intent, delta, plan and boards together. The approval is the commit SHA at that moment, recorded in the plan's first progress entry. Any later edit to the plan's json block, `intent.md` or `delta.md` needs a new approval and a new SHA. When the change merges, apply the delta to the feature's spec file in the same PR; a new feature's spec is named with the merge date, `specs/<YYYY-MM>/<YYYY-MM-DD>__<feature>.md`.
