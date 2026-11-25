# Goal briefing: three separate pieces

`.cfactory/goal-brief.py changes/<slug>/plan.md <M> --approved <sha>` writes all of it from the approved plan. Never hand-write a goal line. `<sha>` is the commit the person approved.

| Piece | Holds | Never holds |
|---|---|---|
| `plan.md` | scope, requirement-to-proof mapping, milestones, risks, progress log | chat history, standing policy |
| `kickoff-<M>.md` | how to run this milestone: preflight, worktree commands per task, owned files, checks, verify order, PR, progress entry, when to stop | the end state |
| `/goal` line | the end states first, the proof in the transcript, a turn clause | process text: steps, who builds what, style |
| `test-integrity.sh` (exit code) | zero-exception rules: builders cannot change existing tests, CI or spec; every path stays inside its task | anything with exceptions |
| `--max-turns` (print mode) | the hard circuit breaker, computed by goal-brief.py; no spend cap | |
| Turn clause in the goal | the soft breaker: the run itself ends INCOMPLETE | |
| CI and branch protection | the merge | |

Why the goal line stays short: after every turn a small model judges it against what the conversation shows. It does not run commands or read files. Every process clause is one more thing it can misjudge.

## The goal line
It starts "Met when any one of these is true." and lists numbered end states, in this order:
1. **SHIPPED:** the PR number, its merge SHA (or the merge-ready URL), and verifier evidence for the requirement ids (`req-<n>`, listed bare in the goal line, which is a machine place). With a `hold` this is **HOLD:** instead: the last message starts with HOLD: and the transcript shows the pushed SHA of the milestone branch and a verifier PASS for that same SHA. Order: commit the progress entry, gallery and spec changes first, run the verifier on that final SHA, then push that same SHA.
2. **BLOCKED:** the last message starts with BLOCKED: and names the decision or action the owner must take, whatever the build state. With a `hold`, a BLOCKED that only names the hold does not count: the hold can end only the HOLD state.
3. **INCOMPLETE:** after `goalTurns` turns, the last message starts with INCOMPLETE and names the next step.

## Starting the run
- **Where:** the milestone worktree on `milestone/<slug>-<M>`, cut from a base that already holds the approved plan (or on milestone 1's branch where the plan lives there).
- **One milestone:** `goal-brief.py <plan.md> <M> --approved <sha>`.
- **Whole plan:** `goal-brief.py <plan.md> --all --approved <sha>`. Every milestone must already have tasks. It prints one kickoff and one goal. The coordinator runs the milestones in order and, at each milestone start, re-reads the pinned plan and the progress log. `--max-turns` is the sum of each milestone's own value.
- **Unattended (default):** `/factory:run <slug>` starts the RUN command the script prints in the background and reports the end state. `claude -p` runs the goal loop to completion in one call; the kickoff goes in through `--append-system-prompt`, the goal is the prompt, and the turn clause in the goal is the bound. A person can still paste the RUN command, or the kickoff and the `/goal` line, by hand.
- **Interactive:** start `claude`, paste the kickoff file, then paste the `/goal` line. The same turn clause bounds it.
- **No stop for a gallery.** The ux-verifier checks UI milestones against the boards approved at the single approval, and writes `evidence/<M>/gallery.md`. The person reviews the gallery once, from the release PR.
- **After BLOCKED or INCOMPLETE:** fix the cause, then run the same command again in a fresh session. The kickoff's resume rule reads the progress log and git state first.

## Merge rules
- **With `integration`:** milestone PRs merge into it on their own, after fast checks, test-integrity and the verifier. No remote CI is required there.
- **The release PR** (integration into base) waits for a human only when a milestone is `risky` or `deployOnMerge` is true. The run then ends `SHIPPED` with the merge-ready release PR URL. Otherwise it merges on its own after required CI.
- **Paid repos (Actions minutes cost money):** a multi-milestone change always sets `integration`; the human merge decision applies only to the release PR.
- **Without `integration`:** `merge: auto` arms auto-merge; `merge: owner` never does, and the run ends the same way, at SHIPPED with the merge-ready PR URL.
- **With a `hold`:** no PR is opened and nothing merges. The branch is pushed once.

## Bug flow (`kind: bug`)
1. The builder's first commit holds only the failing test.
2. The coordinator shows it fails on the base and records that commit SHA.
3. The fix pass runs `test-integrity.sh ... --pin <that sha>`: the test file must keep the same blob.

## Facts the design rests on (code.claude.com/docs/en/goal, checked 2026-11-24)
- The evaluator runs when a turn ends and sees the condition and the conversation; it calls no tools.
- A goal ends when the evaluator says met, on `/goal clear`, on an unrecoverable error, or Ctrl+C in print mode. There is no built-in turn or token cap: bound it with a turn clause in the condition.
- While a subagent or background shell runs at turn end, the evaluation is skipped. Builders and `gh pr checks --watch` run in the foreground.
- If Claude makes no tool use for several turns, the loop stops with the goal still set.
- `--resume` and `--continue` restore an active goal but reset its turn count, timer and spend baseline. Met or cleared goals are not restored.
- The condition can be up to 4,000 characters; the script refuses longer and the generated lines are about 400.
- `--max-turns` counts the coordinator's own tool turns, not goal turns and not subagent steps. A probe with `--max-turns 3` and six one-call steps stopped with `error_max_turns` after 4; a probe with `--max-turns 4` whose one subagent made 8 tool calls ended `success` at 2 turns (both 2026-11-24). The owner rejected a spend cap (`--max-budget-usd`, 2026-11-24).

## The circuit breaker, as math
`goal-brief.py` prints `--max-turns = SAFETY x STEPS_PER_DISPATCH x D`, where D is the worst-case number of agent dispatches the kickoff allows:

- `D = tasks x 3 + 3 + risky + ui`. Every task uses all 3 builder passes, the verifier runs once per pass, then one security review on a risky milestone and one UX verifier on a UI milestone.
- `STEPS_PER_DISPATCH = 10`, measured on a first beta milestone (2026-11-24): 148 coordinator tool calls for 15 dispatches (brief, integrity check, merge, fast checks, progress log).
- `SAFETY = 2`: a run that spends every allowed pass ends at about half the cap, while a coordinator looping on one step hits it.
- `--all`: the sum of each milestone's value.
- Examples: the template M1 (3 tasks, UI) gives 260. A real M1 (5 tasks, risky) gives 380; it used 148 across two sessions with all of T5's passes spent. A small change (one task) gives 120.
- Re-measure `STEPS_PER_DISPATCH` after five milestones, with the progress-log tally (`firstPass`, `planRevisionsAfterApproval`, `diffMatchesPlan`). Raise it only when a healthy run hit the cap.

## Rules
- One milestone per goal and per fresh session, except `--all`, which runs the milestones in order under one goal.
- Run in auto mode with routine actions allowlisted in the user `autoMode` settings. Auto mode asks after three blocks in a row, which stalls an unattended run.
- Auth failure, exhausted credit or context overflow clears the goal. The progress log is the source of truth for resuming.
