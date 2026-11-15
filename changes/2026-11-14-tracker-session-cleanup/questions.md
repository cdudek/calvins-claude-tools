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
