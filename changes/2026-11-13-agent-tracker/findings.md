# Findings: agent-tracker-1

One list for the milestone's one fix round. Unchecked items outside `## Advisory` block `verify_gate.py milestone`.

## Fix round

- [x] **S1 Strip control characters at every trust boundary** (security review of commit b6f48fe, Medium). `core/git.ts` `parsePrs` passes PR title, url and branch from `gh` into the store and the terminal unchanged; an escape sequence in a PR title could rewrite the screen. Fix once in `core/`: a `clean(value, max)` that removes C0 and C1 control characters and clamps length, applied to gh output, transcript-derived ask text and titles, and `claude agents --json` names. Keep `url` only when it starts with `https://`. Add one test with an escape sequence in a PR title and an ask.
- [x] **S2 Run git and gh without repo-controlled side effects** (security review of commit b6f48fe, Medium). `scan.ts` runs `git worktree list` and `gh pr list` in the session's repo. The repo is one the owner opened Claude Code in, so the risk is low, but the guard is cheap: pass `-c core.fsmonitor=false -c core.hooksPath=/dev/null` to git, and call `gh` only when `git remote get-url origin` names `github.com`; otherwise show the no-gh line. Add one test for a non-GitHub remote.
- [ ] **V1 F12's 7-day clause is never exercised** (validation, partly). `plugins/agent-tracker/tests/backfill.test.ts`, test "only sessions with no file, active in the last 7 days, and never its own", sets an mtime on `other('old')` but never puts that file, so the cutoff is untested. Fix: `w.put(other('old'), TRANSCRIPT_TEXT)` before the `mtimes.set` line; the existing `toEqual([STORED])` then proves the old transcript is skipped. Test gap, not a behaviour bug (`backfill.ts:54` is right).

## Advisory

- **Hand checks in a real terminal** (validation, not testable here): hotkey labels and when they fire (F23, F80, F88); focus on the first row and Back returning to it (F38, F89); re-sort on reopen (F43); Escape returns the keys and leaves the pane open, Close and `ctrl+x x` close it (F91, F92); a real permission `waitingFor` value (F4, Q1); buttons not touching at an exact fit (Q19); 150 percent zoom (Q31); details columns on the desktop app (F37).
