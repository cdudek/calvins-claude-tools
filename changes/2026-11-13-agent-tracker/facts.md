---
linear: none
type: facts
change: 2026-11-13-agent-tracker
design: docs/designs/agent-tracker.md
author: Calvin Dudek
status: draft
reviewed_by: null
approved_at: null
created: 2026-11-13
---

# Facts: Agent tracker, milestone 1

## Goal

Open any Claude Code session and see each session's repo, work and state, and which need you, in a band and a pane. This is one change because the collector, backfill, band and pane share one store.

## Acceptance criteria

Rules: `sdlc.json` defines no `rules` list, so the two rules from `CLAUDE.md` are named here. PUB-1 is the public repo rule: no internal names, people, URLs or local paths. PUB-2 is the never-publish-to-claude.ai rule. A fact with no rule cites asks only.

Tests are `*.test.ts` files run by `claude plugin test`, not browser E2E. The tag goes in the test title beside `@2026-11-13-agent-tracker`. Words in quotes are the strings in `spec/screens.md`. Test file names are proposed here and `plan.md` fixes the paths.

### Collector and states

- [ ] **F1** (A1, A10, A12) While the mod runs, the collector shall list every session from `claude agents --json` every 5 seconds. It shall list sessions without the mod too. Screen/state: all. Tag: `@F1`.
- [ ] **F2** (A1, A7) While an interactive session reports status `busy` or a background session reports state `working`, the collector shall mark it running. Screen/state: running. Tag: `@F2`.
- [ ] **F3** (A1, A9) While an interactive session reports status `waiting` or a background one reports state `blocked`, the collector shall mark it needs you. Screen/state: needs you. Tag: `@F3`.
- [ ] **F4** (A1, A9) While a session needs you, the collector shall show a reason. It is "asks permission" when `waitingFor` names a permission prompt, "asks a question" when the question check flagged it, else "waiting". Screen/state: Home, Needs you row. Tag: `@F4`.
- [ ] **F5** (A1) While an interactive session reports status `idle`, the collector shall mark it done. Screen/state: done. Tag: `@F5`.
- [ ] **F6** (A1) When a session reports state `done` or leaves the list, the collector shall mark it ended. Screen/state: ended. Tag: `@F6`.
- [ ] **F7** (A1, A7) The collector shall name each session's repo by the folder of its git top-level path. Two repos with one folder name get the parent folder added, as `work/web-app`. Screen/state: Home, repo heading. Tag: `@F7`.
- [ ] **F8** (A1, A12) The mod shall keep one JSON file per session at `~/.claude/agent-tracker/sessions/<sessionId>.json`, rewritten whole by that session's own mod. Screen/state: store. Tag: `@F8`.
- [ ] **F9** (A7, A8) Where a session's branch belongs to an sdlc-run milestone, the collector shall read its sentence and features. Each feature carries its state. Screen/state: Session, Milestone. Tag: `@F9`.
- [ ] **F10** (A10, A12) Where a repo has no `changes/` folder, the collector shall use the session title and branch. Screen/state: band header, without sdlc-run. Tag: `@F10`.
- [ ] **F11** (A7) While a goal or subagents run, the collector shall report the goal's age and each subagent's status. The goal age shows only while the session runs or needs you. Screen/state: Running now. Tag: `@F11`.
- [ ] **F12** (A10, A12) Where a session has no file, the backfill shall read its transcript under `~/.claude/projects/`. It takes tokens, branch, folder, title, tool errors and asks. It marks each ask "not classified" and makes no model call. Screen/state: Session, from transcript. Tag: `@F12`.
- [ ] **F13** (A12) If a transcript is over 4 MiB, then the backfill shall read it by search, not whole. Screen/state: store. Tag: `@F13`.
- [ ] **F14** (A1, A8) The collector shall read each repo's worktrees with `git worktree list`. It shall read open PRs with `gh pr list --json`, with checks, review and mergeable state. Screen/state: Repo. Tag: `@F14`.

<details>
<summary>Verification</summary>

- F1 — tag `@F1`: `collector.test.ts` › lists sessions with and without the mod
- F2 — tag `@F2`: `collector.test.ts` › busy and working map to running
- F3 — tag `@F3`: `collector.test.ts` › waiting and blocked map to needs you
- F4 — tag `@F4`: `collector.test.ts` › waitingFor becomes the reason
- F5 — tag `@F5`: `collector.test.ts` › idle maps to done
- F6 — tag `@F6`: `collector.test.ts` › done state or absence maps to ended
- F7 — tag `@F7`: `collector.test.ts` › repo label, same folder name twice
- F8 — tag `@F8`: `collector.test.ts` › one file per session, rewritten whole
- F9 — tag `@F9`: `collector.test.ts` › reads a milestone.md fixture
- F10 — tag `@F10`: `collector.test.ts` › repo without a changes folder
- F11 — tag `@F11`: `collector.test.ts` › goal age and subagents
- F12 — tag `@F12`: `backfill.test.ts` › fixture transcript fields
- F13 — tag `@F13`: `backfill.test.ts` › transcript over 4 MiB
- F14 — tag `@F14`: `scans.test.ts` › git and gh output fixtures

</details>


### Asks and the question check

- [ ] **F15** (A1) When the owner sends a prompt, the mod shall store it as the next ask, numbered from 1. Its kind is "task" or "question". Screen/state: Session, Asks. Tag: `@F15`.
- [ ] **F16** (A1) The mod shall derive each ask's status, never set by hand. Words: "in progress", "needs you", "replied". Screen/state: Session, Asks. Tag: `@F16`.
- [ ] **F17** (A1, A2) When `turn.complete` fires in a session with the mod, the mod shall read the last assistant message from the transcript. It shall ask `haiku` whether that message asks the owner a question. Screen/state: needs you. Tag: `@F17`.
- [ ] **F18** (A1) The question check shall not depend on the classic `Stop` hook or any `classic.*` hook, which managed machines skip. Screen/state: needs you. Tag: `@F18`.
- [ ] **F19** (A1, A9) When `haiku` flags a question, the session shall show as needs you with the reason "asks a question". The next prompt clears the flag. Screen/state: Home, Needs you row. Tag: `@F19`.
- [ ] **F20** (A1, A10) While a session runs without the mod, the collector shall leave it done after a turn that asks a question. Screen/state: done. Tag: `@F20`.
- [ ] **F21** (A1) The collector shall carry tokens in and out, tool errors and retries for each session. A retry is the same tool call, same name and input, made directly after it failed. Screen/state: Home row; Session, Usage. Tag: `@F21`.

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

- F15 — tag `@F15`: `asks.test.ts` › prompt stored in order with a kind
- F16 — tag `@F16`: `asks.test.ts` › ask status derives from session state
- F17 — tag `@F17`: `asks.test.ts` › turn.complete reads the transcript and calls the check
- F18 — tag `@F18`: `asks.test.ts` › the check registers no classic hook
- F19 — tag `@F19`: `asks.test.ts` › flagged question shows needs you
- F20 — tag `@F20`: `asks.test.ts` › a session without the mod stays done
- F21 — tag `@F21`: `collector.test.ts` › tokens, errors and retries from fixtures

</details>


### Band, compact

- [ ] **F22** (A4, A6) When no view is stored, the band shall show the compact view. The chosen view is kept in the tracker's settings file for every session. Screen/state: Band compact. Tag: `@F22`.
- [ ] **F23** (A5, A6) The compact band shall show the buttons "Pane" and "Details" and no Board button. Screen/state: Band compact. Tag: `@F23`.
- [ ] **F24** (A1, A6, A7) The compact band shall show needs you, running and done, PRs and the work segment, in that order, in one row. Words: "◐ 3 running · ✓ 2 done" and "4 PRs · 1 ✗". Screen/state: Band compact, All quiet. Tag: `@F24`.
- [ ] **F25** (A1, A6) While a session needs you, the band shall show the count in the warning colour, then the oldest waiting session. Words: "● 2 need you · web-app: fix login 6m". Screen/state: Band compact, Needs you. Tag: `@F25`.
- [ ] **F26** (A1) While this session is the oldest waiting, the band shall name it "this session". Words: "● 2 need you · this session 1m · web-app 6m". Screen/state: Band compact, Needs you, this session. Tag: `@F26`.
- [ ] **F27** (A7) The work segment shall show the milestone and its progress in sdlc-run, else the repo and session title. Words: "agent-tracker-1 2/4 · goal 14m" and "web-app · fix login redirect". Screen/state: Band compact, Work. Tag: `@F27`.
- [ ] **F28** (A4) If the line exceeds `bodyColumns`, then the band shall drop parts in a fixed order. Order: goal age, work segment, the words "running" and "done", PR segment, waiting title. Below 40 columns only "● 2 need you" and the buttons stay. Screen/state: Band compact, narrow. Tag: `@F28`.
- [ ] **F29** (A6) When the owner runs `/tracker band off`, the band shall draw no row until `/tracker band on`. Other mods' rows stay. Screen/state: Band, Hidden. Tag: `@F29`.
- [ ] **F30** (A1) When a session starts to wait, the band in every open session shall show the new count within 5 seconds. Screen/state: Band compact, Needs you. Tag: `@F30`.
- [ ] **F31** (A1, A12) The band's running count shall equal the running sessions in `claude agents --json`. Screen/state: Band compact. Tag: `@F31`.
- [ ] **F32** (A1) While only this session is live, the band shall keep the needs-you segment and add "only this session is running". Screen/state: Band compact, Alone. Tag: `@F32`.

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
- F23 — tag `@F23`: `band.test.ts` › buttons are Pane and Details only
- F24 — tag `@F24`: `band.test.ts` › segment order
- F25 — tag `@F25`: `band.test.ts` › needs you with the oldest waiting session
- F26 — tag `@F26`: `band.test.ts` › this session names itself
- F27 — tag `@F27`: `band.test.ts` › work segment with and without sdlc-run
- F28 — tag `@F28`: `band.test.ts` › drop order at 115, 75 and 50 columns
- F29 — tag `@F29`: `band.test.ts` › band off and on
- F30 — tag `@F30`: `band.test.ts` › redraw within 5 seconds of a state change
- F31 — tag `@F31`: `band.test.ts` › running count against an agents fixture; by hand, 5 spot checks against `claude agents --json`
- F32 — tag `@F32`: `band.test.ts` › alone note

</details>


### Band, details

- [ ] **F33** (A6, A7) The details header shall name the repo and the milestone with its feature progress, or the session title and branch. Words: "calvins-claude-tools · agent-tracker-1 · 2 of 4 features complete" and "web-app · fix login redirect · feat/login". Screen/state: Band details, Header. Tag: `@F33`.
- [ ] **F34** (A7) The details header shall name what runs, each part only when above 0. Words: "goal 14m · 2 subagents · 1 background task". Screen/state: Band details, Header. Tag: `@F34`.
- [ ] **F35** (A6) The details view shall show four columns, each a count and one line, with no line at 0. Labels: "needs you", "running", "done", "PRs". Below 80 columns the lines drop except needs you. Screen/state: Band details. Tag: `@F35`.
- [ ] **F36** (A6) When the owner presses Copy or runs `/tracker copy`, the mod shall copy the state as Markdown. Words: "Tracker state copied as Markdown". Screen/state: Band details, Copy. Tag: `@F36`.
- [ ] **F37** (A6) Where the surface is the desktop app, the details columns shall be one `Svg` whose `alt` lists every label and value. Screen/state: Band details, desktop. Tag: `@F37`.

<details>
<summary>Verification</summary>

- F33 — tag `@F33`: `band.test.ts` › details header in both forms
- F34 — tag `@F34`: `band.test.ts` › what runs, zero parts hidden
- F35 — tag `@F35`: `band.test.ts` › four columns, empty column
- F36 — tag `@F36`: `band.test.ts` › Copy writes Markdown and toasts
- F37 — tag `@F37`: `band.test.ts` › Svg alt lists every value

</details>


### Pane, Home

- [ ] **F38** (A8, A9, A11) When the owner presses Pane or runs `/tracker`, the mod shall open Home with focus on the first row. Words: title "Tracker". Screen/state: Pane Home. Tag: `@F38`.
- [ ] **F39** (A9) The Home page shall list its sections in this order: Needs you, Running, Done, Ended today, Repos. Screen/state: Pane Home. Tag: `@F39`.
- [ ] **F40** (A1, A9) The Needs you section shall list waiting sessions, longest wait first, with this session included. Words: "● fix login redirect   web-app · feat/login · 6m · asks permission". Screen/state: Pane Home, Needs you. Tag: `@F40`.
- [ ] **F41** (A1) Home shall show at most 10 Done rows and 5 Ended today rows since local midnight, then a more line. Words: "and 4 more on the Repo pages". Screen/state: Pane Home. Tag: `@F41`.
- [ ] **F42** (A8, A10) Home shall end with a Repos line of every repo with a session in the last 7 days. It shows in every state. Words: "Repos: web-app 2 PRs · api · docs 1 PR". Screen/state: Pane Home. Tag: `@F42`.
- [ ] **F43** (A9) While the pane has the keyboard, Home shall keep its row order. A newly waiting session is added at the end of Needs you, marked "new". Screen/state: Pane Home. Tag: `@F43`.
- [ ] **F44** (A1) While no session needs you, Home shall show "Nothing needs you." Screen/state: Pane Home, All quiet. Tag: `@F44`.
- [ ] **F45** (A1) While only this session is live, Home shall show "Only this session is running. Sessions in other terminals show up here when they start." Screen/state: Pane Home, Empty. Tag: `@F45`.

<details>
<summary>Verification</summary>

- F38 — tag `@F38`: `pane.test.ts` › Pane button and /tracker open Home
- F39 — tag `@F39`: `pane.test.ts` › section order
- F40 — tag `@F40`: `pane.test.ts` › Needs you rows, longest wait first
- F41 — tag `@F41`: `pane.test.ts` › Done and Ended today caps
- F42 — tag `@F42`: `pane.test.ts` › Repos line in every state
- F43 — tag `@F43`: `pane.test.ts` › frozen order and the "new" mark
- F44 — tag `@F44`: `pane.test.ts` › empty Needs you
- F45 — tag `@F45`: `pane.test.ts` › Empty, alone

</details>


### Pane, Session

- [ ] **F46** (A1, A8) The Session page shall show header, Running now, Usage, Milestone and Asks, in that order. It opens from a session row or `/tracker session <text>`. Screen/state: Pane Session, Live. Tag: `@F46`.
- [ ] **F47** (A1, A8) The Asks section shall list every ask oldest first, with number, kind, status and time. With none it shall read "No asks yet." A transcript session adds "Not classified: this session ran without the tracker." Screen/state: Pane Session, Asks. Tag: `@F47`.
- [ ] **F48** (A8, A10) The Milestone section shall appear only in an sdlc-run session. Words: "2 of 4 features complete"; states "to do", "building", "complete", "merged", "blocked". Screen/state: Pane Session, Milestone. Tag: `@F48`.
- [ ] **F49** (A1) While a session is ended, its page shall offer "Copy resume command", which copies `cd <folder> && claude --resume <id>`. A live session's page shall not offer it. Screen/state: Pane Session, Ended. Tag: `@F49`.

<details>
<summary>Verification</summary>

- F46 — tag `@F46`: `pane.test.ts` › Session section order
- F47 — tag `@F47`: `pane.test.ts` › asks in order and the empty line
- F48 — tag `@F48`: `pane.test.ts` › Milestone section only with sdlc-run
- F49 — tag `@F49`: `pane.test.ts` › resume command for ended sessions only

</details>


### Pane, Repo

- [ ] **F50** (A8, A10) The Repo page shall show Open PRs, Worktrees and Ended, in that order. Ended lists the last 7 days. It opens from a repo heading or `/tracker repo <name>`. Screen/state: Pane Repo. Tag: `@F50`.
- [ ] **F51** (A1, A8) The Open PRs section shall list failing PRs first, then newest. Each row shows number, title, checks, review and mergeable state. A session button shows only when a session ran on that branch. Screen/state: Pane Repo, Open PRs. Tag: `@F51`.

<details>
<summary>Verification</summary>

- F50 — tag `@F50`: `pane.test.ts` › Repo section order
- F51 — tag `@F51`: `pane.test.ts` › PR sort and row words

</details>


### Errors and stale data

- [ ] **F52** (A1) If `claude agents --json` fails twice in a row, then the band and Home shall dim the last good data, with its age. Words: "session list unavailable · counts from 2m ago". Screen/state: Band Stale; Home Stale. Tag: `@F52`.
- [ ] **F53** (A1) While the first read is pending, the band and Home shall show "Reading sessions…" Screen/state: Band Loading; Home Loading. Tag: `@F53`.
- [ ] **F54** (A1) If `gh` is missing or signed out, then the band shall drop its PR segment. The pane shall show "PRs not shown: gh is not installed or not signed in. Run gh auth login to see them." Screen/state: Band Partial; Home Partial; Repo No gh. Tag: `@F54`.
- [ ] **F55** (A10) If a transcript cannot be read, then the session shall show without its asks and numbers. It is read again on the next change. Screen/state: Session, From transcript. Tag: `@F55`.
- [ ] **F56** (A1) If the question check fails, then the session shall show as done, without the "asks a question" flag. Screen/state: done. Tag: `@F56`.
- [ ] **F57** (A1, A2) If classifying an ask fails, then the mod shall keep the ask and show its kind as "not classified". Screen/state: Session, Asks. Tag: `@F57`.
- [ ] **F58** (A1) If the mod cannot write this session's file, then it shall show a status line. Words: "Tracker could not save this session's record. Asks from now on are not kept. Check that the agent-tracker folder in your Claude folder can be written." Screen/state: status line. Tag: `@F58`.
- [ ] **F59** (A8) If `/tracker session <text>` or `/tracker repo <text>` matches nothing, then the pane shall show a not-found line. Words: "No session matches \"<text>\". Pick one on Home." Screen/state: Session Not found; Repo Not found. Tag: `@F59`.

<details>
<summary>Verification</summary>

- F52 — tag `@F52`: `band.test.ts` › stale after two failed reads; `pane.test.ts` › stale line on Home
- F53 — tag `@F53`: `band.test.ts` › loading line; `pane.test.ts` › loading line
- F54 — tag `@F54`: `scans.test.ts` › gh missing; `band.test.ts` › no PR segment
- F55 — tag `@F55`: `backfill.test.ts` › unreadable transcript
- F56 — tag `@F56`: `asks.test.ts` › check failure leaves done
- F57 — tag `@F57`: `asks.test.ts` › classify failure keeps the ask
- F58 — tag `@F58`: `collector.test.ts` › write failure sets the status line
- F59 — tag `@F59`: `pane.test.ts` › not found lines

</details>


### Observe only and cost

- [ ] **F60** (A2) Every model call shall pin `haiku` from one constant, including any `claude -p` call. Screen/state: none. Tag: `@F60`.
- [ ] **F61** (A2) The mod shall make at most one classification call per ask and one question check per completed turn. Screen/state: none. Tag: `@F61`.
- [ ] **F62** (A1) The tracker shall never write to a session, git, gh or bd: no hidden note, no automatic continue, no queued answer. Screen/state: none. Tag: `@F62`.
- [ ] **F63** (A12) The tracker shall write only under `~/.claude/agent-tracker/`. Screen/state: store. Tag: `@F63`.
- [ ] **F64** (A12; rules PUB-1) The committed fixtures and screenshots shall hold no internal names, people, URLs or local paths. Screen/state: none. Tag: `@F64`.
- [ ] **F65** (A5; rules PUB-2) The tracker shall use no Artifact tool, Claude Docs or hosted page, and open no server or port. Screen/state: none. Tag: `@F65`.

<details>
<summary>Verification</summary>

- F60 — tag `@F60`: `safety.test.ts` › every model call passes the MODEL constant
- F61 — tag `@F61`: `safety.test.ts` › call counts for one ask and one turn
- F62 — tag `@F62`: `safety.test.ts` › no write call reaches a session
- F63 — tag `@F63`: `safety.test.ts` › every fs write path is under the folder
- F64 — tag `@F64`: `tests/test_plugin.py` (existing public repo grep) over the new files
- F65 — tag `@F65`: `tests/test_no_claude_ai_publishing.py` (existing) over the new files; `safety.test.ts` › no listener

</details>

## Verification

What proves the whole change, beyond the per-fact checks.

- **Automated:** `python3 -m unittest discover -s tests && scripts/run-plugin-tests.sh` exits 0, and `claude plugin test plugins/agent-tracker` passes.
- **Success measure:** by hand, 5 spot checks where the band's running count equals `claude agents --json`. Target 5 of 5 by 2026-12-04.
- **Manual:** open the band and the pane at 100 percent and 150 percent in the terminal, and the details columns on the desktop app.

## Out of scope

- A5 — the web page and the Board button belong to milestone 2. The band shows no Board button before then.
- A3 — "you should know" and "decided without you" items belong to milestone 3. Milestone 1 shows nothing for them.
- Plan progress, ticket links and superseded tasks — milestone 3.
- Anything from `bd` on screen — Beads links come with milestone 3, so the bd scan in design step 2 builds no screen here.
- Notifications, sound and toasts when a session waits — J10 is met by the band in every session.
- Any write to an agent, session, task, worktree or repo — no-go N1 and N6.

## Assumptions

- **Clarify, decided by the agent on 2026-11-13** (technical calls, no owner question needed):
  - **Reason text (F4):** "asks permission" only when `waitingFor` names a permission prompt, else "waiting". Its exact content is checked in the build.
  - **Goal end (F11):** a mod sees no goal-end event, so the goal age shows only while the session is running or needs you.
  - **Retry (F21):** the same tool name and input called directly after that call failed.
  - **Background tasks (F11):** where classic hooks are skipped, only subagents (`$.agent.list()`) and background sessions from `claude agents --json` are shown.

- **Feature "complete":** a feature in state `done` or `merged` counts as complete. It is the owner's word for finished.
- **Spec wins on the band:** the design file's Board button and you-should-know columns are left out, because the design file says the spec wins.
- **No classification outside a session:** a session without the mod shows "not classified". The spec says so and it saves a model call.
- **Without the mod:** the question check never runs, so such a session stays done. That is the owner's answer.
- **Test layout:** `*.test.ts` files under `plugins/agent-tracker/`, the tag and the change tag in each title.

## Deferred

none. The Medium and Low findings from `spec/validation.md` go to `plan.md`.

## Open questions

None. The three markers were answered under Assumptions.
