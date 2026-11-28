# The board and the status reader

`scripts/factory-status.py` is the one reader of factory state. It stores nothing and derives everything from the plan block and progress log in `changes/<slug>/plan.md`, the git-ignored `.factory/state/<M>.json` files in the repo and its worktrees, `git worktree list`, and `gh pr list`. `scripts/factory-board.py` shows its JSON as a small local web page.

## What the board shows
- **Overview (`/`):** "Needs you" first, longest waiting first: kind chip, change title (link to its project page, anchored at the milestone), age, text, where to paste, the exact command with a Copy button. Below, one row per project (most urgent first) with columns Intent, Plan, Ready, Building, Done: counts, at most two change cards per cell and "n more", a dash when empty. On a phone, one card per project.
- **Project page (`/p/<project>/`, `/p/<project>/<slug>`, `/p/<project>/done`):** all needs of the project, a tab per change in stage order (Done collapsed as "Done (n)"), then the selected change (default: the first that needs you, else a building one, else the newest). A building change shows a summary sentence, a strip of milestones, the intent, a "Now" block (failures, question, verifier, tasks, covers, branch), all milestones grouped by layer with filter and expand/collapse, and an aside with Questions, Failures (newest first) and Run (state, last activity, last end state, log lines). Plan, ready, intent and done changes have their own short views. Unknown projects or changes give a 404 page.
- **Stage:** `intent` (an idea with outcomes, no plan), `plan` (written, no `approved: <sha>`), `ready` (approved, nothing started), `building` (any milestone started or running, including blocked and held), `done` (every milestone SHIPPED or HOLD-MERGED). `column` is kept: needs-you, building, ready, backlog, done.
- **Needs you** kinds: `approve-plan`, `blocked` (last entry of a milestone is BLOCKED), `hold-review` (HOLD), `gallery`, `release-pr` (a PR waits for your merge), `question` (an unanswered `QUESTION`, or a `[NEEDS CLARIFICATION: ...]` in delta.md, on a milestone that is not shipped). Each carries the command to paste: `/factory:run <slug>` for approve-plan, blocked and question; `gh browse --branch <branch>` for hold-review (`git log -1 <sha>` when the repo has no GitHub remote); `gh pr view <url> --web` for gallery and release-pr.
- **Honesty:** nothing is invented. A missing value is null in the JSON and the page says "no result recorded" or "not run yet".
- Read only (GET), bound to `127.0.0.1`, Host header checked, refreshes every 15 seconds. A macOS notification fires once for each new needs item (keyed by project, change, kind and milestone).

## Log lines the board reads
The coordinator writes these to the plan's progress log, one per line, in addition to the free-text entries (also in `templates/kickoff.md` and `references/goal-briefing.md`):
```
QUESTION <M> <id>: <text>            owner question raised in the run; id q1, q2, ...
ANSWERED <M> <id>: <answer>          closes that question
VERIFY <M> PASS <sha>
VERIFY <M> FAIL <sha> <req-ids>: <one-line reason>     req ids comma separated
ERROR <M>: <one line>                a failure that stops progress (integrity, gate, crash)
```
A line may start with `HH:MM ` (or a date); without it the entry heading's date and time is used, else the time is null. Lines for a milestone id not in the plan are ignored; a line repeated across plan copies counts once. Failures (FAIL and ERROR) are listed newest, meaning last in the log, first.

## Install
```
python3 plugins/factory/skills/run/scripts/factory-board.py install --dry-run
python3 plugins/factory/skills/run/scripts/factory-board.py install
```
It copies both scripts to `~/.factory/bin/`, writes `~/Library/LaunchAgents/dev.factory.board.plist` (starts at login, restarts on exit, log in `~/.factory/board/board.log`) and prints `http://127.0.0.1:8765/`. Options: `--port`, `--roots DIR ...` (default `~/projects`, depth 3). `uninstall` removes the agent and the plist. Run it in the foreground with `factory-board.py serve`.

## The JSON contract
`factory-status.py --json [--roots DIR ...]`, also served at `/status.json`. Fields below are in addition to the original ones, which are all kept:

```
{"generated": iso, "warnings": [str],
 "projects": [{"repo", "name", "changes": [{
   "slug", "title", "column", "stage", "approved": bool, "approvedSha", "approvedAt", "integration", "doneAt",
   "outcomes": [{"id", "text"}], "requirementCount",
   "milestones": [{"id", "title", "layer", "risky", "requirements": [req-id], "branch", "state",
                   "tasks": [{"id", "state", "title", "model", "effort"}], "gapRound", "gapRounds",
                   "verifier": {"result": "PASS"|"FAIL"|null, "sha", "reqs"}}],
   "current": {"milestone", "milestoneIndex", "milestoneCount", "task", "taskIndex", "taskCount", "gapRound", "gapRounds", "since"} | null,
   "needs": need | null,  "needsAll": [need],
   "questions": [{"id", "milestone", "text", "source": "log"|"delta.md", "open", "at"}],
   "failures": [{"milestone", "text", "sha", "at", "kind": "verify"|"error", "reqs"}],
   "run": {"state": "running"|"stopped"|"idle", "lastActivity", "lastEndState": "SHIPPED"|"HOLD"|"BLOCKED"|"INCOMPLETE"|null, "worktree", "logLines": [str]},
   "prs": [{"number", "url", "title", "state"}] }]}]}
need = {"kind", "text", "cmd", "where", "since", "milestone"}
```
- `stage`: intent, plan, ready, building, done. `column`: needs-you, building, ready, backlog, done. `current` is set for building cards and for blocked or hold cards.
- `needs` is the first item of `needsAll` (null when empty). `where` is a plain sentence, `cmd` the exact command, `since` an iso time or null.
- Milestone `state`: pending, building, incomplete, blocked, hold, merged, shipped. Task `state`: pending, building, done, failed; a failed gap round shows as a task `<M>-gap<n>` after the planned tasks. PR `state`: open, draft.
- Titles come from the plan prose (`### M1 <layer>: <title>` headings, `**T1:** <title>.` bullets), `model` and `effort` from the plan's json; absent means null.
- Times: a log time with a clock is read as local time and written in UTC (`...Z`); a bare date stays `YYYY-MM-DD`.
- A malformed plan or state file adds a line to `warnings` and the run goes on.

`factory-status.py --repo DIR --line` prints `M3a (4/20) · T2/6 building · gap 0/3 · 38m` for the run in that repo (a worktree is fine), and nothing when none runs.

## Limits
- The progress log is free text. The reader takes each entry's first milestone id and last SHIPPED, HOLD, BLOCKED or INCOMPLETE word; keep one milestone per entry.
- Not derived: whether the approved revision still matches the files (`check-plan.py --approved`), a PR that is already merged, deploy state. Without `gh`, release PRs are not seen.
