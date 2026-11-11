# Designs, changes, and the artifact chain

```
<changesDir>/<YYYY-MM-DD>-<KEY>-<slug>/       open change: decisions.json · intent.md · spec/* · facts.md · plan.md · handover.md?
<changesDir>/<YYYY-MM-DD>-<slug>/             the same, for a change with no Linear issue
  asks/<session-date>-snapmark/              original session.md, img/, optional PDF/zip
  marks.json                                one row per owner note or reference image
  verify/shots/                             fresh headless screenshots for comparison
<changesDir>/archive/<year>/<year-month>/<same name>/   archived when the PR is green
<designsDir>/<date>-<type>-<slug>.md          a design or one decision that outlives one PR
<designsDir>/INDEX.md                         one line per file there, generated; read it first
```

One change = one folder = one PR. The id is `<created>-<KEY>-<slug>`, or
`<created>-<slug>` when there is no Linear issue. `created:` matches the date in the name.
Archiving moves the folder and never renames it.

`spec/` is new in v3. It holds this change's design slice. A design that spans changes still
lives in `docs/designs/`.

## Where things go -- one rule each

| Thing | Folder | Lifetime | Linear |
|---|---|---|---|
| the work of one PR: `intent.md`, `facts.md`, `plan.md`, `handover.md`, and v3 `spec/*` | `changes/<created>-<KEY>-<slug>/` | archived at merge | **issue** (1:1 with the PR) when there is one |
| a design that outlives one PR: data model, ADR, RFC, screen-by-screen design, API contract | `docs/designs/<date>-<slug>.md` | as long as the behaviour exists; `status` and `supersedes` move | **project** (1:1 with the design), plus a Document for ADR and RFC |
| runbooks, architecture, security | `docs/` | forever | none |

**A recurring mistake gets a guardrail, not a lesson.** If something goes wrong twice, the
fix is a check that makes the third time impossible: a test, a CI gate, a lint rule, or a
line in the skill that does the work. There is no `lessons` folder. Either the rule is
enforced somewhere, or it lives in the document it governs.

**One decision, one file. No log.** A decision is an ADR of its own under `docs/designs/`,
with `status`, `supersedes` and `superseded_by` in its frontmatter. A design states what is
true now and is edited in place; it is never a changelog of "Since <ticket>" paragraphs.
`scripts/design_index.py write` turns the folder into `INDEX.md`, one line per file with its
title, status, date and tags, and the guardrail test fails when it is stale. An agent reads
the index and opens the two files it needs, not the folder. Measured in a real repo:
an appended `docs/ux/decisions.md` had reached 2,910 lines in 19 days. `adopt`
splits such a log into one file per decision.

Change = PR, always. Issue = change, when the change has an issue. Project = design.
A project may hold one issue or ten. A design file is required only when the project spans
more than one PR or the behaviour needs a standing description. Nothing under `changes/`
is a design; nothing under `docs/designs/` is a plan.

Two words used to collide, so they are fixed here: the playbook's `spec.md` is our
`facts.md`, inside the change folder. A design is the standing document in `docs/designs/`.

## decisions.json v3

```json
{
  "ticket": "SAM-12",
  "intent": "skip -- the ticket states the problem and the outcome",
  "design": "docs/designs/2026-10-06-my-sampler-sync.md",
  "size": "L",
  "kind": "feature",
  "skips": {
    "ia": "skip -- M: no route, object or name changes"
  },
  "testLocked": false
}
```

| Field | Meaning |
|---|---|
| `ticket` | issue key, `"new"` or `"none"`. Search Linear before writing it. |
| `intent` | starts with `skip -- <reason>` or names the interview/reviewer route. |
| `design` | path under `designsDir`, a new design path, or `"none"`. |
| `size` | `none`, `S`, `M` or `L`. Its presence marks a v3 folder. |
| `kind` | `feature`, `bug`, `refactor`, `docs` or `chore`. |
| `skips` | activity id to `skip -- <reason>`. Ids: `brief`, `ia`, `interaction`, `screens`, `prototype`, `conformance`, `validation`. |
| `testLocked` | only for bugs. Set true after the failing test is committed. |
| `testEdit` | user words that allow a locked test edit. |
| `milestone` | `{"kind": "new"\|"existing"\|"single"\|"hotfix", "slug"}`. Its presence marks a folder on the milestone process. |
| `prExceptions` | `[{"branch", "words"}]`, or absent. A PR or push `pr-gate.sh` would refuse, allowed for that head branch only, with the engineer's own words. Never written without them. |
| `project` | `{"kind": "new"\|"existing", "slug"}`, or **absent**. Absent is the normal case: the milestone is cut from the default branch and its PR goes there. Present means the milestone is cut from `project/<slug>` and its PR goes there instead, and the project branch is what later opens the one reviewed, tiered PR into the default branch. |
| `protectedEdit` | the engineer's words that allow one edit of a protected path after approval. |

Three processes live side by side, chosen by the folder, never by the date:

| Folder has | Process | Gates |
|---|---|---|
| no `size` | v2 | facts accepted, plan gate |
| `size`, no `milestone` | v3 with a design gate (local, 2026-10-06) | owner approves `spec/validation.md`, plan gate |
| `milestone` | the milestone process (approved 2026-10-09) | engineer confirms intent; one gate for UX plan, facts and plan; `lock.json` |

In-flight folders finish on the process they started; `chain-gate.sh` keeps each set of rules.

A folder without `size` is v2. Every v3 gate and guardrail skips it, so in-flight changes keep
working.

### Size presets

| Size | Meaning | Preset skips |
|---|---|---|
| `none` | no interface change | all seven design activities, reason `skip -- no interface change` |
| `S` | words or visuals on an existing screen; no new state, route or control | `brief`, `ia`, `interaction`, `prototype`, `validation`; runs `screens` and `conformance` on the delta |
| `M` | one screen's behaviour, or one flow | `ia`, reason `skip -- M: no route, object or name changes` |
| `L` | a new screen, flow or feature | none |

The agent may remove a preset skip when the work needs the activity. It may not add a skip
silently after the dialog. Adding one needs the user's yes and the reason.

## Files

| File | Playbook name | Made by | Gate | Required |
|---|---|---|---|---|
| `decisions.json` | — | the Stage 1.1 dialog | user answers it | yes |
| `intent.md` | intent.md | sdlc-run and plannotator | originator or reviewer; `## Asks` always present in v3 | yes in v3 |
| `spec/brief.md` | design | `cct:ux-design-run` | Design gate summary | done or skipped |
| `spec/ia.md` | design | `cct:ux-design-run` | Design gate summary | done or skipped |
| `spec/interaction.md` | design | `cct:ux-design-run` | Design gate summary | done or skipped |
| `spec/screens.md` | design | `cct:ux-design-run` | Design gate summary | done or skipped |
| `spec/prototype/index.md` | mock | `cct:ux-design-run` | Design gate summary | done or skipped |
| `spec/conformance.md` | conformance | `cct:ux-rules-validate spec` | Design gate summary | done or skipped |
| `facts.md` | spec.md, the delta | sdlc-run | owner approves with validation | yes |
| `spec/validation.md` | ready review | `cct:ux-spec-validate spec` | owner reads it at the Design gate | done or skipped |
| `plan.md` | plan.md | sdlc-run | owner or allowed self-check | yes |
| `checklist.md` | requirements checklist | a reviewer in a fresh context | `approve` refuses an unchecked item | from 3.8.0 |
| `analyze.md` | analyze pass | sdlc-run, read-only | `approve` refuses an open CRITICAL | from 3.8.0 |
| `challenge.md` | challenge pass | a reviewer in a fresh context, read-only | `approve` refuses an open CRITICAL | from 3.9.0, absent blocks nothing |
| `reflection.md` | reflection | sdlc-run at Stage 7 | none; the owner promotes repeated lessons | from 3.9.0 |
| `spec/qa.md` | build validation | `cct:ux-spec-validate build` | PR evidence | when prototype exists |
| `handover.md` | — | a session that stops mid-build | none | no |
| `marks.json` | owner feedback comparison | `marks.py init`, then the agent | milestone `owner-marks` | when marks or reference images exist |
| `verify/shots/` | build evidence | headless capture | owner comparison and shared UX visual pass | for every row except `ruled-out` |

`python3 scripts/marks.py init <id>` inventories Snapmark notes under `asks/` and reference
images under `asks/` or `spec/prototype/`, excluding mark images from reference rows.
`marks.json` holds a `rows` array. Note rows have `id`, `kind: note`, `session`, `mark`, `note`,
`words` (verbatim) and `image`; reference rows have `id`, `kind: reference` and `image`.
Note IDs use the session folder relative to `asks/`, then the mark and note (`2026-09-26/002.3`);
reference IDs are `ref:<image path>`. Source paths and `shot` are change-relative; `decision`
is a repo-relative ADR path under `designsDir` (default `docs/designs`), or null.

Fill `expected` with one sentence describing what must now be visible after that decision,
`shot` with a fresh headless screenshot, `status`, and `differs` with what still differs.
Notes use `fixed`, `partly`, `not-fixed`, `contradicted`, `ruled-out` or `cant-see`;
references use `match` or `differs`. `fixed` and `match` must have no `differs`.
Only `ruled-out` omits `expected` and `shot`, and it requires an existing ADR.
Every other decision also requires an existing file under `designsDir`.
Non-fixed or unset statuses block unless `accepted` quotes the engineer's acceptance;
acceptance never waives evidence or permits an invalid status.

Init keeps filled fields and adds missing rows. It never deletes rows and reports orphans.
`marks.py check <id>` rejects missing, duplicate, orphaned or changed source rows as well as
unresolved evidence. `marks.py table <id>` prints the milestone comparison, including acceptance.
Use the existing UX visual ledger for opened images; this file does not duplicate it.

## Documents that outlive the change

A change folder holds the work of one PR. Four document types outlive it, and none belongs
under `changes/`. Run the subcommand; do not assemble one by hand. The skill creates the
project, sets the icon and writes the body in a second call so a long description does not 500.

| Document | When | Subcommand | Repo file | Linear |
|---|---|---|---|---|
| **ADR** | a decision worth its reasons in a year | `create-adr` | `docs/designs/<date>-adr-<slug>.md` | Document on the **project** |
| **RFC** | a proposal that needs review before building | `create-rfc` | `docs/designs/<date>-rfc-<slug>.md` | Project **+** Document |
| **PRD** | a PM owns "what" separately from engineering's "how" | `create-prd` | none | Document on the **project** |
| **Research note** | a spike ended without a decision | `create-spike-research` | none | Document on the **issue** |

All four run as `/cct:linear-manage <subcommand>`. Their templates live in
`../linear-manage/references/`, and those files are the source. Do not call `get_template`.

ADR and RFC live in two places, the same way `changes/` does. The repo file under
`docs/designs/` is the source: it is reviewed in the PR where the decision is made, and
`git log docs/designs/` is the audit trail. The Linear document is the readable copy for
everyone without a checkout, written at creation time and not hand-maintained afterwards.
Change the file, then rerun the subcommand.

A PRD and a research note get no repo file. A PM owns the PRD, and a spike finding is not
a standing description of behaviour. Neither is reviewed in a PR, so neither earns a place
in the tree. ADRs, RFCs and research notes carry no EARS; they record a decision, a
proposal or a finding, not a behaviour.

## Frontmatter

Every markdown artifact:

```yaml
linear: REV-947
type: intent | facts | plan | validation | qa
change: 2026-10-06-REV-947-slug
design: docs/designs/2026-10-06-design.md
author: <email>
status: draft | in-review | approved
reviewed_by: null | <name or email>
approved_at: null | YYYY-MM-DD
created: YYYY-MM-DD
archived_at: YYYY-MM-DD
```

`spec/validation.md`:

```yaml
type: validation
change: <id>
verdict: ready | not-ready
status: draft | approved
reviewed_by: null | <owner>
approved_at: null | YYYY-MM-DD
created: YYYY-MM-DD
```

`spec/qa.md`:

```yaml
type: qa
change: <id>
verdict: pass | fail
rounds: <n>
created: YYYY-MM-DD
```

## Gates

`chain-gate.sh` is a PreToolUse hook on `Edit|Write`. It exits 2 before a bad write lands.

| Write to | Refused unless | v3 only |
|---|---|---|
| anything under `<changesDir>/<id>/` | `decisions.json` exists, except for `decisions.json` itself | no |
| `spec/**` | `intent.md` has a non-empty `## Asks` section | yes |
| `facts.md` | v2: intent ran or was skipped. v3: every design activity before facts is done or skipped | partly |
| `plan.md` | `facts.md` is approved, and validation is ready + approved or skipped | validation part yes |
| source outside `changes/**` and `docs/**` | the branch's plan is approved and `## Goal handover` is filled | no |
| source under `prototypeDirs` before plan approval | allowed only for v3 while prototype is not skipped | yes |
| locked test files | `kind` is not `bug`, or `testLocked` is false, or `testEdit` records the user's OK | yes |

The five v3 refusals say the next command:

1. `spec/**` before asks: write `intent.md` `## Asks`.
2. `facts.md` before design is done or skipped: run `cct:ux-design-run <change>` or `cct:ux-rules-validate spec <change>`.
3. `plan.md` before validation is ready and approved: run `cct:ux-spec-validate spec <change>` and get the owner gate.
4. prototype code outside `changes/**` and `docs/**` before plan approval: only paths under `prototypeDirs` are allowed.
5. locked test edit: fix the code, not the test; if the test is wrong, ask the user and record `testEdit`.

Archived folders are never gated. `docs/**` is never gated. A repo with no `sdlc.json`, or with
no branch-matched change folder, is left alone.

## How every artifact is written

Plain American English. One idea per sentence. At most 20 words. Active voice. Lists over
prose. Numbers over adjectives. Exact paths and commands in backticks. Empty template sections
stay in place with `none`.

Facts:

- Open with a Goal paragraph.
- Use EARS for behaviour. Read `references/requirements-grammar.md`.
- Cite asks on every fact: `**F3** (A1, A4) When ...`.
- For UI facts, name the screen or state.
- Every `A<n>` appears in a fact or in `## Out of scope`.
- Unresolved `[NEEDS CLARIFICATION: ...]` blocks the plan gate.

## plan.md sections

Approach · Rules check (with Justified violations) · Where things go · Feature PRs · Design changes · Files that change · Order of work ·
Risks · Out of scope · Done · How to run · Goal handover · Revisions. Beside it: `done.json` (the criteria as
data), `lock.json` (their hash at approval, written by `verify_gate.py approve`), `milestone.md`
(features and their states, the outcome) and `findings.md` (the milestone's one list: `- [ ]` blocking items, `## Converge`, `## Advisory`). `intent.md` frontmatter carries the Decision4 `class`; `approve` copies it into `lock.json`. Detail: `references/quality-passes.md`.

`Done` states how `/goal` knows to stop. `How to run` is the build's process. `Goal handover` is
committed, not spoken: a kickoff prompt, and the `/goal` line, which holds only the end state
(`python3 scripts/sdlc_status.py goal <ID>` printed `GOAL <ID> DONE` or `BLOCKED`) because a small
model judges the condition from the transcript and cannot read files or GitHub.

**Risk:** `goal_active()` in `chain-gate.sh`, `pr-gate.sh` and `verify-on-stop.sh` reads the last
`goal_status` attachment of the transcript. Claude Code does not document that entry, so a release
may rename it. The hooks' fixtures (`test_chain_gate.py`, `test_pr_gate.py`, `test_sdlc.py`) pin
today's shape; a failing fixture after a Claude Code update means the entry moved.

The milestone verify gate appends built-in `owner-marks` (`marks.py check`) after locked checks
when `asks/` holds a Snapmark session or `marks.json` exists; feature gates do not run it.
It cannot be disabled in `sdlc.json`, does not change `lock.json`, and fails as `check=owner-marks`.

## History

| Event | Commit message | In the file |
|---|---|---|
| intent drafted | `changes(<id>): intent drafted` | `status: draft` |
| sent to a reviewer | `changes(<id>): intent to review by <who>` | `status: in-review` |
| intent approved | `changes(<id>): intent approved by <who>` | `status`, `reviewed_by`, `approved_at` |
| spec approved | `changes(<id>): spec approved by <who>` | `facts.md` and `spec/validation.md` approved |
| facts accepted, v2 | `changes(<id>): facts accepted` | |
| plan approved | `changes(<id>): plan approved` | `status`, `reviewed_by`, `approved_at`, annotations file kept |
| failing bug test committed | `changes(<id>): failing test locked` | `testLocked: true` |
| plan changed after approval | in the implementing commit | line under `## Revisions` |
| archived | `changes(<id>): archived` | `archived_at` |
| intent confirmed (milestone process) | `changes(<id>): intent confirmed by <who>` | `intent.md` approved |
| one gate passed (milestone process) | `changes(<id>): approved by <who>` | facts and plan approved, `lock.json` |
| feature merged | in the milestone branch | `milestone.md` row → `merged` |
| outcome read | `changes(<id>): outcome` | `milestone.md` `## Outcome` |

## Linear

Status lives in Linear, content in the repo. Move the issue to `In Progress` when the folder is
created, `In Review` when the PR opens, and `Done` or `Ready To Deploy` after merge. Resolve by
status type where possible.

What crosses into Linear goes through `scripts/linear-safe.py`: repo paths become GitHub
permalinks; local laptop paths are refused.

## sdlc.json keys

| Key | Used by | Meaning |
|---|---|---|
| `linear.team`, `linear.project` | skill | where issues go |
| `defaultBranch` | skill, docs | base for worktrees and PRs |
| `changesDir`, `designsDir`, `docs` | skill, tests, docs | where artifacts live |
| `verify` | PR verify, plan Done, docs | full command before PR |
| `verifyStop` | Stop hook | fast command on stop; falls back to `verify`. Skipped inside an active `/goal` and when the dirty diff is unchanged since the last pass |
| `verifyDirty` | Stop hook | globs that make a stop worth verifying |
| `planGate` | skill | `owner` or `self`; self is barred for data safety, irreversible writes, security or money |
| `testGlobs` | hook, tests | test files locked while `testLocked` is true |
| `prototypeDirs` | hook, design | prototype code paths allowed before plan approval |
| `feedback` | Stage 1.3 | owner-words files or globs for asks |
| `lintOnEdit` | edit hook | file-scoped formatter or lint commands |
| `blocked[]` | Bash hook, tests | blocked shell patterns with routes |
| `toolsCommand` | SessionStart, docs | installs plannotator and plugin |
| `tests`, `testFile` | adopt | rendered guardrail test type and path |
| `codeowners` | compatibility only | ignored; the repository team owns CODEOWNERS |
| `claude` | adopt, test | whether Claude workflows are generated |
| `claudeAllow` | none | obsolete since 3.7.0, when `claude.yml` went; `adopt` leaves the key alone |
| `showChannel` | adopt | Slack channel for show notices |
| `tiers` | adopt, test, docs | Ship / Show / Ask on or off |
| `askGatesMerge` | adopt | whether `ask` withholds auto-merge |
| `keep` | adopt | generated paths this repo owns |
| `checks.feature[]`, `checks.milestone[]` | `verify_gate.py` | commands, cheapest first; `{id}` is the change id; a string or `{name, run}` |
| `milestones` | skill | `{branchPrefix}`; default `milestone/`. A milestone is cut locally from its parent: the project branch when the project has one, else the default branch, or from the milestone its plan row `needs`. `rebaseOnDefault` is obsolete since 3.7.0: a parent is merged in, never rebased |
| `projects` | skill | `{branchPrefix}`; default `project/`. Only used when `decisions.json` `project.branch` is true (or the project predates 3.7.0 and has no `branch` key); otherwise a project is planning only and its milestones go straight to the default branch |
| `rules` | skill | optional list of repo paths holding standing rules (code of conduct, `PRODUCT.md`, `DESIGN.md`, an architecture policy). Stages 1 and 4 read them; intent lists the rule IDs that apply, each fact cites the IDs it touches. Absent: the defaults in `references/quality-passes.md`, existing files only. `adopt` never writes it, keeps it on re-adopt and rejects a value that is not a list of paths |
| `hotfix` | skill | the hotfix lane on or off; default `true` |
| `delivery` | skill | `one-go` (default): one `/goal` builds every feature as commits on the milestone branch and closes the milestone; `feature-prs`: one PR per feature into the milestone |
| `goal` | skill | `{runTurns, featureTurns, milestoneTurns}`; default 150, 40 and 30 |
| `builders` | skill, adopt | who builds feature rows and fix parts: `claude` (`cct:sdlc-feature-builder` agents, default) or `codex` (`scripts/codex-build.sh` runs the Codex CLI in the worktree, network off, `.git` read-only; the wrapper checks the result and makes the commit). The supervisor, the milestone close and the gates stay Claude either way |
| `builderModel`, `builderEffort` | skill, adopt | which model builds and how hard: for `claude` the `model` and `effort` of every `cct:sdlc-feature-builder` dispatch (a Claude Code alias `sonnet`, `opus`, `haiku` or a model id; default `sonnet`, `high`), for `codex` the `--model` and `--reasoning` of `codex-build.sh` (default `gpt-5.5`, `high`). Effort is one of `low`, `medium`, `high`, `xhigh`. A plan's Approach may name another pair for that one change |
| `languages` | skill, checks | the languages the product ships; default `["en"]` |
| `ciPaths` | CI, agents | `{docs, all, code, config, specs, lint, unit, build, e2e, deploy}`: which changed files switch which CI step on (`code`/`config` gate, `include`/`exclude` globs per step); a file in neither runs nothing; not under `checks`, so no lock; defaults per stack in `templates/ci-paths.json`; `references/ci-blueprint.md` |
| `ciCommands` | CI | `{install, lint, unit, build, e2e, e2eTouched, deploy}`: what each job of `templates/ci/github-actions.yml` runs; defaults per stack in `templates/ci-commands.json` |
| `sdlcVersion` | adopt, status, verify_gate | the sdlc-run version the repo was last adopted or upgraded with; a missing or older stamp prints one line naming `adopt --upgrade`; never blocks; `references/changelog.md` |
| `responsiveTier` | milestone stage | the `ux-responsive-audit` matrix tier; default `full` |
| `ux` | skill, hook | `on` or `off`; `off` skips the UX plan and UX checks (python preset default) |
| `tracker` | skill | `{kind: linear\|github\|beads\|none, …ids}`; the old `linear` key means `linear`; `references/trackers.md` |
| `protected` | hook | globs refused after approval; default `sdlc.json`, `**/*-snapshots/**`, `**/__screenshots__/**`, `**/*allowlist*` |

`feedback` is repo paths or globs only. Stage 1.3 copies each resource that came with an ask
into `changes/<id>/asks/<source-date>/` and links it from `intent.md`. Nothing in a change
folder links to `/Users/`, `~/`, `file://` or another local path outside the repo.
