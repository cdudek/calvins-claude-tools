---
linear: none
type: facts
change: 2026-11-14-tracker-session-cleanup
design: docs/designs/agent-tracker.md
author: Calvin Dudek
status: draft
reviewed_by: null
approved_at: null
created: 2026-11-14
---

# Facts: Tracker shows only live sessions and clears dead ones

## Goal

The needs-you list holds only sessions that are alive and waiting, and a session page shows how long the session has really been idle. From an ended session's page the owner can clear it and its open tasks, then remove its merged worktree. `/tracker tidy` does the same for everything idle 30 days or more. It is one change because the state rule, Clear, the worktree offer and tidy share one set of checks.

## Acceptance criteria

Rules: `sdlc.json` defines no `rules` list, so the rules in `intent.md` Constraints get short names here. PUB-1 is the public repo rule (no internal names, people, URLs or local paths). PUB-2 is never publish to claude.ai. NAME-1 is the skill and agent naming rule (no new skill or agent is planned, so no fact cites it). MODEL-1 is every mod model call uses `haiku`. DATA-1 is the standalone data layer (events, transcripts, git, gh, bd, `claude` CLI only). WT-1 is the owner's worktree rule (never force, keep the branch). ACT-1 is the owner's 2026-11-13 observe-only decision, amended by the intent. The tracker acts only on the owner's explicit action, confirms before anything that cannot be undone, and never acts on its own. A fact with no rule cites asks only.

Tests are `*.test.ts` files in `plugins/agent-tracker/tests/`, run by `claude plugin test plugins/agent-tracker`, not browser E2E. The tag goes in the test title beside `@2026-11-14-tracker-session-cleanup`. Existing files extend; `clear.test.ts`, `worktree.test.ts` and `tidy.test.ts` are new, and `plan.md` fixes the paths. Words in quotes are the strings in `spec/screens.md`. "A process" means the session's row in `claude agents --json` carries `pid`.

### State and age

- [ ] **F1** (A5, A6) While a session's row in `claude agents --json` has no `pid`, the collector shall mark it ended, except this session's own (F72). This holds for interactive and background rows alike. It holds whatever the row's `state` or `status`. Screen/state: Home NEEDS YOU; Session header "○ ended 63d ago". Tag: `@F1`.
- [ ] **F2** (A5, A6) While a session's row has a `pid` and reports `blocked` or `waiting`, the collector shall mark it needs you as before. Screen/state: Home NEEDS YOU. Tag: `@F2`.
- [ ] **F3** (A5, A6) The needs-you count, the band's oldest-waiting line and the needs-you task rows shall exclude every session ended by F1. Screen/state: Home header "5 live · 2 need you"; band. Tag: `@F3`.
- [ ] **F4** (A5, A6) If no row in a good read carries a `pid`, then the collector shall keep the old state rule for that read. It shall not mark rows ended by F1. Screen/state: Home; Session "Pid not reported". Tag: `@F4`.
- [ ] **F5** (A5) When the Session page opens, it shall show "branch main  started 12 Sep 16:13  last activity 63d ago" and never "since". Screen/state: Session, Facts line 1. Tag: `@F5`.
- [ ] **F6** (A5) The Session page shall write the start date in local time as `16:13` today and `Tue 16:13` for 1 to 6 days back. Older dates read `12 Sep 16:13`, and over a year `12 Sep 2025 16:13`. Screen/state: Session, Facts line 1. Tag: `@F6`.
- [ ] **F7** (A5) While a session is ended, the Session header shall read "○ ended 63d ago" with the days since last activity. It reads "○ ended" when no time is known. Screen/state: Session header. Tag: `@F7`.
- [ ] **F71** (A5) The mod shall take a session's last activity as the newest of three times. They are its last prompt, its last turn end and the last line of its transcript. If none is known, the Session page shall read "last activity unknown". The idle time is then unknown (F48). Screen/state: Session, Facts line 1. Tag: `@F71`.
- [ ] **F72** (A5, A6) The collector shall never mark this session's own id ended by F1. A background row that reports `done` stays ended, with or without a `pid`, as before. Screen/state: Home NEEDS YOU; Session header. Tag: `@F72`.

### Clear: when it is offered

- [ ] **F8** (A3, A4; rules ACT-1) While a session is ended and has work left, the Session page shall draw "Clear". Work left is a listing, an open task or a removable worktree (F35). An open task is a task that Home lists for the session (F15). Screen/state: Session, Ended something to clear. Tag: `@F8`.
- [ ] **F9** (A4; rules ACT-1) While a session has a process, the Session page shall draw no Clear and no "Copy resume command". It shall draw one line instead: "Clear is for ended sessions. Close its terminal first." Background sessions read "Clear is for ended sessions. This one is still running. Resume comes back when it ends." Screen/state: Session, Live. Tag: `@F9`.
- [ ] **F10** (A3, A4) While an ended session is not listed and has no open task or removable worktree, the Session page shall draw no Clear. It shall draw "Nothing to clear: it is not in Claude Code's list and has no open tasks." Screen/state: Session, Nothing to clear. Tag: `@F10`.
- [ ] **F11** (A4) If no row in a good read carries a `pid` (F4), then the Session page shall draw no Clear. It shall show "Clear waits: Claude Code did not say which sessions have a process." Screen/state: Session, Pid not reported. Tag: `@F11`.
- [ ] **F12** (A4) If the session list could not be read twice, then the Session page shall draw no Clear. It shall show "Clear waits: Claude Code's session list could not be read. Retrying every 5 seconds." Screen/state: Session, List unreadable. Tag: `@F12`.
- [ ] **F13** (A3, A4) When the Session page opens, the focus ring shall start on "Copy resume command", else on the Home crumb. It shall never start on Clear, "Clear session" or "Remove worktree". Screen/state: Session, Ended. Tag: `@F13`.
- [ ] **F14** (A4) While an ended session's worktree folder does not exist, the Session page shall not draw "Copy resume command". Screen/state: Session, Actions. Tag: `@F14`.
- [ ] **F15** (A3, A5) For an ended session, the Tasks line shall list only the tasks Home lists for it, with Home's glyph and word. It shall list no finished task. Screen/state: Session, Tasks. Tag: `@F15`.
- [ ] **F16** (A3, A4) For a session built from its transcript, the Session page shall treat its asks as "not classified". Clear then closes no task. Screen/state: Session, From transcript. Tag: `@F16`.

### Clear: the confirm and the run

- [ ] **F17** (A3, A4; rules ACT-1) When the owner presses "Clear" and it has work, the Session page shall open a confirm instead of the actions. Nothing is written yet. The confirm asks "Clear this session?", says what will happen and has "Clear session" and "Cancel". Screen/state: Session, Confirming. Tag: `@F17`.
- [ ] **F18** (A3, A4; rules ACT-1) When the confirm opens, the focus shall be on "Cancel". Screen/state: Session, Confirming. Tag: `@F18`.
- [ ] **F19** (A3, A4) The confirm shall build its what-happens lines only from the parts that apply. The parts are "It leaves Claude Code's list", "and closes the 2 tasks above" ("1 task") and "The conversation is kept. The list entry does not come back." A listed session in a linked worktree adds this line. "If it made the worktree login, Claude Code also removes it, when that is safe." Screen/state: Session, Confirming. Tag: `@F19`.
- [ ] **F20** (A4) When the owner presses "Cancel" or leaves the page, the Session page shall remove the confirm and change nothing. The focus returns to "Clear". Screen/state: Session, Confirming to Ended. Tag: `@F20`.
- [ ] **F21** (A4; rules ACT-1) When the owner presses "Clear" and only a removable worktree is left, the Session page shall open the offer. It asks no confirm first. Screen/state: Session, Clear only a worktree left. Tag: `@F21`.
- [ ] **F73** (A3, A4) When a Clear has run, the focus shall go to "Keep worktree" when there is an offer. Else it goes to "Copy resume command" when that is drawn, else to the Home crumb. It shall never go to "Reopen tasks". Screen/state: Session, Cleared. Tag: `@F73`.
- [ ] **F22** (A3, A4, A6; rules ACT-1) When the owner presses "Clear session", the mod shall re-read `claude agents --json` before any write. It shall show "Clearing…". Screen/state: Session, Clearing. Tag: `@F22`.
- [ ] **F23** (A4; rules ACT-1) If the re-read shows a `pid` for the session, then the mod shall change nothing. It shall show "This session is running again. Nothing was changed." Screen/state: Session, Refused. Tag: `@F23`.
- [ ] **F24** (A4) If the re-read fails, then the mod shall change nothing. It shall show "Clear waits: Claude Code's session list could not be read. Nothing was changed." Screen/state: Session, Refused unreadable. Tag: `@F24`.
- [ ] **F25** (A3, A4, A6; rules ACT-1) When the re-read shows the session listed with no process, the mod shall run `claude rm <id>`. It shall show "✓ Left Claude Code's list. The conversation is kept." Screen/state: Session, Cleared. Tag: `@F25`.
- [ ] **F26** (A4) When the re-read does not list the session, the mod shall not run `claude rm`. It shall still close the session's tasks and offer its worktree. Screen/state: Session, Cleared. Tag: `@F26`.
- [ ] **F27** (A4) If `claude rm` prints "No job matching" and exits non-zero, then the mod shall treat the session as not listed (F26). It shall show no error. Screen/state: Session, Cleared. Tag: `@F27`.
- [ ] **F28** (A3, A4) If `claude rm` fails otherwise, then the mod shall change nothing else and draw Clear again. It shall show "✗ Claude Code could not clear this session: <reason>. Nothing else was changed. Press Clear to try again." The reason is one line cut at 60 cells, dropped when unusable. Screen/state: Session, Failed. Tag: `@F28`.
- [ ] **F29** (A3, A6) When Clear closes tasks, the mod shall mark each open task of the session closed in the tracker's settings. It shall show "✓ 2 tasks closed." ("1 task"). Screen/state: Session, Cleared; Home. Tag: `@F29`.
- [ ] **F30** (A3) If saving the closed tasks fails after `claude rm` worked, then the mod shall draw Clear again. It shall show "✗ The tracker could not close the tasks: <reason>. The session left Claude Code's list. Press Clear to close them." Screen/state: Session, PartlyCleared. Tag: `@F30`.
- [ ] **F31** (A3) When the owner presses "Reopen tasks", the mod shall remove the closed marks of the tasks that Clear closed. It shall show "✓ 2 tasks reopened." The button is drawn only while the owner stays on the page. It does not survive a pane re-open. A tidy pass offers no reopen. Screen/state: Session, Reopened. Tag: `@F31`.
- [ ] **F32** (A3, A5) When a session is cleared, Home shall stop listing its closed tasks. A task of an ended session older than 7 days still never lists. Screen/state: Home, YOUR TASKS NOT DONE. Tag: `@F32`.
- [ ] **F33** (A4) The result lines of a Clear shall stay until the owner leaves the page and survive the 5-second re-read. A fresh visit shall show "Nothing to clear". Screen/state: Session, Result. Tag: `@F33`.
- [ ] **F34** (A4) The mod shall add no command of its own for Clear. The keyboard route is `/tracker session <text>`, then Tab to Clear. Screen/state: Session. Tag: `@F34`.

### The worktree offer

- [ ] **F35** (A4; rules WT-1) The mod shall count a worktree removable only when all five conditions hold, each computed by code. (1) The session's `cwd` is a linked worktree, not the first entry of `git worktree list --porcelain`. (2) It has no modified, staged or untracked files. (3) It has no commits that are not pushed. (4) Its branch is merged into the default branch, or its PR is merged or closed. (5) No live session uses it. Screen/state: Session, Worktree. Tag: `@F35`.
- [ ] **F36** (A4) While the session's `cwd` is a linked worktree, the Session page shall draw "worktree login · fix-login", never a path. It shall add "Clear offers to remove it." when F35 holds. Screen/state: Session, Worktree. Tag: `@F36`.
- [ ] **F37** (A4) If a condition of F35 fails, then the Session page shall name the first failed one. An example is "Worktree login stays: it has uncommitted changes. Commit or stash them in a terminal." The other three reasons are unpushed commits, an unmerged branch and another session using it. Screen/state: Session, Worktree stays. Tag: `@F37`.
- [ ] **F38** (A4) If `gh` is missing, then the mod shall judge condition 4 of F35 by the branch's merged state only. Screen/state: Session, Partial. Tag: `@F38`.
- [ ] **F39** (A4; rules ACT-1) When F35 holds after a Clear, or F21 applies, the Session page shall draw the offer under the actions row. It says why removal is safe: "Worktree login is clean, pushed and merged." It adds the ignored-files line when there are any, then "Remove it? The branch fix-login stays, so you can make it again." Its buttons are "Remove worktree" and "Keep worktree". Screen/state: Session, Offer. Tag: `@F39`.
- [ ] **F40** (A4; rules WT-1) When the offer opens, the focus shall be on "Keep worktree". Screen/state: Session, Offer. Tag: `@F40`.
- [ ] **F41** (A4) The offer shall list the ignored files from `git status --ignored --porcelain`, the `!!` lines. It shows at most 3 names, files first then folders (a folder ends in "/"), each group A to Z. A name over 30 cells is cut with "…", and the rest read "and 12 more" ("and 1 more"). Ignored files never refuse the offer. Screen/state: Session, Offer. Tag: `@F41`.
- [ ] **F42** (A4; rules WT-1) When the owner presses "Remove worktree", the mod shall re-check all of F35 and re-read the ignored files. It shall then run `git worktree remove <path>` without `--force`. Screen/state: Session, Removing. Tag: `@F42`.
- [ ] **F43** (A4; rules WT-1) When the worktree is removed, the mod shall keep its branch and draw no "Copy resume command". It shall show "✓ Worktree login removed. The branch fix-login stays." and "To resume this conversation, make the worktree again from the branch first." Screen/state: Session, Done. Tag: `@F43`.
- [ ] **F44** (A4; rules WT-1) If a condition of F35 fails at the press, or the ignored files changed, then the mod shall remove nothing. It shall show "✗ The worktree changed since it was checked: <reason>. Nothing was removed. Check it in a terminal." Screen/state: Session, OfferFailed. Tag: `@F44`.
- [ ] **F45** (A4) If git refuses the removal, then the mod shall show "✗ Git could not remove the worktree: <reason>. Nothing was lost. Check it in a terminal." Screen/state: Session, OfferFailed. Tag: `@F45`.
- [ ] **F46** (A4) After `claude rm` has run, the mod shall check the worktree again. If Claude Code removed it, the mod shall draw no offer. It shall show "✓ Claude Code also removed the worktree login." and the resume sentence of F43. Screen/state: Session, Result. Tag: `@F46`.
- [ ] **F47** (A4) When the owner presses "Keep worktree", the mod shall remove the offer for this visit and change nothing. Screen/state: Session, Done. Tag: `@F47`.

### Tidy

- [ ] **F48** (A1, A4, A6) The mod shall collect for tidy ended sessions with work left for Clear, and linked worktrees. Each must be idle 30 days or more. A session's idle time runs from its last activity (F71). A worktree's idle time is the newest of three times. They are its branch's last commit and its folder's own modified time. The third is the last activity of every session that used it, cleared or not. A cleared session's worktree has no second rule. An unknown time is not collected. Screen/state: Home TIDY; tidy pass. Tag: `@F48`.
- [ ] **F49** (A1, A4, A6; rules ACT-1) The mod shall count and list only items that pass every check. A session needs no process and no ask whose last stored verdict in the tracker's ask record is "partly" or "not started". A worktree needs all of F35. Screen/state: Home TIDY; tidy questions. Tag: `@F49`.
- [ ] **F50** (A1, A6) While an item passes F49, Home shall draw the TIDY block last, below REPOS and above the "without the tracker" line. It holds the heading "TIDY" and the button "Tidy". Between them is a dim count: "5 sessions and 3 worktrees idle for 30 days or more" ("1 session", "1 worktree"). Screen/state: Home, Tidy line. Tag: `@F50`.
- [ ] **F51** (A1) While no item passes F49, Home shall draw no TIDY block. Screen/state: Home, No tidy line. Tag: `@F51`.
- [ ] **F52** (A6) While Claude is replying in this session, Home shall replace the button with a line. The line reads "Tidy waits until Claude finishes replying in this session." When the list is unreadable, it says
  "Tidy waits until Claude Code's session list can be read." Screen/state: Home, Tidy line waiting. Tag: `@F52`.
- [ ] **F53** (A6; rules ACT-1) When the owner presses "Tidy" or types `/tracker tidy`, the mod shall hand the supervisor prompt to this session. It uses `$.prompt.submit({ text })` and answers "Tidy started: 5 sessions and 3 worktrees to check. Nothing that is running is touched." Screen/state: Home to the transcript. Tag: `@F53`.
- [ ] **F54** (A1, A6) If no item passes F49, then `/tracker tidy` shall start no turn. It shall answer "Nothing to tidy. Nothing idle for 30 days is ready to clear." Screen/state: tidy, Nothing to tidy. Tag: `@F54`.
- [ ] **F55** (A6) If Claude is replying in this session or the session list could not be read twice, then `/tracker tidy` shall start no turn. It answers "Tidy waits until Claude finishes replying in this session." or "Tidy waits: Claude Code's session list could not be read. Try again in a minute." Screen/state: tidy, busy and unreadable. Tag: `@F55`.
- [ ] **F56** (A6) If `/tracker tidy` has any argument, then the mod shall start no turn. It shall answer "Tidy takes no number: it always uses 30 days." Screen/state: tidy. Tag: `@F56`.
- [ ] **F57** (A4, A6; rules MODEL-1) The supervisor prompt shall hold a fixed list of the items that passed F49. The mod's code computes every safety check, subagents only gather and narrate, and a model never decides that something is safe. The gathering subagents use `haiku` and only read. The supervisor runs on the session's own model and changes nothing before the owner's batch answer. Screen/state: tidy, Started. Tag: `@F57`.
- [ ] **F58** (A4, A6) The supervisor shall ask one question per batch, sessions first, then worktrees. Every item gets one line ("web-app · fix login · idle 41d"). A batch over 25 items splits into batches of 25. The options are "Clear all 5" or "Remove all 3" (recommended) and "Skip these 5", where the number is the size of that batch. Screen/state: tidy, Asking. Tag: `@F58`.
- [ ] **F59** (A4, A6; rules ACT-1) When the owner answers "Clear all N" or "Remove all N", the supervisor shall act item by item. It acts only through the mod's checked functions, the ones the Session page uses. It never runs `claude rm` or git itself. It re-checks each item right before it acts, re-reading the session list for a session. It skips and names an item whose re-check or action fails. Screen/state: tidy, Acting. Tag: `@F59`.
- [ ] **F60** (A4) If an exception typed under Other matches no item or several, then the supervisor shall pause the batch. It says "I could not tell which one you meant. Nothing was changed." Otherwise it shall show the final list ("Clearing 4, keeping 1: web-app · fix login") before it acts. Screen/state: tidy, Asking. Tag: `@F60`.
- [ ] **F61** (A4, A6) When tidy ends, the supervisor shall write the report. The report reads "Cleared 5 sessions." and "Removed 3 worktrees. Branches kept." Failures read "Could not clear: web-app · fix login: <reason>", the reason cut at 60 cells like Clear's error lines. It adds "Kept, needs a look: web-app/login (uncommitted changes)." and "Skipped: docs (a session is running in it)." It counts only what succeeded. Screen/state: tidy, Reported. Tag: `@F61`.
- [ ] **F62** (A1) The supervisor shall name a worktree with a live session in it as skipped and never ask about it. It shall name an item that failed a check as "needs a look" and never remove it, whatever the owner answers. Screen/state: tidy, Reported. Tag: `@F62`.
- [ ] **F63** (A1, A6) The help line shall name tidy. It reads "Try /tracker, details, compact, copy, repo, session, tidy, web, band on, band off." The command hint shall include `tidy`. Screen/state: command help. Tag: `@F63`.

### Safety

- [ ] **F64** (A4, A6; rules WT-1) If a code path passes `--force`, `-f` or `branch -D`, then the build shall fail. The plugin holds no such argument. Screen/state: all. Tag: `@F64`.
- [ ] **F65** (A4, A6; rules ACT-1) The mod shall never run `claude stop`. It shall never run `claude rm` for a session whose latest read has a `pid`. It shall never remove a worktree with a live session in it. Screen/state: all. Tag: `@F65`.
- [ ] **F66** (A4; rules ACT-1) The mod shall never clear, remove or close anything on its own. Every write follows a press of "Clear session", "Remove worktree" or "Reopen tasks", or an answer to a tidy question. Screen/state: all. Tag: `@F66`.
- [ ] **F67** (A4; rules WT-1) The mod shall never delete a branch. It shall run `claude rm` and git through `$.process.run` with an argument list and no shell. Screen/state: all. Tag: `@F67`.
- [ ] **F68** (A4; rules PUB-1) The shipped plugin shall show a worktree by its folder label. No new word shall contain a local path, internal name or URL. Screen/state: all. Tag: `@F68`.
- [ ] **F69** (A1; rules PUB-2, DATA-1) The tidy output shall stay in the local transcript. The mod shall read only its own events, transcripts, git, gh, bd and the `claude` CLI. Screen/state: tidy. Tag: `@F69`.
- [ ] **F70** (A3, A4; rules ACT-1) The band shall gain no button, cell or hotkey, and the web Board shall gain no action. Screen/state: band; Board. Tag: `@F70`.
- [ ] **N1** (A4) While the Session page is drawn at 120, 80 and 40 columns and at a 24-column dock, the system shall clip no button. The actions box wraps one button per line when needed. Screen/state: Session, all.

<details>
<summary>Verification</summary>

- F1 — tag `@F1`: `collector.test.ts` › a row with no pid is ended, whatever its state
- F2 — tag `@F2`: `collector.test.ts` › a row with a pid that is blocked or waiting needs you
- F3 — tag `@F3`: `band.test.ts` › needs-you count, oldest-waiting line and needs-you tasks skip pid-less rows
- F4 — tag `@F4`: `collector.test.ts` › a read where no row has a pid keeps the old rule and marks nothing ended
- F5 — tag `@F5`: `pane.test.ts` › Session first line reads started and last activity, never since
- F6 — tag `@F6`: `pane.test.ts` › started date format for today, this week, older and over a year
- F7 — tag `@F7`: `pane.test.ts` › ended header with and without a time
- F71 — tag `@F71`: `collector.test.ts` › last activity is the newest of prompt, turn end and transcript; unknown reads "last activity unknown"
- F72 — tag `@F72`: `collector.test.ts` › this session's own id is never ended; a background `done` row stays ended
- F73 — tag `@F73`: `clear.test.ts` › focus after a Clear: offer, resume, Home crumb, never Reopen tasks
- F8 — tag `@F8`: `clear.test.ts` › Clear is drawn for an ended session with something to clear
- F9 — tag `@F9`: `clear.test.ts` › a session with a process gets the reason line and no Clear or resume
- F10 — tag `@F10`: `clear.test.ts` › nothing to clear draws the line and no Clear
- F11 — tag `@F11`: `clear.test.ts` › pid not reported withholds Clear
- F12 — tag `@F12`: `clear.test.ts` › unreadable list withholds Clear
- F13 — tag `@F13`: `clear.test.ts` › the ring starts on Copy resume command or the Home crumb
- F14 — tag `@F14`: `clear.test.ts` › no resume button when the worktree folder is gone
- F15 — tag `@F15`: `pane.test.ts` › the ended session's Tasks line matches Home's list
- F16 — tag `@F16`: `clear.test.ts` › a transcript-only session closes no task
- F17 — tag `@F17`: `clear.test.ts` › pressing Clear opens the confirm and writes nothing
- F18 — tag `@F18`: `clear.test.ts` › the confirm's focus is on Cancel
- F19 — tag `@F19`: `clear.test.ts` › the confirm lines for each combination of parts
- F20 — tag `@F20`: `clear.test.ts` › Cancel and leaving the page change nothing
- F21 — tag `@F21`: `clear.test.ts` › only a worktree left opens the offer, no confirm
- F22 — tag `@F22`: `clear.test.ts` › Clear session re-reads the list before any write
- F23 — tag `@F23`: `clear.test.ts` › a pid at the press refuses and writes nothing
- F24 — tag `@F24`: `clear.test.ts` › a failed re-read refuses and writes nothing
- F25 — tag `@F25`: `clear.test.ts` › claude rm runs for a listed session with no pid
- F26 — tag `@F26`: `clear.test.ts` › an unlisted session gets no claude rm and still closes tasks
- F27 — tag `@F27`: `clear.test.ts` › "No job matching" is treated as not listed
- F28 — tag `@F28`: `clear.test.ts` › claude rm failure shows the error line and Clear again
- F29 — tag `@F29`: `tasks.test.ts` › Clear marks the session's open tasks closed
- F30 — tag `@F30`: `clear.test.ts` › a failed save after claude rm shows the partly-cleared line
- F31 — tag `@F31`: `tasks.test.ts` › Reopen tasks removes the closed marks
- F32 — tag `@F32`: `tasks.test.ts` › closed tasks leave Home; tasks over 7 days never list
- F33 — tag `@F33`: `clear.test.ts` › result lines survive the 5-second re-read and not a new visit
- F34 — tag `@F34`: `pane.test.ts` › no clear command exists; session text opens the page
- F35 — tag `@F35`: `worktree.test.ts` › each of the five conditions on git fixtures
- F36 — tag `@F36`: `worktree.test.ts` › the worktree line shows label and branch, never a path
- F37 — tag `@F37`: `worktree.test.ts` › the first failed condition is named
- F38 — tag `@F38`: `worktree.test.ts` › no gh judges by the branch only
- F39 — tag `@F39`: `worktree.test.ts` › the offer draws its lines and buttons
- F40 — tag `@F40`: `worktree.test.ts` › the offer's focus is on Keep worktree
- F41 — tag `@F41`: `worktree.test.ts` › ignored files: cap 3, order, cut names, "and N more"
- F42 — tag `@F42`: `worktree.test.ts` › Remove worktree re-checks then runs git worktree remove without force
- F43 — tag `@F43`: `worktree.test.ts` › branch kept, result lines, no resume button after removal
- F44 — tag `@F44`: `worktree.test.ts` › a changed condition or ignored list removes nothing
- F45 — tag `@F45`: `worktree.test.ts` › a git refusal shows the error line
- F46 — tag `@F46`: `clear.test.ts` › Claude Code removing its own worktree is named and no offer follows
- F47 — tag `@F47`: `worktree.test.ts` › Keep worktree changes nothing
- F48 — tag `@F48`: `tidy.test.ts` › collection by idle time, unknown time not collected
- F49 — tag `@F49`: `tidy.test.ts` › only items passing every check are counted and listed
- F50 — tag `@F50`: `pane.test.ts` › the TIDY block, its count words and its place on Home
- F51 — tag `@F51`: `pane.test.ts` › no TIDY block when nothing passes
- F52 — tag `@F52`: `pane.test.ts` › the waiting lines replace the Tidy button
- F53 — tag `@F53`: `tidy.test.ts` › the command hands the prompt to prompt.submit and answers started
- F54 — tag `@F54`: `tidy.test.ts` › nothing to tidy starts no turn
- F55 — tag `@F55`: `tidy.test.ts` › busy and unreadable start no turn
- F56 — tag `@F56`: `tidy.test.ts` › an argument gets the 30 days answer
- F57 — tag `@F57`: `tidy.test.ts` › the prompt carries the fixed list and states that a model never decides safety
- F58 — tag `@F58`: `tidy.test.ts` › one question per batch, batches of 25, listed items
- F59 — tag `@F59`: `tidy.test.ts` › each item re-checked before acting; a failure skips and names it
- F60 — tag `@F60`: `tidy.test.ts` › an unmatched or ambiguous exception pauses the batch
- F61 — tag `@F61`: `tidy.test.ts` › the report lines count only successes
- F62 — tag `@F62`: `tidy.test.ts` › running-session worktrees are skipped, failed items are never removed
- F63 — tag `@F63`: `pane.test.ts` › help and hint name tidy
- F64 — tag `@F64`: `safety.test.ts` › no --force, -f or branch -D in any argument list the plugin builds
- F65 — tag `@F65`: `safety.test.ts` › no claude stop; no rm or removal with a pid or a live session
- F66 — tag `@F66`: `safety.test.ts` › every write follows an owner press or answer
- F67 — tag `@F67`: `safety.test.ts` › no branch deletion; commands run by $.process.run without a shell
- F68 — tag `@F68`: `safety.test.ts` › new words hold no path, internal name or URL (also `tests/test_plugin.py` grep)
- F69 — tag `@F69`: `safety.test.ts` › no publishing site; data sources are the allowed list
- F70 — tag `@F70`: `band.test.ts` › the band's cells, buttons and words are unchanged
- N1 — manual: the build agent reads the render check, counting rows as well as columns. It covers the Session page, its confirm, its offer and Home with the Tidy line, at 120, 80 and 40 columns, with a terminal screenshot.

</details>

## Verification

- **Automated:** `claude plugin test plugins/agent-tracker` and `python3 -m unittest discover -s tests` exit 0.
- **Manual:** the render check of N1. Also a spot check of the band against `claude agents --json`: 0 needs-you rows with no `pid` in 5 of 5 checks by 2026-12-05.

## Assumptions

- **Clarify, decided by the agent on 2026-11-14** (technical calls, no owner question needed):
  - **Rows with no `pid` (F1, F4, F72):** a row with no `pid` is ended, for interactive and background rows alike. Every live row checked on 2026-11-14 carried a `pid`. The F4 guard (no `pid` anywhere in a good read) stays, and so does the exception for this session's own id.
  - **Idle time (F48, F71):** tidy measures a session's idle time from its last activity. A cleared session's worktree counts through the worktree age rule, with no second definition.
  - **Reopen tasks (F31):** it lives only while the owner stays on the page. It does not survive a pane re-open.
  - **Tidy report reasons (F61):** the report cuts each failed item's reason at 60 cells, like Clear's error lines.
  - **Tidy models (F57):** the gathering subagents use `haiku` and only read. The supervisor is the session's own model and makes no change without the owner's batch answer. MODEL-1 covers the mod's own calls, not these.
  - **Supervisor's actions (F59):** the supervisor reaches the mod's checked functions through the plan's mechanism (`plan.md` fixes it). It never runs `claude rm` or git itself.
  - **Hand-off (F53):** `$.prompt.submit({ text })` starts a turn in the session where the owner typed the command. The build checks this against a fixture first. If the host refuses it, the fallback is a plugin skill, recorded in `plan.md`.
  - **`claude rm` (F25, F43, F46):** it removes the session from Claude Code's list and keeps the conversation file. It also removes a worktree the session itself made, when that is safe (owner, dialog, 2026-11-14, "Allow, name it").
  - **Default branch (F35):** the target of `refs/remotes/origin/HEAD`; with none, `main`, then `master`. With none of them, condition 4 relies on the PR alone (F38).

## Out of scope

- A1, A2 — the cleanup by hand of 72 worktrees and 6 sessions was done on 2026-11-14 (handover); this change builds the tracker side.
- A3 — a Clear button on the band: the band gets no control (F70); the path is band, pane, task row, Clear.
- A4 — "a supervisor agent that launches subagents": answered by `/tracker tidy` (F53 to F62); a standing supervisor is not built.
- Actions on the web Board — it runs no commands (F70).
- A day-count argument for tidy — fixed at 30 days (F56).
- `claude stop` — the tracker never stops a running session (F65).

## Assumptions

- **Worktree-created sessions:** the confirm says "if" because Claude Code decides whether `claude rm` removes its own worktree; the result line says what happened (F19, F46).
- **Linked worktree test:** `git worktree list --porcelain` lists the main checkout first; a build test on a fixture confirms it.
- **Tidy model:** subagents that only gather use `haiku` and the supervisor that acts uses the session's own model; MODEL-1 binds only the mod's own calls.
- **Where tidy runs:** in the session where the owner typed it, because the supervisor asks questions.
- **Copy resume command:** shown for an ended session only, as milestone 1 said; the built page shows it on every session and F9 corrects that.
- **Old tasks:** a forgotten task of an ended session does not age out before 7 days; Clear is the answer.
- **Fact numbering:** F1 to F70 are new for this change; milestone 1's facts keep their own numbers in their own folder.

## Deferred

- Resuming from a worktree made again from the branch is unverified. The default is the page text of F43.

## Open questions

None open.
