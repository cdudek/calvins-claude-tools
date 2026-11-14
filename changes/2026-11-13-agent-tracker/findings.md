# Findings: agent-tracker-1

One list for the milestone's one fix round. Unchecked items outside `## Advisory` block `verify_gate.py milestone`.

## Fix round

- [x] **S1 Strip control characters at every trust boundary** (security review of commit b6f48fe, Medium). `core/git.ts` `parsePrs` passes PR title, url and branch from `gh` into the store and the terminal unchanged; an escape sequence in a PR title could rewrite the screen. Fix once in `core/`: a `clean(value, max)` that removes C0 and C1 control characters and clamps length, applied to gh output, transcript-derived ask text and titles, and `claude agents --json` names. Keep `url` only when it starts with `https://`. Add one test with an escape sequence in a PR title and an ask.
- [x] **S2 Run git and gh without repo-controlled side effects** (security review of commit b6f48fe, Medium). `scan.ts` runs `git worktree list` and `gh pr list` in the session's repo. The repo is one the owner opened Claude Code in, so the risk is low, but the guard is cheap: pass `-c core.fsmonitor=false -c core.hooksPath=/dev/null` to git, and call `gh` only when `git remote get-url origin` names `github.com`; otherwise show the no-gh line. Add one test for a non-GitHub remote.
- [x] **V1 F12's 7-day clause is never exercised** (validation, partly). `plugins/agent-tracker/tests/backfill.test.ts`, test "only sessions with no file, active in the last 7 days, and never its own", sets an mtime on `other('old')` but never puts that file, so the cutoff is untested. Fix: `w.put(other('old'), TRANSCRIPT_TEXT)` before the `mtimes.set` line; the existing `toEqual([STORED])` then proves the old transcript is skipped. Test gap, not a behaviour bug (`backfill.ts:54` is right).

- [x] **R1 asks.ts:30** (code review, rev-080b8e0, confirmed). `plugins/agent-tracker/hooks/tracker/asks.ts`: `prompt.submit` awaits the haiku classify call before returning to the engine; the prompt waits on a model round trip. Classify after returning (do not await in the hook path) and store the kind when it lands.
- [x] **R4 collector.ts:43** (code review, rev-080b8e0, confirmed). `plugins/agent-tracker/hooks/tracker/collector.ts`: subagent descriptions are model-written and shown without `clean()`. Apply `clean()` (S1 follow-up).
- [x] **R5 collector.ts:95** (code review, rev-080b8e0, confirmed). `plugins/agent-tracker/hooks/tracker/collector.ts`: `session.start` awaits the first full poll including `claude agents --json`. Start the poll without awaiting it.
- [x] **R6 collector.ts:123** (code review, rev-080b8e0, confirmed). `plugins/agent-tracker/hooks/tracker/collector.ts`: the ProposeGoal branch sets `goalSince` even when the call failed or was denied, and skips saving its error count. Set it only on success; count the error.
- [x] **R7 core/merge.ts:21** (code review, rev-080b8e0, confirmed). `plugins/agent-tracker/hooks/tracker/core/merge.ts`: a session without a mod file gets `engine.since` = its start time, so its wait shows the session age. Leave `since` unknown and show no wait time for it.
- [x] **R8 core/milestone.ts:13** (code review, rev-080b8e0, confirmed). `plugins/agent-tracker/hooks/tracker/core/milestone.ts`: `parseMilestone` passes slug, sentence, feature names and states from a repo file to the screen without `clean()` (warning). Apply `clean()` (S1 follow-up).
- [x] **R9 core/pane-model.ts:180** (code review, rev-080b8e0, confirmed, unverifiable). `plugins/agent-tracker/hooks/tracker/core/pane-model.ts`: Home shows the gh-not-installed line when any repo is merely not on GitHub. Show it only when gh itself is missing or signed out; a non-GitHub repo shows no PR line.
- [x] **R10 core/rank.ts:10** (code review, rev-080b8e0, confirmed, unverifiable). `plugins/agent-tracker/hooks/tracker/core/rank.ts`: `isLive` excludes every transcript record, including sessions the agents list shows as running or waiting (warning). Live means present in the current agents list, whatever the record source.
- [x] **R11 core/states.ts:65** (code review, rev-080b8e0, confirmed). `plugins/agent-tracker/hooks/tracker/core/states.ts`: a failed list read restores every stored state, including sessions a crash left running weeks ago. Restore only sessions seen in the last good read.
- [x] **R12 pane/home.tsx:26** (code review, rev-080b8e0, confirmed). `plugins/agent-tracker/hooks/tracker/pane/home.tsx`: a repo with running and done sessions draws two headings with the same `repo:<path>` key and focus id. Make keys unique per section.
- [x] **R13 pane/session.tsx:29** (code review, rev-080b8e0, confirmed). `plugins/agent-tracker/hooks/tracker/pane/session.tsx`: Running now rows use their text as the React key; two subagents can share it. Key by id.

## Advisory

- **Hand checks in a real terminal** (validation, not testable here): hotkey labels and when they fire (F23, F80, F88); focus on the first row and Back returning to it (F38, F89); re-sort on reopen (F43); Escape returns the keys and leaves the pane open, Close and `ctrl+x x` close it (F91, F92); a real permission `waitingFor` value (F4, Q1); buttons not touching at an exact fit (Q19); 150 percent zoom (Q31); details columns on the desktop app (F37).
- **R2 backfill.ts:25** (code review, moved by the fix round): keeping the newest fragments of a cut-off grep needs a shell pipeline (`grep | tail`), but F13's test pins a bare `grep` and the safety test (F65) allows reads of `grep`, `git`, `gh` and `claude agents` only; the engine's truncation direction is also unrecorded. Next milestone, with a recorded cut-off and a test that allows the pipeline.
- **R3 band.tsx:52** (nit): every band render reads `settings.json` from disk; cache it with the snapshot. Next milestone.
- **R14 tests/test_agent_tracker_layout.py:21** (nit): the core-purity import check matches one line at a time, so a multi-line `import { … } from` is not checked. Next milestone.
- **Codex co-review did not run:** its workspace is out of credits; the review is Claude-only.

## Converge

- **Round 1 sources:** security review of commit b6f48fe (S1, S2, fixed), validation.md (V1), code review rev-080b8e0 (R1 to R14).
Converged: round 1
