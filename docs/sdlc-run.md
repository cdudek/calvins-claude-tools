# sdlc-run, end to end

Describes sdlc-run 3.26.3.

`/cct:sdlc-run` runs an AI-native software lifecycle in any repo. The agent drafts the intent, the UX plan, the facts and the tech plan. You confirm twice. Then one `/goal` builds the whole milestone as commits, runs the heavy checks once, and opens one PR.

Verification and every push follow the [local-first contract](../plugins/cct/skills/sdlc-run/references/local-first.md); read it before running checks or preparing a push. The runbook the agent follows is in [`plugins/cct/skills/sdlc-run/`](../plugins/cct/skills/sdlc-run/) (`SKILL.md`, `references/stages.md`, `references/ci-blueprint.md`, `references/adopt.md`).

## Where to start reading

One change folder, `changes/<date>-<slug>/`, holds everything: nothing lives only in a chat. Its `README.md` is a generated map. It answers three questions, each with one file:

- **What are we building, and why?** Read `intent.md`.
- **Is it right?** Read `facts.md`, then `plan.md`.
- **Where did the work stop?** Read the stage in the README and the latest `handover*.md`.

Everything else in the folder is a working file for agents. If a sentence names an id such as F3 or Q7, `sdlc_status.py ids <change>` says what it means and which file decides it.

A repo can opt in to a shorter folder, "layout 4": three documents instead of eight. See [The living spec](#the-living-spec-optional). This page describes the default layout first and says where layout 4 differs.

## The seven stages

```mermaid
flowchart LR
  I["1 Intent"] -->|you confirm| U["2 UX plan"]
  U --> F["3 Facts"]
  F --> T["4 Tech plan"]
  T -->|you approve| B
  subgraph G["one /goal per milestone"]
    B["5 Build: one commit per feature"] --> M["6 Milestone: checks once,<br/>validation, one fix round"]
  end
  M -->|you accept| P["milestone PR"]
  P --> O["7 Outcome and removal"]
```

The two touchpoints are the intent and the plan. After the plan is approved, `lock.json` locks the facts, `done.json` and the checks; only your words can open them. The times are typical for a medium change, not promises. The example is one invented change throughout: "sort the invoice list by date".

### 1 Intent

- **You get:** `intent.md` with your asks word for word, job stories, the success measure and the rules that apply.
- **Who acts:** the agent drafts after one dialog (ticket, design, size, kind, milestone, project); **you confirm**.
- **Typical time:** 10 to 20 minutes.
- **Your design:** If you have a design (Figma, an export bundle, an image), say so; it becomes the one source the build is checked against ([design inputs](../plugins/cct/skills/sdlc-run/references/design-inputs.md)).
- **Example:** your words "I can't find the newest invoice" become the ask A1, the job story "when I open the list I want newest first", and the measure "support questions about finding invoices drop by half in a month".

### 2 UX plan

- **You get:** `spec/`: screens, states, words and components, planned against the repo's design rules, and `spec/readiness.md`, the verdict that the design is ready. Images of the screens only when the plan marks the UI risky. Skipped for size `none` or `ux: off`.
- **Who acts:** the agent, with review agents.
- **Typical time:** 30 to 60 minutes.
- **Example:** one screen (the invoice list) with the states "empty", "loading" and "sorted", and the new column header named "Date".

### 3 Facts

- **You get:** `facts.md`: short testable sentences. Each cites its ask, names its screen or state and names the E2E test tag that proves it.
- **Who acts:** the agent drafts; a reviewer in a fresh context writes `checklist.md`.
- **Typical time:** 10 to 20 minutes.
- **Example:** "When the list opens, the system shall show the newest invoice first (A1)".

### 4 Tech plan

- **You get:** `plan.md`: where the code goes, the milestones and the feature rows, and `done.json`, which holds "done" as data. An analyze pass and a challenge pass argue against it first.
- **Who acts:** the agent drafts; **you approve** the UX plan, the facts and the plan in one review. Then `verify_gate.py approve` writes `lock.json`.
- **Typical time:** 15 to 30 minutes to draft, plus your review.
- **Example:** two features: "sort the rows" and "remember the sort in the URL", each with its facts.

### 5 Build

- **You get:** one commit per feature on `milestone/<slug>-<n>`, and `questions.md` with every open question and the default taken.
- **Who acts:** the agent, inside one `/goal`. Builders write each feature's tests first, then the code; the touched tests and the repo's pre-commit checks run between features. A question never stops the build.
- **Typical time:** 20 to 60 minutes per feature; a few hours for a milestone of four to six.
- **Example:** commit "feat: sort the invoice list by date", then the next feature starts at once.

### 6 Milestone

- **You get:** one PR with the report. Code review (Claude and Codex), UX review, accessibility, the full E2E suite once, every fact exercised in the built app (`validation.md`), `findings.md` with one fix round, and `verify_gate.py milestone` on a frozen head.
- **Who acts:** the agent, in the same `/goal`; **you accept** (in one go only when a critical or high finding would be deferred).
- **Typical time:** 30 to 90 minutes, mostly the E2E suite.
- **Example:** `validation.md` shows the fact above as "met", with the test and the screenshot as evidence.

### 7 Outcome

- **You get:** the next change's first commit removes the folder once this one merged (there is no archive, and no records-only PR), a short `reflection.md` written before it goes and, after release, the success measure read where `intent.md` says. What happens to the folder is in [Closing the change](#closing-the-change).
- **Who acts:** the agent removes the folder and records the outcome; **you read** the measure.
- **Typical time:** a minute to remove the folder; the measure is read days or weeks later.
- **Example:** "support questions about finding invoices: down 55 percent in 30 days, target met". A miss starts the next change.

A project, work that spans several milestones, adds stage 6p: after the last milestone merges, the milestone checks run once more on the whole project, and **you accept** the project.

## One /goal per milestone

`delivery: "one-go"` is the only delivery in `sdlc.json`. Everything you asked for at once is one change. One `/goal` builds every milestone in the plan, in order, each on its own local branch `milestone/<slug>-<n>` cut from the default branch, so it merges on its own. Only a milestone whose plan row says `needs: M<k>` is cut from that one; it builds at once and opens its PR after that one merges. Nothing is pushed before the milestone's gate passes. Each feature is a commit. The full suite runs once on the final milestone head before push; failure diagnosis stays targeted.

Builders are `cct:sdlc-feature-builder` agents, at most four at once, each in its own worktree and test slot. Each gets a `Base: <sha>` line, the milestone head, and resets to it before any edit, because a worktree hook cuts from the default branch. The supervisor commits its records first, edits no code, runs no test suite, and merges builder branches back one at a time. The close is one `cct:sdlc-feature-builder` with `Mode: close`; nothing merges while it runs.

## Branches, commits and PRs

```mermaid
flowchart BT
  F["features: commits on the local milestone branch"] --> M["milestone/slug"]
  M -->|"one push after the gate, one PR, merge commit, you accept"| D["default branch"]
  M -.->|"only with project.branch: true"| P["project/slug"]
  P -.->|"project PR: tiered, you accept"| D
```

```
<default> ─── milestone/<slug>-<n> ─── <feature commits>              one milestone, or each milestone of a project
<default> ─── project/<slug> ─── milestone/<slug>-<n> ─── <features>  a project that asked for a branch
```

**Commits, not PRs.** While a milestone is open, everything that belongs to it is a commit on `milestone/<slug>`: features, fixes found during the build, test and flaky-spec repairs, CI timeout tweaks its tests need, and records (plans, handovers, gate lines, `findings.md`, `validation.md`, `questions.md`). No PR holds only a record, a fix or a test repair. The folder removal is the last commit of the change's last milestone PR ([closing the change](#closing-the-change)).

**PRs that exist:**

- The milestone PR, into the default branch (or `project/<slug>` when the project has a branch).
- The project PR, only when the project has a branch.
- Other repositories, and a change you send to the default branch first.

**Only the PR into the default branch is tiered.** Everything below it is an interior merge inside one change and auto-merges on its checks alone. The code review is not a PR step at all: it runs once, locally, at the milestone close. Nothing runs Claude in CI, so no repo needs `ANTHROPIC_API_KEY`.

| PR | Checks | Ship/Show/Ask | Who approves |
|---|---|---|---|
| milestone to `project/*` | milestone checks | no | nobody; auto-merge on green |
| `project/*` or `milestone/*` to the default branch | milestone checks | yes | the tier decides |

Acceptance is separate from PR approval: you accept each milestone at stage 6, and the project at 6p, even though the interior PRs merge themselves. A hotfix goes straight to the default branch with feature checks only.

## The verify contract

`python3 scripts/verify_gate.py feature|milestone <id>` checks `lock.json`, runs the checks named in `sdlc.json`, writes `changes/<id>/verify/report.md`, and ends with exactly one line:

| Last line | The agent |
|---|---|
| `VERIFY PASS <scope> <id> <sha>` | moves on |
| `VERIFY FAIL ... check=<name>` | fixes that check and runs verify again |
| `VERIFY BLOCKED reason=<code>` | stops and asks you |

Blocked reasons: `validation-not-met`, `findings-open`, `findings-blocked`, `not-converged`, `not-approved`, `protected-path`, `no-progress`, `attempts`, `flaky`, `unknown-verdict`, `needs-baseline`, `allowlist-request`, `scope-growth`, `spec-conflict`, `env`, `test-proves-nothing`. `env` also covers a heavy slot that never frees and a parent branch the gate cannot find; the line names the fix.

The agent may never build outside `/goal`, change the approved plan, edit a test to make it pass, start a second fix round at a milestone, decide scope for you, or open a PR for work that belongs to an open milestone.

## Where a change stands

`/cct:sdlc-run status` lists every open change and its stage. Inside a `/goal`, `python3 scripts/sdlc_status.py goal <id>` prints one line: `GOAL <id> DONE`, or `BLOCKED` with the state and the command that leaves it. Every state the goal can print is listed in [`states.json`](../plugins/cct/skills/sdlc-run/references/states.json) with who acts and where it leads. A test keeps that file equal to the code and fails when a state is a dead end.

| State | Meaning | Who acts |
|---|---|---|
| `gate-pass` | the milestone gate has not passed on this head | the agent runs it |
| `findings-open`, `validation-not-met`, `not-converged` | the close is missing work | the agent fixes it |
| `findings-blocked`, `not-approved`, `protected-path`, `scope-growth`, `spec-conflict`, `env` | a decision or a fix that only you can make | you |
| `no-pr:` | gate passed, no PR yet | the agent opens it |
| `pr-awaits-owner` | an Ask PR waits for your `Accept milestone` answer | you |
| `pr-held` | you answered `Hold` or the PR has the `hold` label | you |
| `pr-ci-failed` | a required check is red | the agent fixes it |
| `pr-awaiting-ci` | auto-merge is armed and fires on green | GitHub |
| `done` | merged, with proof | nobody |

A merged Ask PR is not `done` without your answer, and a Hold blocks at any tier.

## Heavy work: builds, browsers and databases

Many helpers can run at once. A machine cannot run many builds, app servers and browsers at once. The kit gives them a queue. Four small scripts, installed by `adopt` into `scripts/`, do the work. Details are in [heavy work](../plugins/cct/skills/sdlc-run/references/heavy-work.md).

- **The queue (`heavy.py`).** A heavy job (a build, an app server, a browser test, the full suite) takes a slot. One slot per machine by default. First come, first served; a dead process never blocks the line; a waiter is told who holds the slot. Waits and runs have deadlines. A light job (format, lint, types, touched unit tests) never waits.
- **The gate uses it.** Every check of the milestone gate runs through the queue. A slot that never frees ends the gate with `VERIFY BLOCKED reason=env` and names the holder.
- **Test databases (`db.py test`).** One local Postgres container holds a migrated template. Each job gets a private copy in under a second and drops it afterwards.
- **Your own dev database (`db.py dev`).** It connects you to your own cloud database through the provider's auth proxy, with your own identity and no shared password. It creates the database once and runs migrations. Every command comes from `sdlc.json` `db`, so the kit names no vendor.
- **Evidence (`evidence.py`).** One file per screen, so helpers never write the same file. When a text key changes, only the screens that show that key are captured again.
- **Preflight (`preflight.py`).** Checks the tools, the sign-in and Docker once, before the work starts. It prints one fix line per failure and ends with `PREFLIGHT OK` or `PREFLIGHT FAIL <n>`.
- **Guard.** The hook `helper-guard.sh` refuses a helper's heavy command that does not go through the queue. Your own session is never refused.

Builders: at most four at once, inside about six helpers in all. A Codex builder runs light checks only; the supervisor runs its heavy checks outside the sandbox. All of it is optional: set `heavy`, `db` and `preflight` in `sdlc.json` to tune it.

## The living spec (optional)

By default a change folder holds eight kinds of file. A repo can opt in to **layout 4** with `"layout": 4` in `sdlc.json` (`adopt` never sets it). A change that started on the old layout finishes on it and is never blocked.

**Three documents per change** replace intent, facts, plan, checklist, analyze, challenge, milestone and the reading map:

- `spec.md`: why and what.
- `design.md`: how.
- `tasks.md`: in what order.

Which ones a change gets depends on its risk, not on how much interface it changes: scope S needs only `spec.md`, M needs `spec.md` and `tasks.md`, L needs all three. Machine files (`decisions.json`, `done.json`, `lock.json`, `verify/`) keep their paths. See [the change folder](../plugins/cct/skills/sdlc-run/references/change-folder.md).

**The living spec** is what the product does today: one file per rule, `specs/<capability>/rules/R123.md`, with one `manifest.yaml` per capability and a generated `specs/CAPABILITIES.md`. The PR that changes the behaviour changes the rule file, so the PR's git diff is the delta. There is no archive and no apply step. Rule ids are `R` and a number and are never reused. See [the living spec](../plugins/cct/skills/sdlc-run/references/living-spec.md).

`python3 scripts/spec.py` is the one tool:

```bash
python3 scripts/spec.py find invoice sort --paths src/invoices   # ranked rules for a request
python3 scripts/spec.py new billing "retry a failed charge once" # a new rule file with the next free id
python3 scripts/spec.py check --base origin/main                 # a changed rule needs a changed test
python3 scripts/spec.py consistency changes/<id> --phase approve # script checks before a model reads
```

`find` is for the start of a change: read the rules it names before you ask for new ones. It warns when a rule looks stale or an open PR edits it. `check` runs at the milestone gate and in CI. If two PRs take the same rule number, `spec.py renumber` gives the later one the next free number. Other commands: `show`, `next`, `index`, `capabilities`, `eval`, `outcome`, `qa`.

## Closing the change

There is no archive and no records-only PR. After the change's PR merged, the next change's first commit runs `sdlc_status.py sweep-merged --apply`:

1. `spec.py outcome write changes/<id>` copies the success measure to `.sdlc/outcomes/<id>.json`. It is the one place the result is recorded, so a change with no tracker and no later PR still has a home for it.
2. `git rm -r changes/<id>` goes in with it, as that next change's first commit, so it ships in that change's one PR. The change's own PR keeps its folder, and a goal reads DONE as before.
3. Before it removes anything, the sweep runs `git grep -l -F "changes/<id>/"` and prints BLOCKED for a hit. A test, script or doc that reads inside the folder would break, so it is repointed first.
4. After release the measure is read and recorded with `spec.py outcome record`. `spec.py outcome due` lists the ones still waiting.

History stays in git and in the merged PR. Folders archived by older versions stay readable. The status and gate code accept a folder that is gone.

## Local verification and GitHub setup

The [local-first contract](../plugins/cct/skills/sdlc-run/references/local-first.md) is the
single verification rule for builders, fixes, E2E work, milestone close and PR creation.
Use targeted local runs while diagnosing, then the full suite once before every push.

GitHub Actions required checks are the merge gate; the rulesets require them. Nothing local
(no script, receipt or hook) gates a push or a PR. GitHub also runs deploys, eligible previews,
cloud plans and scheduled work. Required checks are never the debugging loop. A passed PR does
not need a second full CI run on main.

Decision4 is advisory: PRs say how hard the change is to undo (a level per `boundary-map.yaml`, a decision record above Undo). No workflow, status or hook reads it. See [Decision4 in a PR](../plugins/cct/skills/sdlc-run/references/decision4-pr.md).

Follow the [CI setup guide](../plugins/cct/skills/sdlc-run/references/ci-blueprint.md) to
implement and audit the repo-specific gate before replacing required remote checks.
`adopt` preserves existing workflows and reports the manual gate setup. The legacy
`templates/ci/github-actions.yml` is retained for migration/reference, not automatically
installed. `ciPaths` and `ciCommands` still describe affected paths and stack commands;
commands per stack live in the E2E policy's section K.

## How to adopt

Run `adopt` once per repo, from the repo root, on a branch:

```bash
/cct:sdlc-run adopt
```

It first asks whether to use Ship/Show/Ask merge tiers (a code owner approves risky PRs; the right answer for a one-owner repo is no). Then it installs:

- `sdlc.json`, from a preset, including the stack's default `ciPaths` and `ciCommands` (written once, never overwritten; edit the folder names to your repo's own), and the `sdlcVersion` stamp.
- Hooks in `.claude/hooks/` that refuse edits outside `/goal` and to locked files, and `scripts/verify_gate.py`.
- The review and tier workflows, `docs/sdlc.md`, issue and PR templates, and a section for `CLAUDE.md`.

`adopt` preserves existing CI and does not install a remote verification workflow in a repo without one. It points at GitHub's required checks as the merge gate. Re-run it whenever the plugin updates, because the hooks and workflows are copies that do not update themselves.

## Staying current

`adopt` writes `"sdlcVersion": "3.26.3"` into `sdlc.json`. Every time the skill runs in the repo, `status` and the verify gate compare the stamp with the installed plugin and print one line when it is missing or older, for example:

```text
This repo runs sdlc-run 3.2.0; the kit is 3.3.1. Run `adopt --upgrade` (changes: 3.3.1: adopt --upgrade never overwrites or moves anything; 3.3.0: the CI workflow ships as a template, ciPaths by file type, versioned repos).
```

A repo newer than the plugin is told to update the plugin. The verify gate prints it as a `WARN` line and never blocks.

`/cct:sdlc-run adopt --upgrade` is the safe path. It adds the keys a newer plugin introduced with the stack's defaults, never changes a value, stamps the new version and writes nothing else: no file overwritten, no folder moved. Each file that differs from the plugin's copy (a hook, `scripts/verify_gate.py`, `docs/sdlc.md`, the guardrail test) is listed as `review diff`, together with the manual migrations of `references/changelog.md` since your stamp. `adopt --upgrade --replace <file>` shows one file's diff; `adopt --upgrade --apply --replace <file>` replaces that file (and its partners: `verify_gate.py`, `pr-gate.sh` and `pass_proof.py` come as one set, and `marks.py` comes with `verify_gate.py`, each only when nobody edited it). A plain `adopt` refreshes every copy at once. `--dry-run` writes nothing.

## What changed since 3.7

Each version's headline and migration steps are in the skill's [changelog](../plugins/cct/skills/sdlc-run/references/changelog.md). The ones a newcomer meets first:

- **Rules, clarify, checklist, analyze, challenge (3.8, 3.9):** standing rules are cited by id; a fresh reviewer writes `checklist.md`, an analyze pass writes `analyze.md` and a challenge pass writes `challenge.md`. `approve` refuses an unchecked item or an open critical.
- **Enforcement audit (3.9):** `verify_gate.py audit` says per gate whether it is installed, configured, executed and passed.
- **Readable folders (3.17):** a generated `README.md` in every change folder, plain words with ids in brackets, `sdlc_status.py ids` and a sentence for what blocks the goal. [More](../plugins/cct/skills/sdlc-run/references/readability.md).
- **Faster hooks, cheaper gates, local milestones (3.18):** each hook starts Python once per call; `verify_gate.py` runs checks cheapest first; `milestones.merge: "local"` keeps milestone and project branches off GitHub until the one PR into the default branch. [More](../plugins/cct/skills/sdlc-run/references/local-first.md#local-milestones).
- **A milestone close that is fast and cannot deadlock (3.21):** the milestone gate is the only runner of the full suite and the full E2E, cheap offline checks run first, and your answer to one dialog (not text in a file) settles each leftover finding. Sign-off beats auto-merge: an Ask PR is never `done` without your `Accept milestone`. The full list is in the [changelog](../plugins/cct/skills/sdlc-run/references/changelog.md).
- **Heavy work (3.21):** the heavy-job queue, local test databases, your own dev database and preflight. See [Heavy work](#heavy-work-builds-browsers-and-databases).
- **The living spec (3.21, opt-in):** three documents per change, one file per rule, no archive. See [The living spec](#the-living-spec-optional).
- **One close job, one queue per machine (3.22):** the milestone close takes one heavy slot, builds once and uses one test database copy; heavy commands are recognised by program and script; one queue serves every repo on the machine; the test template is kept per migration version and works with Docker or Podman; preflight checks free disk and merged builder worktrees are removed. See [Heavy work](#heavy-work-builds-browsers-and-databases).
- **Screens mode (3.23):** one record per screen with its frozen defect list and round count, checked by `marks.py`; capture once; status in screens; one owner sheet per screen group; the design-system version frozen at approval; a visual change refuses migrations, auth and new pages.
- **A lighter front (3.24):** the three-document layout by default for new adoptions, size S skips the UX stage and the checklist, analyze and challenge passes, one PR per change (the next change's first commit removes the merged folder), and one delivery mode.
- **Design in the real app (3.25):** a change approved from 3.25.0 (lock `"visual": "app"`) binds the design for which screens and states exist (from 3.26.0: `design.json` lists every board, each mapped to a screen or dropped by the owner; `deviates` records where a screen differs) but never measures pixels against it. The UX plan writes `screens.json` (one entry per screen and state) and names a sample-data fixture; every entry gets a preview page in the app; the close takes one capture batch; `evidence.py gallery <change>` writes one offline page where the owner accepts or sends back each shot; the answers are imported into `screens/approved.json`, and the approved shots become exact visual tests. Status in screens: `screens: N of M approved · K changed since approval · L not captured`. Changes approved earlier keep the old path.
