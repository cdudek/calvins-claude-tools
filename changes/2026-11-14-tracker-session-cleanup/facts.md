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

The needs-you list holds only sessions that are alive and waiting, and a session page shows how long the session has really been idle. From an ended session's page the owner can clear it and its open tasks, then remove its merged worktree. The skill `git-cleanup-run` does the same for everything idle 30 days or more, by script, after the owner's answer for each batch. The tracker has no tidy. It is one change because the state rule, Clear, the worktree offer and the skill share one definition of safe (F35).

## Acceptance criteria

Rules: `sdlc.json` defines no `rules` list, so the rules in `intent.md` Constraints get short names here. PUB-1 is the public repo rule (no internal names, people, URLs or local paths). PUB-2 is never publish to claude.ai. NAME-1 is the skill and agent naming rule (F77 cites it). MODEL-1 is every mod model call uses `haiku`; the mod adds none, and the skill's subagents use `haiku` by the owner's choice. DATA-1 is the standalone data layer (events, transcripts, git, gh, bd, `claude` CLI only). WT-1 is the owner's worktree rule (never force, keep the branch). ACT-1 is the owner's 2026-11-13 observe-only decision, amended by the intent. The tracker acts only on the owner's explicit action, confirms before anything that cannot be undone, and never acts on its own. The skill acts only through its script, on the ids the owner chose in its question. A fact with no rule cites asks only.

Tracker tests are `*.test.ts` files in `plugins/agent-tracker/tests/`, run by `claude plugin test plugins/agent-tracker`, not browser E2E. The tag goes in the test title beside `@2026-11-14-tracker-session-cleanup`. Existing files extend; `clear.test.ts`, `worktree.test.ts` and `cleanup-safety.test.ts` are new. `safety.test.ts` is not edited: its `@F60` to `@F65` belong to milestone 1, so the new safety tests live in `cleanup-safety.test.ts`. Script tests are Python `unittest` in `tests/test_git_cleanup_run.py`, run by `python3 -m unittest discover -s tests`. The tag and the change tag are the first words of each test's docstring. `plan.md` fixes the paths. Words in quotes are the strings in `spec/screens.md`. "A process" means the session's row in `claude agents --json` carries `pid`.

### State and age

- [ ] **F1** (A5, A6) While a session's row in `claude agents --json` has no `pid`, the collector shall mark it ended, except this session's own (F72). This holds whatever the row's `state` or `status`. It is observed for background rows. For interactive rows without `pid` it is an assumption, and a fixture covers it. Screen/state: Home NEEDS YOU; Session header "○ ended 63d ago". Tag: `@F1`.
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
- [ ] **F25** (A3, A4, A6; rules ACT-1) When the re-read lists the session with an `id` and no process, the mod shall run `claude rm <id>`. It shall show "✓ Left Claude Code's list. The conversation is kept." A row with no `id` (an interactive row) gets no `claude rm`: the mod treats it as not listed (F26). Screen/state: Session, Cleared. Tag: `@F25`.
- [ ] **F26** (A4) When the re-read does not list the session, or lists it with no job `id`, the mod shall not run `claude rm`. It shall still close the session's tasks and offer its worktree. Screen/state: Session, Cleared. Tag: `@F26`.
- [ ] **F27** (A4) If `claude rm` fails, then the mod shall read the list again. When the session is no longer listed, the mod shall treat it as not listed (F26) and show no error. It shall never decide from the words of `claude rm`'s message. Screen/state: Session, Cleared. Tag: `@F27`.
- [ ] **F28** (A3, A4) If `claude rm` fails and the session is still listed, then the mod shall change nothing else and draw Clear again. It shall show "✗ Claude Code could not clear this session: <reason>. Nothing else was changed. Press Clear to try again." The reason is one line cut at 60 cells, dropped when unusable. Screen/state: Session, Failed. Tag: `@F28`.
- [ ] **F29** (A3, A6) When Clear closes tasks, the mod shall mark each open task of the session closed in the tracker's settings. It shall show "✓ 2 tasks closed." ("1 task"). Screen/state: Session, Cleared; Home. Tag: `@F29`.
- [ ] **F30** (A3) If saving the closed tasks fails after `claude rm` worked, then the mod shall draw Clear again. It shall show "✗ The tracker could not close the tasks: <reason>. The session left Claude Code's list. Press Clear to close them." Screen/state: Session, PartlyCleared. Tag: `@F30`.
- [ ] **F31** (A3) When the owner presses "Reopen tasks", the mod shall remove the closed marks of the tasks that Clear closed. It shall show "✓ 2 tasks reopened." The button is drawn only while the owner stays on the page. It does not survive a pane re-open. The skill offers no reopen. Screen/state: Session, Reopened. Tag: `@F31`.
- [ ] **F32** (A3, A5) When a session is cleared, Home shall stop listing its closed tasks. A task of an ended session older than 7 days still never lists. Screen/state: Home, YOUR TASKS NOT DONE. Tag: `@F32`.
- [ ] **F33** (A4) The result lines of a Clear shall stay until the owner leaves the page and survive the 5-second re-read. A fresh visit shall show "Nothing to clear". Screen/state: Session, Result. Tag: `@F33`.
- [ ] **F34** (A4) The mod shall add no command of its own for Clear. The keyboard route is `/tracker session <text>`, then Tab to Clear. Screen/state: Session. Tag: `@F34`.

### The worktree offer

- [ ] **F35** (A4; rules WT-1) The mod shall count a worktree removable only when all five conditions hold, each computed by code. (1) The session's `cwd` is a linked worktree, not the first entry of `git worktree list --porcelain`. (2) It has no modified, staged or untracked files. (3) It has no commits that are not pushed. (4) Its branch is merged into the default branch, or its PR is merged or closed. (5) No live row has a `cwd` equal to the worktree path or under it. Screen/state: Session, Worktree. Tag: `@F35`.
- [ ] **F36** (A4) While the session's `cwd` is a linked worktree, the Session page shall draw "worktree login · fix-login", never a path. It shall add "Clear offers to remove it." when F35 holds. Screen/state: Session, Worktree. Tag: `@F36`.
- [ ] **F37** (A4) If a condition of F35 fails, then the Session page shall name the first failed one. An example is "Worktree login stays: it has uncommitted changes. Commit or stash them in a terminal." The other three reasons are unpushed commits, an unmerged branch and another session using it. Screen/state: Session, Worktree stays. Tag: `@F37`.
- [ ] **F38** (A4) If `gh` is missing, then the mod shall judge condition 4 of F35 by the branch's merged state only. Screen/state: Session, Partial. Tag: `@F38`.
- [ ] **F39** (A4; rules ACT-1) When F35 holds after a Clear, or F21 applies, the Session page shall draw the offer under the actions row. It says why removal is safe: "Worktree login is clean, pushed and merged." It adds the ignored-files line when there are any, then "Remove it? The branch fix-login stays, so you can make it again." Its buttons are "Remove worktree" and "Keep worktree". Screen/state: Session, Offer. Tag: `@F39`.
- [ ] **F40** (A4; rules WT-1) When the offer opens, the focus shall be on "Keep worktree". Screen/state: Session, Offer. Tag: `@F40`.
- [ ] **F41** (A4) The offer shall list the ignored files from `git status --ignored --porcelain`, the `!!` lines. Secret-looking names come first and are all listed, never cut and never counted in "and N more". Secret-looking means `.env*`, `*.pem`, `*key*` or `credentials*`. Then it shows at most 3 other names, files first then folders (a folder ends in "/"), each group A to Z. A name over 30 cells is cut with "…". The rest read "and 12 more" ("and 1 more"). Ignored files never refuse the offer. Screen/state: Session, Offer. Tag: `@F41`.
- [ ] **F42** (A4; rules WT-1) When the owner presses "Remove worktree", the mod shall re-check all of F35 and re-read the ignored files. It shall then run `git worktree remove <path>` without `--force`. Screen/state: Session, Removing. Tag: `@F42`.
- [ ] **F43** (A4; rules WT-1) When the worktree is removed, the mod shall keep its branch and draw no "Copy resume command". It shall show "✓ Worktree login removed. The branch fix-login stays." and "To resume this conversation, make the worktree again from the branch first." Screen/state: Session, Done. Tag: `@F43`.
- [ ] **F44** (A4; rules WT-1) If a condition of F35 fails at the press, or the ignored files changed, then the mod shall remove nothing. It shall show "✗ The worktree changed since it was checked: <reason>. Nothing was removed. Check it in a terminal." Screen/state: Session, OfferFailed. Tag: `@F44`.
- [ ] **F45** (A4) If git refuses the removal, then the mod shall show "✗ Git could not remove the worktree: <reason>. Nothing was lost. Check it in a terminal." Screen/state: Session, OfferFailed. Tag: `@F45`.
- [ ] **F46** (A4) After `claude rm` has run, the mod shall check the worktree again. If Claude Code removed it, the mod shall draw no offer. It shall show "✓ Claude Code also removed the worktree login." and the resume sentence of F43. Screen/state: Session, Result. Tag: `@F46`.
- [ ] **F47** (A4) When the owner presses "Keep worktree", the mod shall remove the offer for this visit and change nothing. Screen/state: Session, Done. Tag: `@F47`.

### The skill git-cleanup-run and its script

The skill is `plugins/agent-tracker/skills/git-cleanup-run/SKILL.md`. Its script is `scripts/cleanup.py` in the same folder, Python 3 standard library only, with commands `list` and `act`. Screen/state names are steps of the skill's conversation in `spec/screens.md`.

- [ ] **F48** (A1, A4, A6) The script's `list` shall collect ended sessions and linked worktrees that are each idle 30 days or more. A session is ended when its row in `claude agents --json` has a job `id` and no `pid`. A session's idle time runs from its last activity: the newest time its row and transcript give. A worktree's idle time is the newest of three times. They are its branch's last commit, its folder's own modified time and the last activity of every session that used it. An unknown time is not collected. Screen/state: skill, List. Tag: `@F48`.
- [ ] **F49** (A1, A4, A6; rules ACT-1) The script's `list` shall print JSON. Each item shall carry the result of every check and a verdict: `removable`, or `needs-look` with the first failed check. A session's checks are no process, a job id, and no ask whose last verdict in the tracker's ask record is "partly" or "not started". If the ask record cannot be read, the session is `needs-look`. A worktree's checks are all of F35 and the ignored files. Screen/state: skill, List. Tag: `@F49`.
- [ ] **F58** (A4, A6) The skill shall ask one question per batch with AskUserQuestion, sessions first, then worktrees. Every item gets one line ("web-app · fix login · idle 41d · what it was doing"). A batch over 25 items splits into batches of 25. The options are "Clear all N (Recommended)" or "Remove all N (Recommended)" and "Skip these N". It asks no question when no item is `removable`. Screen/state: skill, Asking. Tag: `@F58`.
- [ ] **F59** (A4, A6; rules ACT-1) When the owner answers "Clear all N" or "Remove all N", the skill shall run `act` with that batch's ids. The script shall re-check each id right before it acts, and re-read the session list for a session. It shall act only on an id that still passes. It skips and names an id whose re-check or action fails, or that is not in a fresh `list`. Screen/state: skill, Acting. Tag: `@F59`.
- [ ] **F60** (A4) If an exception typed under Other matches no item or several, then the skill shall ask again and run nothing. It says "I could not tell which one you meant. Nothing was changed." Otherwise it shall state the final list ("Clearing 4, keeping 1: web-app · fix login") before it runs `act`. Screen/state: skill, Asking. Tag: `@F60`.
- [ ] **F61** (A4, A6) When `act` ends, it shall print JSON with `cleared`, `removed`, `skipped` and `failed`. The skill shall write the report from it. The report reads "Cleared 5 sessions." and "Removed 3 worktrees. Branches kept." Failures read "Could not clear: web-app · fix login: <reason>", the reason cut at 60 cells. It adds "Kept, needs a look: web-app/login (uncommitted changes)." and "Skipped: docs (a session is running in it)." It counts only what succeeded. Screen/state: skill, Reported. Tag: `@F61`.
- [ ] **F62** (A1) The skill shall name an item that failed a check as "needs a look" and never offer it in a question. The script's `act` shall refuse such an id, whatever the owner answers. Screen/state: skill, Reported. Tag: `@F62`.
- [ ] **F74** (A1, A6; rules ACT-1) The script's `list` shall change nothing. It runs read commands only. Screen/state: skill, List. Tag: `@F74`.
- [ ] **F75** (A1, A6) If no row in the read carries a `pid`, then `list` shall mark every session `needs-look`, reason "no pid reported". `act` shall remove no session. The skill says "Nothing is removable: Claude Code did not say which sessions have a process." This is the rule of F4 and F11. Screen/state: skill, List. Tag: `@F75`.
- [ ] **F76** (A6; rules ACT-1) The tracker shall have no tidy. Home shall draw no TIDY block and no Tidy button. There shall be no `/tracker tidy`. The help line and the hint shall not name `tidy`. No source of the mod shall use `$.prompt.submit` or `$.tool.register`, and nothing is armed. Screen/state: Home; command help. Tag: `@F76`.
- [ ] **F77** (A6; rules NAME-1) The skill shall be named `git-cleanup-run`. Its frontmatter `name` equals the folder and `user_invocable` is `true`. Its `allowed-tools` names the script's commands, `Read` and the haiku subagents, and no `claude` or `git` command. Screen/state: skill. Tag: `@F77`.
- [ ] **F78** (A4, A6) The skill shall summarise each item with one read-only subagent that runs on `model: haiku`. The subagent gets the item's label as quoted data. Its text never reaches `act`, which takes only the ids of the owner's batch. Screen/state: skill, Summaries. Tag: `@F78`.
- [ ] **F79** (A1; rules WT-1) The ignored-file list of `list` shall name secret-looking names first and never hide one behind "and N more". The skill's worktree question shall list them. Screen/state: skill, Asking. Tag: `@F79`.
- [ ] **F80** (A4, A6) A row with no job `id` shall never reach `claude rm` in the script. `list` marks it `needs-look` with the reason "no job id". Screen/state: skill, List. Tag: `@F80`.
- [ ] **F81** (A6; rules ACT-1) The script's `act` shall take ids only as explicit arguments. It shall have no `--all`, no `--yes` and no way to read ids from `list`. Screen/state: skill, Acting. Tag: `@F81`.
- [ ] **F82** (A4; rules ACT-1) The script's tests shall run with a fake `claude` and a fake `gh` first on `PATH`. Their git fixtures live in a temporary folder. No test shall touch the owner's sessions, repositories or real `claude agents` output. Screen/state: skill. Tag: `@F82`.

### Safety

- [ ] **F64** (A4, A6; rules WT-1) If a code path of the tracker or the script passes a banned argument, the build fails. The banned are `--force`, `--force-remove-worktree`, `--discard-unpushed`, `-f`, `-D` and `branch -D`. A test greps both source trees. Screen/state: all. Tag: `@F64`.
- [ ] **F65** (A4, A6; rules ACT-1) Neither the tracker nor the script shall run `claude stop`. Neither shall run `claude rm` for a session whose latest read has a `pid`. Neither shall remove a worktree with a live session at or under it. Screen/state: all. Tag: `@F65`.
- [ ] **F66** (A4; rules ACT-1) The tracker shall never clear, remove or close anything on its own. Every tracker write follows a press of "Clear session", "Remove worktree" or "Reopen tasks". Every script write follows `act` with ids the owner chose in the skill's question. No model runs `claude rm` or a worktree removal itself. Screen/state: all. Tag: `@F66`.
- [ ] **F67** (A4; rules WT-1) Neither the tracker nor the script shall delete a branch. The tracker runs `claude rm` and git through `$.process.run`, and the script through `subprocess`, each with an argument list and no shell. Screen/state: all. Tag: `@F67`.
- [ ] **F68** (A4; rules PUB-1) The tracker shall show a worktree by its folder label. No shipped file shall contain a local path, internal name or URL. The script prints a path only in its JSON. Screen/state: all. Tag: `@F68`.
- [ ] **F69** (A1; rules PUB-2, DATA-1) The skill's output shall stay in the local transcript. The tracker reads only its own events, transcripts, git, gh, bd and the `claude` CLI. The script reads only `claude`, git, `gh` and the tracker's own records. Screen/state: skill. Tag: `@F69`.
- [ ] **F70** (A3, A4; rules ACT-1) The band shall gain no button, cell or hotkey, and the web Board shall gain no action. Screen/state: band; Board. Tag: `@F70`.
- [ ] **N1** (A4) While the Session page is drawn at 120, 80, 54 or 40 columns or a 24-column dock, the system shall clip no button. The actions box wraps one button per line when needed. Screen/state: Session, all.

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
- F25 — tag `@F25`: `clear.test.ts` › claude rm runs for a listed session with a job id and no pid; no id, no claude rm
- F26 — tag `@F26`: `clear.test.ts` › an unlisted session, or one with no job id, gets no claude rm and still closes tasks
- F27 — tag `@F27`: `clear.test.ts` › a failed `claude rm` is treated as not listed when a fresh read no longer lists the session
- F28 — tag `@F28`: `clear.test.ts` › claude rm failure with the session still listed shows the error line and Clear again
- F29 — tag `@F29`: `tasks.test.ts` › Clear marks the session's open tasks closed
- F30 — tag `@F30`: `clear.test.ts` › a failed save after claude rm shows the partly-cleared line
- F31 — tag `@F31`: `tasks.test.ts` › Reopen tasks removes the closed marks
- F32 — tag `@F32`: `tasks.test.ts` › closed tasks leave Home; tasks over 7 days never list
- F33 — tag `@F33`: `clear.test.ts` › result lines survive the 5-second re-read and not a new visit
- F34 — tag `@F34`: `pane.test.ts` › no clear command exists; session text opens the page
- F35 — tag `@F35`: `worktree.test.ts` › each of the five conditions on git fixtures, a session in a subfolder counts as using the worktree
- F36 — tag `@F36`: `worktree.test.ts` › the worktree line shows label and branch, never a path
- F37 — tag `@F37`: `worktree.test.ts` › the first failed condition is named
- F38 — tag `@F38`: `worktree.test.ts` › no gh judges by the branch only
- F39 — tag `@F39`: `worktree.test.ts` › the offer draws its lines and buttons
- F40 — tag `@F40`: `worktree.test.ts` › the offer's focus is on Keep worktree
- F41 — tag `@F41`: `worktree.test.ts` › ignored files: secret-looking names first and always listed, then cap 3, order, cut names, "and N more"
- F42 — tag `@F42`: `worktree.test.ts` › Remove worktree re-checks then runs git worktree remove without force
- F43 — tag `@F43`: `worktree.test.ts` › branch kept, result lines, no resume button after removal
- F44 — tag `@F44`: `worktree.test.ts` › a changed condition or ignored list removes nothing
- F45 — tag `@F45`: `worktree.test.ts` › a git refusal shows the error line
- F46 — tag `@F46`: `clear.test.ts` › Claude Code removing its own worktree is named and no offer follows
- F47 — tag `@F47`: `worktree.test.ts` › Keep worktree changes nothing
- F48 — tag `@F48`: `tests/test_git_cleanup_run.py` › list collects by idle time; unknown time is not collected
- F49 — tag `@F49`: `tests/test_git_cleanup_run.py` › list prints every check's result and a verdict; an unreadable ask record is needs-look
- F58 — tag `@F58`: `tests/test_git_cleanup_run.py` › SKILL.md holds one question per batch, batches of 25, the options and the item line
- F59 — tag `@F59`: `tests/test_git_cleanup_run.py` › act re-checks each id right before acting; a failure or an unknown id is skipped and named
- F60 — tag `@F60`: `tests/test_git_cleanup_run.py` › SKILL.md says an unmatched or ambiguous exception asks again and runs nothing, and the final list comes first
- F61 — tag `@F61`: `tests/test_git_cleanup_run.py` › act prints cleared, removed, skipped and failed, counting only successes; SKILL.md holds the report lines
- F62 — tag `@F62`: `tests/test_git_cleanup_run.py` › act refuses a needs-look id, whatever the answer
- F74 — tag `@F74`: `tests/test_git_cleanup_run.py` › list runs read commands only (the fake claude and git record their argv)
- F75 — tag `@F75`: `tests/test_git_cleanup_run.py` › no pid in any row: every session is needs-look and act removes none
- F76 — tag `@F76`: `pane.test.ts` › no TIDY block, no Tidy button, help and hint do not name tidy; `tests/test_agent_tracker_layout.py` › no `$.prompt.submit` or `$.tool.register`
- F77 — tag `@F77`: `tests/test_git_cleanup_run.py` › the skill's name passes `taxonomy.check_names`, folder equals name, `user_invocable` is true, `allowed-tools` has no claude or git
- F78 — tag `@F78`: `tests/test_git_cleanup_run.py` › SKILL.md names haiku and read-only for the subagents and passes labels as quoted data; act has no summary argument
- F79 — tag `@F79`: `tests/test_git_cleanup_run.py` › secret-looking ignored names come first and are never hidden
- F80 — tag `@F80`: `tests/test_git_cleanup_run.py` › a row with no job id is needs-look and never reaches claude rm
- F81 — tag `@F81`: `tests/test_git_cleanup_run.py` › act has no --all or --yes and refuses no ids
- F82 — tag `@F82`: `tests/test_git_cleanup_run.py` › the tests put a fake claude and a fake gh first on PATH
- F64 — tag `@F64`: `tests/test_git_cleanup_run.py` › no banned argument in the script or in `hooks/tracker/`; `cleanup-safety.test.ts` › none in any tracker argv
- F65 — tag `@F65`: `cleanup-safety.test.ts` › no claude stop, no rm or removal with a pid or a live session; the same in `tests/test_git_cleanup_run.py`
- F66 — tag `@F66`: `cleanup-safety.test.ts` › each tracker write follows a press; `tests/test_git_cleanup_run.py` › only act writes, and SKILL.md allows no claude or git
- F67 — tag `@F67`: `cleanup-safety.test.ts` › no branch deletion, no shell; `tests/test_git_cleanup_run.py` › no `shell=True`, no branch deletion
- F68 — tag `@F68`: `cleanup-safety.test.ts` › new words hold no path, internal name or URL (also `tests/test_plugin.py` grep)
- F69 — tag `@F69`: `cleanup-safety.test.ts` › no publishing site; `tests/test_git_cleanup_run.py` › the script's commands are `claude`, git and `gh`, and reads of the tracker's records
- F70 — tag `@F70`: `band.test.ts` › the band's cells, buttons and words are unchanged
- N1 — manual: the build agent reads the render check, counting rows as well as columns. It covers the Session page, its confirm, its offer and Home. Widths are 120, 80, 54 and 40 columns and a 24-column dock, with a terminal screenshot.

</details>

## Verification

- **Automated:** `claude plugin test plugins/agent-tracker` and `python3 -m unittest discover -s tests` exit 0.
- **Manual:** the render check of N1. Also one owner-run pass of `/git-cleanup-run`, because a test proves the script and the text of `SKILL.md`, not that Claude asks one question per batch.
- **Success measure:** the owner's spot check of the needs-you rows they judge dead: 0 in 5 of 5 checks by 2026-12-05. It does not use the rule's own data.

## Assumptions

- **Rows with no `pid` (F1, F4, F72, F75):** a row with no `pid` is ended. This is observed for background rows: every live row checked on 2026-11-14 carried a `pid`. For interactive rows without `pid` it is an assumption, and a fixture covers it. The F4 guard and the exception for this session's own id stay. If a read lacks this session's own row, it marks nothing ended, and the 5-second re-read corrects it.
- **Idle time (F48, F71):** the skill measures a session's idle time from its last activity. A cleared session's worktree counts through the worktree age rule, with no second definition. A time the row and transcript do not give is unknown.
- **Reopen tasks (F31):** it lives only while the owner stays on the page. It does not survive a pane re-open.
- **Report reasons (F61):** the report cuts each failed item's reason at 60 cells, like Clear's error lines.
- **Models (F78):** the subagents use `haiku` and only read. The session's own model asks the owner and changes nothing before the owner's answer. MODEL-1 covers the mod's own calls, which are unchanged.
- **Where the skill runs (F58):** in the session where the owner invokes it, because it asks questions.
- **Which id `claude rm` takes (F25, F80):** the row's job `id`. An interactive row has `sessionId` and no `id`, so the tracker and the script run no `claude rm` for it. This is observed on 2026-11-14 in `claude agents --json` and `claude rm --help`.
- **`claude rm` (F25, F43, F46):** it removes the session from Claude Code's list and keeps the conversation file. It also removes a worktree the session itself made, when that is safe (owner, dialog, 2026-11-14, "Allow, name it"). The confirm says "if", because Claude Code decides.
- **Default branch (F35):** the target of `refs/remotes/origin/HEAD`; with none, `main`, then `master`. With none of them, condition 4 relies on the PR alone (F38).
- **Linked worktree test:** `git worktree list --porcelain` lists the main checkout first; a fixture confirms it.
- **Copy resume command:** milestone 1 said ended sessions only; the built page shows it on every session, and F9 corrects that.
- **Old tasks:** a forgotten task of an ended session does not age out before 7 days; Clear is the answer.
- **Two implementations of F35:** the tracker's is TypeScript and the script's is Python. Both test files use the same case names for the five conditions, so a drift shows.
- **Fact numbering:** F1 to F70 belong to this change, and milestone 1's facts keep their own numbers in their own folder. F74 to F82 are new after the owner's decision of 2026-11-14. Retired ids are never reused.

## Retired

Facts of the first design that put tidy in the tracker. The owner's decision of 2026-11-14 removed it. Their ids are not reused.

- **F50, F51, F52:** the Home TIDY block, its absence and its waiting lines. F76 says Home has none.
- **F53, F54, F55, F56:** `/tracker tidy`, its prompt hand-off and its answers. F76 says there is no such command.
- **F57:** the supervisor prompt with a fixed list. F58 to F62, F74 and F78 replace it: code lists, Claude reports.
- **F63:** the help line and the hint naming tidy. They stay as built, and F76 says they do not name it.

## Out of scope

- A1, A2: the cleanup by hand of 72 worktrees and 6 sessions was done on 2026-11-14 (handover). This change builds the tracker side and the skill.
- A3: a Clear button on the band. The band gets no control (F70). The path is band, pane, task row, Clear.
- A4: "a supervisor agent that launches subagents": answered by the skill `git-cleanup-run` (F48 to F62, F74 to F82). A standing supervisor is not built, and neither are tracker tools or arming.
- Actions on the web Board: it runs no commands (F70).
- A day-count argument for the skill: fixed at 30 days.
- `claude stop`: neither the tracker nor the script stops a running session (F65).
- A tidy line, button or command in the tracker (F76).

## Deferred

- Resuming from a worktree made again from the branch is unverified. The default is the page text of F43.

## Open questions

None open.
