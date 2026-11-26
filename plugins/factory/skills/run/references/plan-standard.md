# Plan standard (`plan.md`)

A fresh engineer who never saw the conversation can execute it. The person can approve it in five minutes. No runner plumbing.

A bug or small feature uses the same file, with `kind` and one milestone with one task: start from `plan-small-template.md`.

## Sections
1. **Outcome:** one observable sentence, plus the requirement ids it covers, each after an explainer: "guests see only their own comments (req-159)". The check fails a bare id in the plan text up to the json block and in `intent.md`; ids in the json block, fenced code, headings and the progress log are free, but the log reads better with explainers too.
2. **Inputs:** delta revision, design boards, target branch, run command, fast-test commands, and whether the repo deploys on merge (readiness URL) or has deploy disabled; with deploy disabled, SHIPPED is merge plus CI.
   - **Multi-repo change:** the sibling repos' delta and plan paths with their revisions, the merge order (producer before consumer, for example the kit before the apps that pin it), and the version or SHA each consumer pins. The joint change is SHIPPED only when every sibling's merge is confirmed from git or `gh`.
3. **Not in scope.**
4. **Milestones:** in layer order, one PR each.
   - Each has an observable result, a validation command with its expected output, and a recovery path: revert, or a forward fix migration where the repo's policy is forward-only. A down-migration only where the repo allows them.
   - Tasks, requirement ids per task, owned files and what runs in parallel are detailed for every milestone you will run. A milestone you will run later, after a separate approval, gets one line. `--all` needs every milestone detailed.
5. **Risks:** what would hit a user or data, and how we would notice. Name the riskiest step. Name the options rejected and why. The plan review checks both.
6. **Owner decisions:** each with a recommendation.
7. **Turns:** goal turns per milestone session, plus the critical path.
8. **Progress log,** appended by the coordinator only. Entry fields:
   - time, milestone, requirement ids, done and remaining, PR, check result, decision or surprise, next action;
   - `firstPass`: true when every task passed the verifier on its first pass;
   - `planRevisionsAfterApproval`: how many times the plan needed a new approval after the first;
   - `diffMatchesPlan`: true when the milestone's integrity check found no path outside the tasks.
   - State: `SHIPPED`, `HOLD`, `INCOMPLETE` or `BLOCKED`.
   - The first entry records `approved: <sha>`.

Learn tallies the three numbers every five milestones, together with the `STEPS_PER_DISPATCH` re-measure.

## Layers
Milestones run in this order; an empty layer is skipped; the same layer may repeat:
1. `components`: each on a preview page with sample data
2. `layouts`
3. `backend`
4. `screens`: grouped into series of similar screens
5. `rest`: wiring, E2E journeys, docs

## Rules
- **Dependencies:** a milestone depends on all earlier milestones and nothing else. Array order is the only milestone dependency; `needs` on a milestone fails. Tasks inside a milestone never depend on each other, so a cycle cannot be written.
- **Append points:** shared registries (i18n, routes, nav, migrations index) are split earlier, by their own task, into one file per series. No task owns a folder.
- **Parallelism:** start with 2 or 3 builders; add one only while the owner's queue stays flat. A blocker shared by all tasks is fixed once, by one task.
- **Checks:** every check fails on the base. No `|| true`. The last milestone proves the outcome sentence end to end.
- **Own tests stay green:** a milestone that removes a route moves or deletes its tests in that milestone, and lists them in the `allowTestEdits` of the task that does it.
- **Isolation:** each worktree gets its own app instance, port and test data.
- **Approved means frozen:** after the approval, the json block, `intent.md` and `delta.md` do not change. Any change needs a new approval and a new SHA. Only the progress log is free.
- **Drift:** if the work departs from the plan, the person approves a new revision first. Scope growth goes into the intent and delta first.
- **Who can see what:** a milestone that touches auth, money, consent or data lists every place the actor can see it (see `surface`).
- **E2E:** only critical and highly important journeys. No per-button or per-label E2E.

## Graph block
End the plan body (before the progress log) with one fenced block whose info string is `json cfactory`. `scripts/check-plan.py` reads the first one.

```json cfactory
{"change": "2026-11-24-saved-searches", "base": "main", "goalTurns": 12,
 "setup": "npm ci", "preflight": ["command -v npm"], "deployOnMerge": false,
 "requirements": ["req-1", "req-2"],
 "milestones": [
   {"id": "M1", "layer": "components", "covers": ["req-1"],
    "tasks": [{"id": "T1", "covers": ["req-1"], "files": ["src/ui/Chip.tsx"], "check": "npm test -- Chip", "needs": [], "allowTestEdits": ["src/ui/old-chip.test.tsx"]}]},
   {"id": "M2", "layer": "backend", "covers": ["req-2"], "risky": true,
    "surface": [{"exposure": "GET /api/saved-searches", "requirement": "req-2", "scenario": "scenario-2 another user sees none"},
                {"exposure": "weekly digest mail", "requirement": "req-2", "deferred": {"reason": "no digest exists yet", "probe": "rg -n digest src/ shows no match"}}],
    "deferred": [{"item": "sharing", "reason": "out of appetite", "probe": "rg -n share src/ shows no route"}]}]}
```

### Plan keys
- `change`: the dated slug, `YYYY-MM-DD-words`. `base`: the target branch.
- `goalTurns`: goal-loop turns per milestone session (a turn ends each time Claude stops and the evaluator checks; one turn holds many tool steps). It goes into the goal line's INCOMPLETE clause (the soft breaker). The hard breaker, `--max-turns`, is computed by goal-brief.py from the milestone's tasks (formula in goal-briefing.md); the plan never sets it. There is no spend cap.
- `kind` (optional): `"bug"` or `"feature"`. Both need exactly one milestone with one task and at most 3 requirements. `bug` turns on the two-commit flow.
- `merge` (optional): `"auto"` (default) arms auto-merge on the PR; `"owner"` never does, and the run ends `SHIPPED` with the merge-ready PR URL and its CI conclusion (with `integration`, this applies to the release PR only). Use `"owner"` when intake found no merge gate.
- `integration` (optional): a branch name other than `base`. Milestone PRs target it and merge on their own after fast checks, test-integrity and the verifier, with no remote CI required there. One release PR from it into `base` runs the full required CI and is the only PR that needs the merge gate.
- `deployOnMerge` (optional, default false): the repo deploys when the release PR merges. With a risky milestone it makes the release PR wait for a human; the run ends `SHIPPED` with the merge-ready URL.
- `hold` (optional): an owner action known in advance, for example `"owner restores GitHub billing on the account"`. Ship becomes push-only: no PR. The run ends `HOLD` with the pushed SHA and a verifier PASS for it.
- `setup` (optional): a command run in every new task worktree, for example `"npm ci"`.
- `preflight` (optional): commands that prove tools and credentials exist, and never print secrets: `"command -v squawk"`, `"gcloud auth print-access-token >/dev/null"`. They run at approval and as the first step of the kickoff. Not the task checks: those are meant to fail first.
- `layer`: `components`, `layouts`, `backend`, `screens` or `rest`.
- `risky` (milestone, optional): `true` when it touches auth, money, consent or data; adds a security review by an Opus 5.5 high advisory agent or the Codex `gpt-6.2-astra` pass. A risky milestone needs `surface`.
- `surface` (milestone, required when `risky`): every place an actor can see the data, from the sweep of the base: routes and pages, lists, notifications, mail, queues, role changes (member to guest). Each entry is `{exposure, requirement, scenario}` or `{exposure, requirement, deferred: {reason, probe}}`. `requirement` is a requirement this milestone covers.
- `deferred` (milestone, optional): `{item, reason, probe}`. `probe` is the command you ran and what it showed. A reason written as a fact without a probe fails.
- `effort` (task, optional): `low` for mechanical code or text replacement, `high` for complex work, default `medium`. The builder runs on Sonnet 5.5 at this effort.
- `model` (task, optional): `haiku`, `sonnet` or `opus`, default `sonnet`. The builder dispatch passes it with `effort`. `scripts/size-tasks.py` sets both from the rules in SKILL.md.
- `verifier` (milestone, optional): `{"model": "sonnet" | "opus", "effort": "medium" | "high"}`, default Opus 5.5 high. The verifier dispatch passes it. Security review of a risky milestone is not affected.
- `allowTestEdits` (task, optional): existing test files this task edits, nothing else. A top-level `allowTestEdits` fails. `test-integrity.sh` reads it per task.
- Milestone `tasks` only on detailed milestones. When present, their `covers` union equals the milestone's `covers`, and every `check` is non-empty.
- Task `needs` is a list and references tasks of earlier milestones only. Milestone ids are unique. A milestone has no `needs`.
- `files` are disjoint within a milestone. Task files are required once a milestone is detailed.
- Requirement ids are `req-<n>`, unique across the repo (`references/spec-standard.md`, "Ids and explainers"). The old `<spec>/R<n>`, `I<n>` and `C<n>` forms fail with a pointer to `migrate-ids.py`.
- Every requirement is covered by at least one milestone; every `covers` id exists in `requirements`. The plan's `requirements` equal the delta's ADDED, MODIFIED and REMOVED ids. A REMOVED id is covered by a task like any other: the task proves the old behaviour is gone.
