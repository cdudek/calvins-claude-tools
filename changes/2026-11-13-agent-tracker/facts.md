---
linear: none
type: facts
change: 2026-11-13-agent-tracker
design: docs/designs/agent-tracker.md
author: Calvin Dudek
status: approved
reviewed_by: Calvin Dudek
approved_at: 2026-11-14T00:45
created: 2026-11-13
---

# Facts: Agent tracker, milestone 1

## Goal

Open any Claude Code session and see each session's repo, work and state, and which need you, in a band and a pane. This is one change because the collector, backfill, band and pane share one store.

## Acceptance criteria

Rules: `sdlc.json` defines no `rules` list and `CLAUDE.md` gives no ids, so the two rules from `CLAUDE.md` get short names here. PUB-1 is `CLAUDE.md#Public repo rule`: no internal names, people, URLs or local paths. PUB-2 is `CLAUDE.md#Never publish to claude.ai`. A fact with no rule cites asks only.

Tests are `*.test.ts` files run by `claude plugin test`, not browser E2E. The tag goes in the test title beside `@2026-11-13-agent-tracker`. Words in quotes are the strings in `spec/screens.md`. Test file names are proposed here and `plan.md` fixes the paths.

### Collector and states

- [ ] **F1** (A1, A10, A12) While the mod runs, the session holding the poller lease shall list every session from `claude agents --json` every 5 seconds. Every other session shall read that list from `agents.json` (F127 to F129). The list holds sessions without the mod too. Screen/state: all. Tag: `@F1`.
- [ ] **F2** (A1, A7) While an interactive session reports status `busy` or a background session reports state `working`, the collector shall mark it running. Screen/state: running. Tag: `@F2`.
- [ ] **F3** (A1, A9) While an interactive session reports status `waiting` or a background one reports state `blocked`, the collector shall mark it needs you. Screen/state: needs you. Tag: `@F3`.
- [ ] **F4** (A1, A9) While a session needs you, the collector shall show a reason. It is "asks permission" when `waitingFor` matches the permission value recorded from a real waiting session at build. If the build had no waiting session, "asks permission" never shows and any `waitingFor` gives "waiting". It is "asks a question" when the question check flagged it, else "waiting". An unknown state has its own reason (F66). Screen/state: Home, Needs you row. Tag: `@F4`.
- [ ] **F5** (A1) While an interactive session reports status `idle` and the question check has not flagged it, the collector shall mark it done. Screen/state: done. Tag: `@F5`.
- [ ] **F6** (A1) When a session reports state `done` or leaves the list, the collector shall mark it ended. Screen/state: ended. Tag: `@F6`.
- [ ] **F7** (A1, A7) The collector shall name each session's repo by the folder of its main worktree, the parent of `git rev-parse --git-common-dir`. A linked worktree's sessions group under their repo. Two repos with one folder name get the parent folder added, as `work/web-app`. Screen/state: Home, repo heading. Tag: `@F7`.
- [ ] **F8** (A1, A12) The mod shall keep one JSON file per session at `~/.claude/agent-tracker/sessions/<sessionId>.json`, rewritten whole by that session's own mod. Screen/state: store. Tag: `@F8`.
- [ ] **F9** (A7, A8) Where a `changes/*/milestone.md` in the session's worktree has a `branch:` equal to the session's branch, the collector shall read it. It takes the sentence and features. Each feature carries its state. Screen/state: Session, Milestone. Tag: `@F9`.
- [ ] **F10** (A10, A12) Where no `milestone.md` matches the session's branch, the collector shall use the session title and branch. A `changes/` folder alone does not make a milestone. Screen/state: band header, without sdlc-run. Tag: `@F10`.
- [ ] **F11** (A7) While a goal, subagents or background sessions run, the collector shall report the goal's age, each subagent's status and each background session. The goal age shows only while the session runs or needs you. Subagents come from `$.agent.list()`, background sessions from `claude agents --json`. Screen/state: Running now. Tag: `@F11`.
- [ ] **F12** (A10, A12) Where a session active in the last 7 days has no file, live or ended, the backfill shall read its transcript. Transcripts sit under `~/.claude/projects/`. It takes tokens, branch, folder, title, tool errors and asks. It marks each ask "not classified" and makes no model call. Screen/state: Session, from transcript. Tag: `@F12`.
- [ ] **F13** (A12) If a transcript is over 4 MiB, then the backfill shall read it by search, a grep over the file, not whole. The search finds the prompt, usage and tool-error lines and returns the fields of F12. Screen/state: store. Tag: `@F13`.
- [ ] **F14** (A1, A8) The mod shall read its repo's worktrees with `git worktree list`. It shall read open PRs with `gh pr list --json`, with checks, review and mergeable state. Screen/state: Repo. Tag: `@F14`.
- [ ] **F66** (A1) If a session reports an unknown `status` or `state`, then the collector shall show needs you with the reason "state unknown". The raw value appears in the Session state line. Screen/state: needs you; Session, header. Tag: `@F66`.
- [ ] **F67** (A1, A12) While the mod runs, it shall scan git and gh for its own session's repo every 2 minutes. It shall scan no other repo. Screen/state: Repo. Tag: `@F67`.
- [ ] **F68** (A1, A12) The band and the pane shall merge every session file into one list. A session whose mod is gone still shows from its last file. Screen/state: store. Tag: `@F68`.
- [ ] **F69** (A8, A12) While a repo has no live session with the mod, the pane shall show its last stored PR state. A line above it reads "PRs as of 2h ago: no live session in this repo". Screen/state: Pane Repo, Open PRs. Tag: `@F69`.
- [ ] **F70** (A10, A12) When the backfill reads a transcript, it shall take every prompt the owner typed, in order, as an ask. It shall skip tool results, slash-command expansions and system notes. Screen/state: Session, from transcript. Tag: `@F70`.
- [ ] **F71** (A7, A8) The collector shall count a feature complete when its state is `done` or `merged`. Screen/state: Band compact, Work; Band details, Header; Session, Milestone. Tag: `@F71`.
- [ ] **F127** (A1, A12) When no lease in `~/.claude/agent-tracker/poller.json` is fresh, a session's mod shall take it by writing its session id and the time. A lease is fresh when its heartbeat is under 15 seconds old. A holder that finds another session's fresh lease shall stop polling. Screen/state: store. Tag: `@F127`.
- [ ] **F128** (A1, A12) While a mod holds the lease, it shall poll `claude agents --json` every 5 seconds. Each poll refreshes the heartbeat and writes `agents.json` without exposing half a file: a temp file in the same folder, then a rename. Without a rename in the mod API, it writes the whole file and readers keep their last good copy (F68). Screen/state: store. Tag: `@F128`.
- [ ] **F129** (A1, A12) While another session holds a fresh lease, a mod shall not run `claude agents --json`. It shall read `agents.json` every 5 seconds. An `agents.json` older than 15 seconds, or one that cannot be read, counts as a failed read for F52 and F123. Screen/state: store; Band Stale; Home Stale. Tag: `@F129`.
- [ ] **F130** (A12) Each session's mod shall write only its own session file. While it holds the lease it also writes `poller.json` and `agents.json`. The backfill writes only `transcripts/` files and the view choice only `settings.json`. Screen/state: store. Tag: `@F130`.

<details>
<summary>Verification</summary>

- F1 — tag `@F1`: `collector.test.ts` › lists sessions with and without the mod; the lease holder polls, the others read agents.json
- F2 — tag `@F2`: `collector.test.ts` › busy and working map to running
- F3 — tag `@F3`: `collector.test.ts` › waiting and blocked map to needs you
- F4 — tag `@F4`: `collector.test.ts` › waitingFor becomes the reason, from a recorded fixture or else the default "waiting" logged to questions.md
- F5 — tag `@F5`: `collector.test.ts` › idle maps to done unless the question flag is set
- F6 — tag `@F6`: `collector.test.ts` › done state or absence maps to ended
- F7 — tag `@F7`: `collector.test.ts` › repo label from the main worktree, same folder name twice
- F8 — tag `@F8`: `collector.test.ts` › one file per session, rewritten whole
- F9 — tag `@F9`: `collector.test.ts` › reads a milestone.md fixture whose branch equals the session branch
- F10 — tag `@F10`: `collector.test.ts` › changes folder without a matching milestone
- F11 — tag `@F11`: `collector.test.ts` › goal age, subagents and background sessions
- F12 — tag `@F12`: `backfill.test.ts` › fixture transcript fields, live and ended
- F13 — tag `@F13`: `backfill.test.ts` › transcript over 4 MiB read by search
- F14 — tag `@F14`: `scans.test.ts` › git and gh output fixtures
- F66 — tag `@F66`: `collector.test.ts` › unknown status shows as needs you, state unknown, with the raw value
- F67 — tag `@F67`: `scans.test.ts` › own repo only, every 2 minutes
- F68 — tag `@F68`: `collector.test.ts` › files of several sessions merge into one list
- F69 — tag `@F69`: `scans.test.ts` › stored PR state and its age with no live mod session
- F70 — tag `@F70`: `backfill.test.ts` › asks skip tool results, slash commands and system notes
- F71 — tag `@F71`: `collector.test.ts` › done and merged count as complete
- F127 — tag `@F127`: `collector.test.ts` › lease taken when none is fresh, kept while fresh, dropped when another session holds it
- F128 — tag `@F128`: `collector.test.ts` › the holder polls every 5 seconds, refreshes the heartbeat and writes agents.json by temp file and rename
- F129 — tag `@F129`: `collector.test.ts` › a non-holder runs no call and reads agents.json; an old file counts as a failed read
- F130 — tag `@F130`: `safety.test.ts` › every write path is the session's own file, a lease file while held, a transcripts file or settings.json

</details>


### Asks and the question check

- [ ] **F15** (A1) When the owner sends a prompt, the session's own mod shall store it as the next ask, numbered from 1. At `prompt.submit` it shall classify the ask with `haiku` as "task" or "question". Screen/state: Session, Asks. Tag: `@F15`.
- [ ] **F16** (A1) The mod shall derive each ask's status, never set by hand. Words: "in progress", "needs you", "replied". Screen/state: Session, Asks. Tag: `@F16`.
- [ ] **F17** (A1, A2) When `turn.complete` fires in a session with the mod, the mod shall read the last assistant message from the transcript. Only when its final paragraph holds a "?" shall it ask `haiku` whether that message asks the owner a question (F132). Screen/state: needs you. Tag: `@F17`.
- [ ] **F18** (A1) The question check shall not depend on the classic `Stop` hook or any `classic.*` hook, which managed machines skip. Screen/state: needs you. Tag: `@F18`.
- [ ] **F19** (A1, A9) When `haiku` flags a question, the session shall show as needs you with the reason "asks a question". The next prompt clears the flag. Screen/state: Home, Needs you row. Tag: `@F19`.
- [ ] **F20** (A1, A10) While a session runs without the mod, the collector shall leave it done after a turn that asks a question. Screen/state: done. Tag: `@F20`.
- [ ] **F21** (A1) The collector shall carry tokens in and out, tool errors and retries for each session. A retry is the same tool call, same name and input, made directly after it failed. Screen/state: Home row; Session, Usage. Tag: `@F21`.
- [ ] **F72** (A1) While an ask's turn runs, the mod shall show the ask as "in progress", from the prompt until the turn ends. Screen/state: Session, Asks. Tag: `@F72`.
- [ ] **F73** (A1) While the session needs you during an ask, the mod shall show that ask as "needs you". Screen/state: Session, Asks. Tag: `@F73`.
- [ ] **F74** (A1) When an ask's turn ends, the mod shall show the ask as "replied", or as "needs you" when the question check flags it. Screen/state: Session, Asks. Tag: `@F74`.
- [ ] **F75** (A1) When the owner sends the next prompt, the mod shall close the previous ask as "replied". Screen/state: Session, Asks. Tag: `@F75`.
- [ ] **F132** (A1, A2) At `turn.complete`, with no "?" in the last message's final paragraph, the mod shall make no call and set no flag. Screen/state: done. Tag: `@F132`.

<details>
<summary>Scenario — proves the flag and its clearing</summary>

```gherkin
Scenario: a finished turn that asks the owner a question
  Given a session with the mod whose engine status is idle
  When  turn.complete fires and the last assistant message ends "Which branch should I use?"
  Then  the band counts the session as needs you with the reason "asks a question"
  And   the owner's next prompt returns it to running and clears the flag
```

</details>


<details>
<summary>Verification</summary>

- F15 — tag `@F15`: `asks.test.ts` › prompt stored in order, classified at prompt.submit
- F16 — tag `@F16`: `asks.test.ts` › ask status derives from session state
- F17 — tag `@F17`: `asks.test.ts` › turn.complete reads the transcript and calls the check only when the final paragraph holds a question mark
- F18 — tag `@F18`: `asks.test.ts` › the check registers no classic hook
- F19 — tag `@F19`: `asks.test.ts` › flagged question shows needs you
- F20 — tag `@F20`: `asks.test.ts` › a session without the mod stays done
- F21 — tag `@F21`: `collector.test.ts` › tokens, errors and retries from fixtures
- F72 — tag `@F72`: `asks.test.ts` › in progress from submit to turn end
- F73 — tag `@F73`: `asks.test.ts` › needs you while the session waits during the ask
- F74 — tag `@F74`: `asks.test.ts` › replied at turn end, or needs you when flagged
- F75 — tag `@F75`: `asks.test.ts` › the next prompt closes the previous ask as replied
- F132 — tag `@F132`: `asks.test.ts` › no question mark in the final paragraph: no model call, no flag

</details>


### Band, compact

- [ ] **F22** (A4, A6) When no view is stored, the band shall show the compact view. The chosen view is kept in the tracker's settings file for every session. Screen/state: Band compact. Tag: `@F22`.
- [ ] **F23** (A5, A6) The compact band shall show the buttons "Pane" (`p`) and "Details" (`d`) and no Board button. A letter hotkey acts only while the band or pane has the keyboard. Screen/state: Band compact. Tag: `@F23`.
- [ ] **F24** (A1, A6, A7) The compact band shall show needs you, running and done, PRs and the work segment, in that order, in one row. Words: "◐ 3 running · ✓ 2 done" and "4 PRs · 1 ✗". Screen/state: Band compact, All quiet. Tag: `@F24`.
- [ ] **F25** (A1, A6) While a session needs you, the band shall show the count in the warning colour, then the oldest waiting session. Words: "● 2 need you · web-app: fix login 6m". Screen/state: Band compact, Needs you. Tag: `@F25`.
- [ ] **F26** (A1) While this session is the oldest waiting, the band shall name it "this session". Words: "● 2 need you · this session 1m · web-app 6m". Screen/state: Band compact, Needs you, this session. Tag: `@F26`.
- [ ] **F27** (A7) The work segment shall show the milestone and its progress in sdlc-run, else the repo and session title. Words: "agent-tracker-1 2/4 · goal 14m" and "web-app · fix login redirect". Screen/state: Band compact, Work. Tag: `@F27`.
- [ ] **F28** (A4) If the line exceeds `bodyColumns`, then the band shall drop parts in a fixed order. Order: goal age, work segment, the words "running" and "done", PR segment, waiting title. When `bodyColumns` is below 40, only "● 2 need you" and the buttons stay. Screen/state: Band compact, narrow. Tag: `@F28`.
- [ ] **F29** (A6) When the owner runs `/tracker band off`, the band shall draw no row in any session until `/tracker band on`. The choice is kept in the settings file. Other mods' rows stay. Screen/state: Band, Hidden. Tag: `@F29`.
- [ ] **F30** (A1) When a session starts to wait, every open band shall show the new count by the next poll and its redraw. Screen/state: Band compact, Needs you. Tag: `@F30`.
- [ ] **F31** (A1, A12) The band's running count shall equal the running sessions in `claude agents --json`, for sessions whose status or state the collector knows. Screen/state: Band compact. Tag: `@F31`.
- [ ] **F32** (A1) While only this session is live, the band shall replace the running and PR segments with "only this session is running". The needs-you and work segments stay. Screen/state: Band compact, Alone. Tag: `@F32`.
- [ ] **F76** (A1, A6) While exactly one session needs you, the band shall write the count as "● 1 needs you · web-app: fix login 6m". Screen/state: Band compact, Needs you. Tag: `@F76`.
- [ ] **F77** (A1, A6) While no session needs you, the band shall write "0 need you" in the dim colour. Screen/state: Band compact, All quiet. Tag: `@F77`.
- [ ] **F78** (A1, A8) The band's PR segment shall count open and failing PRs in every repo with a session in 7 days. It uses each repo's latest stored scan. Screen/state: Band compact, PRs. Tag: `@F78`.

<details>
<summary>Scenario — proves the this-session case</summary>

```gherkin
Scenario: this session is the one that waits
  Given two sessions need you and this session has waited 1m
  And   the other, in web-app, has waited 6m
  When  this session's band draws
  Then  it reads "● 2 need you · this session 1m · web-app 6m"
```

</details>


<details>
<summary>Verification</summary>

- F22 — tag `@F22`: `band.test.ts` › default compact, view kept in settings.json
- F23 — tag `@F23`: `band.test.ts` › buttons are Pane and Details only, with hotkeys p and d
- F24 — tag `@F24`: `band.test.ts` › segment order
- F25 — tag `@F25`: `band.test.ts` › needs you with the oldest waiting session
- F26 — tag `@F26`: `band.test.ts` › this session names itself
- F27 — tag `@F27`: `band.test.ts` › work segment with and without sdlc-run
- F28 — tag `@F28`: `band.test.ts` › drop order at 115, 75 and 50 columns; below 40 bodyColumns
- F29 — tag `@F29`: `band.test.ts` › band off and on, kept in settings.json, every session
- F30 — tag `@F30`: `band.test.ts` › redraw by the next poll after a state change
- F31 — tag `@F31`: `band.test.ts` › running count against an agents fixture of known values
- F32 — tag `@F32`: `band.test.ts` › alone note replaces running and PRs
- F76 — tag `@F76`: `band.test.ts` › one needs you
- F77 — tag `@F77`: `band.test.ts` › zero need you, dim
- F78 — tag `@F78`: `band.test.ts` › PR count over repos with a session in 7 days

</details>


### Band, details

- [ ] **F33** (A6, A7) The details header shall name the repo and the milestone with its feature progress, or the session title and branch. The branch is left out when its name holds the milestone slug. Words: "calvins-claude-tools · agent-tracker-1 · 2 of 4 features complete" and "web-app · fix login redirect · feat/login". Screen/state: Band details, Header. Tag: `@F33`.
- [ ] **F34** (A7) The details header shall name what runs, each part only when above 0. Words: "goal 14m · 2 subagents · 1 background session". It goes on a second header line when the first is full. Screen/state: Band details, Header. Tag: `@F34`.
- [ ] **F35** (A6) The details view shall show four columns, each a count and one line, with no line at 0. Labels: "needs you", "running", "done", "PRs". Below 80 `bodyColumns` the lines drop except needs you. Screen/state: Band details. Tag: `@F35`.
- [ ] **F36** (A6) When the owner presses Copy (`c`) or runs `/tracker copy`, the mod shall copy the state as Markdown. Words: "Tracker state copied as Markdown". Screen/state: Band details, Copy. Tag: `@F36`.
- [ ] **F37** (A6) Where the surface is the desktop app, the details columns shall be one `Svg` whose `alt` lists every label and value. Screen/state: Band details, desktop. Tag: `@F37`.
- [ ] **F79** (A4, A6) When the owner runs `/tracker details` or `/tracker compact`, the mod shall switch the band to that view. Screen/state: Band compact; Band details. Tag: `@F79`.
- [ ] **F80** (A6) The details header shall show the buttons "Copy" (`c`), "Pane" (`p`) and "Compact" (`d`) at the right edge. Screen/state: Band details, Header. Tag: `@F80`.
- [ ] **F81** (A1, A6) The details columns shall carry one line each for needs you, running and done. Words: "web-app: fix login 6m" (the oldest waiting, or "this session"). Words: "api: migrate users 22m" (the longest running). Words: "docs: rename skills 3m ago" (the latest done). The needs-you line is in the normal colour and the others are dim. Screen/state: Band details. Tag: `@F81`.
- [ ] **F82** (A6, A8) The PRs column shall show the count "4 open" and the line "1 failing · 2 mergeable". Screen/state: Band details. Tag: `@F82`.
- [ ] **F83** (A4, A6) While `bodyColumns` is below 60, the details columns shall fold into two rows of two. Screen/state: Band details, narrow. Tag: `@F83`.
- [ ] **F84** (A4, A7) If the details header exceeds `bodyColumns`, then it shall cut parts in this order: branch, session title, milestone name. "2 of 4 features complete" then shortens to "2/4 complete", and what runs stays on its own line. Screen/state: Band details, narrow. Tag: `@F84`.
- [ ] **F85** (A6) The copied Markdown shall hold the four counts, then one line per needs-you and running session, then the open PRs with their state. A session line holds repo, title and wait or duration. It holds no path beyond a repo name. Screen/state: Band details, Copy. Tag: `@F85`.
- [ ] **F86** (A6) If the copy fails, then the mod shall show the toast "Copy failed: <reason>. Press Copy again or run /tracker copy." Screen/state: Band details, Copy failed. Tag: `@F86`.
- [ ] **F87** (A1, A6) While Loading, Partial or Stale applies, the details view shall show its line in one line under the header. Screen/state: Band details, Loading, Partial, Stale. Tag: `@F87`.

<details>
<summary>Verification</summary>

- F33 — tag `@F33`: `band.test.ts` › details header in both forms, branch left out when it holds the slug
- F34 — tag `@F34`: `band.test.ts` › what runs, zero parts hidden, second line when full
- F35 — tag `@F35`: `band.test.ts` › four columns, empty column
- F36 — tag `@F36`: `band.test.ts` › Copy writes Markdown and toasts
- F37 — tag `@F37`: `band.test.ts` › Svg alt lists every value
- F79 — tag `@F79`: `band.test.ts` › /tracker details and /tracker compact switch the view
- F80 — tag `@F80`: `band.test.ts` › details buttons and hotkeys
- F81 — tag `@F81`: `band.test.ts` › needs you, running and done lines
- F82 — tag `@F82`: `band.test.ts` › PRs count and line
- F83 — tag `@F83`: `band.test.ts` › columns fold below 60 bodyColumns
- F84 — tag `@F84`: `band.test.ts` › header cut order at 80 columns
- F85 — tag `@F85`: `band.test.ts` › Markdown content and no paths
- F86 — tag `@F86`: `band.test.ts` › copy failure toast
- F87 — tag `@F87`: `band.test.ts` › Loading, Partial and Stale line under the header

</details>


### Pane, Home

- [ ] **F38** (A8, A9, A11) When the owner presses Pane or runs `/tracker`, the mod shall open Home with focus on the first row. Words: title "Tracker". Screen/state: Pane Home. Tag: `@F38`.
- [ ] **F39** (A9) The Home page shall list its sections in this order: Needs you, Running, Done, Ended today, Repos. Screen/state: Pane Home. Tag: `@F39`.
- [ ] **F40** (A1, A9) The Needs you section shall list waiting sessions, longest wait first, with this session included. A row holds glyph, title, repo, branch, wait and reason, and errors and retries when above 0. Words: "● fix login redirect   web-app · feat/login · 6m · asks permission". Screen/state: Pane Home, Needs you. Tag: `@F40`.
- [ ] **F41** (A1) Home shall show at most 10 Done rows and 5 Ended today rows since local midnight, then a more line. Words: "and 4 more on the Repo pages". Screen/state: Pane Home. Tag: `@F41`.
- [ ] **F42** (A8, A10) Home shall end with a Repos line of every repo with a session in the last 7 days, most recent session first. Each entry is a button to its Repo page. It shows in every state. Words: "Repos: web-app 2 PRs · api · docs 1 PR". Screen/state: Pane Home. Tag: `@F42`.
- [ ] **F43** (A9) While the pane has the keyboard, Home shall keep its row order. A newly waiting session is added at the end of Needs you, marked "new". Home re-sorts when the keyboard leaves the pane or the pane reopens. Screen/state: Pane Home. Tag: `@F43`.
- [ ] **F44** (A1) While no session needs you and another session is live, Home shall show "Nothing needs you." Screen/state: Pane Home, All quiet. Tag: `@F44`.
- [ ] **F45** (A1) While only this session is live and it does not wait, Home shall show "Only this session is running. Sessions in other terminals show up here when they start." Screen/state: Pane Home, Empty. Tag: `@F45`.
- [ ] **F88** (A8, A9) The Home page shall show the button "Close" (`x`). The Session and Repo pages shall show "Back" (`b`), "Home" (`h`) and "Close" (`x`). Screen/state: Pane Home; Pane Session; Pane Repo. Tag: `@F88`.
- [ ] **F89** (A8) When the owner presses Back, the pane shall show the previous page with the same row focused. Screen/state: Pane Session; Pane Repo. Tag: `@F89`.
- [ ] **F90** (A8) When the owner presses Home, the pane shall show the Home page. Screen/state: Pane Session; Pane Repo. Tag: `@F90`.
- [ ] **F91** (A9) When the owner presses Close or `ctrl+x x`, the pane shall close and the keys return to the prompt. Screen/state: Pane Home; Pane Session; Pane Repo. Tag: `@F91`.
- [ ] **F92** (A9) While the pane has the keyboard, when the owner presses Escape, the mod shall hand the keyboard back to the prompt and keep the pane open. Close (`x`) or `ctrl+x x` closes it. Screen/state: Pane, all pages. Tag: `@F92`.
- [ ] **F93** (A1, A9) The Running section shall list running sessions under repo headings, the repo with the longest-running session first, then longest running. A row holds glyph, title, branch, turn time, tokens, and errors and retries when above 0. Words: "◐ migrate users   feat/users · 22m · 41k tokens · 2 errors · 1 retry". Screen/state: Pane Home, Running. Tag: `@F93`.
- [ ] **F94** (A1, A9) The Done section shall list sessions whose turn ended under repo headings, latest first. A row holds glyph, title, branch, time since, tokens, and errors and retries when above 0. Words: "✓ rename skills   main · 3m ago · 12k tokens". Screen/state: Pane Home, Done. Tag: `@F94`.
- [ ] **F95** (A1, A9) The Ended today section shall list sessions ended since local midnight, newest first. Words: "○ fix typo   main · ended 2h ago · 4k tokens". Screen/state: Pane Home, Ended today. Tag: `@F95`.
- [ ] **F96** (A9) While Running, Done or Ended today has no session, Home shall hide that section. Screen/state: Pane Home. Tag: `@F96`.
- [ ] **F97** (A8, A9) Each repo heading on Home shall be a button that opens the Repo page. Words: "web-app · 2 PRs · 1 failing". Screen/state: Pane Home, repo heading. Tag: `@F97`.
- [ ] **F98** (A8) If no repo has a session in 7 days, then the Repos line shall read "No repos yet." Screen/state: Pane Home, Repos. Tag: `@F98`.
- [ ] **F99** (A4, A9) While the pane is below 70 columns wide, a row shall take two lines: glyph and title, then branch, time and numbers. At 70 and wider a row takes one line. Only the title is cut, with "…". Screen/state: Pane Home, narrow. Tag: `@F99`.
- [ ] **F100** (A4, A9) While the pane is below 40 columns wide, the second line shall drop tokens first, then the branch. Wait, reason, errors and retries never drop, and a repo heading cuts its label, never its counts. Screen/state: Pane Home, narrow. Tag: `@F100`.
- [ ] **F101** (A1) Home shall show the time of the last read in the title row, to the minute. Words: "updated just now" and "updated 2m ago". Screen/state: Pane Home. Tag: `@F101`.
- [ ] **F102** (A1, A9) While only this session is live and it waits, Home shall list it under Needs you as "this session". The Empty line then does not show. Screen/state: Pane Home, Needs you. Tag: `@F102`.
- [ ] **F131** (A1, A10) While `claude agents --json` lists sessions that have no `sessions/` file, Home shall show a dim line under the title row. Words: "2 sessions run without the tracker. Questions they ask in text are not detected." For one session: "1 session runs without the tracker. Questions it asks in text are not detected." With none the line is hidden. Screen/state: Pane Home, notice. Tag: `@F131`.

<details>
<summary>Verification</summary>

- F38 — tag `@F38`: `pane.test.ts` › Pane button and /tracker open Home
- F39 — tag `@F39`: `pane.test.ts` › section order
- F40 — tag `@F40`: `pane.test.ts` › Needs you rows, longest wait first
- F41 — tag `@F41`: `pane.test.ts` › Done and Ended today caps
- F42 — tag `@F42`: `pane.test.ts` › Repos line in every state, entries are buttons
- F43 — tag `@F43`: `pane.test.ts` › frozen order, the "new" mark, re-sort on leave and reopen
- F44 — tag `@F44`: `pane.test.ts` › empty Needs you
- F45 — tag `@F45`: `pane.test.ts` › Empty, alone
- F88 — tag `@F88`: `pane.test.ts` › Close, Back and Home buttons per page, with hotkeys
- F89 — tag `@F89`: `pane.test.ts` › Back returns to the same row
- F90 — tag `@F90`: `pane.test.ts` › Home button
- F91 — tag `@F91`: `pane.test.ts` › Close and ctrl+x x
- F92 — tag `@F92`: `pane.test.ts` › two-step Escape
- F93 — tag `@F93`: `pane.test.ts` › Running rows, grouping and sort
- F94 — tag `@F94`: `pane.test.ts` › Done rows
- F95 — tag `@F95`: `pane.test.ts` › Ended today rows
- F96 — tag `@F96`: `pane.test.ts` › empty sections are hidden
- F97 — tag `@F97`: `pane.test.ts` › repo heading is a button with its words
- F98 — tag `@F98`: `pane.test.ts` › No repos yet
- F99 — tag `@F99`: `pane.test.ts` › two-line rows at 54 columns, one line at 70
- F100 — tag `@F100`: `pane.test.ts` › second line drops tokens then branch below 40
- F101 — tag `@F101`: `pane.test.ts` › updated just now and updated 2m ago
- F102 — tag `@F102`: `pane.test.ts` › alone and waiting
- F131 — tag `@F131`: `pane.test.ts` › without-the-tracker line for one and many sessions, hidden at none

</details>


### Pane, Session

- [ ] **F46** (A1, A8) The Session page shall show header, Running now, Usage, Milestone and Asks, in that order. It opens from a session row or `/tracker session <text>`. Screen/state: Pane Session, Live. Tag: `@F46`.
- [ ] **F47** (A1, A8) The Asks section shall list every ask oldest first, with number, kind, status and time. With none it shall read "No asks yet." A transcript session adds "Not classified: this session ran without the tracker." Screen/state: Pane Session, Asks. Tag: `@F47`.
- [ ] **F48** (A8, A10) The Milestone section shall appear only in an sdlc-run session. Words: "2 of 4 features complete". A feature in state `done` reads "complete", and one in state `merged` reads "merged". The other states read "to do", "building" and "blocked". Screen/state: Pane Session, Milestone. Tag: `@F48`.
- [ ] **F49** (A1) While a session is ended, its page shall offer "Copy resume command". It copies `cd '<folder>' && claude --resume <id>`, the folder single-quoted. A live session's page shall not offer it. A failed copy shows "Copy failed: <reason>. Press Copy resume command again." Screen/state: Pane Session, Ended. Tag: `@F49`.
- [ ] **F103** (A7, A8) The Session header shall show the title, below it the state line, the repo as a button to Repo, and the branch. Screen/state: Pane Session, header. Tag: `@F103`.
- [ ] **F104** (A1, A8) The Session state line shall show the state and the time in it. Words: "● needs you · 6m · asks permission", "◐ running · 22m", "✓ done · 3m ago" and "○ ended 4m ago". Screen/state: Pane Session, header. Tag: `@F104`.
- [ ] **F105** (A8) Where the session's branch has an open PR, the header shall show the branch and the link "#42" with its checks. Words: "feat/login · PR #42 ✗ checks failing". Screen/state: Pane Session, header. Tag: `@F105`.
- [ ] **F106** (A1) The Usage section shall show one line. Words: "41k tokens in · 9k out · 2 tool errors · 1 retry · started 10:42 · last activity 1m ago". Screen/state: Pane Session, Usage. Tag: `@F106`.
- [ ] **F107** (A7) Where something runs in the session, Running now shall list the goal first, then subagents, then background sessions. Words: "goal · 14m", "subagent · review-code-reviewer · running" and "background session · docs check · 2m". With nothing running the section is hidden. Screen/state: Pane Session, Running now. Tag: `@F107`.
- [ ] **F108** (A8) The Milestone section shall show the sentence from `milestone.md`, then "2 of 4 features complete", then one row per feature in milestone order. Words: "2  collector   complete". Screen/state: Pane Session, Milestone. Tag: `@F108`.
- [ ] **F109** (A4, A8) While the pane is 70 columns or wider, an ask row shall show number, kind, status, time and the wrapped text. Words: "1  task      replied       add a compact view". Screen/state: Pane Session, Asks. Tag: `@F109`.
- [ ] **F110** (A4, A8) While the pane is below 70 columns or the zoom is 150 percent, an ask row shall take two lines. The first holds number, kind, status and time. The second holds the text, wrapped and cut at 4 lines with "…". Screen/state: Pane Session, Asks, narrow. Tag: `@F110`.
- [ ] **F111** (A1) When a session leaves `claude agents` while its page is open, the page shall show it as ended, with the time. Screen/state: Pane Session, Ended. Tag: `@F111`.
- [ ] **F112** (A1) When the owner presses Copy resume command (`r`), the mod shall copy the command and show the toast "Resume command copied". Screen/state: Pane Session, Ended. Tag: `@F112`.
- [ ] **F113** (A8) The Session page shall show the breadcrumb "Home › web-app › fix login redirect", and the Repo page "Home › web-app". Screen/state: Pane Session; Pane Repo. Tag: `@F113`.

<details>
<summary>Verification</summary>

- F46 — tag `@F46`: `pane.test.ts` › Session section order
- F47 — tag `@F47`: `pane.test.ts` › asks in order and the empty line
- F48 — tag `@F48`: `pane.test.ts` › Milestone section only with sdlc-run; done reads complete, merged reads merged
- F49 — tag `@F49`: `pane.test.ts` › resume command for ended sessions only, folder with a space quoted
- F103 — tag `@F103`: `pane.test.ts` › Session header fields
- F104 — tag `@F104`: `pane.test.ts` › state line in each state
- F105 — tag `@F105`: `pane.test.ts` › branch and PR link
- F106 — tag `@F106`: `pane.test.ts` › Usage line
- F107 — tag `@F107`: `pane.test.ts` › Running now rows and order, hidden when empty
- F108 — tag `@F108`: `pane.test.ts` › Milestone sentence, count and feature rows
- F109 — tag `@F109`: `pane.test.ts` › ask row at 70 columns
- F110 — tag `@F110`: `pane.test.ts` › ask row at 54 columns, cut at 4 lines
- F111 — tag `@F111`: `pane.test.ts` › open page turns ended
- F112 — tag `@F112`: `pane.test.ts` › resume toast
- F113 — tag `@F113`: `pane.test.ts` › breadcrumbs

</details>


### Pane, Repo

- [ ] **F50** (A8, A10) The Repo page shall show Open PRs, Worktrees and Ended, in that order. Ended lists the last 7 days. It opens from a repo heading or `/tracker repo <name>`. Screen/state: Pane Repo. Tag: `@F50`.
- [ ] **F51** (A1, A8) The Open PRs section shall list failing PRs first, then newest by creation time. Each row shows number, title, checks, review and mergeable state. A session button shows only when a session ran on that branch. Screen/state: Pane Repo, Open PRs. Tag: `@F51`.
- [ ] **F114** (A8) Each Open PRs row shall show the number as a link that opens the PR in the browser. Words: "#42 fix login redirect · ✗ checks failing · review requested · conflicts · session: fix login". Screen/state: Pane Repo, Open PRs. Tag: `@F114`.
- [ ] **F115** (A8) A PR row shall use these words. Checks: "✓ checks pass", "✗ checks failing", "checks running". Review: "approved", "changes requested", "review requested", "no review". Mergeable: "↓ mergeable", "conflicts", "mergeable unknown". Screen/state: Pane Repo, Open PRs. Tag: `@F115`.
- [ ] **F116** (A4, A8) While the pane is below 70 columns or the zoom is 150 percent, a PR row shall take two lines. The first holds number, title and checks, and the second review, mergeable and the session button. Failing checks show in the error colour, never dim. Screen/state: Pane Repo, Open PRs, narrow. Tag: `@F116`.
- [ ] **F117** (A8, A9) The Worktrees section shall list each worktree with its branch and its live sessions as rows. The main checkout comes first, then by most recent session. Words: "main checkout · main" and ".worktrees/login · feat/login". Screen/state: Pane Repo, Worktrees. Tag: `@F117`.
- [ ] **F118** (A8) If the repo has no worktrees to list, then the Worktrees section shall read "No worktrees found." Screen/state: Pane Repo, Worktrees. Tag: `@F118`.
- [ ] **F119** (A8) If `gh` works and no PR is open, then the Open PRs section shall read "No open PRs." Screen/state: Pane Repo, No PRs. Tag: `@F119`.
- [ ] **F120** (A8) The Ended section shall list the sessions ended in the last 7 days, newest first, and hide when there are none. Words: "○ rename skills   main · ended 2d ago · 12k tokens". Screen/state: Pane Repo, Ended. Tag: `@F120`.

<details>
<summary>Verification</summary>

- F50 — tag `@F50`: `pane.test.ts` › Repo section order
- F51 — tag `@F51`: `pane.test.ts` › PR sort by creation time and row fields
- F114 — tag `@F114`: `pane.test.ts` › PR row words and link
- F115 — tag `@F115`: `pane.test.ts` › PR states
- F116 — tag `@F116`: `pane.test.ts` › PR row at 54 columns, failing checks not dim
- F117 — tag `@F117`: `pane.test.ts` › Worktrees rows and sort
- F118 — tag `@F118`: `pane.test.ts` › No worktrees found
- F119 — tag `@F119`: `pane.test.ts` › No open PRs
- F120 — tag `@F120`: `pane.test.ts` › Ended rows on Repo

</details>


### Errors and stale data

- [ ] **F52** (A1) If `claude agents --json` fails twice in a row, then the band shall dim the last counts. It shows "session list unavailable · counts from 2m ago". Below 60 `bodyColumns` it reads "stale 2m". This text takes the work segment's place and never drops. Screen/state: Band Stale. Tag: `@F52`.
- [ ] **F53** (A1) While the first read is pending, the band and Home shall show "Reading sessions…" Screen/state: Band Loading; Home Loading. Tag: `@F53`.
- [ ] **F54** (A1) If `gh` is missing or signed out, then the band shall drop its PR segment. The pane shall show "PRs not shown: gh is not installed or not signed in. Run gh auth login to see them." Home then shows repo headings without PR counts. Screen/state: Band Partial; Home Partial; Repo No gh. Tag: `@F54`.
- [ ] **F55** (A10) If a transcript cannot be read, then the session shall show without its asks and numbers. It is read again on the next change. Screen/state: Session, From transcript. Tag: `@F55`.
- [ ] **F56** (A1) If the question check fails, then the session shall show as done, without the "asks a question" flag. Screen/state: done. Tag: `@F56`.
- [ ] **F57** (A1, A2) If classifying an ask fails, then the mod shall keep the ask and show its kind as "not classified". Screen/state: Session, Asks. Tag: `@F57`.
- [ ] **F58** (A1) If the mod cannot write this session's file, then it shall show a status line. Words: "Tracker could not save this session's record. Asks from now on are not kept. Check that the agent-tracker folder in your Claude folder can be written." Screen/state: status line. Tag: `@F58`.
- [ ] **F59** (A8) If `/tracker session <text>` matches nothing, then the pane shall show a not-found line. Words: "No session matches \"<text>\". Pick one on Home." Screen/state: Session Not found. Tag: `@F59`.
- [ ] **F121** (A8) If `/tracker repo <text>` matches nothing, then the pane shall show a not-found line. Words: "No repo named \"<text>\" has had a session. Pick one on Home." Screen/state: Repo Not found. Tag: `@F121`.
- [ ] **F122** (A8) When the owner runs `/tracker session <text>`, the pane shall match the title by case-insensitive substring, else the id by prefix. Several matches open the most recent. `/tracker repo <text>` uses the same rule on repo names. Screen/state: Session; Repo. Tag: `@F122`.
- [ ] **F123** (A1) If `claude agents --json` fails twice in a row, then Home shall dim the last list and show a top line. Words: "Session list unavailable. Showing what was read 2m ago. Retrying every 5 seconds; if it keeps failing, update Claude Code." Screen/state: Home Stale. Tag: `@F123`.

<details>
<summary>Verification</summary>

- F52 — tag `@F52`: `band.test.ts` › stale after two failed reads, and "stale 2m" below 60 columns
- F53 — tag `@F53`: `band.test.ts` › loading line; `pane.test.ts` › loading line
- F54 — tag `@F54`: `scans.test.ts` › gh missing; `band.test.ts` › no PR segment; `pane.test.ts` › partial line
- F55 — tag `@F55`: `backfill.test.ts` › unreadable transcript
- F56 — tag `@F56`: `asks.test.ts` › check failure leaves done
- F57 — tag `@F57`: `asks.test.ts` › classify failure keeps the ask
- F58 — tag `@F58`: `collector.test.ts` › write failure sets the status line
- F59 — tag `@F59`: `pane.test.ts` › session not found line
- F121 — tag `@F121`: `pane.test.ts` › repo not found line
- F122 — tag `@F122`: `pane.test.ts` › title substring, id prefix, several matches, repo names
- F123 — tag `@F123`: `pane.test.ts` › stale line on Home

</details>


### Words, times and colour

- [ ] **F124** (A6, A9) The tracker shall put a word or a count beside every glyph, so colour never carries meaning alone. Screen/state: all. Tag: `@F124`.
- [ ] **F125** (A1, A6) The tracker shall write durations to the minute. They read "<1m", "6m" below an hour, "2h 10m" below a day, then "3d". Screen/state: all. Tag: `@F125`.
- [ ] **F126** (A1, A6) While the band or a pane is shown, it shall redraw once a minute, so times stay true. Screen/state: Band; Pane. Tag: `@F126`.

<details>
<summary>Verification</summary>

- F124 — tag `@F124`: `band.test.ts` and `pane.test.ts` › every glyph has a word or count beside it
- F125 — tag `@F125`: `band.test.ts` › duration format at 6m, 2h 10m and 3d
- F126 — tag `@F126`: `band.test.ts` and `pane.test.ts` › redraw after one minute with no data change

</details>


### Observe only and cost

- [ ] **F60** (A2) Every model call shall pin `haiku` from one constant, including any `claude -p` call. Screen/state: none. Tag: `@F60`.
- [ ] **F61** (A2) The mod shall make at most one classification call per ask and one question check per completed turn. A turn whose final paragraph holds no "?" gets no check. Screen/state: none. Tag: `@F61`.
- [ ] **F62** (A1) The tracker shall never write to a session, git, gh or bd: no hidden note, no automatic continue, no queued answer. Screen/state: none. Tag: `@F62`.
- [ ] **F63** (A12) The tracker shall write no file outside `~/.claude/agent-tracker/`. The clipboard is not a file. Screen/state: store. Tag: `@F63`.
- [ ] **F64** (A12; rules PUB-1) The committed fixtures and screenshots shall hold no internal names, people, URLs or local paths. Screen/state: none. Tag: `@F64`.
- [ ] **F65** (A5; rules PUB-2) The tracker shall use no Artifact tool, Claude Docs or hosted page, and open no server or port. Screen/state: none. Tag: `@F65`.

<details>
<summary>Verification</summary>

- F60 — tag `@F60`: `safety.test.ts` › every model call passes the MODEL constant
- F61 — tag `@F61`: `safety.test.ts` › call counts for one ask and one turn, none for a turn without a question mark
- F62 — tag `@F62`: `safety.test.ts` › no write call reaches a session
- F63 — tag `@F63`: `safety.test.ts` › every fs write path is under the folder
- F64 — tag `@F64`: `tests/test_plugin.py` (existing public repo grep) over the new files
- F65 — tag `@F65`: `tests/test_no_claude_ai_publishing.py` (existing) over the new files; `safety.test.ts` › no listener

</details>

## Verification

What proves the whole change, beyond the per-fact checks.

- **Automated:** `python3 -m unittest discover -s tests && scripts/run-plugin-tests.sh` exits 0, and `claude plugin test plugins/agent-tracker` passes.
- **Success measure:** by hand, 5 spot checks where the band's needs-you count matches the sessions the owner sees waiting. Waiting means a permission prompt or a question to the owner. Target 5 of 5 by 2026-12-04. The owner revised it on 2026-11-14 in `intent.md`.
- **Manual:** open the band and the pane at 100 percent and 150 percent in the terminal, and the details columns on the desktop app.

## Out of scope

- A5 — the web page and the Board button belong to milestone 2. The band shows no Board button before then.
- A3 — "you should know" and "decided without you" items belong to milestone 3. Milestone 1 shows nothing for them.
- Plan progress, ticket links and superseded tasks — milestone 3.
- Anything from `bd` on screen — Beads links come with milestone 3, so the bd scan in design step 2 builds no screen here.
- Notifications, sound and toasts when a session waits — J10 is met by the band in every session.
- Any write to an agent, session, task, worktree or repo — no-go N1 and N6.
- The project name in the band header — the milestone names the work, and the project slug adds width. Milestone 1 shows repo and milestone only.
- A milestone and feature view on the Repo page (J12) — milestone 2's web page has the Milestone pages. Milestone 1 reaches a milestone through a session's Milestone section.
- Scheduled wake-ups — they come from the classic `Stop` hook, which managed machines skip. Milestone 1 shows subagents and background sessions.

## Assumptions

- **Clarify, decided by the agent on 2026-11-13** (technical calls, no owner question needed):
  - **Reason text (F4):** "asks permission" only when `waitingFor` matches the permission value the builder records from a real waiting session at build. With no waiting session then, "asks permission" never shows, any `waitingFor` gives "waiting", and the build logs it to `questions.md`.
  - **Goal end (F11):** a mod sees no goal-end event, so the goal age shows only while the session is running or needs you.
  - **Retry (F21):** the same tool name and input called directly after that call failed.
  - **Background tasks (F11):** where classic hooks are skipped, only subagents (`$.agent.list()`) and background sessions from `claude agents --json` are shown. Wake-ups are out of scope.
  - **Who classifies (F15, F17, F132):** the session's own mod, with `haiku` from the one constant. It classifies at `prompt.submit`. At `turn.complete` it checks only when the final paragraph holds a "?".
  - **Collector topology (F1, F67, F68, F127 to F130):** one session polls. Its mod takes a lease file, `poller.json`, when none is fresh (older than 15 seconds). The holder polls `claude agents --json` every 5 seconds and writes `agents.json`; every other session reads it. Each session scans git and gh only for its own repo, every 2 minutes, and writes its own file. The pane merges all files. A repo with no live mod session shows its last stored PR state with its age.
  - **Ask status (F72 to F75):** in progress from the prompt until the turn ends. Needs you while the session needs you. Replied at turn end, or needs you when flagged.
  - **Copy as Markdown (F85):** the four counts, one line per needs-you and running session, then open PRs with state. It holds no path beyond repo names.

- **Mod API (Claude Code 2.1.323 engine types, checked 2026-11-13):** `turn.complete`, `bodyColumns`, `waitingFor`, `$.agent.list()`, and `Svg` on the desktop only exist. A letter hotkey fires only while the band or pane has the keyboard. Managed machines skip `classic.*` hooks, as seen in this repo's own session.
- **Feature "complete":** a feature in state `done` or `merged` counts as complete (F71). It is the owner's word for finished.
- **Spec wins on the band:** the design file's Board button and you-should-know columns are left out, because the design file says the spec wins.
- **No classification outside a session:** a session without the mod shows "not classified". The spec says so and it saves a model call.
- **Without the mod:** the question check never runs, so such a session stays done. That is the owner's answer. Home says how many sessions run this way (F131).
- **Unknown state:** a status or state the collector does not know counts as needs you, so a changed engine never hides a waiting session (F66). A technical call of 2026-11-14, taken over counting it as running.
- **Plugin folder:** the design file says the line "one plugin" in `CLAUDE.md` is updated when the mod lands. `plan.md` names `plugins/agent-tracker/`.
- **Test layout:** `*.test.ts` files under `plugins/agent-tracker/`, the tag and the change tag in each title.

## Deferred

none. The Medium and Low findings from `spec/validation.md` go to `plan.md`.

## Open questions

None. The three markers were answered under Assumptions. The intent asked whether `blocked` and `waiting` mean a permission prompt. The checked 2.1.323 mapping in `spec/ia.md` answers it: both mean needs you, and `waitingFor` gives the reason.
