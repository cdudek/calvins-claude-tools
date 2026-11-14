# Questions

Open questions never stopped the build. Each has the default taken.

## Feature 4: git-cleanup-run

- **Owner pass of the skill (plan step 16):** one owner-run pass of `/agent-tracker:git-cleanup-run` is left to the owner at the render check. The build proves the script and the text of `SKILL.md`, not that Claude asks one question per batch. Default: none taken; the pass is the proof.
- **Ended sessions need `--all`:** `claude agents --json` lists only active sessions. A row with a job id and no `pid` appears only with `--all` ("also include completed background sessions"), so the script reads `claude agents --json --all` in `list` and in every re-read of `act`. The tracker's own poll does not pass `--all`. Default taken: use `--all` in the script.
- **Missing ask record:** F49 says an unreadable ask record makes a session `needs-look`. Default taken: a torn or unreadable record is `needs-look`; a record that does not exist means the tracker saw no asks, so the check passes. Reason: a session older than 30 days is usually outside the tracker's week of backfill, and treating every missing file as unreadable would leave almost nothing removable.
- **Where the ask record is read:** the mod's own `sessions/<id>.json` first, then the backfilled `transcripts/<id>.json`. The `asks[].verdict` stored there is the last verdict; `closed` marks in `settings.json` are not read.
- **Which repos the script looks at:** only repos the tracker's records name (`repo.path`) and the working folders of the rows of `claude agents --json --all`, each resolved to its main checkout with `git worktree list --porcelain`. Nothing is crawled. A worktree of a repo no known session used is not found. Default taken: accept.
- **Idle time of a session:** the newest of the row's `startedAt`, the transcript's modified time and the tracker record's `lastActivityAt`. The record is an addition to F48's "row and transcript"; it can only make a session newer, so it can only remove items from the list.
- **A live session counts as use of a worktree:** its start or last activity enters the worktree's idle time, and condition 5 of F35 also refuses the removal. Default taken: both.
- **Ids:** a session's id is its job `id` (the id `claude rm` takes); a row with no job id lists its `sessionId` instead and is `needs-look` ("no job id"). A worktree's id is its absolute path. Both appear only in the script's JSON.
- **Secret-looking names inside a collapsed ignored folder** (for example a `.env` inside `build/`) are not seen: git prints the folder, and the script lists the folder name. Default taken: accept; the folder is named in the offer.
- **`allowed-tools` form:** `${CLAUDE_PLUGIN_ROOT}` was not verified to expand inside `allowed-tools`, so the frontmatter uses the glob form this repo already uses (`Bash(python3 */git-cleanup-run/scripts/cleanup.py list)`), and the body runs the script through `${CLAUDE_SKILL_DIR}`.
- **`skills` key:** not needed. `claude plugin validate --strict plugins/agent-tracker` reads `skills/git-cleanup-run/SKILL.md` without a `skills` entry in `plugin.json`.
- **Commit trailer:** the prompt named a different model than the harness attribution line; the harness line was used.
