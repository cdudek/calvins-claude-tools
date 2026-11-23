---
name: sdlc-run
description: >-
  Runs an AI-native SDLC across one or more repos with nothing installed in them: one plan and a
  machine-checked contract, one owner approval, then builders in worktrees, an independent
  verifier, milestones merged locally and one PR per repo. Use when someone starts or continues a
  feature, bug fix, refactor, docs change or multi-repo project, asks how work moves here, or says
  "run sdlc", "sdlc status", "sdlc check", "sdlc clean". Subcommands: plan, check, status, resume,
  stop, clean.
allowed-tools: "Read Grep Glob Edit Write Agent Skill AskUserQuestion Bash(python3 */sdlc-run/runner/sdlc.py *) Bash(git *) Bash(gh *) Bash(plannotator *) Bash(wt *) EnterWorktree"
user_invocable: true
metadata:
  version: 4.0.0
  author: calvindudek
effort: high
---

# sdlc-run 4: one approval, a checked contract, nothing installed

Verification and every push follow the [local-first contract](references/local-first.md); read it before running checks or preparing a push.

Read the [shared worktree policy](../../references/worktree-usage.md) for every lifecycle operation; the runner makes its own worktrees under `<repo>/.worktrees/` and keeps them out of the tracked tree. The runner has a preflight for tools, credentials and browsers (`sdlc plan` prints it).

The owner approves what will change and how it is proven. The runner builds across every named repo, verifies the result and prepares the PRs. The owner's next action is a merge. Product repos get no SDLC config, scripts, hooks, workflow or records folder: the plugin carries everything. Design: `docs/designs/2026-11-23-sdlc-greenfield.md`.

`sdlc` below is `python3 ${CLAUDE_SKILL_DIR}/runner/sdlc.py`. Records live in `~/.sdlc/runs/<run-id>/` and are never committed. The run ID is `<date>-<start repo>-<slug>`; every repo works on branch `sdlc/<run-id>`; `~/.sdlc/active/` holds a link per live run. Plugin hooks stop agents writing under `~/.sdlc/runs/`: only the runner does.

The user input is: $ARGUMENTS

| Input | Do |
|---|---|
| `<title>` or a ticket | Plan a run (below). |
| `check [<id>]` | `sdlc check`: read-only completion test. Exit 0 `READY`, 1 `FAIL`, 2 `BLOCKED` or `STOPPED`, 3 `PENDING`. One status line. |
| `status` · `list` | `sdlc status` (run from any repo on an `sdlc/` branch) · `sdlc list`. |
| `resume <id>` | `sdlc resume`: same machine; keeps counters; interrupted work is requeued and checks run again. |
| `stop <id>` | `sdlc stop`: durable; cancels job process groups; `sdlc gate <id> restart` clears it. |
| `clean <repo> [--apply]` | Remove 3.x copies. Dry run lists exact matches, edited copies, fragments, unknown files; `--apply` prepares a cleanup branch. |
| empty | `sdlc status`. |

## The run

1. **Plan.** `sdlc plan <repo>... --slug <slug>` discovers commands from each repo's own instructions, manifests and CI, probes tools, credentials, browsers and CI jobs, creates `sdlc/<run-id>` in each repo and writes drafts. Write the plan, `contract.json` and `tasks.json` in a scratch folder and ingest them with `sdlc draft <id> --plan .. --contract .. --tasks .. --input <repo>:<path>=<file> --dep <repo>:<path>=<file>`. The contract has one row per required check (`id`, `repo`, `milestone`, `runner` argv, `expect.kind` of `pass`, `fails_on_base` or `negative_control`, `pins`, `prereqs`, `site`, `consumes`), plus `limits`, `edges` (producer, consumer, pack, release, pin) and `deps`. Task graphs list `needs`; a cycle is a planning error. One fresh reviewer reports blockers; one correction round; open blockers stay visible.
2. **One approval.** `sdlc gate <id> --by <name>` writes the screen (plan, actual checks with expected values, the real manifest and lockfile diff, destinations, caps), runs `plannotator annotate <file> --gate --json` (found by absolute path at a known install location, in a scrubbed environment; the owner decides) and only on `{"decision":"approved"}` approves in the same process: no marker file exists. It refuses to run when HOME, PATH or PYTHON* are changed. Approval refuses a second time, an uncovered milestone or task (a check, or a named waiver) and a missing `limits.max_dispatches`. `sdlc gate <id> restart` is the only restart. Nothing is asked mid-run except a real `BLOCKED`. Models are named only in the kickoff and passed to the live role invocation, never stored in a file, record or PR.
3. **Build.** Loop: `sdlc next` lists ready tasks (up to 8 at once, fewer when the graph or owned paths allow; the kickoff can change the cap). For each: `sdlc dispatch <id> <task>` counts the dispatch durably, cuts a worktree at the integration SHA and writes a brief. Launch `cct:sdlc-task-builder` with the brief path (no `isolation: "worktree"`: the runner made the worktree). Then `sdlc submit` (tamper check: pinned specs, test and CI config, skips, removed assertions, unapproved manifests), `sdlc verify --task` through `cct:sdlc-task-verifier` (a fresh subagent that sees no builder transcript), `sdlc integrate`. A fix is a new dispatch of the same task: one build and two fixes at most.
4. **Close a milestone.** `sdlc milestone <id> <m>` runs its due contract items and the repo's full local gate on the integrated head; on pass it merges into `sdlc/<run-id>` locally, no PR. Failure: fix and rerun on the new head.
5. **Finish.** `sdlc final <id>` runs the whole contract on the final heads. Multi-repo: `sdlc pack` the producer, build the consumer against it, push and merge the producer first (`sdlc pr`), then `sdlc publish` validates the published artifact against the packed one and applies the approved pin; the consumer contract and gate rerun on the new head. `sdlc push <repo>`, `sdlc pr <repo> [--auto-merge]` (auto-merge only where the repo allows it). `sdlc check` is the completion test; `/goal` is optional and must call it explicitly.

**FAIL vs BLOCKED.** A real mismatch is `FAIL`. A missing tool, browser, credential or runtime, zero collected tests, or a check that passes on the base is `BLOCKED`, naming the prerequisite. A pass is bound to the commit it ran on, to the approved bundle and to the pinned inputs; a later integration makes it stale. Agents cannot write `passes`: receipts are written by the runner from the exit status of the process it ran, and the plugin hook that keeps agents out of `~/.sdlc/runs/` (read and write) is the barrier: there is no signature. Caps (`BLOCKED cap`), a graph deadlock (`BLOCKED deadlock`, naming the cycle) and an unapproved irreversible action end the attempt with the precise unmet condition. A check that cannot run is never waived by a worker.

## UI and UX verification

Contract rows are measured from a pinned design source (computed style and geometry, resolved tokens), on the real surface: web, Chrome extension or Electron, with keyboard and accessibility assertions. A bitmap cannot establish a token or padding: it is listed as unsupported before approval and never becomes a measured fact. Screenshots are diagnostic evidence only; there are no baselines and no image approval. See [design inputs](references/design-inputs.md) and `runner/board.py`.

## Reuse and legacy

`runner/e2e-repeat.sh` runs changed and flaky E2E specs three times. The 3.x code is gone from this skill: only the shipped-hash list (`runner/kit/kit-hashes.json`) and the template text under `templates/` remain, as evidence for `sdlc clean` (and the shared Decision4 and CI assets other skills read). A repo mid-run on 3.x finishes with the copies it already has. [Changelog and migration](references/changelog.md).
