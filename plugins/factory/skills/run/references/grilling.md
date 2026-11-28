# Grilling

The first step of every change, every size. The goal: no decision is left for the run to stop on.

Use `mattpocock-skills:grilling` when it is installed. Otherwise use this method. The result is the same: answers written into `intent.md`.

## Method
- Rounds of at most 5 numbered questions.
- Every question has a recommended answer. The person can say "yes" or change it.
- Start from what the person brings: an idea, a journey or screen, or a bug.
- Facts are looked up by subagents (code, routes, specs, tools, billing state). Never ask the person what a subagent can read.
- Write the answers into `intent.md` after each round, as `- outcome-1: ...` and `- constraint-1: ...`.
- Name an id in a question only after an explainer: "who sees invite mail (req-159)?", never a bare id.
- Keep going until no decision is open. Then write delta, scenarios and plan.
- Nothing may stay as `[NEEDS CLARIFICATION]`. A question the person cannot answer yet is resolved before approval.

## The tree
Walk every branch. Skip one only when a subagent shows it does not apply.

1. **Outcome and size.** What must be true after? A bug, a small feature, a milestone or a project? How many milestones fit the appetite?
2. **Who can see what.** For every actor and role: each page, list, notification, mail and queued job that can show the data. Include role changes (member to guest) and mail already queued. This becomes `surface` and the scenarios. On a milestone with access or privacy requirements also ask which files and tests a late finding may touch, seeded from the files the `guards` check lists; that becomes `mayTouch`, the owner's pre-approved gap rounds (`gapRounds`, default 3). For every access, privacy or billing requirement, ask which data is guarded and how the code reads it, and write that as `guards`: patterns for the query call (generic form: `(from|join)\(orders\b`), not the bare name, which matches comments and tests. The plan check greps the repo for each and fails on any source file nobody owns. Then write the access `rule` in one sentence, covering role changes and moves between teams or scopes, and plan one `ruleTest` task that tests it on every read path.
3. **Clause coverage.** Every clause of every requirement maps to a task and a test: each actor, each "shall", each "and/or" branch, each named surface (menu, API, mail). The plan's requirement-to-proof mapping lists clauses, not only requirement ids. A clause with no task or no test is a decision still open.
4. **Test edits.** Which existing tests will this change break on purpose? A subagent greps unit tests and E2E specs for every behaviour the delta changes or removes. Name each file and the task that edits it, and how that task's check runs it (an E2E spec needs an E2E command in the check and its tools in `preflight`). This becomes `allowTestEdits`. An edited test keeps or gains the negative assertion the new rule implies.
5. **Deferrals.** What is left out for later? For each: run the command that proves the reason, and write what it showed. This becomes `deferred` with a `probe` (numbered `deferred-<n>` in prose).
6. **Merge and production.** Does a human merge? Does a merge deploy? Is there an integration branch? A risky milestone or a deploy on merge means the release PR waits for a human, and the run ends at a merge-ready PR.
7. **Holds.** Is an owner action already known (billing, access, a key)? This becomes `hold`: the run pushes and opens no PR.
8. **Design boards (UI).** Which boards? Each (`board-<n>`) is a screen in this change or dropped. The person approves the boards now. There is no later gallery stop.
9. **Preflight tools.** Which tools and logins must exist (linters, cloud login, CLIs)? Check them now. This becomes `preflight`.
10. **Test tiers.** Which tests guard repo-wide invariants (schema, migrations, architecture, config), and on which paths? Draft `tests` from the manifests and CI first and ask only what they leave open: the `related` command, the `triggers` with their paths and `why`, which existing test files must grow when those paths change (the trigger's `edits`, e.g. a table list or fixture), the full `suites` and which need `lock`.
11. **Setup.** What must run in every new worktree (`npm ci`)? This becomes `setup`.
12. **Scenarios.** Which journeys end to end? Each scenario (`scenario-<n>`) names the first milestone that can run it.

## Learn: questions added from BLOCKED runs
Every BLOCKED that grilling could have prevented becomes a new question here, with the date and the run. Keep each to one line.

- 2026-11-24, a beta milestone: "Which places can a guest see this data?" (five leaks were found after the build, not before).
- 2026-11-24, a beta milestone: "Which tools and logins does a migration check need?" (SQUAWK and a cloud login were found mid-run).
- 2026-11-24, a beta milestone: "Is billing or another owner action blocking the merge?" (a hold was hand-written into the kickoff).
- 2026-11-25, a beta milestone: "Which existing tests and E2E specs assert what the delta changes?" (six guest E2E specs still expected the old visibility; the verifier found them after the build).
