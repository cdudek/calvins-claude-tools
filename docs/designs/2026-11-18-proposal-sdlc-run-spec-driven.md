---
type: proposal
status: accepted
created: 2026-11-18
author: Claude, from the owner's verdict on sdlc-run
supersedes: none
---

# sdlc-run follows spec-driven development in three documents

The owner's verdict: "It does not follow proper spec-driven development (SDD), and the spec is spread across too many documents." This proposal makes sdlc-run follow SDD properly with far fewer documents, keeps what works, and does not slow the pipeline. Speed and failing fast stay the top priority. Paths below are under `plugins/cct/skills/sdlc-run/` in the latest stacked version. No code changes are made here.

## 0. What proper SDD means (primary sources)

- **The spec is the primary artifact.** "The specification becomes the primary artifact"; code expresses it, and acceptance scenarios become tests ([Spec Kit, spec-driven.md](https://github.com/github/spec-kit/blob/main/spec-driven.md)).
- **The spec is kept current.** "Maintaining software means evolving specifications" (same source).
- **One spec per feature, and it persists.** Spec Kit keeps `specs/<nnn-feature>/spec.md` in the repo. Kiro keeps `requirements.md`, `design.md` and `tasks.md` per feature ([Kiro specs](https://kiro.dev/docs/specs/)).
- **Three roles, in order.** What and why (requirements with ids and acceptance criteria), then how (design), then tasks derived from both ([Spec Kit spec template](https://github.com/github/spec-kit/blob/main/templates/spec-template.md) uses FR-001 style ids and `[NEEDS CLARIFICATION]`; Kiro's design holds architecture, data flow, error handling and testing strategy).
- **Persistent project context is separate from the feature spec.** Spec Kit has a constitution; Kiro has steering files `product.md`, `tech.md`, `structure.md` ([Kiro steering](https://kiro.dev/docs/steering/)). sdlc-run already covers this with `sdlc.json` rules, `CLAUDE.md` and architecture policy, so nothing new is needed there (the research note on this said the same).

## 1. What is wrong today

### 1.1 The inventory

A change folder can hold these. "Gate" means a hook, script or check that depends on it.

| Document | Purpose | Writer | Reader | Gate depending on it |
|---|---|---|---|---|
| `decisions.json` | size, kind, milestone, skips | the intake dialog | every script | status script, builder launch, status routing (SKILL.md:98-105) |
| `intent.md` | asks, job stories, success measure, problem, outcome, constraints | agent, owner confirms | owner, UX, facts | lint, owner touchpoint one |
| `asks/` | the owner's requests as given, images, bundles | agent | marks script | `marks.json` and the owner-marks check |
| `spec/brief.md`, `ia.md`, `interaction.md`, `screens.md` | UX brief, structure, behaviour, screen specs | UX design skill | owner, builder | chain-gate refuses facts before it |
| `spec/conformance.md`, `readiness.md` | rules verdict, spec readiness | validate skills | owner at the gate | read at the gate |
| `spec/prototype/` | generated images | UX skill | owner | only when UI is risky |
| `facts.md` | goal, EARS criteria with ids and tags, out of scope, assumptions, deferred, open questions | agent | everyone | locked by hash; chain-gate blocks edits after approval (chain-gate.sh:145) |
| `checklist.md` | gaps and ambiguities in the facts | fresh reviewer | agent | approve refuses an open item (verify_gate.py:207) |
| `plan.md` | approach, rules check, where things go, feature rows, order, milestones, risks, done, how to run, goal handover | agent | owner, builders | the plan gate, lint |
| `analyze.md` | coverage table and six consistency passes | agent | agent | approve refuses an open critical (verify_gate.py:209) |
| `challenge.md` | five-lens argument against the change | fresh reviewer | agent, owner | approve refuses an open critical |
| `done.json` | the criteria as data (ids, tags, pages, widths, turn caps) | approve step | checks | locked by hash |
| `lock.json` | hashes proving criteria did not move | approve step | every gate run | feature and milestone gates |
| `questions.md` | questions asked during the build, defaults taken | builders | owner | lint |
| `milestone.md` | features, state, outcome | builders | owner, status script | status script, milestone gate |
| `validation.md` | each fact exercised in the built app | builder | milestone gate | blocks on "not met" |
| `findings.md` | review findings and the converge section | review agents | fix round | blocks on open items and on a missing `Converged:` line |
| `verify/` | gate reports, screenshots | gate script | owner | the owner comparison |
| `marks.json`, `handover.md`, `reflection.md`, `spec/qa.md` | marks comparison, session handover, lessons, build QA | various | various | owner-marks check for the first |

That is about 20 documents plus a generated `README.md` reading map (SKILL.md:44). The writer list in `change_docs.py:132-151` is, in effect, the confession: a map is needed because nobody can find the spec.

### 1.2 Where this breaks SDD

1. **The spec is split across five documents.** The why is in `intent.md`, behaviour in `spec/*`, acceptance criteria in `facts.md`, the how in `plan.md`, and the proof in `validation.md`. A reader, or a new agent, must open all of them to learn what the change is. SDD wants one spec.
2. **The word "spec" means two things.** `spec/` is the UX folder, while the file chain.md:49-50 says "the playbook's `spec.md` is our `facts.md`". Three names for one idea.
3. **Facts die in the archive.** Specs live in `changes/` and move to `changes/archive/` on merge (chain.md:9, stage 7). After release the only description of what the product does is the code. Spec Kit and Kiro keep the spec per feature; here it is deleted from the working tree. A new change cannot "read the current spec first" because there is none. (`docs/designs/` holds only designs that span changes, chain.md:18.)
4. **Requirements and design are mixed or missing.** `plan.md` is the design but has no test strategy, error handling, contracts, rollout or rollback, and no proof-before-build for risks (research note, gaps 1-6).
5. **Tasks are not derived from the spec.** The plan's feature rows and `milestone.md` rows are written by hand next to the facts, then `analyze.md` checks they match. Derivation by hand, verification by a second document.
6. **Review is three passes with three files.** `checklist.md`, `analyze.md` and `challenge.md` each read the same documents and write a separate finding table (quality-passes.md:38, 46, 62). Each is a model call, and the owner reads none of them.
7. **State sits next to prose.** `done.json`, `lock.json`, `decisions.json`, `verify/`, `findings.md` and `questions.md` are machine state or logs, yet live in the same folder as the documents a person must read.

### 1.3 What works and must stay

Verbatim asks mapped both ways; EARS facts with ids and test tags; budgeted clarification and "questions never block"; fresh-context reviewer; the hash lock after approval; two owner touchpoints; the milestone gate with converge; size scaling. All of these survive below. Most move to a new file, none is removed.

## 2. Target structure: three documents

Per change, under `changes/<id>/`:

1. **`spec.md`**: why and what. Frontmatter (type, status, size, kind, tracker key, links), then sections:
   - Intent in one sentence; **Asks** table (verbatim, ids A1...); **Job stories** with evidence label; **Success measure**.
   - **Requirements**: EARS sentences with stable ids, each citing asks and rules and naming its test tag (the current `facts.md` content).
   - **UX** (only when there is a UI): one section with the state table and screen list. The long form (brief, ia, interaction, screens, prototype) stays a linked folder `ux/` only when size is L. The folder is renamed from `spec/` to `ux/`, which removes the clash in 1.2.
   - **Clarifications** (answered, plus at most three open `[NEEDS CLARIFICATION]`), **Assumptions**, **Out of scope**.
2. **`design.md`**: how. Approach and the rejected option; rules check and justified violations; where things go (components, data flow); interfaces and contracts; data and migrations; error handling; **test strategy per requirement id** (level, real versus faked); **risks, each with a proof-before-build check** (a command or a short script, or "known"); rollout and rollback; the open design questions.
3. **`tasks.md`**: ordered list derived from spec plus design. Each task has an id, the requirement ids it satisfies, its test, its dependencies and its milestone. A `[P]` mark flags tasks that can run in parallel (Spec Kit does this). Milestone groups replace the feature rows now in `plan.md` and `milestone.md`. Task state (todo, done with commit) is ticked here, which replaces `milestone.md`.

The "goal handover" and "how to run" blocks of `plan.md` become a short generated header in `tasks.md`, since they are process, not design.

Everything else is machine state in one folder, `state/`, which people never need to read: `state/lock.json`, `state/done.json`, `state/decisions.json`, `state/findings.json` (review output), `state/questions.jsonl`, `state/validation.json`, `state/verify/`, `state/asks/`, `state/marks.json`.

### 2.1 Decision for every current document

| Current | Decision | Why |
|---|---|---|
| `intent.md` | merge into `spec.md` (Intent, Asks, Job stories, Success measure) | same reader, same time; two files cost an approval round |
| `facts.md` | merge into `spec.md` Requirements | this is the requirements section under another name |
| `spec/*` UX files | keep as `ux/` for L; a section of `spec.md` for S and M | UX is part of the spec; a folder only when it earns its size |
| `spec/conformance.md`, `readiness.md` | machine state (review findings) | a verdict, not a document to read |
| `spec/prototype/` | stay under `ux/` | images; unchanged |
| `plan.md` | becomes `design.md` plus the task part of `tasks.md` | separates how from the ordered work |
| `checklist.md`, `analyze.md`, `challenge.md` | folded into one review; findings become `state/findings.json` | one pass over three documents, see 4.2 |
| `done.json` | machine state, generated from `spec.md` ids at approval | already data, never read by people |
| `lock.json` | machine state | hashes now cover the three documents |
| `decisions.json` | machine state; size and kind also stay in `spec.md` frontmatter | scripts read the JSON; the person reads the frontmatter |
| `questions.md` | machine state `questions.jsonl`; the owner sees them as one generated list in the PR body | an append log is not a document |
| `milestone.md` | folded into `tasks.md` (groups and state) | state of tasks is the same fact twice |
| `validation.md` | machine state `validation.json`; summary in the PR | evidence for the gate |
| `findings.md` | machine state, same file as review findings with a `converge` section | one findings store for review and converge |
| `asks/`, `marks.json`, `verify/` | machine state | evidence |
| `handover.md`, `reflection.md` | delete as separate files; one `## Handover` line group at the end of `tasks.md`, reflection goes to the PR body | rarely read, often stale |
| `README.md` reading map | delete; three documents need no map | the map existed because of the sprawl |

### 2.2 Readability keeps working

The "plain words first, id in brackets" rule and `verify_gate.py lint` carry over: OWNER_FILES (verify_gate.py:107) becomes the three documents. Id families shrink: A, J, R (requirements, replacing F and N), T (tasks); X, H, Q and C become fields inside the machine findings.

## 3. Living specs

**Where the accepted spec lives.** After merge, `specs/<capability>/spec.md` at the repo root. A capability is a thing a user can name ("series and webinars", "billing settings"), not a ticket. This follows the split OpenSpec makes between current specs and proposed changes, already noted in `references/layout-research.md`. The change folder holds only the **delta**: new, changed and removed requirement ids, written in the same `spec.md` format with a `## Delta` heading per capability. `design.md` stays in the archive with the change, because design rationale is history; only decisions worth keeping become one-file-each designs as today.

**On merge:** the close step applies the delta to `specs/<capability>/spec.md`, moves the change folder to the archive as now, and the milestone PR carries both, so the spec moves with the code in the same review. A small script does the merge mechanically: requirement ids are stable, so added, modified and removed ids are plain operations.

**A new change reads the current spec first.** Stage 1 searches `specs/` by capability name (the way it already reads the designs index), lists the capabilities touched in `decisions.json` and loads only those specs. A change with no capability yet creates one.

**Drift is caught cheaply.** One check in the milestone gate and in CI: every requirement id in `specs/**/spec.md` must appear as a tag in some test title (`@R12`), and every tag in a test must exist in a spec. Ids are scoped by capability prefix (for example `SER-12`) so tags stay unique. Cost: a grep over two trees, seconds. It catches a requirement dropped without tests, a test with no requirement, and a spec edited by hand without the matching delta. It does not prove the tests are good; the existing converge pass still does that.

A requirement may carry `status: planned | live | removed`. Planned requirements in the spec do not need tags yet; the check starts at `live`.

## 4. Gates in the new shape

### 4.1 Touchpoints: keep two, merged into one if the size allows

Today: confirm intent, then approve the UX plan, facts and plan together (SKILL.md:129-134). In the new shape the second one is **approve spec and design and tasks**, a single plannotator round on three documents.

**Recommendation: one gate for S and M, two for L.**
- *For one gate:* the intent confirmation today mostly checks that the asks and job stories were understood. In `spec.md` those are the top of the same file the owner will read for requirements anyway, so one read and one decision cover it. It removes a round trip and a wait, which is the owner's top priority.
- *For two on L:* a wrong spec found after the design is written wastes the design. On L (new screen or flow) approve `spec.md` first, then `design.md` and `tasks.md`. This is exactly the Kiro order, and it fails fast where the cost of being wrong is highest.
- On a one-gate change, the agent writes the spec, runs the cheap lint and the reviewer, and only then asks.

### 4.2 One review, findings as machine state

Replace checklist, analyze and challenge by **one reviewer call** in a fresh context over the three documents, returning structured findings into `state/findings.json` with the same severities. Its brief carries all the old lenses: gap and ambiguity (checklist), coverage and consistency (analyze), existence, simpler alternative, failure assumptions, implicit choices, who else is affected (challenge), plus the new "build this from the documents alone and list every question you would have" question from the research note. Fewer calls, one context load, no three-file hand-off. The reviewer never edits; the agent fixes at the source and marks the finding fixed. `approve` still refuses an open critical.

### 4.3 Fail-fast order

1. **Lint** (seconds, no model): bare ids, sentence length, placeholders, missing frontmatter, an empty section the size requires.
2. **Cross-document consistency, by script** (seconds, no model): every ask maps to a requirement or out of scope; every requirement id has a task and a test strategy line; every task cites ids that exist; every risk has a proof column. This replaces the coverage table of `analyze.md`. A script fails faster and more reliably than a model for this.
3. **Reviewer** (one model call), only after steps 1 and 2 pass. A reviewer should never be the first thing to find a missing id.
4. Owner gate.

### 4.4 How the existing machinery maps

| Today | New |
|---|---|
| `facts.md` and `done.json` hashed in `lock.json` (verify_gate.py LOCKED) | `spec.md` Requirements section, `design.md` and `tasks.md` task list hashed in `state/lock.json`; `state/done.json` generated at approve |
| chain-gate PROTECTED_FILES: `facts.md`, `done.json`, `lock.json` (chain-gate.sh:145) | `spec.md`, `state/done.json`, `state/lock.json`; the hook blocks edits to requirement lines only, so ticking tasks is still allowed |
| approve refuses open checklist item, open critical in analyze or challenge | refuses an open critical in `state/findings.json` or a failed consistency script |
| milestone gate: `validation.md`, `findings.md`, converge line | same checks, read from `state/validation.json` and `state/findings.json` |
| status script reads `milestone.md` rows | reads `tasks.md` task state |
| `marks.py`, `design-inputs` | unchanged, paths move under `state/` |
| plan gate hook (`plan.md` approved) | the three documents `status: approved` |

## 5. Scaling by size

**S: one short `spec.md`, no `design.md`.** A one-sentence change gets one plain sentence, the asks it answers and one test tag; nothing else. No tasks file; the builder reads the spec. The lint check and the script consistency check run; the reviewer is skipped (as challenge is skipped for S today). Example:

```
---
type: spec
size: S
---
# Spec: show the plan name on the invoice page
Asks: A1 "the invoice page does not say which plan this is"
R1 (A1) When the invoice page loads, the system shall show the plan name under the title. Tag @R1.
Out of scope: changing invoice layout.
```

**M: `spec.md` plus `tasks.md`.** The spec is full; there is no separate design, only a short `## Design notes` section inside `tasks.md` for approach, rejected option and risks with their proof check. The reviewer runs, with a narrower brief.

**L: all three.** Spec with a UX section or `ux/` folder, a full `design.md` (rollout and rollback required when data or an API is touched), and `tasks.md` with milestone groups and dependencies. Two owner gates, per 4.1.

The size already exists in `decisions.json` and gates what the lint demands; no new decision.

## 6. Migration

- **In flight changes keep the old layout.** Every reader (status script, gates, hooks) falls back: if `spec.md` is absent and `facts.md` exists, use the old file names; `state/` is checked first, then the old location. The layout version is recorded in `decisions.json` (`layout: 4` for new, absent for old). No flag day.
- **Adopt upgrades repos.** The adopt command gets a `layout` step: install new templates and scripts, add `specs/` and the drift check to CI, and print what an open change must do. It does not touch an open change.
- **A converter script outline** `convert_layout.py <id>`: (1) read `intent.md` and `facts.md`, write `spec.md` (concatenate asks, job stories, success measure, then requirements with ids renamed F to R and N to R); (2) read `plan.md`, split into `design.md` (approach through risks) and `tasks.md` (feature rows, order, milestones, merged with `milestone.md` state); (3) move `done.json`, `lock.json`, `decisions.json`, `questions.md`, `validation.md`, `findings.md`, `asks/`, `marks.json`, `verify/` into `state/` converting tables to JSON; (4) recompute the lock hashes, which the owner re-approves (the agent never re-locks, as today); (5) optional back-fill: for each archived change in the last quarter, build the first `specs/<capability>/spec.md` from its requirements. Back-fill is a lower priority and can wait.
- **Order of PRs.**
  1. cct: new templates, `spec.md` format, the reviewer brief, consistency script, drift check, fallback readers and the converter; one version bump and one changelog entry. Stacked work in the convergence branch lands first.
  2. The downstream kit copy, through the existing parity check (cct leads, the copy follows).
  3. The adopted repos, one `adopt` upgrade PR each, batched so each repo carries one PR, with the drift check in report-only mode for one week, then blocking.
- **Do not rename the skill or the stage numbers.** Only documents change.

## 7. Cost and speed

**Saves per change (M or L):**
- Documents the agent writes: from about 8 prose files (intent, facts, plan, checklist, analyze, challenge, milestone, README) to 3. The agent drafts one `spec.md` in one pass; today it drafts intent, then facts after the UX plan.
- Model calls at the gate: three review passes become one (about two fewer calls, each a fresh-context load of the same documents).
- Consistency checking moves from a model pass to a script: seconds, no tokens.
- The owner reads three documents, with the first one containing what they previously read as two. One gate on S and M removes a wait.
- Less reconciliation: today the coverage table exists only because facts, plan and milestone could disagree.
- Later changes start faster: they read `specs/<capability>/spec.md` instead of reconstructing behaviour from archive.

**Adds:**
- A `design.md` the owner reads on L (test strategy, rollback, proof-before-build). This is deliberate and is the research note's top gaps; it is added work only where the risk is.
- The delta merge at close: a small script, a few seconds, one extra diff for the owner to scan in the PR.
- The drift check: seconds in CI.
- A one-time migration cost: the converter and fallback readers, paid once in cct and once per adopted repo.

**Net:** faster for every size. S gets lighter than today (one file, no reviewer). M and L drop two model passes and one or two documents; they add design content only where the process now demands it anyway. I have not measured this on a real change; the first migrated change should record gate time and calls before and after, and the numbers should go in the changelog.

## 8. Owner decisions

1. **One gate or two?** Recommend one for S and M, two for L (spec, then design plus tasks). Reasons in 4.1.
2. **Where do accepted specs live?** Recommend `specs/<capability>/spec.md` at the repo root, kept current by the delta merge at close. Alternative: keep them under the designs folder; recommended against, since designs there are dated, one-file-each and never edited in place by a change.
3. **Capability names.** Recommend that the agent proposes a capability at intake from the asks and the existing `specs/` list, and the owner confirms in the existing intake dialog. No new dialog.
4. **Requirement id style.** Recommend a capability prefix plus number (`SER-12`) so ids stay unique across specs and test tags; the drift check relies on this. Alternative is plain `R12` per change, which cannot be checked across specs.
5. **Rename the UX folder from `spec/` to `ux/`.** Recommend yes; it removes the word clash and costs a path update in the UX skills and chain-gate.
6. **Fold three reviews into one.** Recommend yes, with the script consistency check before it. The risk is a missed finding class; the one-round rule and the converge pass at close still apply.
7. **Drop `README.md`, `handover.md` and `reflection.md` as files.** Recommend yes. Reflection goes into the PR body; handover becomes the tail of `tasks.md`.
8. **Back-fill specs from recent archive?** Recommend not now. Start `specs/` as changes touch a capability; back-fill only the capabilities the owner names.
9. **Drift check strictness.** Recommend report-only for one week per repo, then blocking at the milestone gate and in CI, for `live` requirements only.
10. **Constitution or steering file.** Recommend none. `sdlc.json` rules, `CLAUDE.md` and architecture policy already play that role; adding a file would be one more thing to keep current.

## 9. Amendments after the reviews and the owner's decisions (what was built)

Owner decisions of 2026-11-19 win over sections 2 to 8. Where they differ, this section is the
design; the sections above stay as the reasoning.

- **Living spec (replaces section 3).** One file per requirement, `specs/<capability>/rules/R123.md`, a `manifest.yaml` per capability, a generated `specs/CAPABILITIES.md`. No `specs/<capability>/spec.md`, no `## Delta`, no apply script, no hashes: the PR's git diff is the delta. Rule ids are `R` plus a running number with no fixed width, never reused (next = highest ever used + 1, from git history or `.sdlc/last-rule-id`); `spec renumber` fixes a collision before merge, moving a rule to another capability is a file move with no retag. The `SER-12` prefix style is dropped (it looked like a tracker key and made every move a retag).
- **Drift check (replaces the grep in section 3).** A changed rule needs a changed test; tagged tests that are skipped do not count; `proof: test | manual | check:<name>` keeps rules no test can prove from forcing fake tests; `planned` rules need no tag until live.
- **Finding rules.** A local index inside `.git` (id, capability, summary, status; never committed), `spec find` with git dates as the tie-break, an open-PR conflict warning and a staleness flag; a recall@10 eval against a grep before a repo goes blocking.
- **No archive.** Change folders are removed after the merge; existing archives go once their changes are complete. The success measure moves to `.sdlc/outcomes/<id>.json` first. This replaces the flat archive of section 3 and Stage 7.
- **Three documents, as proposed, with these changes from the reviews.** Scope S, M or L is chosen by change risk, not UX size. The lock covers `spec.md`, `design.md` and the task rows, never ticks or the handover; only the supervisor ticks `tasks.md`. Findings carry a `phase`. The `state/` folder move, the `intake.json` rename and capability `decisions/` folders are not built: machine files keep their paths so every reader keeps working, and layout 4 is opt-in per repo and pinned per change in `decisions.json`.
- **Planning practices folded into `design.md`.** Ground truth with `file:line`, a proof before build per risk, rollout and rollback, the architecture checklists as a trigger, a test strategy per rule, a cold-read question in the single reviewer's brief.
- **Deadlocks.** D1 (spec needs future facts), S1 (skip behind a prerequisite) and S3 (outcome with no later PR) are closed in `references/change-folder.md` and tested in `scripts/test_spec.py`.
- **Where.** `plugins/cct/skills/sdlc-run/templates/scripts/spec.py`, `templates/change/{spec,design,tasks}.md`, `templates/specs/`, `references/change-folder.md`, `references/living-spec.md`. Gate wiring is in [sdd-integration](sdd-integration.md).
