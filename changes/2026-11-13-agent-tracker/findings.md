# Findings: agent-tracker-1

One list for the milestone's one fix round. Unchecked items outside `## Advisory` block `verify_gate.py milestone`.

## Fix round

- [ ] **S1 Strip control characters at every trust boundary** (security review of commit b6f48fe, Medium). `core/git.ts` `parsePrs` passes PR title, url and branch from `gh` into the store and the terminal unchanged; an escape sequence in a PR title could rewrite the screen. Fix once in `core/`: a `clean(value, max)` that removes C0 and C1 control characters and clamps length, applied to gh output, transcript-derived ask text and titles, and `claude agents --json` names. Keep `url` only when it starts with `https://`. Add one test with an escape sequence in a PR title and an ask.
- [ ] **S2 Run git and gh without repo-controlled side effects** (security review of commit b6f48fe, Medium). `scan.ts` runs `git worktree list` and `gh pr list` in the session's repo. The repo is one the owner opened Claude Code in, so the risk is low, but the guard is cheap: pass `-c core.fsmonitor=false -c core.hooksPath=/dev/null` to git, and call `gh` only when `git remote get-url origin` names `github.com`; otherwise show the no-gh line. Add one test for a non-GitHub remote.

## Advisory
