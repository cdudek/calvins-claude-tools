---
type: findings
change: 2026-11-14-tracker-session-cleanup
created: 2026-11-15
---

# Findings: agent-tracker-4

One list from the milestone reviews on head 16754d0: a Claude code review (full-spectrum correctness and safety) and a criteria audit of every live fact. The Codex co-review did not run: its workspace is out of credits. No Critical or High finding. One fix round.

## Fix round 1

- [ ] **R1 F11 order (audit):** with no `pid` in the read, a session the old rule keeps as done or needs-you shows F9's line, not F11's "Clear waits" line. Check the pid-known gate before `hasProcess` in `core/clear.ts`; add a test with a non-ended session.
- [ ] **R2 act loses results (review 1, Medium):** an unreadable session list mid-`act` throws away `cleared` and `removed`. Catch it per id, skip the rest with "session list unreadable", print the four lists; test with a fake `claude` that fails on a later read.
- [ ] **R3 removal timeout (review 2, Medium):** the script's `git worktree remove` stops at 60 s; the tracker allows 120 s. Use 120 s.
- [ ] **R4 late verdicts (review 3, Medium):** the script's asks check ignores `latechecks.json`, which Home uses for open tasks. Read it; a late `partly` or `not-started` fails `asks`; a torn file is `needs-look`; test both.
- [ ] **R5 quoting (review 4, Medium):** `SKILL.md` puts ids in single quotes with no escape, and worktree ids are paths. `list` prints a ready-quoted `act_arg` per item (`shlex.quote`); `SKILL.md` uses it; test a path with a quote.
- [ ] **R6 double press (review 5, Low):** a second Remove worktree press before the first await reaches `removing` runs the removal twice and overwrites the success line. Set `removing` before the first await; test two overlapping presses.
- [ ] **R7 repo config (review 7, Low):** the script's git calls lack `-c core.fsmonitor=false -c core.hooksPath=/dev/null`, which the tracker passes. Add them; test.
- [ ] **R8 job id shape (review 8, audit):** the script passes any job id to `claude rm`. Apply the tracker's `^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$`; an id that fails is `needs-look`; test.
- [ ] **R9 F61 cut (audit):** the 60-cell cut of a failure reason lives only in `SKILL.md`. Cut it in the script's JSON too; test.
- [ ] **R10 F76 and F69 tests (audit):** no `@F76` test that Home draws no TIDY block or Tidy button; the layout test lacks its tag. No tracker test that every process call is one of the allowed sources (`claude`, `git`, `gh`, `bd`, `tail`). Add both.

## Advisory

- [ ] **A1 symlinked cwd (review 6, Low, unverified):** the tracker compares worktree paths as strings, the script with `realpath`. A row whose `cwd` differs from git's path by a symlink fails safe at `readWorktree`, but condition 5 could pass. Claude Code reports a resolved `cwd`; not changed here.
- [ ] **A2 skill conversation (F58, F60, F78, F79):** the model's side is proven only as text. The owner runs `/agent-tracker:git-cleanup-run` once (questions.md).
- [ ] **A3 N1 render:** frames come from a layout model, not a terminal. At 24 columns the offer runs 37 rows and the pane does not scroll. The owner checks a real render.
- [ ] **A4 real `claude rm`:** never run by the build. The owner's first press of Clear is the real check.
