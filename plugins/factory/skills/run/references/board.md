# The board and the status reader

`scripts/factory-status.py` is the one reader of factory state. It stores nothing and derives everything from the plan block and progress log in `changes/<slug>/plan.md`, the git-ignored `.factory/state/<M>.json` files in the repo and its worktrees, `git worktree list`, and `gh pr list`. `scripts/factory-board.py` shows its JSON as a small local web page.

## What the board shows
- **Columns:** needs you, building, ready, backlog, done. One card per change: project, title, a bar with one segment per milestone, the current milestone and task, the gap round, what you must do (text and where), and its open PRs.
- **Needs you** has five kinds: `approve-plan` (plan written, no `approved: <sha>` in the log), `blocked` (a milestone's last entry is BLOCKED), `hold-review` (HOLD), `gallery` (a release PR waits and a `gallery.md` exists), `release-pr` (a PR waits for your merge: `merge: owner`, `deployOnMerge` or a risky milestone).
- **Building:** a state file changed in the last 15 minutes, or an unmerged task worktree of the current milestone exists. **Ready:** approved and nothing running or waiting on you. **Backlog:** an `intent.md` with outcome ids, or a plan without its json block. **Done:** every milestone SHIPPED or HOLD-MERGED.
- Read only, bound to `127.0.0.1`, refreshes every 15 seconds. A macOS notification fires once when a card enters needs you.

## Install
```
python3 plugins/factory/skills/run/scripts/factory-board.py install --dry-run
python3 plugins/factory/skills/run/scripts/factory-board.py install
```
It copies both scripts to `~/.factory/bin/`, writes `~/Library/LaunchAgents/dev.factory.board.plist` (starts at login, restarts on exit, log in `~/.factory/board/board.log`) and prints `http://127.0.0.1:8765/`. Options: `--port`, `--roots DIR ...` (default `~/projects`, depth 3). `uninstall` removes the agent and the plist. Run it in the foreground with `factory-board.py serve`.

## The JSON contract
`factory-status.py --json [--roots DIR ...]`, also served at `/status.json`:

```
{"generated": iso, "warnings": [str],
 "projects": [{"repo", "name", "changes": [{
   "slug", "title", "column", "approved": bool,
   "milestones": [{"id", "state", "tasks": [{"id", "state"}], "gapRound", "gapRounds"}],
   "current": {"milestone", "milestoneIndex", "milestoneCount", "task", "taskIndex", "taskCount", "gapRound", "gapRounds", "since"} | null,
   "needs": {"kind", "text", "where"} | null,
   "prs": [{"number", "url", "title", "state"}] }]}]}
```
- `column`: `needs-you`, `building`, `ready`, `backlog`, `done`. `current` is set for building cards and for blocked or hold cards.
- Milestone `state`: `pending`, `building`, `incomplete`, `blocked`, `hold`, `merged`, `shipped`. Task `state`: `pending`, `building`, `done`. PR `state`: `open`, `draft`.
- A malformed plan or state file adds a line to `warnings` and the run goes on.

`factory-status.py --repo DIR --line` prints `M3a (4/20) · T2/6 building · gap 0/3 · 38m` for the run in that repo (a worktree is fine), and nothing when none runs.

## Limits
- The progress log is free text. The reader takes each entry's first milestone id and last SHIPPED, HOLD, BLOCKED or INCOMPLETE word; keep one milestone per entry.
- Not derived: whether the approved revision still matches the files (`check-plan.py --approved`), a PR that is already merged, deploy state. Without `gh`, release PRs are not seen.
