---
name: sdlc-run
description: >-
  Runs OMR's AI-native SDLC in any repo: the agent drafts intent, UX plan, facts and tech plan,
  the engineer confirms twice, then one /goal builds every feature as commits on a milestone
  branch and closes the milestone with the heavy checks once and one PR (one go, the default;
  per-feature PRs remain as an option). Work
  spanning several milestones adds a project branch between the milestones and the trunk; only
  the PR into the default branch is reviewed and tiered. Use when someone starts or continues a
  feature, bug fix, refactor, docs change, chore, hotfix, milestone or project, asks "how do we
  do X here", or says "run sdlc", "adopt sdlc", "sdlc status". Subcommands: "adopt" installs the
  chain, "status" lists open changes and gates.
allowed-tools: "Read Grep Glob Edit Write Agent Skill AskUserQuestion Bash(bash */sdlc-run/scripts/*) Bash(python3 */sdlc-run/scripts/*) Bash(python3 */sdlc-run/templates/scripts/sdlc_version.py*) Bash(python3 scripts/sdlc_version.py*) Bash(python3 scripts/verify_gate.py *) Bash(python3 scripts/sdlc_status.py *) Bash(git *) Bash(gh *) Bash(bd *) Bash(plannotator *) Bash(make *) Bash(pnpm *) Bash(uv *) Bash(npx *) EnterWorktree mcp__claude_ai_Linear__* mcp__linear__*"
user_invocable: true
metadata:
  version: 3.6.1
  author: calvindudek
effort: high
---

# sdlc-run — two confirmations, then autonomous inside /goal

```
1 Intent ──▶ engineer confirms ──▶ 2 UX plan ─ 3 Facts ─ 4 Tech plan ──▶ engineer confirms once
                                                                              │
     ┌──────────────────────── one /goal, one go ────────────────────────────┘
     ▼
5 Build: feature ─▶ commit ─▶ next feature at once (no checks between features)
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
| 1 Intent | 1.0 preconditions · 1.1 one dialog: ticket, design file, size, kind, milestone (new, existing, milestone of one, hotfix) **and project (none, new, existing)** · 1.2 folder, Linear, worktree, project branch if any, milestone branch · 1.3 asks · 1.4 agent **drafts** `intent.md`: asks, job stories (observed/reported/assumed), success measure. Never skipped. | **Engineer confirms intent** |
| 2 UX plan | `cct:ux-design` (brief, IA, interaction, screens), `cct:ux-sitemap-create diff`, `cct:ux-conformance spec` (components: exists / adapt / new, with paths), `cct:microcopy-write`, then `cct:ux-validate spec` as **one pass**, its findings into the plan. Size `none` or `ux: off` skips; size S does components and words only. Prototype images only when the plan marks the UI risky: `cct:designs-explore spec`. | none |
| 3 Facts | Drafted after the UX plan. Each fact cites asks, names its screen or state, and names the E2E tag that proves it. `verify_gate.py lint` on intent, facts and plan. | none |
| 4 Tech plan | `plan.md`: Where things go, Feature PRs, Done, Goal handover; `done.json` holds the criteria as data. Call when relevant: `architecture-review`, `data-model-create`, `api-design`, `security-review`, `dependency-review`, `tracking-apply` (the success-measure events). | **One gate for UX plan + facts + plan**, then `verify_gate.py approve` |
| 5 Build | **One go (default):** one `/goal` (`templates/goal/run.txt`) builds every milestone of the plan in order, each on `milestone/<slug>-<n>` cut from the previous one: per feature, write its tests, build, commit, next feature at once. **No check, lint or test runs per feature or commit.** Open questions go to `questions.md` with the default taken and never block; answers become asks of the next milestone. Then Stage 6 for that milestone in the same goal. **Feature PRs:** per feature, inside `/goal` (`templates/goal/feature.txt`): `e2e-write`, `e2e-test-run` on the feature tags, `flaky-test-fix`; bugs via `behavior-test-writer` → locked test → `fix-implementer`; `verify_gate.py feature`; `pr-create --base milestone/<slug>`; `cct:ux-review` on that PR's screens, its Critical and High fixed before auto-merge is armed. No Claude review and no tier on this PR — it is interior. When it merges, the next feature starts. | none |
| 6 Milestone | Inside `/goal` (the same one in one go; `templates/goal/milestone.txt` for feature PRs), on the milestone diff only, in parallel: `cct:ux-review`, `pr-review` + `review-fix-loop 1` (one round), `responsive-audit` full matrix, states, `accessibility-audit`, the full E2E suite once, ×3 only for changed and flaky specs (`../e2e-test-run/references/suite-speed-and-reliability.md` section G), `cct:ux-audit` when a screen is new, **validation**: every fact and ask exercised in the built app into `validation.md` (expected, observed, evidence, verdict; `not met` blocks), `cct:ux-validate build`, the `verifier` and `ac-auditor` agents for jobs and facts. **Last milestone of the goal only:** `security-review` on the whole goal diff when auth, money or consent is touched anywhere in it (in a project it waits for 6p). One findings list, one fix round, `verify_gate.py milestone`, one PR **to the milestone's parent** — `project/<slug>` in a project, else the default branch. | **Engineer accepts the milestone** (one go: only when a Critical or High would be deferred) |
| 6p Project | Only in a project, and only once every milestone has merged into `project/<slug>`: rebase it on the default branch, re-run `checks.milestone` on the whole project diff, plus `security-review` on it when auth, money or consent is touched, then one PR to the default branch. This is the PR CI reviews and tiers. No second fix round — what is left starts the next project. | **Engineer accepts the project** |
| 7 Outcome + archive | Archive the folder when the change reaches the default branch. After release, read the success measure from PostHog into `milestone.md`. A miss starts the next change at 1.3. | Engineer reads it |

## Agents and models

Agents: every build, fix, test, capture, restack or records agent is `cct:builder` (Sonnet); review and checks use their typed agents (`cct:code-reviewer`, `cct:verifier`, `cct:ac-auditor`, `cct:ux-reviewer`, `cct:validate-finding`). Never launch general-purpose for this work: it inherits the session's model. Any other subagent gets `model: sonnet` explicitly. The session's own model is only for the gate's visual judgement and for decisions. Dispatch builders yourself, never through a closer agent that spawns its own.

Every step, input, output, skip and failure mode: `references/stages.md`. A step whose skill is
not installed is skipped with a printed note naming it, never silently.

## The two touchpoints, and nothing else

1. **Intent.** The agent drafts; the engineer confirms or edits `intent.md`. Then
   `status: approved`, commit `changes(<id>): intent confirmed by <who>`.
2. **Plan.** One `plannotator annotate changes/<id>/plan.md --gate` covering `spec/`, `facts.md`
   and `plan.md` (`planGate: self` allowed only when no risk touches data safety, irreversible
   writes, security or money). On approval set all three `status: approved`, run
   `python3 scripts/verify_gate.py approve <id>`, commit `lock.json`: `changes(<id>): approved by <who>`.

No design gate exists. `cct:ux-validate spec` runs once and its findings go into the plan.

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
`VERIFY BLOCKED reason=<code>` (stop and ask the engineer). Reasons: `not-approved`,
`protected-path`, `no-progress`, `flaky`, `unknown-verdict`, `needs-baseline`,
`allowlist-request`, `scope-growth`, `spec-conflict`, `env`, `test-proves-nothing`.
Snapmark feedback and supplied reference images require comparison against fresh headless
screenshots, including ADR refinements; milestone `owner-marks` checks `marks.json` (see `references/stages.md`).

## Branches

Two shapes. **One milestone** is the default and is unchanged:

```
<defaultBranch> ─── milestone/<slug> ─── <feature branches>
```

**A project** — work that spans several milestones — adds one level above it:

```
<defaultBranch> ─── project/<slug> ─── milestone/<slug> ─── <feature branches>
```

- `project/<slug>` is cut from `origin/<defaultBranch>` at 1.2 and rebased on it after every
  default-branch merge. It exists only while `decisions.json` names a `project`; without one,
  milestones are cut from `<defaultBranch>` exactly as before.
- `milestone/<slug>` is cut from its **parent** — `origin/project/<slug>` in a project,
  `origin/<defaultBranch>` otherwise — and rebased on it after every parent merge (a Stage 5
  precondition). The tracker's milestone maps to it.
- One go (default): the build works in one worktree on `milestone/<slug>-<n>` itself, a commit
  per feature; milestone `n+1` is cut from `n`, and its PR opens after `n` merges (rebase
  `--onto` the default branch). Parallel builders, when used, merge back locally.
- Feature PRs: feature worktrees branch from the milestone: `git worktree add` from
  `origin/milestone/<slug>`, then `EnterWorktree path=` (`references/stages.md` 1.2). Their
  branch names contain the change slug.
- Builders are `cct:builder` agents, at most 4 at once; the supervisor edits no code and runs
  no test suite. Every builder dispatch carries `sdlc.json` `builderModel` and `builderEffort`
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

| PR | Checks | Claude review | Ship/Show/Ask | Who approves |
|---|---|---|---|---|
| feature → `milestone/*` | `checks.feature` | no | no | nobody; auto-merge on green |
| milestone → `project/*` | `checks.milestone` | no | no | nobody; auto-merge on green |
| `project/*` or `milestone/*` → `<defaultBranch>` | `checks.milestone` | **yes** | **yes** | the tier decides |

Both CI workflows enforce this themselves, by comparing
`github.event.pull_request.base.ref` with the repository's default branch — so the rule holds
even for a PR opened by hand. Reviewing every interior PR re-reads the same diff two or three
times on its way up and costs ~$1 each time; the integration PR is where the whole change is
first seen as one thing, and that is where it is read.

### Records, gates and waiting

**One milestone, one push, one PR, enforced by `pr-gate.sh`.** Every milestone starts with its
sync row: `git merge origin/<default>` (and `origin/project/<slug>` in a project) locally; the
gate fails `check=parent-sync` without it. While a milestone is open, everything that belongs to
it is a commit on `milestone/<slug>`, never its own PR or push: fixes found in the build, test
and flaky-spec repairs, CI timeout tweaks its tests need, and records (plans, handovers, gate
lines, findings). A record written after a merge is the next milestone's first commit; a fix for
a merged milestone goes into the next one. The close runs locally: one `cct:builder` subagent runs
unit tests, the full E2E suite, the one fix round and `verify_gate.py milestone`, while the
supervisor dispatches the reviews and the validation. With `builders: "codex"` the close
builder runs the checks and the gate but implements nothing: the fix parts go to
`codex-build.sh`, then the close builder runs the checks and the gate again. Only its
`VERIFY PASS` head is pushed, once, with one PR and auto-merge armed, while the supervisor builds
the next independent milestone (at most 4 builders). CI is the last check, never the test loop:
a red check gets one fix commit and the gate again, never a rerun. Another repository follows
the same rule on its own milestone branch; an exception needs the engineer's words in
`decisions.json` `prExceptions`. Agents run only the tests they touched.
CI runs each step (lint, unit, build, e2e, deploy) only when a changed code or config path needs it (`sdlc.json` `ciPaths`), nothing for a file that is neither, and runs the full E2E suite only on the
PRs into the default branch or `project/*` and on milestone heads. Rules and per-stack
commands: `references/stages.md` "Records, gates and waiting", `references/ci-blueprint.md`.

## Never

- Build outside `/goal`. `chain-gate.sh` refuses the edit; never work around it.
- Edit `facts.md`, `done.json`, `lock.json`, `sdlc.json` checks, baselines or allowlists after
  approval without the engineer's words in `decisions.json` `protectedEdit`. Never re-lock.
- Decide the ticket, size, kind or milestone yourself; create a ticket without searching.
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
- Run the whole suite to check one change: the touched tests only, the full suite once per
  milestone (`../e2e-test-run/references/suite-speed-and-reliability.md` section K).
- Name the change's issue key in a feature branch or feature PR: its merge closes the change
  early. Feature PRs carry their sub-issue key; only the milestone PR says `Closes <KEY>`.

## Prerequisites

| Dependency | Required | How to obtain |
|---|---|---|
| `sdlc.json` + `scripts/verify_gate.py` | Yes | `sdlc-run adopt` |
| `plannotator` binary + plugin | Yes for the gates | the repo's `toolsCommand` |
| `omr-ux` plugin | Yes when `ux` is `on` | enable the plugin |
| A tracker: Linear MCP, `gh` with `project` scope, or `bd` | No: `none` runs ticketless | `references/trackers.md` setup guides |
| `gh` authenticated | Yes for PRs | `gh auth login` |
| `codex` CLI, signed in | Yes when `builders` is `codex` | `npm i -g @openai/codex`, then `codex login` |

## References

- `references/stages.md` — every step, input, output, skip and failure mode.
- `references/trackers.md` — Linear, GitHub, Beads: choosing, setting up, the four levels in each.
- `references/chain.md` — folder layout, decisions, frontmatter, `sdlc.json` keys, history.
- `references/requirements-grammar.md` — EARS and Gherkin grammar for `facts.md`.
- `references/adopt.md` — what `adopt` writes, what stays manual, migrations.
- `references/ci-blueprint.md` — how to set CI up in GitHub Actions (`templates/ci/github-actions.yml`), per-step gating by changed file type and path, nothing runs for a file that is neither code nor config, one `check` status, E2E scope, protected interior branches.
- `references/changelog.md` — what each sdlc-run version changed and what a repo must do (`adopt --upgrade` reads it).
- `references/tiers.md` — Ship / Show / Ask by path.
- `references/playbook.md` — playbook mapping and metrics.
- `references/layout-research.md` — why `changes/` plus archive.
