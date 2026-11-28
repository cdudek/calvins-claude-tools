---
type: plan
status: in-progress
created: 2026-11-28T19:00
author: Calvin Dudek with Claude
project: factory plugin
supersedes: none
---

# Factory 0.8.0: visible whole-plan goal, status line, board

One PR (owner, 2026-11-28: "do this in one PR, not multiple ones").

## Why

- The owner's brief asked for a run started with `/goal` that finishes unattended. The plugin turned that into headless `claude -p` runs, one milestone per session. Neither was asked for.
- The owner wants to see where things stand: in the session (status line and pane) and across projects (a small background board with a "needs you" column).

## Decisions

- **Run mode.** `/factory:run` never starts a run. It prints one command the owner pastes into a terminal in the repo:
  `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1 claude --model sonnet --effort medium --permission-mode auto --append-system-prompt-file <kickoff> "/goal <condition>"`
  The kickoff goes in as system prompt so it survives compaction. No token, no chain script.
- **Whole plan by default.** The default run is `--all`. A single milestone stays available (`<M>`).
- **Hold under `--all`.** Allowed when the plan has `integration`. Per milestone: verifier PASS on the final SHA, push the milestone branch, merge it with `--no-ff` into the integration branch, push integration, append `HOLD-MERGED <M> <sha>` to the progress log, cut the next milestone from integration. The run ends HOLD after the last milestone, with each milestone's pushed SHA and verifier PASS in the transcript. A hold without `integration` keeps refusing `--all`.
- **Bounds.** The interactive run has no `--max-turns`; the turn clause in the goal is the bound (no spend cap, owner 2026-11-24). `goal-brief.py --headless` keeps the old `claude -p ... --max-turns N` line for the eval harness only.
- **Status contract.** `scripts/factory-status.py` is the one reader. It stores nothing and derives everything from the plan block, the progress log, `.factory/state/*.json` in the repo and its worktrees, and `gh pr list`.
  - `--json [--roots DIR ...]`: every repo under the roots with `changes/*/plan.md`.
  - `--repo DIR --line`: one line for the run in that repo, e.g. `M3a (4/20) · T2/6 building · gap 0/3 · 38m`, empty when nothing runs.
  - Columns: `needs-you`, `building`, `ready`, `backlog`, `done`. A `needs-you` card carries `needs: {kind, text, where}`; kinds: `approve-plan`, `blocked`, `hold-review`, `gallery`, `release-pr`.
- **Mod.** A separate plugin `factory-status` in the cct marketplace: status line plus a pane with the running goal's tasks, refreshed on a timer and at each turn end, by running the status script.
- **Board.** `scripts/factory-board.py`: `serve` (stdlib http.server on 127.0.0.1, read only, auto refresh), `install` (copies both scripts to `~/.factory/bin/`, writes a launchd agent), `uninstall`. A macOS notification when a card enters `needs-you`. No database, no drag and drop, no phone access.

## Steps

- [x] A: run mode (goal-brief, check-plan, SKILL.md, references, kickoff template, eval call site)
- [x] B: factory-status.py and factory-board.py with tests
- [x] C: factory-status mod with validate, tsc and plugin test
- [x] Version 0.8.0, marketplace entry, full suite
- [ ] PR with auto-merge; the install update waits until the running app chain ends
