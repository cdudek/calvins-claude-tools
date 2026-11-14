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
