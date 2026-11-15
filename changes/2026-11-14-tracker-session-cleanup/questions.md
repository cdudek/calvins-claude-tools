# Questions

Open questions from the build, each with the default taken. None blocks the build.

## Feature 1, state and age

- **Pid rule needs this session's row:** F1 ends rows only when some row has a `pid` and the read lists this session. Otherwise nothing is ended; the next read corrects it.
- **Start counts as no activity:** `lastActivityAt` equal to `startedAt` is no activity, so a just-started session reads "last activity unknown".
- **F7 header time:** the header uses `endedAt`, then last activity. Pid-ended rows have no `endedAt`, so they read days since last activity as F7 says. Milestone 1's `@F111` stays true.
- **Recorded fixture:** the blocked background row of `AGENTS` got a made-up `pid`, so milestone 1's band tests keep a live needs-you row.
- **Transcript read:** `tail -c 65536` and the newest `"timestamp"`, not the last line: transcripts often end in a record with no timestamp.
- **Listed ended sessions older than 7 days:** `merge.ts` drops ended sessions idle over 7 days, so a 13-day dead session would have no Session page and the skill only collects at 30 days. Default taken in feature 2: an ended session that Claude Code still lists stays in the snapshot whatever its age, so Clear can reach it (F8: a listing is work left). Tasks still follow F32's 7-day rule.
- **Dead background jobs on the running line:** `collector.ts` lists a pid-less background row in this session's background runs (filter is `state !== 'done'`). Not in this change's facts; left as is, noted for a later change.

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

## Feature 2, Clear

- **Where the list rows come from:** the snapshot had no `pid` or job `id`, and the page reads only the snapshot. `Snapshot.listing` (optional, `types.d.ts`) holds the last good read's rows by session id, written by `collector.ts`. A failed read keeps the old rows, so one failed read does not flash "Nothing to clear"; two failed reads withhold Clear (F12). Outside the plan's file list for `types.d.ts`, but nothing else can carry the fact.
- **Listed means a job id:** F25 says a row with no `id` is treated as not listed. So "listed" in F8, F10 and the confirm means a row with a plain job id and no `pid`. An interactive pid-less row alone shows "Nothing to clear".
- **A job id that is not plain** (a leading "-", a space, over 64 characters) never reaches `claude rm`: it reads as not listed.
- **No pid in the press's read:** F23 only names a `pid` on the session. A read at the press where no row carries a `pid` also refuses and changes nothing, with F11's line plus "Nothing was changed." (F65: the process fact is then unknown).
- **A failed re-read after a failed `claude rm`:** the page shows the F28 line (the list could not say the session is gone), and closes nothing.
- **Save failure with no `claude rm` run (F30):** the session was not listed, so the line drops "The session left Claude Code's list." and ends "Press Clear to try again." `writeSettings` gained a `strict` flag that puts the old settings back on a failed save; Keep, Close and Mark all seen behave as before.
- **Reopen tasks failing to save:** no line; the button stays, nothing changed. The facts name no error for it.
- **Confirm lines:** the three lines of the spec are what-happens, the worktree line and the kept line; "You can reopen the tasks afterwards." follows the kept sentence on the same line (or stands alone when the session is not listed).
- **Milestone 1's @F49 tests:** F9 withdraws "Copy resume command" from live sessions and F14 from sessions whose folder is gone, so the two `@F49` tests in `pane.test.ts` now open an ended session whose folder exists. Their assertions are unchanged.
- **Only four of the six new actions:** `clear`, `confirm-clear`, `cancel-clear` and `reopen`. `remove-worktree` and `keep-worktree` belong to row 3, with the seam `ctx.worktree` (`{ label, branch, removable } | null`, null until row 3 reads git).
- **The real `claude rm`:** never run by the build. The fake `claude` in the test world proves a hang (cut by the 15-second timeout), a refusal and a success. The owner's press at the render check is the one real run (X3); its result goes here.

## Feature 3, worktree offer

- **Stays replaces the label line:** the spec's worktree line is "label and branch (dim); or, when a condition fails, why it stays". Default taken: a failing worktree shows only the "Worktree login stays: …" line (it names the label, not the branch). F36's "worktree login · fix-login" shows when no condition fails.
- **Live sessions:** a session with a process shows the dim label line and never the "stays" or "Clear offers" text, and its page reads only `git worktree list` (no status, no `gh`). "Another session is using it" would be wrong on its own live session.
- **When git is read:** once per visit, in the background after the page first draws, so opening a page never waits on `gh`. The worktree line and the offer appear on the redraw that follows. It is read again when the session's process state changes, after `claude rm` ran (F46), and at the Remove press (F42, F44). The 5-second redraws read nothing.
- **Condition 5 at page open:** the snapshot's session records joined with the listing's `pid` give the live folders. At the Remove press it reads `claude agents --json` again. With no `pid` in a read, every listed row counts as live, as the script does. A list that cannot be read fails condition 5 ("another session is using it").
- **Press after a stale page:** pressing Clear when only a worktree seems left opens the offer from the page's facts, with no re-check: the offer is its own confirm and Remove worktree checks everything again.
- **`gh` only for GitHub:** `git remote get-url origin` first, as `scan.ts` does (S2); a remote that is not on github.com means no `gh` call and the branch alone decides. `gh pr list --head <branch> --state all --json state --limit 20`: merged or closed counts when none is open, as the script does.
- **No branch (detached HEAD):** the label shows with no branch, the offer's last line is "Remove it?" and the result reads "✓ Worktree login removed." with the resume sentence. Not in the spec.
- **A fifth reason for F44:** "git could not read it" when the worktree cannot be read at the press (a folder deleted by hand, git failing). The spec lists four reasons and "its ignored files changed".
- **Removal timeout:** reads wait 15 seconds; `git worktree remove` waits 120, because cutting git off midway would leave half a tree.
- **Symlinked folders:** the TypeScript compares paths as git prints them and as the rows report them; the script applies `realpath`. A session folder reached through a symlink may match no worktree (no line, no offer, the safe side). A live row reached through a symlink under the worktree would not count as using it. Accepted: a process's own folder is already physical in practice. Residual risk, noted.
- **First read still running at the press:** if Clear session is pressed before the first git read lands, the page has no worktree facts, so no F46 claim and no offer follow. Reopening the page offers it.
- **After a refused or changed removal:** the page reads the worktree again, so it shows how it stands now, and Clear is drawn again when it is removable.
- **Existing tests changed (not weakened):** the page now runs git reads when it opens, so "runs nothing" became "runs no write and no call that is not a worktree read". Touched: `clear.test.ts` @F14, @F17, @F20, @F22 (`ran(w)` replaces `w.procs.length === 0` and the exact `claude` list); `pane.test.ts` walk test (procs filtered the same way); `cleanup-safety.test.ts` @F65 x3, @F66, @F67 (the claude lists are the same, the git reads are allowed, `cwd` joins `timeoutMs` as an allowed init key). Every banned-argument check is unchanged; `isAllowed` takes the git reads and the exact `git worktree remove <path>` argument list.
- **No terminal screenshot:** the test kit draws the element tree, not cells, and no headless render of the mod exists in `claude plugin`. Text frames from a layout model (`tests/fixtures/frame.ts`) are under `verify/shots/`, with the row counts. The owner's real press of Clear at the render check is still the one real look.
- **Commit trailer:** the prompt named `Co-Authored-By: Claude Opus 5.5`; the attribution rule of the session names `Claude Sonnet 5.5`, the model that built this. Default taken: the session's rule.
