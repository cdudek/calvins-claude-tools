# sdlc-run stages — the milestone process

Verification and every push follow the [local-first contract](local-first.md); read it before running checks or preparing a push.

The detailed runbook for `SKILL.md`, as the owner approved it on 2026-10-09. Rules that hold in
every stage:

- **No design gates.** The engineer confirms twice: the intent (1.4), then UX plan, facts and
  tech plan together (4.3). Nobody else is a gate.
- **After the second confirmation the run is autonomous and always inside `/goal`.**
  `chain-gate.sh` refuses a source edit when the transcript holds no active goal.
- **One go is the default** (`sdlc.json` `delivery: "one-go"`, the owner's call on
  2026-10-25). Everything the engineer asked for goes into one change; the engineer pastes
  **one** `/goal` (`templates/goal/run.txt`) that builds every milestone of the plan in order.
  The goal is an end state only: `python3 scripts/sdlc_status.py goal <ID>` prints
  `GOAL <ID> DONE` or `GOAL <ID> BLOCKED`. The process the run follows is the plan's
  `## How to run`, started by the kickoff prompt in `## Goal handover`.
  Features are commits; **run touched tests and required pre-commit checks**. The full
  local gate runs once on the final head before every push (see [local-first](local-first.md)). One PR and one release
  per milestone. `delivery: "feature-prs"` keeps the older per-feature PRs (Stage 5, second
  half) for repos where several people build one milestone at once.
- **Questions never block.** When the build meets a question only the engineer can answer, it
  writes it to `changes/<id>/questions.md` (`Q<n>`, the question, the default it took, the
  milestone it affects), tells the engineer in one line, and keeps building on the default. An
  answer, whenever it arrives, is copied verbatim into the row and becomes an ask (`A<n>`) of
  the next milestone; a default the answer overturns is reworked there, not mid-milestone.
  Only `VERIFY BLOCKED` and an unfixable Critical or High stop the goal.
- **Feature checks run on what the feature touched; milestone checks on what the milestone
  changed.** Never the whole product.
- **Project values come from the repo.** Where sdlc.json, PRODUCT.md or DESIGN.md say nothing,
  the kit default applies and the report names it.
- **A step whose skill is not installed is skipped with a printed note** (`skipped: <skill> is
  not installed`), never silently, and the note goes into the report of that stage.

## Waiting

Pick the tool by what ends the wait. `/goal` ends when a model confirms its condition from the
transcript, `/loop` when time passes, a Stop hook when a script decides.

- **CI on the milestone PR:** one background `gh pr checks --watch <n>` or a `Monitor` on it, only to learn
  the result. No polling turns, and never a fix loop: a red check is fixed locally first
  ([local-first](local-first.md)).
- **After the merge (deploy, live checks):** `/loop` self-paced, stopped when the deploy is
  confirmed. Start it after the goal is met.
- **The success measure, days later:** `/schedule` (a cloud routine, it runs while the machine
  is off). Never a session loop.
- **Never a `/loop` inside a running `/goal`.** Two things then decide when the session stops.

## Stage 1 — Intent

Worktree lifecycle commands follow the [shared worktree policy](../../../references/worktree-usage.md).

### 1.0 Preconditions

- **Worktrunk preflight:** check `command -v wt`; if missing, use the shared policy’s single `AskUserQuestion` installation prompt, then continue with Git on decline or installation failure. Reuse a setup answer from this session.
- **Steps:** Run `status.sh`; `templates=stale` → run `adopt` first. No `tracker` in `sdlc.json`:
  run `scripts/tracker.py detect`, ask, set it up (`references/trackers.md`). Check plannotator, the tracker
  MCP and `gh`; say once what is missing and continue where the chain allows.
- **Failure modes:** stale templates, no `sdlc.json`, missing `scripts/verify_gate.py`.

### 1.1 The dialog

- **Steps:**
  1. Search the tracker first with distinctive title words. Read `<designsDir>/INDEX.md`, one
     line per design and decision, and open only the files whose title or tags touch the
     ticket. Never read the whole designs folder, and never build on a line under `Replaced`.
  2. One `AskUserQuestion` with five forks: ticket, design file, size, kind, milestone. Each
     fork puts your pick first as `(Recommended)` with the reason, read from the ticket and the
     code: "M (Recommended): the ticket changes one screen's behaviour".
  3. Sizes, one line each: `none` no interface change; `S` words or visuals on an existing
     screen; `M` one screen's behaviour or one flow; `L` a new screen, flow or feature.
  4. Kind: `feature`, `bug`, `refactor`, `docs`, `chore`.
  5. Milestone: `new` (this change opens `milestone/<slug>`), `existing` (name it; this change
     adds its features to that milestone's `milestone.md`), `single` (a milestone of one: both
     checks on one change), `hotfix` (PRs to the default branch, feature checks only).
     When the engineer names several things at once, they are features of **one** change and
     one milestone, not one change each; the plan orders them.
  6. Project, asked only when the milestone fork was `new`: `none` (**recommended** — the
     milestone goes straight to the default branch), `new` (this change opens a project),
     `existing` (name it). A project is for work that will span several milestones; a single
     milestone never needs one. A project is planning, not a branch: its milestones still go
     to the default branch one by one, unfinished work behind a flag. Only when the engineer
     asks for a branch does the project get `project/<slug>` (`"branch": true`).
  7. Write `decisions.json` first: `{"size", "kind", "milestone": {"kind", "slug"}, "ticket",
     "design"}`, plus `"project": {"kind", "slug", "branch": false}` when the answer was not `none`
     (`true` only on the engineer's words; a project written before 3.7.0 has no `branch` key
     and keeps its branch). `design` is
     the design file's path or `"none"`. The `milestone` key marks a folder on this process.
- **Failure modes:** asking before searching the tracker; deciding a fork yourself; opening a
  project branch nobody asked for, which holds finished milestones back from the default branch.

### 1.2 Folder, tracker, worktree, project and milestone branches

- **Steps:**
  1. Slug of at most four words. Create `changes/<today>-<slug>/`; nothing waits for the tracker.
  2. Attach to the named issue, create one for `new` (minimal first, then update; retry twice),
     or none, at the level `references/trackers.md` gives for this tool. A Linear key: `git mv`
     to `changes/<today>-<KEY>-<slug>/` and set `linear:`; a GitHub or Beads id: `decisions.json` `ticket`.
  3. A project branch only when `decisions.json` `project.branch` is true and `kind` is `new`:
     `git push origin origin/<defaultBranch>:refs/heads/project/<slug>`. An `existing` project
     branch is already on the remote; confirm it with `git ls-remote --exit-code origin
     project/<slug>` rather than assuming. Then create or attach the tracker's milestone.
     **The milestone branch is not pushed here** (3.7.0): it is created locally in step 5 and
     pushed once, at the close, after `VERIFY PASS`; `pr-gate.sh` refuses an earlier push.
     Only `delivery: "feature-prs"` pushes it now, because feature PRs need a remote base:
     `git push origin <parent>:refs/heads/milestone/<slug>`. `<parent>` is
     `origin/project/<slug>` when the project has a branch, else `origin/<defaultBranch>`.
     `hotfix` cuts no milestone branch.
  4. Write `milestone.md` from the template for `new` and `single`; for `existing`, add a row to
     the named milestone's `milestone.md`. When the change names a design, add one line for it
     under that design's `## Milestones` (the guardrail test and `status` both read it).
  5. The worktree, from the main checkout (`ExitWorktree keep` first when in one):
     use the shared create flow: fetch, then `wt switch -c <branch> -b <base> --no-cd --format json`
     with the exact `.worktrees/<slug>` path override (plain Git fallback in the policy),
     then read `.path` and `EnterWorktree path=<returned-path>`. One go: `<branch>` is
     `milestone/<slug>-<n>` itself and `<base>` is `<parent>` (or, for a milestone the plan
     marks `needs: M<k>`, the local predecessor branch). Feature PRs: `<base>` is
     `origin/milestone/<slug>`. Hotfix: `origin/<defaultBranch>`. `<branch>` contains the slug.
     Never `EnterWorktree name=<slug>@<branch>`: the tool allows only letters, digits, `.`,
     `_`, `-` and `/` in a name, and the WorktreeCreate hook always cuts from the default branch.
- **Failure modes:** a duplicate ticket, a worktree outside `.worktrees/`, a branch name without
  the slug (the hooks then cannot find the change), a feature branch cut from the default branch
  instead of the milestone branch (a milestone of one hides it: both are the same commit).

### 1.3 Asks

- **Steps:**
  1. Collect sources in order: ticket, conversation, the owner-words file from `docs/ux/setup.md`,
     then every `sdlc.json` `feedback` file since the last archived change for the same screen.
     Copy each request verbatim into `intent.md` `## Asks` as `A1`, `A2`, …;
     copy resources into `changes/<id>/asks/<source-date>/` and link them.
  2. Copy each Snapmark export whole into `changes/<id>/asks/<session-date>-snapmark/`:
     `session.md`, `img/`, and any PDF or zip. Never re-encode the images.
     Run `python3 scripts/marks.py init <id>`. Every numbered note becomes an `A<n>`, quoting
     the owner's words with its mark id. Every ask still lands in a fact or `## Out of scope`.
  3. The same command inventories reference images in `asks/` and `spec/prototype/`.
     Rerun it when sources arrive; keep filled rows and resolve reported orphans.
- **Failure modes:** a dropped or paraphrased ask; a link to `/Users/`, `~/` or `file://`.

### 1.4 Draft the intent; the engineer confirms

- **Steps:**
  1. The agent drafts the rest of `intent.md`: job stories with an evidence label each
     (**observed**, **reported**, **assumed**), the success measure (one number, where it is
     read, the target), problem, outcome, constraints. Read the files in `sdlc.json` `rules`
     (defaults in `references/quality-passes.md`) and list the rule IDs that touch the asks under
     "Rules that apply". Infer; ask only what the engineer alone knows, inside the clarify budget
     (`references/quality-passes.md`).
  2. `python3 scripts/verify_gate.py lint <id>`; fix every line it names.
  3. Show the draft in five lines: the asks, the job stories, the success measure. Then one
     `AskUserQuestion`: "Confirm (Recommended)" with why the draft covers every ask, or "Edit".
     Never skipped.
  4. `status: approved`, `reviewed_by`, `approved_at`; commit `changes(<id>): intent confirmed by <who>`.
- **Gate:** touchpoint one. `chain-gate.sh` refuses `spec/**` and `facts.md` before it.

## Stage 2 — UX plan

Skipped for size `none` and for `sdlc.json` `ux: off`, with one printed line.

- **Steps:**
  1. `cct:ux-design-run <change>`: brief, IA, interaction, screens into `spec/`. Size S skips to 3.
  2. `cct:ux-sitemap-create diff <change>`: the sitemap change this makes.
  3. `cct:ux-rules-validate spec <change>`: the component table — exists / adapt / new, with paths.
  4. `cct:ux-copy-write`: every changed word, in every language in `sdlc.json` `languages`.
  5. `cct:ux-spec-validate spec <change>` **once**, sizes M and L. No loop: its findings go into
     `plan.md` (a fix in the spec now, or a Risk row), and the run continues.
  6. Prototype images only when the plan marks the UI risky (a new pattern, a dense screen, a
     flow nobody has drawn): `cct:design-mockups-create spec <change>`. Otherwise none.
- **Output:** `spec/*`. **Gate:** none.
- **Failure modes:** a validation loop (the old process's cost), images drawn by default.

## Stage 3 — Facts

- **Steps:**
  1. Read `references/requirements-grammar.md`. Draft `facts.md` after the UX plan.
  2. Every fact cites asks and the rule IDs it touches `(A1, A3; rules SEC-2)`, names its screen
     or state, and names the E2E tag that will prove it (`@F1` in the test title). A
     one-sentence change gets one plain fact.
  3. Every ask maps to a fact or to `## Out of scope`.
  4. Clarify, budgeted: at most 5 questions over nine areas, one at a time, each with a
     recommended answer; each answer goes into the facts at once. Fill the rest with defaults
     under `## Assumptions`; at most 3 `[NEEDS CLARIFICATION]` markers; leftovers under
     `## Deferred` (`references/quality-passes.md`).
  5. A reviewer in a fresh context writes `checklist.md`: items that test how the facts are
     written (Gap, Ambiguity, Conflict, Assumption), never the behaviour. The agent answers each
     in the facts, and the reviewer ticks it.
  6. `python3 scripts/verify_gate.py lint <id>` over intent, facts and plan.
- **Gate:** none; `chain-gate.sh` refuses `facts.md` before the UX plan is done or skipped.

## Stage 4 — Tech plan and the one gate

### 4.1 Plan

- `plan.md` from the template: Approach (with what was rejected), **Rules check** (run before the
  design and again after it; a rule the plan breaks becomes a row in **Justified violations**),
  **Where things go** (a folder
  for every new file), **Milestones** and the feature rows under them (ordered, each with its
  facts and branch), Files that
  change, Order of work with a proof per step, Risks (including the validate findings), Done,
  **How to run** (the process of the build, from `templates/change/plan.md`), and **Goal
  handover**: a kickoff prompt plus the `/goal` line. One go: the filled
  `templates/goal/run.txt` (turns from `goal.runTurns`); feature PRs, one filled
  `templates/goal/feature.txt` per feature (`goal.featureTurns`).
- `done.json`: facts with their tags, pages, states, widths, turn caps — the criteria as data.
- **Decisions get their own file.** A choice worth its reasons in a year is a new ADR,
  `<designsDir>/<date>-adr-<slug>.md`, with `supersedes` when it replaces one; set the old
  one's `status: superseded` and `superseded_by`. **Design changes** edit the design's
  sections in place. A design states what is true now: never append a "Since <ticket>"
  paragraph or a dated entry to it. Then `python3 scripts/design_index.py write`.
- A decision that changes or rules out a Snapmark note is an ADR too. Put its repo-relative
  path in that `marks.json` row's `decision`; set `expected` to what must now be visible.
  Read `<designsDir>/INDEX.md` and the relevant ADRs before refining the owner's words.

### 4.2 Calls, when relevant

`cct:arch-plan-write` (a new service or boundary, a schema, an endpoint), `review-security-run` (auth, money, consent), `review-dependency-run` (new
package), `tracking-apply` (the success-measure events). Each result lands in the plan.

### 4.3 The gate

0. **Analyze pass**, read-only (`references/quality-passes.md`): six passes over intent, facts,
   plan and `spec/`, findings into `analyze.md`. Fix every CRITICAL in its source file and mark it
   `fixed`; mention open HIGH findings in the five lines below.
0b. **Challenge pass** (`references/quality-passes.md`): a reviewer in a fresh context argues
   against the change (existence, simpler alternative, failure assumptions, implicit choices, who
   else is affected) into `challenge.md`. Answer every CRITICAL in the plan or facts and mark it
   `answered`, or take it to the engineer for `accepted`. The strongest open challenge goes into
   the five lines below.
1. Say in five lines what the plan builds, the feature PRs in order, and the biggest risk with
   your recommendation for it. Then `plannotator annotate changes/<id>/plan.md --gate`; the plan
   links `spec/` and `facts.md`, so one gate covers all three. `planGate: self` only when no risk touches data safety,
   irreversible writes, security or money.
2. Annotated: revise and re-gate. Approved: set `status: approved` on facts and plan.
3. `python3 scripts/verify_gate.py approve <id>` writes `lock.json` (facts, done.json, checks). It refuses (`APPROVE FAIL`) an unchecked `checklist.md` item, an open CRITICAL
   in `analyze.md` or `challenge.md`, and a row of **Justified violations** with an empty cell.
4. Commit `changes(<id>): approved by <who>`. One tracker comment with the folder permalink.
5. One tracker sub-issue per row of `## Feature PRs`, under the change's issue (minimal first,
   then update; retry twice). Write each key into its row in `milestone.md`. Feature branches
   and PR titles carry that key, never the change's key (`references/trackers.md`, "Which merge
   closes what"). No tracker, or a tool without sub-issues: skip with a printed line.

## Stage 5 — Build, inside /goal

### One go (default)

One `/goal` from `templates/goal/run.txt` (turns: `goal.runTurns`) runs Stage 5 and Stage 6
for every milestone of the plan, back to back. The goal holds only the end state; the run
follows the plan's `## How to run`, which is the steps below as the plan states them. The plan's `## Milestones` groups the features;
a change small enough for one milestone has one.

1. Milestone `n` works on a local `milestone/<slug>-<n>`, cut from fresh `origin/<parent>`, so it
   merges on its own. Only a milestone whose `## Milestones` row says `needs: M<k>` is cut from
   the local `milestone/<slug>-<k>` instead; it builds at once and opens its PR after `k`
   merges. Milestone PRs merge with a merge commit, so a stacked milestone needs no rebase.
   **Its first row is the sync:** `git fetch origin && git merge origin/<default>`, in a project also
   `git merge origin/project/<slug>`, locally in the milestone's worktree. Repeat it whenever an
   earlier milestone merges, and right before each close (the parent moves while you build).
   The merge may run in the supervisor's worktree. It is a commit, never a PR; `verify_gate.py milestone` fails with
   `check=parent-sync` until it is done, so it cannot be skipped.
2. Per feature, in order: write the
   tests for its facts (`cct:test-e2e-coverage-run`, tagged `@F<n>`;
   bugs: `test-behavior-writer`, then `review-fix-implementer`), build in the plan's folders, commit,
   set the row in `milestone.md` to `done <sha>`, start the next feature at once. **Run touched tests and required pre-commit checks between features**; do not
   repeat the full suite while diagnosing one failure. Before pushing, use the full local gate.
3. Features that edit different files may build in parallel (Wall clock below): the supervisor
   commits its records, then dispatches each builder with a `Base: <milestone head sha>` line,
   and merges the builders' branches into the milestone branch locally, one at a time. Commits
   need Conventional Commit subjects: a merge commit keeps them, and the release reads them.
4. When every feature of the milestone is `done`, the supervisor hands the milestone's local
   pipeline to **one `cct:sdlc-feature-builder` subagent with `Mode: close`** and the head it runs on
   (unit tests, the full E2E suite, the one fix round, `verify_gate.py milestone`; it spawns no
   agents of its own). Nothing merges into the milestone while it runs: the gate fails
   `check=moved` if the head changes. The supervisor dispatches
   the Stage 6 reviews and the validation in parallel, writes the findings the subagent fixes, and
   goes on building the next milestone wherever that does not build on this one. Only a
   `VERIFY PASS milestone` head is pushed, once, with one PR and auto-merge armed. CI is the last
   check, never the test loop.
   Scope the owner adds mid-run re-locks (`verify_gate.py approve <id>`) and gets one more close,
   logged under `## Revisions`.

### Feature PRs (`delivery: "feature-prs"`)

- **Preconditions:** the milestone branch has merged **its parent** when that moved —
  `git merge origin/<defaultBranch>`, in a project also `git merge origin/project/<slug>`, in the
  milestone worktree, then pushed (`delivery: "feature-prs"` is the one mode where `pr-gate.sh`
  lets a milestone branch be pushed before its close). Each next feature's worktree is cut from
  it the way 1.2 step 5 says. Never rebase a pushed milestone or project branch.
- **Steps (the goal runs these):**
  1. Start `/goal` with the feature's condition from `## Goal handover`.
  2. Tests first: `cct:test-e2e-coverage-run` for the feature's facts, tagged `@F<n>`. The feature's
     journey row in `e2e/journeys.md` is added or updated in the same PR: tier, states and
     specs (`../test-e2e-policy/references/strategy.md` section 2.8).
     Bugs: `test-behavior-writer` writes the failing test, `testLocked: true`, then
     `review-fix-implementer`.
  3. Build in the plan's folders. A file elsewhere is `scope-growth`: stop and ask.
  4. `cct:test-e2e-policy` on the feature tags locally, in the feature's own worktree and E2E
     slot, in the foreground (see Wall clock below); `test-flake-fix` for an inconsistent test.
  5. `python3 scripts/verify_gate.py feature <id>`, once per feature at the end, never after a
     task group; between edits run only the test files the change touched, since the gate is
     the final full check. On `FAIL`, use the targeted failure loop in [local-first](local-first.md), then rerun the full gate once: passed checks on an
     unchanged tree are cached, and the third failed run blocks with `reason=attempts`. On `BLOCKED`: one
     `AskUserQuestion` naming the reason in plain words, two or three ways forward, your pick
     first as `(Recommended)` with why.
  6. `cct:git-pr-run --base milestone/<slug>` (hotfix: the default branch), auto-merge not
     yet armed. The branch and title carry the feature's sub-issue key, never the change's key.
  7. UX check on the feature's own screens: `cct:ux-assessment-run <pr>`, run from the feature's
     worktree and E2E slot. Capture every changed screen and control open.
     For a marked screen or referenced wireframe, run `python3 scripts/marks.py init <id>`;
     capture that screen and state headless at the mark's width (Stage 6's headless rule).
     Open both the mark or reference image and the fresh shot; fill the rows this feature touches.
     Keep fresh shots under `changes/<id>/verify/shots/`, with change-relative paths in `shot`.
     Open every captured image with the image-reading tool. Require the
     review's visual ledger and one convention verdict per issue: `violates` with a quoted
     rule, `allowed by` with its decision or exception (remove from fixes), or `no convention`
     (keep it; propose `cct:ux-decision-log`). Run the Laws of UX and conformance passes too.
     Fix Critical and High findings in this PR, in one round; recapture and inspect the fixes.
     After the fixes rerun only the visual check, not the whole gate. Run step 5 once more with
     `--visual-check "<checker>" --visual-run "<run>"` only after the last fix commit, because
     its PASS sha must equal HEAD; use the
     checker path and current run returned by `cct:ux-assessment-run`. A failed check means the review
     did not run; the gate and report must say FAIL or BLOCKED. An earlier PASS cannot clear it.
     Medium and below stay for the milestone review,
     which sees the same screens. Never post its comments. Skipped with a printed line when
     `sdlc.json` `ux` is `off`, the size is `none`, or the PR changes no interface file.
     Supplied marks and reference images still require comparison, even when the UX skill is skipped.
  8. Arm auto-merge and start the next independent feature at once (Records, gates and
     waiting, below). Local checks run lint, types, unit tests and the specs this PR changed; the
     full E2E suite runs in the local gate before push (`local-first.md`). This PR is
     **interior** — its base is `milestone/<slug>`, not the default branch — so Ship/Show/Ask
     does not run on it, and no human is asked to approve it. The workflow skips itself on the
     base ref (`references/tiers.md`). The code is reviewed once, locally, at the milestone
     close.
  9. On merge: the feature's row in `milestone.md` → `merged`; the next feature starts.
- **Failure modes:** an edit outside `/goal` (refused), a protected-path edit (refused), a test
  edited to pass.

## Records, gates and waiting

Measured on one repo in one day: 13 of 22 PRs were docs-only records, and the agent sat idle
while a dependency PR's CI ran. Four rules, for every stack.

- **One milestone, one push, one PR — enforced.** While a milestone is open, everything that
  belongs to it is a commit on `milestone/<slug>` and ships in the milestone PR: a fix found
  during the build, a test or flaky-spec repair, a CI timeout tweak its tests need, plans,
  handovers, gate lines (`verify/report.md`), `validation.md`, `findings.md`, `questions.md`,
  `milestone.md` rows and the integrated project check. A record that can only be written after
  a merge (the merge commit, the tested head) is the next milestone's first commit; after the
  last milestone it goes in the project PR's description. A fix for a milestone that already
  merged goes into that repo's next milestone. A merge from the default branch is the next
  milestone's sync row, never a `chore/merge-main-*` PR. `project/<slug>` is never pushed after
  its creation; it moves only through milestone PRs. `pr-gate.sh` refuses everything else: a PR
  into `project/*` or `milestone/*` from any other branch, a push of a milestone head without
  `VERIFY PASS milestone` on it (a records-only commit after the PASS is fine), and inside
  `/goal` any other PR or push. Another repository follows the same rule with its own milestone
  branch. The only exception is the engineer's words in `decisions.json` `prExceptions`. The
  archive move (Stage 7) is a commit in the last milestone.
- **A cross-repo dependency builds against a local copy.** When this repo needs another repo's
  unreleased code (a kit fix found by the app), link or pack it locally (`npm pack`, a
  workspace `file:` path that is not committed) and build on. The published version arrives with
  that repo's next milestone close, and this repo pins it then. Never a PR in the other repo just
  to publish a snapshot.
- **A merge gate only for a real code dependency.** Waiting for another PR to merge is justified
  only when this row's code imports, calls or edits something that exists only in that open PR.
  Tests, docs, records, config and unrelated rows are not dependencies: build on. When the code
  does depend, merge the PR's branch into the milestone branch locally
  (`git merge origin/<dependency-branch>`) and build on top; that PR merges when its CI is green.
  When it has merged, the next sync row merges the parent, which already holds those commits.
- **Never idle on CI.** After the milestone push: arm auto-merge (`gh pr merge <n> --merge --auto`), watch
  the PR in the background (`gh pr checks <n> --watch` as a background command, or `Monitor`),
  and start the next independent row at once. The supervisor watches, not the builder; a
  builder returns when it has pushed. A red check interrupts: dispatch a builder to the PR's
  branch, then go back. Independent rows build in parallel builders, at most 4 (Wall clock).
- **Agents run what they touched.** A builder runs only the tests or specs its change touched
  (the command per stack: `../../test-e2e-policy/references/suite-speed-and-reliability.md`
  section K, column "Touched tests"). The full local gate runs once on the final head before each push. Existing remote CI only confirms it; see [local-first](local-first.md).

## Wall clock: one worktree per builder

A milestone spent three hours between "every feature done" and "PR merged" (a milestone audit), and almost none of it was work that had to wait. Every builder and every E2E run
shared one checkout and one port, so nothing could overlap. These rules make the waiting
disappear.

- **One worktree per builder, from the milestone head.** Each feature or fix-part builder is an
  `Agent` of type `cct:sdlc-feature-builder` with `isolation: "worktree"` and a `Base: <sha>` line in
  its prompt: the milestone head after the supervisor committed its records. A worktree hook
  (the owner's, or Claude Code's default) cuts that worktree from `origin/<default>`, and in one
  go the milestone exists only locally, so the builder's first act is `git reset --hard <sha>`;
  without it a second builder never sees the features already committed. It never checks out
  the milestone branch. The supervisor's worktree holds the milestone branch and is the one
  integrator: it merges builder branches one at a time with the shared policy’s `wt merge`
  command (Git fallback), and never while a close runs. Independent features
  build at the same time. Features that edit the same files run one after another, the second
  cut after the first has merged.
- **The supervisor plans, dispatches, judges and merges.** The session that runs this skill edits
  no code and runs no test suite; the builders and the gate do. Every feature and fix part goes to
  an `cct:sdlc-feature-builder`, never to `general-purpose`, dispatched with `model` and `effort` set to
  `sdlc.json` `builderModel` and `builderEffort` (default `sonnet`, `high`; the agent's own
  frontmatter says the same, so the default changes nothing), or to the pair the plan's
  Approach names for this change. A subagent's result comes back as a file path
  plus a summary of at most about 2k tokens. At most 4 builders run at once.
- **Codex builders (`sdlc.json` `builders: "codex"`).** The same rows go to the Codex CLI
  instead of an agent, one run per worktree, through the kit's `scripts/codex-build.sh`
  (`${CLAUDE_PLUGIN_ROOT}/skills/sdlc-run/scripts/`). Per row: run the stack's install in the
  worktree once (`ciCommands.install`; the sandbox has no network, so nothing installs later),
  write the brief to a file (the feature row, its facts, the worker branch), start
  `codex-build.sh --worktree <wt> --change <id> --brief <file> --model <M> --reasoning <R>` as a
  **background Bash** with `sdlc.json` `builderModel` and `builderEffort` (or the pair the plan's
  Approach names for this change), and watch it with
  `Monitor`. The script waits on Codex, writes `<out>/run.json` (model, reasoning, branch, base,
  pid = process group) and `<out>/result.json`, checks a `done` (the tree changed; no protected
  path, lockfile, manifest or locked test among the changes, else exit 3 `rejected`, left
  uncommitted) and then makes the one commit itself with the subject the result names: the
  sandbox keeps every `.git` read-only, so Codex only edits the tree and never touches history.
  Read its last lines, nothing more, and merge the worker branch into the milestone branch as
  for any builder. `blocked` or `failed` (exit 4) carries the blockers: answer in the brief and
  re-dispatch. To cancel, kill the process group in `run.json` first; the lock in the worktree's
  git dir refuses a second run while one lives. Loopback stays open with the network off
  (checked 2026-11-02), so a Codex builder runs its touched E2E specs in its slot like any
  builder. The milestone close keeps its one `cct:sdlc-feature-builder`, which then runs checks and gate
  only: Claude checks, Codex fix parts, Claude checks and gate again.
- **A builder gets a context pack, not whole files.** The supervisor puts three things in the
  prompt (or in the brief file for Codex): the feature's facts verbatim with their tags, the
  plan excerpt for the feature (its row, the Where-things-go folders, the Rules check and any
  Risks naming it), and the text of every rule ID those facts cite, quoted from the rule files.
  Data-model and contract constraints are quoted, not summarised. The builder opens `plan.md`
  or `facts.md` only for a gap the pack names.
- **Isolate each worktree's E2E resources.** Give its run an app port, stub port, database and
  logs, derived from the worktree path. A repo that hard-codes a port or database name gets
  one env var per value first. Schedule runs under the lock and load policy in
  `../../test-e2e-policy/references/suite-speed-and-reliability.md` section F.
- **Builders never wait on background work.** E2E and long gates run in the foreground with a
  long tool timeout. A builder that parks on its own background job stalls the supervisor and
  the next builder.
- **Fit and width assertions keep slack.** CI's Linux fonts render wider than a Mac. A test that
  asserts text fits its box requires text ≤ 0.9 × the box, or a measured wrap, so a pass on a Mac
  is a pass on CI. Before the milestone PR, where a container runtime exists, run the fit specs
  once in the Playwright Linux image.
- **The milestone review does not wait for the last feature.** Start the Stage 6 review on the
  merged features while the last one builds, and review the last one's diff when it lands. Start
  the full E2E run at the same time as the review, not after it.
- **The fix round runs in parallel parts.** Split the findings by the files they touch, give each
  part its own builder and worktree, and run the parts at once. Don't hold the fix round for an
  E2E result: dispatch the review's findings at once and add an E2E failure to the part that
  owns its files when it arrives.
- **Fixtures belong to the spec.** Every spec makes its own tenant or business unit and deletes
  it after, so parallel runs and later specs never read another spec's rows.

## Stage 6 — Milestone, inside /goal

Scope: `git diff <parent>...milestone/<slug>` only, where `<parent>` is
`origin/project/<slug>` when the project has a branch and `origin/<defaultBranch>` otherwise.
Diffing a project's milestone against the trunk pulls in the sibling milestones already
merged into the project branch, and reviews them again.

Capture real screenshots headless: `agent-browser` CLI first, or Playwright
headless through the repo's E2E setup. This is reproducible, works in CI, and never uses the
person's own browser session. Never use Claude in Chrome or any tool driving that browser.

1. One go: the same goal continues from Stage 5. Feature PRs: start `/goal` with
   `templates/goal/milestone.txt` filled (`goal.milestoneTurns`).
2. Run on the diff, each once and in parallel: `cct:ux-assessment-run`, `cct:review-code-run` (Claude
   and Codex; it reads the repo's `REVIEW.md` when there is one, the only code review the
   change gets, since 3.7.0 nothing reviews in CI),
   `cct:ux-responsive-audit` (the `responsiveTier` matrix, nothing overflows; reflow at
   320 × 640, WCAG 1.4.10 as written, never a 320 × 256 window), the states of
   every changed page, `cct:ux-accessibility-audit`, the full E2E suite once, ×3 only for
   changed and flaky specs. Use the committed `e2e/flaky-specs.txt` list and the selection
   and line-format rules in `../../test-e2e-policy/references/suite-speed-and-reliability.md`
   section G. Send inconsistent results to `test-flake-fix`. Also run `cct:ux-assessment-run` only
   when the change adds a screen,
   `cct:ux-spec-validate build`, the `cct:test-behavior-verifier` and `cct:review-criteria-auditor` agents for job
   stories and facts. `cct:review-security-run` runs only on the goal's last milestone, on the whole
   goal diff (`git diff origin/<defaultBranch>...milestone/<slug>-<last>`), and only when auth, money or
   consent is touched anywhere in it; in a project it waits for Stage 6p. Never on earlier milestones.
   The review starts while the last feature builds, and the full E2E starts with it, not after.
   Require the shared visual pass from each UX run: open every image, including responsive
   and state captures, and validate each issue against the repo's documents with the same
   three verdicts as Stage 5. Include late feature captures before the final check.
   Run `python3 scripts/marks.py init <id>`, then capture every marked and referenced screen
   headless into `verify/shots/`. Match the screen, state and width, including populated fixtures
   and open controls; an admin screen cannot prove a partner-screen fix.
   Open each original/build pair with the image-reading tool and fill every `marks.json` row
   against the owner's words as refined by its ADR. Reuse the shared visual pass and its ledger;
   `marks.json` records the comparison, not a second inspection ledger. Missing states are coverage
   gaps, not inferred passes. A `ruled-out` note needs its ADR, not a screenshot.
2a. **Validation: does each feature do what the plan said?** Separate from the checks, which
   prove the code is sound. For every fact and every ask of this milestone, exercise the
   built app (E2E with the fact's tag, a headless capture of the named screen and state, or
   the `cct:test-behavior-verifier` agent driving the flow) and write one row to
   `changes/<id>/validation.md`: `F<n>/A<n>`, expected (the fact's words), observed (what the
   app did), evidence (test name, shot path, command output), verdict `met`, `not met` or
   `partly`. A `not met` or `partly` row is a blocking finding (the gate blocks on it: `validation-not-met`). `cct:review-criteria-auditor` grades the
   same rows against the code; where it and the observed behaviour disagree, the behaviour
   wins and the row says so. Also list the open `questions.md` rows and the default each took.
2b. **Converge**, after validation and before the findings are final (`references/quality-passes.md`):
   append-only; a ticked box is not evidence. Re-read every fact and ask against the diff and
   `validation.md`; append each `missing`, `partial`, `contradicts` or `unrequested` item, with its
   source ref, as `- [ ] **C<n>**` under `## Converge` in `findings.md`. After the fix round run it
   again; a pass that adds nothing writes `Converged: round <n>`.
3. One `changes/<id>/findings.md`: blocking items first (`- [ ]`, ticked when fixed), advisory
   after under `## Advisory`; the gate treats every other unchecked item as open. Link the visual
   ledgers and checks. A missing or failed visual check is BLOCKED: the review did not run.
   Run `python3 scripts/marks.py check <id>`; open rows are blocking findings.
   A `fixed` row names the passing test tag that proves it in `test` (`@F<n>`); the tag must
   appear in a `testGlobs` file or the check fails.
   Only the engineer's words in `accepted` can accept a non-fixed row; never infer acceptance.
4. One fix round: `cct:review-fix-run 1` (the `1` is `max_iterations`; always pass it) on the blocking items and the converge items only, split into parallel
   parts by the files they touch, one builder and worktree per part; each part's fix is a commit
   on `milestone/<slug>`, never a PR of its own. What is left, or new scope, becomes a change in
   the next milestone. Each fix updates its record: the `validation.md` row re-run and set to
   `met`, the `findings.md` item ticked.
5. Reopen recaptured images and rerun their visual checks. Then
   `python3 scripts/verify_gate.py milestone <id> --visual-check "<checker>" --visual-run "<run>"`
   once, after the fixes, never between them, run by the close builder (`Mode: close`) on a
   head nothing else touches; on `FAIL` use the targeted local failure loop, then the full gate once until `VERIFY PASS` (passed
   checks on an unchanged tree are cached; the third failed run blocks with `reason=attempts`).
   Repeat `--visual-run` for every required current UX run; failures enter
   `verify/report.json` and `report.md` as failed checks. Resolve the checker from the installed
   cct UX skill, never a cross-plugin relative path. Omit visual flags only for explicitly
   recorded UX skips. An older gate without these flags needs `sdlc-run adopt`, not a bypass.
   The milestone gate also runs `marks.py check` as `owner-marks` when sessions or `marks.json`
   exist, independently of `sdlc.json` checks or UX skips. Paste `python3 scripts/marks.py table <id>`
   into the milestone report, including accepted gaps. A file check proves coverage, not pixels.
5. **Enforcement audit**, once, before the gate: `python3 scripts/verify_gate.py audit`
   (read-only; see "Enforcement audit" below). Paste its last line into `validation.md`. A
   `problems` count above 0 is a finding for the fix round, not a gate.
6. Compose the PR body from the repo's template, following [scannable bodies](pr-body.md).
   Validate the proposed body locally before pushing, then the actual body before the gate
   publishes its successful status.
   One push and one PR `milestone/<slug>` → **its parent** (`project/<slug>` when the project
   has a branch, else the default branch) with the report, `validation.md` and `Closes <KEY>`
   for the change's issue, only once the gate passed on that exact head; it merges with a merge
   commit (`gh pr merge <n> --merge --auto`). This push is the milestone branch's first. A
   milestone that `needs` an earlier one opens its PR once that one has merged and this one has
   merged the new parent in (its sync row, run again); an independent milestone opens its PR at
   once. A red CI check: read the exact failed job/test and reason, reproduce locally,
   fix and rerun that test plus the directly affected suite until green, then the full local
   gate once and one batched push. Never rerun the pipeline or push a speculative fix.
   Into a project it is an interior PR:
   no tier, auto-merge armed on green. Into the default branch the tier
   decides. **The engineer accepts the milestone** in one `AskUserQuestion`: "Accept
   (Recommended)" with the one-line reason, or "Hold" with what is left. One go: no dialog;
   auto-merge is armed on green and the engineer reads `validation.md` in the PR. The dialog
   comes only when a Critical or High would be deferred.

### Enforcement audit

`python3 scripts/verify_gate.py audit` answers "is every gate we declared really enforced?". It
changes nothing and keeps four states apart, because a green run proves only the last:

- **installed**: the checker program or script exists; a hook file exists and is executable.
- **configured**: the gate scope that runs it, the CI job (`ci <file>:<job>`) that runs the same
  command, the hook event and matcher in `.claude/settings.json`.
- **executed**: the newest `verify/report.json` (any change, archive included) that ran it; a hook
  leaves no log, so it says so.
- **passed**: that run's status.

`required` is read from the default branch with `gh api` (rulesets, then branch protection): `yes`
(the CI job, or a job a required job `needs`, is a required status), `no`, `local` (no CI job
runs it; `pr-gate.sh` is the only enforcement) or `unknown` (gh or the API unavailable; counted,
never failing). The last line is `AUDIT PASS|FAIL problems=<n> unknown=<m>`; exit 1 for a
missing checker, a check that never ran, a CI-run check that is not required, a hook missing or
not registered. It fails on a fresh adopt until the first gate has run: that is the point.

Run it at `adopt`, at every milestone close (step 5 above) and once a month from CI, so a ruleset
edited by hand or a deleted job shows up before a PR depends on it
(`references/ci-blueprint.md`, "Monthly audit").

## Stage 6p — Project, inside /goal

Only when `decisions.json` has a `project`, and only once its last milestone has merged.

1. **Without a project branch (the default):** every milestone already reached the default
   branch. Re-run `checks.milestone` locally on a fresh checkout of `origin/<defaultBranch>`,
   the whole project as it shipped. The per-milestone reviews each saw one slice; this is the
   first time anything looks at the seams between them. Run `cct:review-security-run` on the same diff when auth, money or consent is touched;
   it is the project's only security review. The gate line goes in the project's
   tracker entry. No PR. Remove the flags that hid unfinished work as the project's last
   change, or record when they go.
2. **With `project.branch: true`:** nothing is pushed to `project/<slug>` directly: every
   milestone merged the default branch in (its sync row), so the project branch carries it.
   Re-run `checks.milestone` on a checkout of `origin/project/<slug>` merged with
   `origin/<defaultBranch>`, then one PR `project/<slug>` → default branch with the gate line
   in its description, merged with a merge commit. This is the PR that gets a tier. If the
   default branch moved after the last sync, merge it in locally once; never rebase it.
3. A blocking finding becomes one more milestone, closed and merged like any other.
4. **The engineer accepts the project** in one `AskUserQuestion`. No second fix round: what is
   left becomes the next project's first change.

## Stage 7 — Outcome and archive

1. Before the PR into the default branch merges, its last commit does
   `git mv changes/<id> changes/archive/<year>/<year-month>/<id>`, sets `archived_at` and reads
   `changes(<id>): archived`: no separate PR after the merge. After it merges: comment the merge
   SHA in the tracker, `ExitWorktree keep`, then remove the owned path using the shared policy’s `wt remove`
   command (Git fallback; a worktree entered by path is never removed by `ExitWorktree`). Move the tracker forward only, never backwards.
2. After release: read the success measure from PostHog (`cct:posthog-manage` or the insight
   named in `intent.md`) and write it in the tracker at once and under `## Outcome` in the
   archived `milestone.md`, committed with the next change's PR, never a PR of its own.
3. A miss starts the next change at 1.3, with the measurement as its first ask.
4. **Reflection**, before the archive move: one short `reflection.md` in the change folder, four
   lines: what surprised us, what the challenge or analyze pass caught (or missed), what we would
   do differently, and one **Lesson** sentence a future agent could act on (or `none`). The agent
   writes it, the engineer may edit it. It is not a report; skip a line rather than pad it.
   When the same lesson appears in two or more archived `reflection.md` files, the agent lists it
   in the milestone message as "repeated lesson, promote?". Only the owner moves it into the repo's
   agent file (`CLAUDE.md` or `AGENTS.md`, its pitfalls section); the agent never edits that file
   for this.
5. **Operational metrics** need no writing: every `verify/report.md` ends with a `## Metrics`
   block (also `metrics` in `report.json`): checks run, cached, passed and failed, retries (earlier
   failed runs of this scope), review rounds, elapsed seconds and open findings. Quote the
   milestone's block in `milestone.md` under `## Outcome` so a slow or retry-heavy change is
   visible later.

## PR bodies and milestone close reports

Read [scannable bodies and the full example](pr-body.md) before writing any feature,
milestone or project PR. Use What → Why → Proof → Before merge (only if open). The milestone report,
validation link, `Closes <KEY>` and exact-head gate results are bold-labelled bullets in
the appropriate sections; preserve each required gate line verbatim inside its bullet.
