# Factory eval

Measures which factory configuration to make the default: cost, time and quality per arm, on replayed tasks. Python 3 stdlib plus matplotlib. Task data and results are private and live in `~/.factory/eval/`, never in a repo.

## What it measures
- **Quality (`hidden_frac`)** is the same fixed grading for every arm, never the arm's own verifier: the tests the task's reference commit added or changed (copied into the result tree after the run). `hidden_frac` is the share of `fail_to_pass` files that pass (all hidden files when `task.json` has no such list; `grade.json` says which in `hidden_basis`), so a hidden file that already passes at the start commit gives a do-nothing arm no credit. The repo's existing suite and the `pass_to_pass_hidden` files must still pass, otherwise `regression`. Prose scenarios, graded by one blind grader (default Codex `gpt-6.2-astra`, read-only; `--grader opus` is the alternative), are a separate optional `scenario_frac` (null without eval-only scenarios). `solved` means `hidden_frac == 1` and no regression.
- **Implementation-coupled:** a hidden test that imports names the plan, delta and ticket never give can only pass when a builder guesses the reference's names. `check_coupled.py <task dirs>` lists them (it follows `export * from`); add each to `task.json` `implementation_coupled`, where it runs and is reported but never scored.
- **Out of scope:** a hidden test for a real bug next to the ticket that the ticket never asks for goes in `task.json` `out_of_scope` (with `out_of_scope_why`). It runs and is reported as `outside_fixed`, never in `hidden_frac`, `solved` or the false-pass counts: a run is not failed for skipping work nobody asked for. `rescore.py <task dir> <run dirs>` re-keys already graded runs after a list changes, without rerunning tests.
- **Approved gap scope:** task.json `may_touch` lists the globs written into the replay milestone as `mayTouch`, so a gap inside them gets a fix round instead of `BLOCKED`. Without it every gap a replay finds ends the run, and the hidden tests score an unmerged build.
- **Codex arms:** a run whose builder or reviewer is Codex gets a `Bash(codex exec *)` allow rule, because auto mode's classifier denies sending the diff to an outside service.
- **Cost, tokens, time** from `stream.jsonl`, split per model and per role (subagent usage is attributed through `parent_tool_use_id` to the dispatching Agent call). Time is reported raw and adjusted for parallel load.
- **Guards**: unverified exit, regressions, integrity violations (the factory's `test-integrity.sh` on the result), visible-versus-hidden gap, verifier false-pass, goal met but task not solved, files outside the plan, unexpected models.
- **Every run is a goal run**: `claude -p ... "/goal <condition>"`, the plain single-agent arm included. `grade.py` marks a run INVALID when the stream shows no goal set or no goal evaluation; INVALID and infrastructure runs are excluded from every statistic and listed.

## Stages
| Stage | Arms | Purpose |
|---|---|---|
| `0` | `default` x3 | variance, grader proof, smoke checks (below) |
| `grid` | `grid_<haiku,sonnet,opus>_<low,medium,high>` x3 | builder model x effort, builder-only: the arm's verifier and security review are off, coordinator fixed Sonnet medium |
| `1` | `pb1`..`pb8` (Plackett-Burman, 7 factors), `plain_sonnet`, `plain_opus`, `codex_builder`, `ablate_*`, `enforce_prompt` | screen the levers |
| `2` | `default` plus the finalists by name | confirm, 8 runs each |
| `3` | `always_cheap` (Haiku builder), `default`, `always_strong`, `cascade` | routing on extra tasks |

Plackett-Burman factors, default level first: A verifier model Opus/Sonnet, B builder effort medium/high, C advisor off/Opus, D context spec/raw ticket, E parallel builders 3/1, F reviewer Opus/Codex astra, G verifier effort high/medium. Arms are data in `configs.py`.

## Prepare a task
```bash
python3 prepare_task.py <repo> --start <sha> --reference <sha> --task-id <id> --plan changes/<slug>/plan.md \
  --out ~/.factory/eval/tasks/<name> --suite-cmd "<fast suite>" --e2e-cmd "<e2e>" --setup "<install>" \
  --scenarios <folder of prose scenarios> --intent-from-outcome
```
It writes the start tree as a tarball without history (plan progress entries dated after the start commit are stripped), the hidden tests, the reference diff stat and `task.json`. Optional: `--env NAME=TEMPLATE` (repeatable; exported into every arm and the grading run, templates may use `{db}`, `{port}`, `{run}`, e.g. `TEST_DATABASE_URL=postgres://user@127.0.0.1:5433/{db}`; shown by `--dry-run`), `--exclude-glob G` (repeatable; leaves large non-code assets such as evidence images out of `start.tar.gz`), `--prove` (runs the hidden command per hidden file on the start tree and records `fail_to_pass` and `pass_to_pass_hidden` in `task.json`) or `--fail-to-pass FILE...` / `--pass-to-pass-hidden FILE...` (the same lists, for tasks proven elsewhere), `--verifier-scenarios` (what the arm's own verifier may read), `--ticket-delta` (the raw-ticket delta, needed by arms with context `raw`), `--hidden-cmd` (`{files}` is replaced), `--port-env/--port-range` and `--db-name/--db-env/--db-create/--db-drop` (per-run port and database). `--intent-from-outcome` writes a minimal `intent.md` and runs the factory's `migrate-ids.py` on the tree. A plan written before the readable-id scheme may still need shimming (bare ids in prose, citations, a per-task `allowTestEdits`, the risky milestone surface); run `check-plan.py` on the start tree and its output says what. A plan without `hold` gets one at run time: eval repos have a local bare origin and no pull requests, so runs end `HOLD`.

## Run
```bash
python3 run_eval.py --task ~/.factory/eval/tasks/<name> --stage grid --repeats 3 --parallel 3 --dry-run
python3 run_eval.py --task ~/.factory/eval/tasks/<name> --stage grid --repeats 3 --parallel 3
python3 grade.py ~/.factory/eval/results/grid/<run-id>
python3 analyze.py ~/.factory/eval/results/grid
python3 plot.py ~/.factory/eval/results/grid
```
`grade.py` runs once per run. `plot.py` writes `plots/` and `report.html`, local only.
- **Auth**: if `CLAUDE_CODE_OAUTH_TOKEN` (from `claude setup-token`) is in the environment it is used and never printed or stored. Otherwise all runs share the one logged-in config dir `~/.factory/eval/claude-config` (log in there once); each run still gets its own `--settings` and plugin copy, but history and todos are shared across runs in that mode.
- **Isolation**: a unique directory per run, one commit, no history, factory plugin copied from a pinned commit with each agent's model and effort written into its frontmatter. The coordinator's model and effort are `--model` and `--effort`; `CLAUDE_CODE_EFFORT_LEVEL` is never set. `ANTHROPIC_DEFAULT_HAIKU_MODEL` must be unset (the runner refuses otherwise): it re-points the goal evaluator and the `haiku` alias for every arm. Managed policy files cannot be removed by a clean config dir; they are the same for every arm.
- **Parallel**: `--parallel N` (default 3), arms land on random free slots. Each run has its own directory, database (`dbName` template) and port block. Heavy steps share one lock, `~/.factory/eval/heavy.lock`: runs call `heavy <cmd>` for E2E, full test runs and app servers, and `grade.py` takes the same lock. Each run records `slot` and `concurrent_at_start`; `analyze.py` computes the mean parallel load over every run's interval and reports time raw and load-adjusted.
- **Infrastructure**: rate-limit, auth and unreachable-API stops set `infra_failure` and `rerun` in `run.json`; rerun them with the same command and arm list, they are never dropped silently. A timeout is a failure.
- A cascade arm runs its tiers in turn, escalating when a tier does not end `SHIPPED` or `HOLD`; `analyze.py` folds the tiers into one row with the summed cost.

## Stage 0 checks (before spending the rest)
- The grader passes on the reference commit and fails on the start commit; measure the hidden-test flake rate (grading reruns failing hidden files 3 times).
- The stream carries no goal verdict events, only the synthetic message `Goal set: <condition>`. So `grade.py` marks a run INVALID without it, and counts the goal as evaluated when Haiku usage in `modelUsage` exceeds what the stream's own Haiku messages show (the evaluator call, probed 2026-11). `goal_met` is `terminal_reason == completed`, no error, and a last-message end state (`goal_met_source` says so). A run that errored before its first turn ended is flagged `infra_suspect`, not judged on the goal.
- The evaluator's spend is in `total_cost_usd` and `modelUsage`, not in per-message usage. `grade.json` records it as `goal_evaluator_cost` and `cost_by_role.goal_evaluator`, and keeps the Haiku line as `haiku_usage`. With Haiku builder arms it stays separable only because builder messages are in the stream; check it once.
- `subagent_stats` from the result is recorded (`subagents_started_in_background`, `subagents_killed`, failed, refused). A killed or backgrounded subagent sets `harness_violation`; `analyze.py` lists those runs.
- Advisor calls show up (`--advisor`), every subagent's model and effort match its arm, the planner splits the task into at least 2 builder tasks (otherwise factor E is inert), the raw-ticket arm runs.
- `--max-turns` counts coordinator turns only; subagent turns are recorded separately.

## Plots (`plots/`, embedded in `report.html`)
01 cost vs `hidden_frac` with the front, interval crosses and time as size: which arm to pick. 02 cost per solved task. 03 cost per role: where the money goes. 04 time ECDFs: tails. 05 pass^k: reliability. 06 forest against the default with the equivalence band (+-10% cost, +-5 min, +-0.05 `hidden_frac`). 07 screening main effects. 08 verifier and goal-evaluator confusion matrices: false passes. 09 failure taxonomy. 10 routing: policies against the per-task oracle, regret. 11 cache hit vs cost: confound check.

## Tests
`python3 -m pytest -q -p no:cacheprovider tools/factory-eval`, also run by `scripts/run-plugin-tests.sh`. Fixtures are synthetic: a tiny git repo and fake streams. No test calls a model.
