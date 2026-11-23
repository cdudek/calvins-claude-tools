---
name: sdlc-run
description: >-
  Runs an AI-native SDLC in any repo: the agent drafts intent, UX plan, facts and tech plan,
  the engineer confirms twice, then one /goal builds every feature as commits on a milestone
  branch and closes the milestone with the heavy checks once and one PR (one go, the only delivery). Work
  spanning several milestones adds a project branch between the milestones and the trunk; only
  the PR into the default branch is reviewed and tiered. Use when someone starts or continues a
  feature, bug fix, refactor, docs change, chore, hotfix, milestone or project, asks "how do we
  do X here", or says "run sdlc", "adopt sdlc", "sdlc status". Subcommands: "adopt" installs the
  chain, "status" lists open changes and gates.
allowed-tools: "Read Grep Glob Edit Write Agent Skill AskUserQuestion Bash(bash */sdlc-run/scripts/*) Bash(python3 */sdlc-run/scripts/*) Bash(python3 */sdlc-run/templates/scripts/sdlc_version.py*) Bash(python3 scripts/sdlc_version.py*) Bash(python3 scripts/verify_gate.py *) Bash(wt *) Bash(git *) Bash(gh *) Bash(bd *) Bash(plannotator *) Bash(make *) Bash(pnpm *) Bash(uv *) Bash(npx *) EnterWorktree mcp__claude_ai_Linear__* mcp__linear__*"
user_invocable: true
metadata:
  version: 3.26.4
  author: calvindudek
effort: high
---

# sdlc-run — two confirmations, then autonomous inside /goal

Verification and every push follow the [local-first contract](references/local-first.md); read it before running checks or preparing a push.

```
1 Intent ──▶ engineer confirms ──▶ 2 UX plan ─ 3 Facts ─ 4 Tech plan ──▶ engineer confirms once
                                                                              │
     ┌──────────────────────── one /goal, one go ────────────────────────────┘
     ▼
5 Build: feature ─▶ touched tests and pre-commit checks ─▶ commit ─▶ next feature
     ▼                                       questions ─▶ questions.md, never blocking
6 Milestone: checks + E2E once, validation against the facts, one fix round ─▶ PR, release
     │  (next milestone, cut from this one, builds meanwhile)
7 Outcome: the next change removes the merged folder (no archive), read the success measure after release

Branches: <default> ─ [project/<slug>] ─ milestone/<slug> ─ features
          only the PR into <default> is reviewed and tiered
```

One change folder `changes/<YYYY-MM-DD>[-<KEY>]-<slug>/` holds intent, `spec/`, facts, plan,
`done.json`, `lock.json` and `milestone.md`. **One go is the only delivery** (`sdlc.json`
`delivery: "one-go"`): everything asked for at once is one change, its features land as commits on
`milestone/<slug>` inside one `/goal`, and one milestone PR ships them — into `project/<slug>`
when the change belongs to a project, otherwise straight into the default branch, which
releases. The change keeps its folder in that PR; the next change's first commit removes it (`sdlc_status.py sweep-merged`), so a change needs one PR, never a records-only second one. The tracker (`sdlc.json` `tracker`: Linear, GitHub, Beads or
none) is the status record; a missing ticket never blocks. What is what in each tool:
`references/trackers.md`.

Designs and decisions outlive a change: one file each in `designsDir`, never an appended log.
**Read `<designsDir>/INDEX.md` first** and open only the files it points to; run
`python3 scripts/design_index.py write` after adding or changing one (`references/chain.md`).

Every change folder starts with a generated `README.md`, the reading map: three entry points
(understand, review, pick up) and one row per document. Regenerate it just before each stage commit, so the commit carries it
(`sdlc_status.py readme <id>`; it writes only when the content changed, only over a README it
generated, and `status` never writes it). Write plain words first and the id in brackets after ("Designs
win over today's app (Q202)"); `verify_gate.py lint` flags a bare id in what the owner reads, and
`sdlc_status.py ids <id>` says what each id means. `references/readability.md` has the rest.

Read `sdlc.json` first: `tracker`, `checks`, `milestones`, `projects`, `hotfix`, `goal`, `languages`, `responsiveTier`,
`ux`, `protected`, `planGate` and the v2 keys. No file means the repo is not adopted: run
`adopt`. **Project values come from the repo** (sdlc.json, PRODUCT.md, DESIGN.md); where it
defines nothing, the kit default applies and every report names the defaults it used.

Read the [shared worktree policy](../../references/worktree-usage.md) for every lifecycle operation; Stage 1.0 owns its one-time installation preflight.

## Scannable PR text (required)

- **Order:** `## What` → `## Why` → `## Proof` → `## Before merge` (only while something is open) → `## How hard is it to undo this PR after merging?` → `## Decision record` (Repair, Migrate and Answer only).
- **Bullets:** Every section is a list; start each bullet with a bold label (`- **Source plan:** 0 adds, 8 updates, 38 destroys.`). Keep one idea per bullet, at most two lines, and no paragraph longer than two sentences. Keep checklist syntax and bold-label the item.
- **Proof:** Name the check and result (`- **Unit tests:** 1,320 passed.`). Put links on the label or result, never a bare URL in prose. Preserve claims and human checklist attestations when restructuring an existing body.
- **Decision4 (advisory):** Copy the section from the repo's PR template. Pick one level (🟢 Undo, 🟡 Repair, 🟠 Migrate, 🔴 Answer) at or above the lowest level `boundary-map.yaml` gives the changed paths; unsure, take the higher. Give concrete recovery steps and who is responsible. Nothing checks it and it never blocks a merge.
- **Decision record:** Only above Undo, as `AGENTS.md` says: Repair names what was chosen, over what, why and what it commits us to; Migrate lists at least two options; Answer lists facts marked observed, inferred, asked or unknown and recommends nothing.
- **Milestone and review text:** The same layout covers milestone-close PRs, issue bodies and PR comments. Put addressed feedback under What, its rationale under Why and its check results under Proof. A short thread reply can be one bold-labelled bullet; include only applicable sections.
- **Validation:** Validate the proposed body before pushing and the actual body after creation or edits against these rules. Use `--body-file`.

Read the full [body example](references/pr-body.md) before writing a PR, milestone-close body, issue or review reply.

## Routing

The user input is: $ARGUMENTS

**First, every time, in an adopted repo:** `python3 ${CLAUDE_SKILL_DIR}/templates/scripts/sdlc_version.py`
compares `sdlc.json` `sdlcVersion` with this skill's version. It prints one line when the repo
has no stamp or an older one (`This repo runs sdlc-run <old or none>; the kit is <new>. Run
\`adopt --upgrade\` (changes: …)`) or a newer one (update the plugin). Relay the line, then
carry on: it never blocks. `references/changelog.md` lists what each version changed.

| Input | Do |
|---|---|
| `adopt [--dry-run] [--upgrade [--apply --replace FILE]] [--preset node\|python]` | Install or refresh the chain → `references/adopt.md`. `--upgrade` never overwrites or moves anything: it adds missing `sdlc.json` keys, stamps `sdlcVersion`, lists every differing file as `review diff` and the changelog's manual migrations; `--upgrade --apply --replace <file>` replaces one kit-owned file after showing its diff. First ask "Use Ship/Show/Ask?" (that file, "Ask first"), on the first adopt and on every upgrade. |
| `status [<id>]` · `status --shipped [n]` | `bash ${CLAUDE_SKILL_DIR}/scripts/status.sh …`, then `python3 ${CLAUDE_SKILL_DIR}/scripts/sdlc_status.py map` for every milestone and this one's features. `status` is read-only. |
| `<title>` or a ticket id | Start at Stage 1.0. |
| `tracker` | Choose or set up the tracker → `references/trackers.md`. |
| empty | `status.sh --current` finds this branch's change; continue from its state. |

| Found | Next |
|---|---|
| no folder, or no `decisions.json` | Stage 1.1 |
| `intent.md` `status: draft` | Stage 1.4: the engineer confirms intent |
| intent approved, no `facts.md` | Stage 2, then 3 |
| `plan.md` draft | Stage 4 gate |
| `lock.json`, a feature not `merged` in `milestone.md` | Stage 5, next feature |
| every feature `merged` | Stage 6 |
| milestone PR merged | Stage 7 |
| `decisions.json` without `milestone` | an in-flight v2/v3 change: finish it on its own process (`references/chain.md` → History) |

## Stages

| Stage | Steps | Touchpoint |
|---|---|---|
| 1 Intent | 1.0 preconditions · 1.1 one dialog: ticket, design file, size, kind, milestone (new, existing, milestone of one, hotfix) **and project (none, new, existing)** · 1.2 folder, Linear, worktree, the local milestone branch (a project branch only with `project.branch: true`) · 1.3 asks · 1.4 agent **drafts** `intent.md`: asks, job stories (observed/reported/assumed), success measure, the rules that apply (read from `sdlc.json` `rules`). Never skipped. | **Engineer confirms intent** |
| 2 UX plan | `cct:ux-design-run` (brief, IA, interaction, screens), `cct:ux-sitemap-create diff`, `cct:ux-rules-validate spec` (components: exists / adapt / new, with paths), `cct:ux-copy-write`, then `cct:ux-spec-validate spec` as **one pass**, its findings into the plan. Size `none`, size S or `ux: off` skips the stage. Prototype images only when the plan marks the UI risky: `cct:design-mockups-create spec`. From 3.25.0 also `screens.json` (one entry per screen and state) and the sample-data fixture. From 3.26.0, with a design input, also `design.json` (every board of the source, each mapped to a screen or dropped by the owner): the design is binding for which screens exist and how each is structured, and nothing measures pixels against it. | none |
| 3 Facts | Drafted after the UX plan. Each fact cites asks and rule IDs, names its screen or state, and names the E2E tag that proves it. Clarify (at most 5 questions, then Assumptions); `verify_gate.py lint` on intent, facts and plan, then a reviewer writes `checklist.md` (not on size S). | none |
| 4 Tech plan | `plan.md`: Rules check, Where things go, Milestones and feature rows, Done, How to run (the build's process), Goal handover (kickoff prompt + `/goal` line; the plan keeps `<STATUS>` as written, never a local path; when the `/goal` is written, fill `<STATUS>` with the absolute path of `${CLAUDE_SKILL_DIR}/scripts/sdlc_status.py`, the plugin copy: no repo carries one); `done.json` holds the criteria as data. Author the design sections (boundaries, schema, endpoints) with `cct:arch-plan-write`. Call when relevant: `review-security-run`, `review-dependency-run`, `tracking-apply` (the success-measure events). | **Analyze pass** (read-only, writes `analyze.md`), **challenge pass** (a fresh reviewer argues against the change, writes `challenge.md`), neither on size S, then **one gate for UX plan + facts + plan**, then `verify_gate.py approve` (refuses an open checklist item, an open CRITICAL in analyze or challenge and an unjustified rule violation) |
| 5 Build | **One go (default):** one `/goal` (`templates/goal/run.txt`, `<STATUS>` filled as above, an end state: `sdlc_status.py goal <ID>` prints `GOAL <ID> DONE` or `BLOCKED`) runs the plan's `## How to run` for every milestone in order, each on a local `milestone/<slug>-<n>` cut from fresh `origin/<default>`, or from the previous milestone only when the plan says `needs: M<k>`: per feature, write its tests, build, commit, next feature at once; each builder gets a context pack (its facts, plan excerpt, cited rule text). **Run touched tests and the repo's pre-commit checks; run the full suite once on the final head before push; GitHub's required checks are the merge gate.** Open questions go to `questions.md` with the default taken and never block; answers become asks of the next milestone. Then Stage 6 for that milestone in the same goal. Each `screens.json` entry gets a preview page in the app (dev and test builds). | none |
| 6 Milestone | Inside `/goal` (the same goal as Stage 5), on the milestone diff only, in parallel: `cct:ux-assessment-run scope=change base=<parent> head=<head> worktree=<path>` (the local form, once; it owns the captures in one manifest and dispatches responsive, accessibility and build QA), `review-code-run changes <parent> --codex` (Claude and Codex, reading `REVIEW.md` when the repo has one) + one fix round fed the joined findings and that review's state directory (never `review-fix-run`, which starts its own review), ×3 only for changed and flaky specs (`../test-e2e-policy/references/suite-speed-and-reliability.md` section G; the full suite and full E2E run once, inside the gate, its only runner), **validation**: every fact and ask exercised in the built app into `validation.md` (expected, observed, evidence, verdict; `not met` blocks), the `test-behavior-verifier` and `review-criteria-auditor` agents for jobs and facts (size S: the code review is the one reviewer, add them for visual work, auth or data), then **converge** (append-only; `references/quality-passes.md`), `verify_gate.py audit` (read-only: is every declared gate enforced; `references/stages.md`), **Every milestone close:** `review-security-run` on the diff from the goal's recorded start when auth, money or consent is touched in the goal so far (a project's 6p runs it again on the whole project). One findings list, one fix round, `verify_gate.py milestone` on a frozen head, one push, one PR **to the milestone's parent** — the default branch, or `project/<slug>` when the project has a branch — merged with a merge commit. With `screens.json`: one capture batch, `evidence.py gallery` for the owner, approved shots become exact tests. | **Engineer accepts the milestone** (one go: only when a Critical or High would be deferred) |
| 6p Project | Only in a project, once its last milestone has merged: re-run `checks.milestone` on the whole project, on the default branch, plus `review-security-run` on it when auth, money or consent is touched. No PR. With `project.branch: true`: merge the default branch into `project/<slug>` locally, the same checks, then one PR to the default branch, the one that gets the tier. No second fix round — what is left starts the next project. | **Engineer accepts the project** |
| 7 Outcome | One short `reflection.md` (repeated lessons are listed for the owner to promote, never written to the agent file by the agent). The change's PR keeps its folder. The next change's first commit runs `sdlc_status.py sweep-merged --apply`: it writes the outcome record (`spec.py outcome write <folder>`) and removes the folders of merged changes, so there is no archive and no records-only PR. After release, read the success measure from PostHog into the outcome record (`spec.py outcome record`). A miss starts the next change at 1.3. | Engineer reads it |

## Documents and the living spec (layout 4)

A change may keep three documents, `spec.md` (why and what), `design.md` (how) and `tasks.md` (in
what order), instead of eight; scope S needs only the first, M the first and last, L all three,
chosen by risk. What the product does today is `specs/<capability>/rules/R123.md`, one file per
requirement, edited in the PR that changes the behaviour: the PR's git diff is the delta, there is
no archive and no apply step. `python3 scripts/spec.py` finds rules (`find`), allocates ids (`new`,
`next`, `renumber`), checks drift (`check`) and the documents (`consistency`), and records the
outcome after the folder is removed (`outcome`). Layout 4 is the default: a new adoption writes `"layout": 4` in
`sdlc.json` and new changes follow it. An adopted repo keeps its value (`adopt --upgrade` prints one
MANUAL line offering the switch), and a change already on the old layout finishes on it. Read [change-folder](references/change-folder.md)
and [living-spec](references/living-spec.md); the per-stage differences are the first section of
`references/stages.md`.

## Heavy work

Builds, app servers, browsers and the full suite are heavy; format, lint, types and touched unit
tests are light. A heavy job takes a slot in a per-machine queue (`scripts/heavy.py run|submit`,
one slot by default), and the milestone gate runs every check through it. A helper's heavy command
that skips the queue is refused by `helper-guard.sh`. `scripts/db.py test` gives each job a private
copy of a migrated local Postgres; `db.py dev` connects the engineer to their own cloud database;
`scripts/preflight.py` checks tools, sign-in and Docker once, and `preflight.py doctor` (read-only; run by `adopt`, at Stage 1.0 and before the plan gate) names every gate-config gap with its fix. All optional (`heavy`, `db`,
`preflight` in `sdlc.json`); `references/heavy-work.md`.

## Agents and models

Agents: every build, fix, test, capture, restack or records agent is `cct:sdlc-feature-builder` (Sonnet); review and checks use their typed agents (`cct:review-code-reviewer`, `cct:test-behavior-verifier`, `cct:review-criteria-auditor`, `cct:ux-usability-reviewer`, `cct:review-finding-validator`). Never launch general-purpose for this work: it inherits the session's model. Any other subagent gets `model: sonnet` explicitly. The session's own model is only for the gate's visual judgement and for decisions. Dispatch builders yourself, never through a closer agent that spawns its own.

Every step, input, output, skip and failure mode: `references/stages.md`. How to wait (CI, deploy, success measure): its "Waiting" section; never a `/loop` inside a running `/goal`. A step whose skill is
not installed is skipped with a printed note naming it, never silently.

## The two touchpoints, and nothing else

1. **Intent.** The agent drafts; the engineer confirms or edits `intent.md`. Then
   `status: approved`, commit `changes(<id>): intent confirmed by <who>`.
2. **Plan.** One `plannotator annotate changes/<id>/plan.md --gate` covering `spec/`, `facts.md`
   and `plan.md` (`planGate: self` allowed only when no risk touches data safety, irreversible
   writes, security or money). On approval set all three `status: approved`, run
   `python3 scripts/verify_gate.py approve <id>`, commit `lock.json`: `changes(<id>): approved by <who>`.

No design gate exists. `cct:ux-spec-validate spec` runs once and its findings go into the plan.

## Talking to the engineer

- **Ask in a dialog, never in prose.** Every question is an `AskUserQuestion`: the 1.1 forks,
  both touchpoints, every `VERIFY BLOCKED`, the milestone acceptance, an outcome miss.
- **Always recommend, with the reason.** The recommended option comes first, labelled
  `(Recommended)`, and its description says why in one sentence. No option without a pick.
- **Plain words, short.** One idea per sentence, at most 20 words. Say what a term means the
  first time. Lead with the answer, then what you need; never restate.
- **Do not ask what you can decide.** Cheap and reversible: decide, and say what you picked and why.

## The verify contract

`python3 scripts/verify_gate.py feature|milestone <id>` checks `lock.json`, runs
`sdlc.json` `checks.<scope>` in order, writes `changes/<id>/verify/report.{json,md}` and ends
with one line: `VERIFY PASS <scope> <id> <sha>`, `VERIFY FAIL … check=<name>` (fix and rerun) or
`VERIFY BLOCKED reason=<code>` (stop and ask the engineer). Reasons: `validation-not-met`, `findings-open`, `findings-blocked`, `not-converged`, `not-approved`,
`protected-path`, `no-progress`, `attempts`, `flaky`, `unknown-verdict`, `needs-baseline`,
`allowlist-request`, `scope-growth`, `spec-conflict`, `env`, `test-proves-nothing`. A milestone blocks on a `not met` or `partly` row in `validation.md`, an unchecked item in `findings.md` outside `## Advisory`, and a `## Converge` section without `Converged:`.
`goal` ends in `DONE` or `BLOCKED` with a state; `references/states.json` lists every state and who leaves it.
Snapmark feedback and supplied reference images require comparison against fresh headless
screenshots, including ADR refinements; milestone `owner-marks` checks `marks.json` (see `references/stages.md`).

## Branches

**One milestone** is the default; a project is several of them, each merging on its own:

```
<defaultBranch> ─── milestone/<slug>-<n> (local until VERIFY PASS) ─── <parallel builder worktrees>
```

Only a project that asks for a branch (`project.branch: true`) adds one level above it:

```
<defaultBranch> ─── project/<slug> ─── milestone/<slug>-<n> ─── <parallel builder worktrees>
```

- **A project is planning by default, not a branch.** `decisions.json` `project.branch` is
  `false` for a new project: its milestones go to the default branch one by one, unfinished work
  behind a flag. With `branch: true` (and for every project written before 3.7.0, which has no
  `branch` key), `project/<slug>` is cut from `origin/<defaultBranch>` at 1.2 and takes it in
  by a local merge after every default-branch merge.
- **A milestone branch is local until it passes.** `milestone/<slug>-<n>` is created in the
  supervisor's worktree from fresh `origin/<parent>` (the project branch when there is one,
  else the default branch), takes its parent in by a local merge (the sync row, a Stage 5
  precondition), and is pushed once, at the close, after `VERIFY PASS`. Pushed branches are
  never rebased. The tracker's milestone maps to it.
- **Milestones are independent unless the plan says otherwise.** Each is cut from its parent and
  merges on its own. A milestone whose `## Milestones` row says `needs: M<k>` is cut from the
  local predecessor instead, builds at once, and opens its PR after the predecessor merges;
  milestone PRs merge with a merge commit, so it needs no rebase.
- The build works in the supervisor's worktree on `milestone/<slug>-<n>`
  itself, a commit per feature. Parallel builders, when used, start from the milestone head and
  merge back locally, one at a time, through the shared policy’s `wt merge` flow (Git fallback).
- Builders are `cct:sdlc-feature-builder` agents, at most `sdlc.json` `maxBuilders` at once (default 4; the engineer may raise it in the kickoff), plus about 2 helpers, each dispatched with
  `isolation: "worktree"` and `Repo`, `Worktree`, `Change` and `Base: <milestone head sha>` lines, checked and reset to before any
  edit: a worktree hook cuts from the trunk. The supervisor commits its records first, edits no
  code, runs no test suite, and is the one integrator. Every builder dispatch carries a model and effort the orchestrator chooses
  (`references/stages.md`, "Models are an orchestrator choice"): `sdlc.json` `builderModel` and `builderEffort` are only the
  defaults (`sonnet`, `high`), and the engineer's "Orchestrator instructions for this run" in the kickoff win. With `sdlc.json` `builders: "codex"`, every feature row and fix part runs
  instead through `scripts/codex-build.sh` (the Codex CLI in the same worktree, network off,
  `.git` read-only; the wrapper checks the result and makes the commit; `references/stages.md`
  → Wall clock); the supervisor, the milestone close and the gates stay Claude.
- Each builder runs in its own worktree and E2E slot, so independent features build at once
  (`references/stages.md` → Wall clock).
- Milestone of one: one change, both checks. Hotfix: `--base <defaultBranch>`, feature checks only.

### Only the PR into `<defaultBranch>` is reviewed and tiered

Everything below the trunk is an **interior merge inside one change**: a milestone PR into
`project/*`. That carries code that has not reached anyone
yet, and they auto-merge on their checks alone.

| PR | Checks | Ship/Show/Ask | Who approves |
|---|---|---|---|
| milestone → `project/*` | `checks.milestone` | no | nobody; auto-merge on green |
| `project/*` or `milestone/*` → `<defaultBranch>` | `checks.milestone` | **yes** | the tier decides |

`ship-show-ask.yml` enforces this itself, by comparing `github.event.pull_request.base.ref`
with the repository's default branch, so the rule holds even for a PR opened by hand. The code
review is not in CI at all (3.7.0): it runs once, locally, at the milestone close, with Claude
and Codex on the whole milestone diff. A CI review re-read that diff for about $1 a PR.

### Records, gates and waiting

**One milestone, one push, one PR, enforced by `pr-gate.sh`.** Every milestone starts with its
sync row: `git merge origin/<default>` (and `origin/project/<slug>` in a project) locally; the
gate fails `check=parent-sync` without it. While a milestone is open, everything that belongs to
it is a commit on `milestone/<slug>`, never its own PR or push: fixes found in the build, test
and flaky-spec repairs, CI timeout tweaks its tests need, and records (plans, handovers, gate
lines, findings). A record written after a merge is the next milestone's first commit; a fix for
a merged milestone goes into the next one. The close runs locally: one `cct:sdlc-feature-builder` subagent runs
the one fix round and `verify_gate.py milestone`, the only runner of the full suite and the full
E2E at the close, while the supervisor dispatches the reviews and the validation. With
`builders: "codex"` the close builder implements nothing: the fix parts go to `codex-build.sh`,
then the close builder runs the gate once. Only its
`VERIFY PASS` head is pushed, once, with one PR; auto-merge is armed only after the owner and visual dispositions are recorded (never arm an `ask`-labelled or a closed PR), while the supervisor builds
the next independent milestone (up to `maxBuilders` builders). CI is the last check, never the test loop:
a red check uses the exact-test local failure loop in `references/local-first.md`, then the full suite once and one batched push. Several repos in one project: [multi-repo](references/multi-repo.md). Another repository follows
the same rule on its own milestone branch; an exception needs the engineer's words in
`decisions.json` `prExceptions`. Agents run only the tests they touched.
GitHub's required checks are the merge gate; `pr-gate.sh` only enforces branch order (a milestone
head needs `VERIFY PASS milestone` before it is pushed). Commands:
`references/stages.md` "Records, gates and waiting", `references/ci-blueprint.md`.

## Never

- Build outside `/goal`. `chain-gate.sh` refuses the edit; never work around it.
- Edit `facts.md`, `done.json`, `lock.json`, `sdlc.json` checks, baselines or allowlists after
  approval without the engineer's words in `decisions.json` `protectedEdit`. Re-lock
  (`verify_gate.py approve`) only scope the engineer added, never to make a gate pass.
- Decide the ticket, size, kind or milestone yourself; create a ticket without searching.
- Edit a test to make verify pass, or while `testLocked` without `testEdit`.
- Start a second fix round at the milestone. What is left is settled by the owner's answer to an
  `AskUserQuestion` (`Change <id>, finding <finding id>: ...`; Fix it now, Accept as is, Defer to milestone <n>, Block the close); the gate reads it.
- Put a local path in any tracker (`scripts/linear-safe.py`); keep a plan in `.claude/plans/`.
- Open a PR or push for anything but a milestone close (the folder removal of Stage 7 is the
  next change's first commit): records, fixes, test repairs and merges
  from the default branch are commits on the milestone branch; a fix for a merged milestone goes
  into the next one. Push a milestone head only after `VERIFY PASS milestone` on it, once.
  `pr-gate.sh` refuses the rest; never work around it. Never wait on a PR your code does not
  depend on.
- Start a milestone without its sync row: `git merge origin/<default>` (and
  `origin/project/<slug>` in a project), locally. The gate fails `check=parent-sync` without it.
- Run the whole suite to diagnose one failure: use the failing tests and directly affected
  suite until green, then the full suite once before every push (`../test-e2e-policy/references/suite-speed-and-reliability.md` section K).
- Name the change's issue key in a feature commit or branch: its merge closes the change
  early. Feature commits carry their sub-issue key; only the milestone PR says `Closes <KEY>`.

## Prerequisites

| Dependency | Required | How to obtain |
|---|---|---|
| `sdlc.json` + `scripts/verify_gate.py` | Yes | `sdlc-run adopt` |
| `plannotator` binary + plugin | Yes for the gates | the repo's `toolsCommand` |
| the cct UX skills | Yes when `ux` is `on` | enable the cct plugin |
| A tracker: Linear MCP, `gh` with `project` scope, or `bd` | No: `none` runs ticketless | `references/trackers.md` setup guides |
| `gh` authenticated | Yes for PRs | `gh auth login` |
| `codex` CLI, signed in | Yes when `builders` is `codex` | `npm i -g @openai/codex`, then `codex login` |

## References

- `references/convergence.md` — six-layer pass rule, severity, frozen defect list, fix-round budget, design-system audit.
- `references/visual-work.md` — capture headless, the shared visual pass, marked screens, one manifest and pinned commit, one record per screen, the owner sheet.
- `references/design-inputs.md` — the visual source of truth, the six layers, each kind of input, bundles and rendering, what wins, questioning the design.
- `references/stages.md` — every step, input, output, skip and failure mode.
- `references/trackers.md` — Linear, GitHub, Beads: choosing, setting up, the four levels in each.
- `references/chain.md` — folder layout, decisions, frontmatter, `sdlc.json` keys, history.
- `references/requirements-grammar.md` — EARS and Gherkin grammar for `facts.md`.
- `references/quality-passes.md` — rules wiring, clarify, checklist, analyze, challenge, converge.
- `references/adopt.md` — what `adopt` writes, what stays manual, migrations.
- `references/ci-blueprint.md` — GitHub Actions required checks as the merge gate, cloud workflows and the example workflow.
- `references/local-first.md` — the shared local verification and targeted debugging contract. Its last section, "Local milestones", covers `milestones.merge: "local"` (no milestone PRs).
- `references/harness-audit.md` — monthly local whole-harness evidence, pinned consumer sync, owner-assigned gaps and legacy refusal fixtures.
- `references/decision4-pr.md` — Decision4 in a PR: advisory undo level and decision record, no gate.
- `references/changelog.md` — what each sdlc-run version changed and what a repo must do (`adopt --upgrade` reads it).
- `references/tiers.md` — Ship / Show / Ask by path.
- `references/heavy-work.md` — the heavy-job queue, local test databases, a cloud dev database, guards and preflight (`scripts/heavy.py`, `db.py`, `evidence.py`, `preflight.py`), and what the gate, hooks and status do with them.
- `references/states.json` — every state `sdlc_status.py goal` can print, who leaves it and how; a test keeps it equal to the code.
- `references/change-folder.md`, `references/living-spec.md` — layout 4: three documents, one file per rule, `spec.py`.
- `references/playbook.md` — playbook mapping and metrics.
- `references/layout-research.md` — why `changes/` (its archive half is superseded: folders are removed after merge).
