---
name: sdlc-run
description: >-
  Runs an AI-native SDLC in any repo: the agent drafts intent, UX plan, facts and tech plan,
  the engineer confirms twice, then one /goal builds every feature as commits on a milestone
  branch and closes the milestone with the heavy checks once and one PR (one go, the default;
  per-feature PRs remain as an option). Work
  spanning several milestones adds a project branch between the milestones and the trunk; only
  the PR into the default branch is reviewed and tiered. Use when someone starts or continues a
  feature, bug fix, refactor, docs change, chore, hotfix, milestone or project, asks "how do we
  do X here", or says "run sdlc", "adopt sdlc", "sdlc status". Subcommands: "adopt" installs the
  chain, "status" lists open changes and gates.
allowed-tools: "Read Grep Glob Edit Write Agent Skill AskUserQuestion Bash(bash */sdlc-run/scripts/*) Bash(python3 */sdlc-run/scripts/*) Bash(python3 */sdlc-run/templates/scripts/sdlc_version.py*) Bash(python3 scripts/sdlc_version.py*) Bash(python3 scripts/verify_gate.py *) Bash(python3 scripts/sdlc_status.py *) Bash(scripts/ci-local *) Bash(git *) Bash(gh *) Bash(bd *) Bash(plannotator *) Bash(make *) Bash(pnpm *) Bash(uv *) Bash(npx *) EnterWorktree mcp__claude_ai_Linear__* mcp__linear__*"
user_invocable: true
metadata:
  version: 3.9.1
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
7 Outcome + archive: archive on merge, read the success measure after release

Branches: <default> ─ [project/<slug>] ─ milestone/<slug> ─ features
          only the PR into <default> is reviewed and tiered
```

One change folder `changes/<YYYY-MM-DD>[-<KEY>]-<slug>/` holds intent, `spec/`, facts, plan,
`done.json`, `lock.json` and `milestone.md`. **One go is the default** (`sdlc.json`
`delivery`): everything asked for at once is one change, its features land as commits on
`milestone/<slug>` inside one `/goal`, and one milestone PR ships them — into `project/<slug>`
when the change belongs to a project, otherwise straight into the default branch, which
releases. `delivery: "feature-prs"` keeps one PR per feature for teams building in parallel. The tracker (`sdlc.json` `tracker`: Linear, GitHub, Beads or
none) is the status record; a missing ticket never blocks. What is what in each tool:
`references/trackers.md`.

Designs and decisions outlive a change: one file each in `designsDir`, never an appended log.
**Read `<designsDir>/INDEX.md` first** and open only the files it points to; run
`python3 scripts/design_index.py write` after adding or changing one (`references/chain.md`).

Read `sdlc.json` first: `tracker`, `checks`, `milestones`, `projects`, `hotfix`, `goal`, `languages`, `responsiveTier`,
`ux`, `protected`, `planGate` and the v2 keys. No file means the repo is not adopted: run
`adopt`. **Project values come from the repo** (sdlc.json, PRODUCT.md, DESIGN.md); where it
defines nothing, the kit default applies and every report names the defaults it used.

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
| `status [<id>]` · `status --shipped [n]` | `bash ${CLAUDE_SKILL_DIR}/scripts/status.sh …`, then `python3 scripts/sdlc_status.py map` for every milestone and this one's features. |
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
| 1 Intent | 1.0 preconditions · 1.1 one dialog: ticket, design file, size, kind, milestone (new, existing, milestone of one, hotfix) **and project (none, new, existing)** · 1.2 folder, Linear, worktree, the local milestone branch (a project branch only with `project.branch: true`) · 1.3 asks · 1.4 agent **drafts** `intent.md`: asks, job stories (observed/reported/assumed), success measure, the rules that apply (read from `sdlc.json` `rules`) and the Decision4 class. Never skipped. | **Engineer confirms intent** |
| 2 UX plan | `cct:ux-design-run` (brief, IA, interaction, screens), `cct:ux-sitemap-create diff`, `cct:ux-rules-validate spec` (components: exists / adapt / new, with paths), `cct:ux-copy-write`, then `cct:ux-spec-validate spec` as **one pass**, its findings into the plan. Size `none` or `ux: off` skips; size S does components and words only. Prototype images only when the plan marks the UI risky: `cct:design-mockups-create spec`. | none |
| 3 Facts | Drafted after the UX plan. Each fact cites asks and rule IDs, names its screen or state, and names the E2E tag that proves it. Clarify (at most 5 questions, then Assumptions); a reviewer writes `checklist.md`. `verify_gate.py lint` on intent, facts and plan. | none |
| 4 Tech plan | `plan.md`: Rules check, Where things go, Milestones and feature rows, Done, Goal handover; `done.json` holds the criteria as data. Author the design sections (boundaries, schema, endpoints) with `cct:arch-plan-write`. Call when relevant: `review-security-run`, `review-dependency-run`, `tracking-apply` (the success-measure events). | **Analyze pass** (read-only, writes `analyze.md`), **challenge pass** (a fresh reviewer argues against the change, writes `challenge.md`), then **one gate for UX plan + facts + plan**, then `verify_gate.py approve` (refuses an open checklist item, an open CRITICAL in analyze or challenge and an unjustified rule violation) |
| 5 Build | **One go (default):** one `/goal` (`templates/goal/run.txt`) builds every milestone of the plan in order, each on a local `milestone/<slug>-<n>` cut from fresh `origin/<default>`, or from the previous milestone only when the plan says `needs: M<k>`: per feature, write its tests, build, commit, next feature at once; each builder gets a context pack (its facts, plan excerpt, cited rule text), and work above the class approved at gate 2 goes to `questions.md` unbuilt. **Run touched tests and the repo's pre-commit checks; run the full local gate once on the final head before push.** Open questions go to `questions.md` with the default taken and never block; answers become asks of the next milestone. Then Stage 6 for that milestone in the same goal. **Feature PRs:** per feature, inside `/goal` (`templates/goal/feature.txt`): `test-e2e-coverage-run`, `test-e2e-policy` on the feature tags, `test-flake-fix`; bugs via `test-behavior-writer` → locked test → `review-fix-implementer`; `verify_gate.py feature`; `git-pr-run --base milestone/<slug>`; `cct:ux-assessment-run` on that PR's screens, its Critical and High fixed before auto-merge is armed. No tier on this PR — it is interior. When it merges, the next feature starts. | none |
| 6 Milestone | Inside `/goal` (the same one in one go; `templates/goal/milestone.txt` for feature PRs), on the milestone diff only, in parallel: `cct:ux-assessment-run`, `review-code-run` (Claude and Codex, reading `REVIEW.md` when the repo has one) + `review-fix-run 1` (one round), `ux-responsive-audit` full matrix, states, `ux-accessibility-audit`, the full E2E suite once, ×3 only for changed and flaky specs (`../test-e2e-policy/references/suite-speed-and-reliability.md` section G), `cct:ux-assessment-run` when a screen is new, **validation**: every fact and ask exercised in the built app into `validation.md` (expected, observed, evidence, verdict; `not met` blocks), `cct:ux-spec-validate build`, the `test-behavior-verifier` and `review-criteria-auditor` agents for jobs and facts, then **converge** (append-only; `references/quality-passes.md`), `verify_gate.py audit` (read-only: is every declared gate enforced; `references/stages.md`), **Last milestone of the goal only:** `review-security-run` on the whole goal diff when auth, money or consent is touched anywhere in it (in a project it waits for 6p). One findings list, one fix round, `verify_gate.py milestone` on a frozen head, one push, one PR **to the milestone's parent** — the default branch, or `project/<slug>` when the project has a branch — merged with a merge commit. | **Engineer accepts the milestone** (one go: only when a Critical or High would be deferred) |
| 6p Project | Only in a project, once its last milestone has merged: re-run `checks.milestone` on the whole project, on the default branch, plus `review-security-run` on it when auth, money or consent is touched. No PR. With `project.branch: true`: merge the default branch into `project/<slug>` locally, the same checks, then one PR to the default branch, the one that gets the tier. No second fix round — what is left starts the next project. | **Engineer accepts the project** |
| 7 Outcome + archive | One short `reflection.md` (repeated lessons are listed for the owner to promote, never written to the agent file by the agent). Archive the folder when the change reaches the default branch. After release, read the success measure from PostHog into `milestone.md`. A miss starts the next change at 1.3. | Engineer reads it |

## Agents and models

Agents: every build, fix, test, capture, restack or records agent is `cct:sdlc-feature-builder` (Sonnet); review and checks use their typed agents (`cct:review-code-reviewer`, `cct:test-behavior-verifier`, `cct:review-criteria-auditor`, `cct:ux-usability-reviewer`, `cct:review-finding-validator`). Never launch general-purpose for this work: it inherits the session's model. Any other subagent gets `model: sonnet` explicitly. The session's own model is only for the gate's visual judgement and for decisions. Dispatch builders yourself, never through a closer agent that spawns its own.

Every step, input, output, skip and failure mode: `references/stages.md`. A step whose skill is
not installed is skipped with a printed note naming it, never silently.

## The two touchpoints, and nothing else

1. **Intent.** The agent drafts; the engineer confirms or edits `intent.md`. Then
   `status: approved`, commit `changes(<id>): intent confirmed by <who>`.
2. **Plan.** One `plannotator annotate changes/<id>/plan.md --gate` covering `spec/`, `facts.md`
   and `plan.md` (`planGate: self` allowed only when no risk touches data safety, irreversible
   writes, security or money). On approval set all three `status: approved`, run
   `python3 scripts/verify_gate.py approve <id>` (it also locks the intent's class), commit `lock.json`: `changes(<id>): approved by <who>`.

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
`VERIFY BLOCKED reason=<code>` (stop and ask the engineer). Reasons: `validation-not-met`, `findings-open`, `not-converged`, `not-approved`,
`protected-path`, `no-progress`, `attempts`, `flaky`, `unknown-verdict`, `needs-baseline`,
`allowlist-request`, `scope-growth`, `spec-conflict`, `env`, `test-proves-nothing`. A milestone blocks on a `not met` or `partly` row in `validation.md`, an unchecked item in `findings.md` outside `## Advisory`, and a `## Converge` section without `Converged:`.
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
- One go (default): the build works in the supervisor's worktree on `milestone/<slug>-<n>`
  itself, a commit per feature. Parallel builders, when used, start from the milestone head and
  merge back locally, one at a time.
- Feature PRs: feature worktrees branch from the milestone: `git worktree add` from
  `origin/milestone/<slug>`, then `EnterWorktree path=` (`references/stages.md` 1.2). Their
  branch names contain the change slug.
- Builders are `cct:sdlc-feature-builder` agents, at most 4 at once, each dispatched with
  `isolation: "worktree"` and a `Base: <milestone head sha>` line, which it resets to before any
  edit: a worktree hook cuts from the trunk. The supervisor commits its records first, edits no
  code, runs no test suite, and is the one integrator. Every builder dispatch carries `sdlc.json` `builderModel` and `builderEffort`
  (default `sonnet`, `high`; set `opus` for a hard change, or let one plan's Approach override
  them for that change). With `sdlc.json` `builders: "codex"`, every feature row and fix part runs
  instead through `scripts/codex-build.sh` (the Codex CLI in the same worktree, network off,
  `.git` read-only; the wrapper checks the result and makes the commit; `references/stages.md`
  → Wall clock); the supervisor, the milestone close and the gates stay Claude.
- Each builder runs in its own worktree and E2E slot, so independent features build at once
  (`references/stages.md` → Wall clock).
- Milestone of one: one change, both checks. Hotfix: `--base <defaultBranch>`, feature checks only.

### Only the PR into `<defaultBranch>` is reviewed and tiered

Everything below the trunk is an **interior merge inside one change**: a feature PR into
`milestone/*`, a milestone PR into `project/*`. Those carry code that has not reached anyone
yet, and they auto-merge on their checks alone.

| PR | Checks | Ship/Show/Ask | Who approves |
|---|---|---|---|
| feature → `milestone/*` | `checks.feature` | no | nobody; auto-merge on green |
| milestone → `project/*` | `checks.milestone` | no | nobody; auto-merge on green |
| `project/*` or `milestone/*` → `<defaultBranch>` | `checks.milestone` | **yes** | the tier decides |

`ship-show-ask.yml` enforces this itself, by comparing `github.event.pull_request.base.ref`
with the repository's default branch, so the rule holds even for a PR opened by hand. The code
review is not in CI at all (3.7.0): it runs once, locally, at the milestone close, with Claude
and Codex on the whole milestone diff. A CI review re-read that diff for about $1 a PR and
needed `ANTHROPIC_API_KEY` in every repo.

### Records, gates and waiting

**One milestone, one push, one PR, enforced by `pr-gate.sh`.** Every milestone starts with its
sync row: `git merge origin/<default>` (and `origin/project/<slug>` in a project) locally; the
gate fails `check=parent-sync` without it. While a milestone is open, everything that belongs to
it is a commit on `milestone/<slug>`, never its own PR or push: fixes found in the build, test
and flaky-spec repairs, CI timeout tweaks its tests need, and records (plans, handovers, gate
lines, findings). A record written after a merge is the next milestone's first commit; a fix for
a merged milestone goes into the next one. The close runs locally: one `cct:sdlc-feature-builder` subagent runs
unit tests, the full E2E suite, the one fix round and `verify_gate.py milestone`, while the
supervisor dispatches the reviews and the validation. With `builders: "codex"` the close
builder runs the checks and the gate but implements nothing: the fix parts go to
`codex-build.sh`, then the close builder runs the checks and the gate again. Only its
`VERIFY PASS` head is pushed, once, with one PR and auto-merge armed, while the supervisor builds
the next independent milestone (at most 4 builders). CI is the last check, never the test loop:
a red check uses the exact-test local failure loop in `references/local-first.md`, then the full local gate once and one batched push. Another repository follows
the same rule on its own milestone branch; an exception needs the engineer's words in
`decisions.json` `prExceptions`. Agents run only the tests they touched.
The full local gate runs before every push and publishes `local-ci` + `decision4` for the
verified head; rulesets require both. GitHub keeps cloud/GitHub work and schedules, not the
local debugging loop. Existing remote CI remains confirmation during migration. Commands:
`references/stages.md` "Records, gates and waiting", `references/ci-blueprint.md`.

## Never

- Build outside `/goal`. `chain-gate.sh` refuses the edit; never work around it.
- Edit `facts.md`, `done.json`, `lock.json`, `sdlc.json` checks, baselines or allowlists after
  approval without the engineer's words in `decisions.json` `protectedEdit`. Never re-lock.
- Decide the ticket, size, kind or milestone yourself; create a ticket without searching.
- Build above the class approved at gate 2: that item goes to `questions.md` unbuilt.
- Edit a test to make verify pass, or while `testLocked` without `testEdit`.
- Start a second fix round at the milestone. What is left goes to the next milestone.
- Put a local path in any tracker (`scripts/linear-safe.py`); keep a plan in `.claude/plans/`.
- Open a PR or push for anything but a milestone close: records, fixes, test repairs and merges
  from the default branch are commits on the milestone branch; a fix for a merged milestone goes
  into the next one. Push a milestone head only after `VERIFY PASS milestone` on it, once.
  `pr-gate.sh` refuses the rest; never work around it. Never wait on a PR your code does not
  depend on.
- Start a milestone without its sync row: `git merge origin/<default>` (and
  `origin/project/<slug>` in a project), locally. The gate fails `check=parent-sync` without it.
- Run the whole suite to diagnose one failure: use the failing tests and directly affected
  suite until green, then the full local gate once before every push (`../test-e2e-policy/references/suite-speed-and-reliability.md` section K).
- Name the change's issue key in a feature branch or feature PR: its merge closes the change
  early. Feature PRs carry their sub-issue key; only the milestone PR says `Closes <KEY>`.

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

- `references/stages.md` — every step, input, output, skip and failure mode.
- `references/trackers.md` — Linear, GitHub, Beads: choosing, setting up, the four levels in each.
- `references/chain.md` — folder layout, decisions, frontmatter, `sdlc.json` keys, history.
- `references/requirements-grammar.md` — EARS and Gherkin grammar for `facts.md`.
- `references/quality-passes.md` — rules wiring, clarify, checklist, analyze, challenge, converge, the Decision4 class.
- `references/adopt.md` — what `adopt` writes, what stays manual, migrations.
- `references/ci-blueprint.md` — local gate setup, required `local-ci` + `decision4` statuses, cloud workflows and migration from existing remote CI.
- `references/local-first.md` — the shared local verification and targeted debugging contract.
- `references/changelog.md` — what each sdlc-run version changed and what a repo must do (`adopt --upgrade` reads it).
- `references/tiers.md` — Ship / Show / Ask by path.
- `references/playbook.md` — playbook mapping and metrics.
- `references/layout-research.md` — why `changes/` plus archive.
