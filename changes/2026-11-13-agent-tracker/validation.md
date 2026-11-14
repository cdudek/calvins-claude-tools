---
type: validation
change: 2026-11-13-agent-tracker
milestone: agent-tracker-1
branch: milestone/agent-tracker-1
created: 2026-11-14
---

# Validation: agent-tracker-1

Does each fact and ask of milestone 1 do what the plan said? One row each. A fact is `met` only when a test with its `@F<n>` tag passes and the test body asserts the fact's behaviour (read for every row). `met (default, Q<n>)` is met under a default logged in `questions.md`. Behaviour only a real terminal shows is `not testable here`, with the hand check.

## Runs

- **`claude plugin test plugins/agent-tracker`:** 183 pass, 0 fail, 7 files. Every F1 to F132 carries at least one passing tagged test.
- **`claude plugin validate --strict plugins/agent-tracker`:** Validation passed.
- **`python3 -m unittest discover -s tests`:** 42 tests OK (includes the public-repo grep and the no-publishing scan over the mod: F64, F65).
- **Harness limit:** the tests drive the mod through the engine mock (`ui.press`, `ui.redraw`, props). They show what the mod draws and sends, not what a terminal renders or what the engine does with a key.

## Facts


| ID | Expected | Observed | Evidence | Verdict |
|---|---|---|---|---|
| F1 | Lease holder lists every session from claude agents --json every 5 s; others read agents.json | Holder ran the call and wrote agents.json with 5 rows, engine-only rows included; a non-holder ran no call and read the file | collector.test.ts › @F1 (2 tests), @F128 (6 polls in 25 s) | met |
| F2 | busy / working is running | deriveState gives running for both | collector.test.ts › @F2 | met |
| F3 | waiting / blocked is needs you | deriveState gives needs-you for both | collector.test.ts › @F3 | met |
| F4 | Reason from waitingFor; no recorded permission value, so any waitingFor reads "waiting" | PERMISSION_WAITING_FOR is null, waiting gives "waiting"; an injected value gives permission, a flag gives question | collector.test.ts › @F4; questions.md Q1 | met (default, Q1) |
| F5 | idle is done unless the question flag is set | idle gives done with no reason; flag gives needs-you / question | collector.test.ts › @F5 | met |
| F6 | state done or leaving the list is ended | background done is ended; a file absent from a good list is ended; a failed read keeps the last state | collector.test.ts › @F6 | met |
| F7 | Repo named by main worktree folder; worktrees group; same name twice adds parent | repoFromCommonDir, labelRepos gives work/web-app and play/web-app, a linked worktree resolves to its repo | collector.test.ts › @F7 | met |
| F8 | One JSON file per session, rewritten whole by its own mod | Every write under sessions/ is the session's own file; record shape asserted | collector.test.ts › @F8 | met |
| F9 | Read the milestone.md whose branch equals the session branch | slug, sentence and five features with states read from the fixture | collector.test.ts › @F9 | met |
| F10 | No matching milestone.md: title and branch; a changes/ folder alone is no milestone | Milestone is null with a bare changes folder and with another branch's milestone.md; band header uses title and branch (F27, F33) | collector.test.ts › @F10; band.test.ts › @F27, @F33 | met |
| F11 | Goal age, subagents and background sessions reported | goalSince, subagent row and background row stored; goal age hidden once done (band and pane) | collector.test.ts › @F11; band.test.ts › @F27; pane.test.ts › @F107; questions.md Q4 | met (default, Q4) |
| F12 | Backfill reads transcripts of sessions active in 7 days with no file: tokens, branch, folder, title, errors, asks "not classified", no model call | Fields, not-classified asks, no model call and no-file / own-session exclusions asserted. The 7-day clause is now exercised (V1, fix round): the test puts the old transcript, so the existing `toEqual([STORED])` proves a transcript older than 7 days is skipped (backfill.ts:54) | backfill.test.ts › @F12 (3 tests), passing at 902f586 | met |
| F13 | Over 4 MiB: read by grep, returning the F12 fields | One grep -o on the path; cwd, branch, title, times, usage and asks equal the fixture | backfill.test.ts › @F13 | met |
| F14 | git worktree list and gh pr list --json with checks, review, mergeable | Both argv asserted, field list asserted, parsers match fixtures, record stored and merged | scans.test.ts › @F14 | met |
| F15 | Each prompt stored as the next ask from 1; classified with haiku at prompt.submit | Two asks numbered 1, 2, kinds task / question, both model calls pinned haiku | asks.test.ts › @F15 | met |
| F16 | Ask status derived: in progress, needs you, replied | askStatuses gives the three states from state and open flag | asks.test.ts › @F16 | met |
| F17 | At turn.complete read last assistant message from transcript; check only when final paragraph has ? | One check call whose text is the transcript's last message | asks.test.ts › @F17; asks.test.ts › @F132 (negative); questions.md Q6 | met |
| F18 | Question check uses no classic hook | register() names no classic.* hook; source has only a comment naming classic | asks.test.ts › @F18; hooks/tracker/asks.ts:48 | met |
| F19 | haiku flag gives needs you / asks a question; next prompt clears | Flag set, state needs-you, survives a poll; next prompt clears and runs | asks.test.ts › @F19 | met |
| F20 | Session without the mod stays done after a question | Engine-only idle session is done, source engine, no flag | asks.test.ts › @F20 | met |
| F21 | Tokens in/out, tool errors, retries per session | tokensIn 2020, out 50, 3 errors, 2 retries from fixtures | collector.test.ts › @F21; questions.md Q3 | met (default, Q3) |
| F22 | No stored view: compact; view kept in settings.json for every session | Default compact, nothing stored; Details press writes settings.json; second press writes compact | band.test.ts › @F22 (2 tests) | met |
| F23 | Compact buttons Pane (p) and Details (d), no Board; letter hotkey acts only with the keyboard | Props asserted: labels, hotkey p and d, plain; no board key; two buttons. Real hotkey render and keyboard gating are the engine's. Hand check: hotkeys draw and fire only while the band has the keyboard | band.test.ts › @F23 | not testable here |
| F24 | Order: needs you, running and done, PRs, work; one row | Text and segment ids asserted; 125 cells at full width; row on screen equals layout | band.test.ts › @F24, @F22, @F23; questions.md Q19 | met (default, Q19) |
| F25 | Count in warning colour then oldest waiting session | Chunk tone warning, ' · web-app: fix login 6m' in normal colour | band.test.ts › @F25 | met |
| F26 | This session named "this session" when it waits | Reads '● 2 need you · this session 1m · web-app 6m'; scenario wins over F26 text (Q15) | band.test.ts › @F26; questions.md Q15 | met (default, Q15) |
| F27 | Work segment: milestone and progress, else repo and title | 'agent-tracker-1 2/4 · goal 14m' and 'web-app · fix login redirect'; goal hidden when done | band.test.ts › @F27 | met |
| F28 | Drop order goal age, work, words, PR segment, waiting title; below 40 only count and buttons | Exact strings at 115, 79, 75, 54, 50, 39 columns; fits at every listed width; steps past five per Q16 | band.test.ts › @F28 (2 tests); questions.md Q16 | met (default, Q16) |
| F29 | /tracker band off hides the band in every session until band on; other mods' rows stay | Settings written, row gone, other mod's Text stays, on restores; another session's file followed | band.test.ts › @F29 | met |
| F30 | New count by next poll and redraw | Idle session turned waiting; after one poll and redraw the band reads 3 need you | band.test.ts › @F30 | met |
| F31 | Running count equals running sessions of the list | '◐ 3 running'; history and ended records not counted; agents fixture gives 2 running, 1 done | band.test.ts › @F31 (2 tests) | met |
| F32 | Alone: 'only this session is running' replaces running and PR segments | Replaced, dim, work and needs-you stay; gone when another session is live | band.test.ts › @F32 | met |
| F33 | Details header: repo, milestone and progress, or title and branch; branch left out when it holds the slug | Both forms, slug case, fallbacks 'untitled session' / 'detached HEAD' (Q24) | band.test.ts › @F33; questions.md Q24 | met (default, Q24) |
| F34 | What runs in the header, each part only above 0; second line when full | Singular and plural words, zero parts hidden, second line at 100, one line at 160 | band.test.ts › @F34 | met |
| F35 | Four columns with a count and one line, none at 0; lines drop below 80 except needs you | Labels, counts, empty column, 79 vs 80 columns, on screen with rule and Box width | band.test.ts › @F35 (2 tests) | met |
| F36 | Copy (c) or /tracker copy copies Markdown; toast 'Tracker state copied as Markdown' | Press and command each copy once with the same text; toast equals COPIED | band.test.ts › @F36 | met |
| F37 | Desktop: columns are one Svg whose alt lists every label and value | Svg found on desktop surface; alt holds counts and lines; markup escaped; no rule Text. Hand check on the real desktop app | band.test.ts › @F37 (3 tests) | met |
| F38 | Pane button or /tracker opens Home with focus on first row | Pane opened with focus true, title first, first row autoFocus, Close not; opens on four surfaces. Real focus ring is the engine's. Hand check: ring sits on the first row on open | pane.test.ts › @F38 (3 tests); questions.md Q22 | not testable here |
| F39 | Sections in order Needs you, Running, Done, Ended today, Repos | Headings in order; Repos after Ended today | pane.test.ts › @F39 | met |
| F40 | Needs you: longest wait first, this session included; row with glyph, title, repo, branch, wait, reason, errors, retries | Exact row strings with reason, 2 errors, 1 retry; unknown and waiting reasons; this session in F102 | pane.test.ts › @F40 (2 tests) | met |
| F41 | At most 10 Done and 5 Ended today rows, then a more line | 10 and 5 rows from 12 and 7; two 'and 2 more on the Repo pages' lines | pane.test.ts › @F41 | met |
| F42 | Repos line: every repo of 7 days, most recent first, buttons, in every state | Four buttons in order with PR counts; kept in alone, stale, partial and quiet states | pane.test.ts › @F42 | met |
| F43 | Order frozen while the pane has the keyboard; new waiter last, marked new; re-sort on leave or reopen | Frozen, new mark, re-sort on isFocused false and on /tracker reopen asserted. A reopen by ctrl+x x is not seen (Q27). Hand check: reopen by ctrl+x x re-sorts | pane.test.ts › @F43; questions.md Q27 | not testable here |
| F44 | No waiter and another session live: 'Nothing needs you.' | Line shown, alone line absent | pane.test.ts › @F44 | met |
| F45 | Alone and not waiting: the 'Only this session is running...' line | Line shown, Running hidden, Repos shown | pane.test.ts › @F45; questions.md Q29 | met (default, Q29) |
| F46 | Session page: header, Running now, Usage, Milestone, Asks, in order; opens from a row or /tracker session | Order asserted; opened from a row; command path in F122 | pane.test.ts › @F46 (2 tests) | met |
| F47 | Asks oldest first with number, kind, status, time; 'No asks yet.'; transcript note | Row strings, ask:1 before ask:2, empty line, 'Not classified: this session ran without the tracker.' | pane.test.ts › @F47 | met |
| F48 | Milestone section only with sdlc-run; done reads complete, merged reads merged; others to do, building, blocked | Five state words asserted; section gone without a milestone | pane.test.ts › @F48 | met |
| F49 | Ended session offers Copy resume command with single-quoted folder; live offers none; failed copy words | Command with space and quote escaped; no button when live; toast 'Copy failed: no-clipboard. Press Copy resume command again.' | pane.test.ts › @F49 (2 tests) | met |
| F50 | Repo page: Open PRs, Worktrees, Ended in order; from a heading or /tracker repo | Order asserted; opened from a heading and from the Repos line; command path in F122 | pane.test.ts › @F50 | met |
| F51 | Open PRs: failing first, then newest by creation; session button only where a session ran on the branch | Key order 44, 42, 43, 41; session buttons on 42 and 43 only; questions.md Q32 for never scanned | pane.test.ts › @F51 | met |
| F52 | Two failed reads: dim counts, 'session list unavailable · counts from 2m ago', 'stale 2m' below 60; takes work segment's place, never drops | Text, dim tones, 100/70 columns, 59 columns, one failed read is not stale, on screen and live | band.test.ts › @F52 (3 tests) | met |
| F53 | First read pending: 'Reading sessions…' on band and Home | LOADING on band layout, on screen and on Home | band.test.ts › @F53 (2 tests); pane.test.ts › @F53 | met |
| F54 | gh missing: band drops PR segment; pane shows the PRs not shown line; Home headings lose PR counts | Band, Home, Repo page and scan all asserted; non-GitHub remote runs no gh (S2); control characters stripped (S1); Q18 for placement | band.test.ts › @F54 (2); pane.test.ts › @F54 (2); scans.test.ts › @F54 (4) | met (default, Q18) |
| F55 | Unreadable transcript: session without asks and numbers; read again on change | Empty record stored, not retried after 2 min, read again after the file changes | backfill.test.ts › @F55 | met |
| F56 | Question check fails: stays done, no flag | Check called once, flag null, state done after a poll | asks.test.ts › @F56 | met |
| F57 | Classify fails: ask kept as not classified | Ask 1 kept with kind not-classified | asks.test.ts › @F57 | met |
| F58 | Cannot write the session file: status line with the fact's words | Exact status string set; cleared after a good write | collector.test.ts › @F58 | met |
| F59 | /tracker session with no match: not-found line | 'No session matches "nothing-like-it". Pick one on Home.' with Home and Close | pane.test.ts › @F59 | met |
| F60 | Every model call pins haiku from one constant | MODEL is 'haiku'; every recorded call op classify with that model; source passes MODEL at both calls (asks.ts:30, :52); no claude -p in source | safety.test.ts › @F60 | met |
| F61 | At most one classify per ask and one check per turn; none without a ? | Two asks give two classifies, one check; none for subagent or aborted turn | safety.test.ts › @F61; asks.test.ts › @F61 | met |
| F62 | Never writes to a session, git, gh or bd | No appended message, no prompt, tool or command of its own; every process is a read; no bd | safety.test.ts › @F62; band.test.ts and pane.test.ts observe-only tests | met |
| F63 | No file written outside ~/.claude/agent-tracker/ | Every recorded write starts with the folder | safety.test.ts › @F63 | met |
| F64 | Committed fixtures hold no internal names, people, URLs or local paths | Fixture leak scan passes; repo-wide git grep in test_plugin.py passes (unit run OK); no screenshots committed | safety.test.ts › @F64; tests/test_plugin.py | met |
| F65 | No Artifact, Claude Docs or hosted page; no server or port | No net call, no non-read process; mod scanned whole by test_no_claude_ai_publishing.py (unit run OK) | safety.test.ts › @F65; tests/test_no_claude_ai_publishing.py | met |
| F66 | Unknown status: needs you, 'state unknown', raw value in Session state line | Reason unknown with unknownValue; Home 'state unknown'; Session '● needs you · 6m · state unknown (weird)' | collector.test.ts › @F66; pane.test.ts › @F40, @F104 | met |
| F67 | Scan own repo's git and gh every 2 minutes; no other repo | Calls at 0, 2 and 6 min, all in own cwd, none in another repo; no repo scans nothing | scans.test.ts › @F67 (2 tests) | met |
| F68 | Merge every session file into one list; a gone mod shows from its last file | Four sources merged, torn file skipped, sessions/ beats transcripts/, gone session ended | collector.test.ts › @F68 | met |
| F69 | No live mod session: last stored PR state with 'PRs as of 2h ago: no live session in this repo' | Line on Repo page; none while a live mod session runs; repoPrs age and hasLive | pane.test.ts › @F69 (2); scans.test.ts › @F69; questions.md Q14 | met |
| F70 | Backfill takes every typed prompt in order; skips tool results, slash expansions, system notes | Three asks in order with times; eight kinds of skipped text absent; caps 200 asks, 2,000 chars | backfill.test.ts › @F70 (2 tests); questions.md Q9 | met |
| F71 | Feature complete when done or merged | isComplete true for done and merged only; count 3 | collector.test.ts › @F71 | met |
| F72 | Ask in progress from prompt to turn end | in-progress after submit and a poll, replied after turn.complete | asks.test.ts › @F72 | met |
| F73 | Ask needs you while the session waits | State and ask both needs-you after engine says waiting | asks.test.ts › @F73 | met |
| F74 | Turn end: replied, or needs you when flagged | replied after a plain turn, needs-you after a question turn | asks.test.ts › @F74 | met |
| F75 | Next prompt closes previous ask as replied | Statuses [replied, in-progress] | asks.test.ts › @F75 | met |
| F76 | One waiter reads '● 1 needs you · web-app: fix login 6m' | String prefix asserted | band.test.ts › @F76 | met |
| F77 | None waiting: '0 need you' dim | Chunk tone dim; follows with running segment | band.test.ts › @F77 | met |
| F78 | PR segment counts open and failing PRs over repos of 7 days, latest scan each | 4 PRs · 1 ✗: latest scan per repo, failed gh adds none, 8-day repo excluded; singular and no ✗ cases | band.test.ts › @F78 | met |
| F79 | /tracker details and compact switch the view | Settings and redraw follow each command; case and spaces ignored | band.test.ts › @F79 | met |
| F80 | Details header buttons Copy (c), Pane (p), Compact (d) at the right edge | Keys, labels, hotkey props and plain asserted; Compact press returns to compact. Real hotkey render is the engine's. Hand check: labels draw at the right edge, hotkeys fire with the keyboard | band.test.ts › @F80 | not testable here |
| F81 | Columns carry oldest waiting (or this session), longest running, latest done lines; needs you normal, others dim | Three exact lines; tones undefined / dim / dim; 'this session 10m' | band.test.ts › @F81 | met |
| F82 | PRs column '4 open' and '1 failing · 2 mergeable' | Count and line asserted, plus 2 open, 1 open cases | band.test.ts › @F82 | met |
| F83 | Below 60 columns fold into two rows of two | One row at 60, two rows at 59 and 30; widths 27 and 13 | band.test.ts › @F83 | met |
| F84 | Header cut order branch, title, milestone; '2/4 complete'; what runs on its own line | Ladder asserted at 101 to 51 columns with and without sdlc-run; button width is 24 not 21 (Q17) | band.test.ts › @F84 (2 tests); questions.md Q17 | met (default, Q17) |
| F85 | Markdown: four counts, a line per waiter and runner, open PRs, no path beyond repo name | Counts, five session lines, PR lines, no /work/ path, no PR lines when gh gave nothing; layout is Q23 | band.test.ts › @F85; questions.md Q23 | met |
| F86 | Copy failure toast 'Copy failed: <reason>. Press Copy again or run /tracker copy.' | Exact toast from button and command | band.test.ts › @F86 | met |
| F87 | Loading, Partial, Stale line under the header | Note equals LOADING, stale text, 'stale 2m', PRS_NOT_SHOWN; stale wins; Loading on screen only | band.test.ts › @F87 (2 tests); questions.md Q18 | met (default, Q18) |
| F88 | Close (x) on Home; Back (b), Home (h), Close (x) on Session and Repo | Labels, hotkey props, plain asserted per page; Home has no Back or Home. Real hotkey render is the engine's. Hand check: hotkeys draw and fire on each page | pane.test.ts › @F88 (2 tests) | not testable here |
| F89 | Back shows previous page with the same row focused | Back to Home gives docs-1 autoFocus; Repo to Session via Back. Real focus ring is the engine's. Hand check: ring on the row left | pane.test.ts › @F89, @F88; questions.md Q27 | not testable here |
| F90 | Home button shows Home | Headings back, first row focused again | pane.test.ts › @F90 | met |
| F91 | Close or ctrl+x x closes the pane, keys return to the prompt | Close press records a close; nothing refuses a person's close. ctrl+x x and the key return are the engine's. Hand check: ctrl+x x closes, typing reaches the prompt | pane.test.ts › @F91 | not testable here |
| F92 | Escape hands the keyboard back, pane stays open; Close or ctrl+x x closes (owner's reword) | Opened with focus true and no closeOnEscape; nothing closes it; Close closes it. Real Escape is the engine's (decisions.json protectedEdit, Q26). Hand check: Escape returns the prompt and leaves the pane drawn | pane.test.ts › @F92; questions.md Q26 | not testable here |
| F93 | Running under repo headings, longest-running repo first; row words | Heading order api then platform-tools-suite; exact rows with tokens, errors, retries | pane.test.ts › @F93 | met |
| F94 | Done under repo headings, latest first; row words | Exact rows; docs-2 (3m) before web-2 (9m). Headings come from the same grouped() as Running (pane-model.ts:185-186), asserted in F93 | pane.test.ts › @F94; pane.test.ts › @F93 | met |
| F95 | Ended today since local midnight, newest first; row words | Exact row; yesterday's session absent | pane.test.ts › @F95 | met |
| F96 | Empty Running, Done, Ended today hidden | Only Needs you and Running headings remain | pane.test.ts › @F96 | met |
| F97 | Repo heading is a button to Repo page | Button 'web-app · 4 PRs · 2 failing' | pane.test.ts › @F97 | met |
| F98 | No repo in 7 days: 'No repos yet.' | Line shown, no repos: buttons | pane.test.ts › @F98 | met |
| F99 | Below 70 columns a row takes two lines; at 70 one; only the title is cut with … | Two lines at 54, one at 70, ellipsis only in title; zoom is unknown (Q31) | pane.test.ts › @F99 (2 tests); questions.md Q31 | met (default, Q31) |
| F100 | Below 40 second line drops tokens then branch; wait, reason, errors, retries stay; heading keeps counts | Exact second lines at 39 and 30; heading cut keeps ' · 2 PRs · 1 failing' | pane.test.ts › @F100 (2 tests) | met |
| F101 | Time of last read: 'updated just now', 'updated 2m ago' | Both strings after a 2 min clock advance | pane.test.ts › @F101 | met |
| F102 | Alone and waiting: this session under Needs you; no Empty line | Row '● this session   platform-tools-suite · main · 4m · waiting'; line absent | pane.test.ts › @F102; questions.md Q29, Q30 | met (default, Q29) |
| F103 | Session header: title, state line, repo button, branch | Order title then state line, Button 'web-app', branch text | pane.test.ts › @F103 | met |
| F104 | State line words for each state | Four exact strings plus the unknown form | pane.test.ts › @F104 | met |
| F105 | Branch with open PR shows link #42 and checks | Link href and text, ' · PR ', ' ✗ checks failing'; none without a PR | pane.test.ts › @F105 | met |
| F106 | Usage line with tokens, errors, retries, start, last activity | Exact string and singular / plural variant | pane.test.ts › @F106 | met |
| F107 | Running now: goal, subagents, background; hidden when empty | Three rows in order; section gone when empty or done | pane.test.ts › @F107 | met |
| F108 | Milestone: sentence, count, one row per feature in order | Order asserted; '2 of 5 features complete' | pane.test.ts › @F108, @F48 | met |
| F109 | At 70 columns an ask row is one line of number, kind, status, time, wrapped text | Exact first line, continuation indent 34, text rejoins, all lines within 70 | pane.test.ts › @F109 | met |
| F110 | Below 70 columns or zoom 150%: ask row on two lines, text cut at 4 lines with … | First line, 4 text lines, ellipsis, all within 54; zoom unknown (Q31) | pane.test.ts › @F110; questions.md Q31 | met (default, Q31) |
| F111 | Open page of a session that left the list shows ended with time | Page turns '○ ended 1m ago', resume appears | pane.test.ts › @F111 | met |
| F112 | Copy resume command (r) copies and toasts 'Resume command copied' | Toast asserted | pane.test.ts › @F112, @F49 | met |
| F113 | Breadcrumbs 'Home › web-app › fix login redirect' and 'Home › web-app' | Both strings | pane.test.ts › @F113 (2 tests) | met |
| F114 | PR number is a link; row words | Row string exact; Link #42 with its href | pane.test.ts › @F114 | met |
| F115 | PR words for checks, review, mergeable | Three exact rows covering pass, running, failing, approved, changes requested, no review, mergeable, unknown | pane.test.ts › @F115 | met |
| F116 | Below 70 columns or zoom 150%: PR row two lines; failing checks in error colour, never dim | Two lines at 54, one at 70, color error and not dim; zoom unknown (Q31) | pane.test.ts › @F116 (2 tests); questions.md Q31 | met (default, Q31) |
| F117 | Worktrees: main checkout first then by recent session, live sessions as rows | Order asserted twice; session rows under worktrees | pane.test.ts › @F117 (2 tests) | met |
| F118 | No worktrees: 'No worktrees found.' | Line shown | pane.test.ts › @F118 | met |
| F119 | gh works, none open: 'No open PRs.' | Line shown, no PR boxes | pane.test.ts › @F119; questions.md Q32 | met |
| F120 | Ended on Repo: 7 days, newest first, hidden when none | Row 'ended 2d ago', order 2h, 13h, 2d, hidden when none | pane.test.ts › @F120 | met |
| F121 | /tracker repo with no match: not-found line | 'No repo named "Nope" has had a session. Pick one on Home.' | pane.test.ts › @F121 | met |
| F122 | /tracker session matches title by case-insensitive substring else id prefix; several open most recent; repo same rule | Substring, prefix, most recent, title over id, repo substring and most recent; empty argument is Q33 | pane.test.ts › @F122 (6 tests); questions.md Q33 | met |
| F123 | Two failed reads: Home dims and shows the stale top line | Exact line with '2m ago', dimColor on titles, one failed read shows none | pane.test.ts › @F123 (2 tests) | met |
| F124 | A word or count beside every glyph | Band regexes, pane rows (glyph plus time), Session and Repo page text scans | band.test.ts › @F124; pane.test.ts › @F124 (3 tests) | met |
| F125 | Durations '<1m', '6m', '2h 10m', '3d' | Table of seven values; whole hours write '2h' (Q11); band uses the format | band.test.ts › @F125; questions.md Q11 | met (default, Q11) |
| F126 | Redraw once a minute with no data change | Invalidations rise after 60 s and the wait reads 7m, band and pane | band.test.ts › @F126; pane.test.ts › @F126 | met |
| F127 | Lease taken when none fresh (heartbeat under 15 s), kept, dropped for another's fresh lease | leaseState free / mine; taken, heartbeat refreshed, polling stopped, retaken after 20 s | collector.test.ts › @F127 | met |
| F128 | Holder polls every 5 s, refreshes heartbeat, writes agents.json by temp file and rename | 6 polls in 25 s, heartbeat and readAt refreshed; whole-file write because the API has no rename (Q2) | collector.test.ts › @F128; questions.md Q2 | met (default, Q2) |
| F129 | Non-holder runs no call, reads agents.json every 5 s; an old or unreadable file is a failed read | No claude call; 16 s old file gives agentsOk false and state stays done | collector.test.ts › @F129 | met |
| F130 | Each mod writes only its own session file; holder also lease files; backfill transcripts/; view settings.json | Regex over every write path for holder and non-holder; non-holder writes no lease file | safety.test.ts › @F130 (2 tests) | met |
| F131 | Dim line for sessions without a sessions/ file, singular and plural, hidden at none | Both strings, dimColor, hidden at none and for an ended engine-only session | pane.test.ts › @F131 | met |
| F132 | No ? in final paragraph: no call, no flag | models length 0, flag null | asks.test.ts › @F132, safety.test.ts › @F61 | met |

## Asks

| ID | Expected | Observed | Evidence | Verdict |
|---|---|---|---|---|
| A1 | See every session, its repo, work and state, which wait; asks kept; usage | Collector, backfill, asks, band and pane rows all met; the owner's success measure (5 of 5 spot checks by 2026-12-04) is read after release | F1-F21, F66-F78 rows above; intent.md Success measure | met |
| A2 | Cheap model for model calls | Both calls pin haiku from one constant; call counts bounded | F60, F61, F132 | met |
| A3 | 'You should know' and decided-without-me items | Nothing built or shown in milestone 1 | facts.md Out of scope | out of scope (facts.md Out of scope) |
| A4 | A compact view of the band | Compact is the default, drops by width, below 40 keeps count and buttons | F22, F28, F52, F83, F84, F99-F100 | met |
| A5 | A web page instead of a TUI | Web page and Board button belong to milestone 2; band shows no Board button | facts.md Out of scope; F23, F65 | out of scope (facts.md Out of scope) |
| A6 | Band with compact and details views, Copy, buttons | Switch, Copy, Markdown and details columns asserted through ui.press and commands; hotkey render is a hand check (F23, F80) | F22-F37, F79-F87 | met |
| A7 | Repo, what is developed, whether a goal or something runs | Repo and milestone in the band and header, goal age, subagents, background sessions; project name left out by facts.md Out of scope | F11, F27, F33, F34, F107 | met |
| A8 | Explore and dig into one repo, navigate, detail page, milestones | Session and Repo pages, Back, Home, breadcrumbs, PRs, worktrees, milestone section; a milestone view on the Repo page is Out of scope (milestone 2) | F46-F51, F88-F90, F103-F122 | met |
| A9 | Triage-queue pane interface | Home sections, ordering, rows, narrow layout asserted; keyboard behaviour (focus, Escape, hotkeys) is a hand check | F38-F45, F91-F102 | met |
| A10 | Works without sdlc-run | No milestone falls back to title and branch; backfill and engine-only sessions without a file; without-the-tracker line | F10, F12, F20, F42, F131 | met |
| A11 | Pane mod (surface 1) and a standalone UI (surface 2, later replaced by the web page) | Pane mod delivered; the standalone UI is replaced by milestone 2's web page per A5 | F38, F65; facts.md Out of scope | met |
| A12 | Fully standalone data layer | One folder, one file per session, no dependency on other memory tools or bd; own-file writes only | F8, F62, F63, F127-F130 | met |

## Open questions and the default each took

`questions.md` Q1 to Q33 are all answered by a default; none waits on the owner. Each row below is the default the build took. Where a fact depends on it, the fact's row cites it.

| Q | Question | Default taken |
|---|---|---|
| Q1 | Which waitingFor means a permission prompt | None recorded; PERMISSION_WAITING_FOR is null, any waitingFor reads "waiting" |
| Q2 | Mod API has no rename | agents.json and poller.json written whole; readers keep last good copy |
| Q3 | What counts as tokens in | input plus cache reads plus cache writes; out is output tokens |
| Q4 | Which background sessions belong to a session | Not-done background sessions in the same folder |
| Q5 | Two fields added to the record | source 'engine' and unknownValue added |
| Q6 | Where the question check reads the last message | Last assistant row of the session transcript, else answer |
| Q7 | $ only to top-level functions | Every I/O helper is a top-level function |
| Q8 | Mod loaded mid-session has no session.start | Record starts at first prompt or poll; README says restart |
| Q9 | How the backfill reads a transcript | One regex, grep -o over 4 MiB; ask rules in NOT_AN_ASK |
| Q10 | How often the backfill runs | At start and each minute, 25 transcripts per pass |
| Q11 | Where the duration format lives | core/format.ts; whole hours write '2h' |
| Q12 | When the scan runs | At start and every 2 min, own repo, own timer |
| Q13 | Scan time when gh fails | Keeps last PRs and their time, ghOk false |
| Q14 | What is a live session | source mod and not ended |
| Q15 | Who is named when this session waits | Scenario wins: this session first, then the oldest other |
| Q16 | What drops after the spec's five steps | Step 6 drops counts, step 7 the waiter; below 40 jumps to 7 |
| Q17 | Details buttons are 24 cells, not 21 | 24 used; thresholds sit 3 cells earlier |
| Q18 | Where the 'PRs not shown' line shows | Compact band drops the segment; details and pane write the line |
| Q19 | Buttons have no gap in the count | Measured as the spec; add gap 1 if a real terminal shows them touching |
| Q20 | Where /tracker lives until row 4 | Band registers and chains; pane adds its own hook |
| Q21 | Snapshot gained okAt and failedReads | Added |
| Q22 | What Pane opens before row 4 draws it | id 'tracker' |
| Q23 | Markdown layout | Heading, bold-labelled counts, three lists |
| Q24 | Header fallbacks and what runs | 'untitled session', 'detached HEAD', folder name; cut ladder fixed |
| Q25 | Column lines | this session named; zero parts dropped; singular PR |
| Q26 | Escape hands back first, closes second | Reworded by the owner: Escape only returns the keys, no closeOnEscape (decisions.json protectedEdit) |
| Q27 | How the pane knows the ring and reopened | ui.focus hook and autoFocus; a reopen by ctrl+x x is not seen |
| Q28 | Where the Partial line goes | Under the title (screens.md) |
| Q29 | Where this session is when alone | Empty line when alone; one row under Needs you when waiting |
| Q30 | Row name for this session; word beside a glyph | 'this session' on Needs you only |
| Q31 | Zoom 150% not known to the mod | Width rules only (70 columns) |
| Q32 | Repo page for a repo never scanned | 'No open PRs.' |
| Q33 | Empty /tracker session or repo; ask times | Opens Home; ask time like '30m'; unknown word gets a hint line |

## Summary

Rows: 144 (132 facts F1 to F132, and 12 asks A1 to A12, of which A3 and A5 are out of scope).

- **met:** 116
- **met (default, Q<n>):** 17
- **not testable here:** 8
- **partly:** 1
- **not met:** 0
- **out of scope (facts.md Out of scope):** 2

### Blocking rows and the smallest fix

- **F12 (partly):** the "active in the last 7 days" clause is not exercised. In `plugins/agent-tracker/tests/backfill.test.ts` the test "only sessions with no file, active in the last 7 days, and never its own" sets `w.mtimes.set(other('old'), NOW - WEEK_MS - 1)` but never calls `w.put(other('old'), TRANSCRIPT_TEXT)`, so the file is never listed. Fix: add `w.put(other('old'), TRANSCRIPT_TEXT)` before the `mtimes.set` line (put sets the mtime, so keep the `mtimes.set` after it); the existing `toEqual([STORED])` then proves the old transcript is skipped. The code is `hooks/tracker/backfill.ts:54` and reads right; this is a test gap, no behaviour change.

### Hand checks (not testable here)

- **Hotkeys (F23, F80, F88):** in a real terminal the labels Pane p, Details d, Copy c, Compact d, Close x, Back b, Home h and Copy resume command r draw, and fire only while the band or pane has the keyboard.
- **Focus (F38, F89, F43):** the ring sits on the first Home row on open, Back returns it to the row left, and the frozen order re-sorts on keyboard leave and on a reopen by `ctrl+x x` (Q27 says that path is not seen).
- **Escape and close (F91, F92):** Escape returns the keys and leaves the pane drawn; Close and `ctrl+x x` close it and typing reaches the prompt.
- **Real waiting value (F4, Q1):** wait on a real permission prompt, record `waitingFor`, set `PERMISSION_WAITING_FOR` in `core/types.ts`; until then "asks permission" never shows.
- **Width and zoom (F24, F28, F99, F110, F116, Q19, Q31):** the band at 100 and 150 percent; buttons must not touch when the row fits exactly (else add `gap=1`); details columns on the desktop app (F37).
- **Success measure (A1):** 5 of 5 spot checks of the needs-you count by 2026-12-04, read after release.
