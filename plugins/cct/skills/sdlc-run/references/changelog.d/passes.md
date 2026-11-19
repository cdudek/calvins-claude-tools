# Pass records (notes for the release entry)

**A gate pass outlives its worktree.** The gate writes a copy of its bound report into
`<git-common-dir>/sdlc/passes/<change>/<scope>-<key>.json`, atomically (temp file, then rename).
The key is the milestone number (`milestone_number`: `<prefix><slug>-<n>` is n, the unnumbered
branch is 1), the feature's branch percent-encoded (`feat/a-b` and `feat/a/b` stay two files) or `0`
for the project. A failing run replaces the copy too. The copy survives `wt remove` and branch deletion.

- **Readers.** `pr-gate.sh` and `sdlc_status.py` read the checkout report and the shared copy through
  `pass_proof.py` only (`shared`, `chain`, `newest`; a test keeps every other file out of that folder).
  The newest report of the key wins, a newer failure or block ends the walk whichever copy holds it, and
  both copies go through the same `bound` check.
- **Old writers.** A writer from before this release writes no shared copy: its checkout report is read
  exactly as before. A report with no `format` and no binding key is read by its result line; a report
  with a `format` that lacks `change`, `owner` or `milestone` holds nothing. The mode comes from the
  report, never from the gate's source text. `bound` now also requires `change` on a `format` feature report.
- **A retained old writer** that fails after a new pass updates only the checkout report. That newer
  report blocks. The limit: when the failing checkout is removed, only the older shared pass is left.
- **Upgrade.** `verify_gate.py`, `pr-gate.sh` and `pass_proof.py` stay one kit version (the partner rule
  of `adopt --upgrade --replace` is unchanged); the new hashes are in `KIT_GATE`, `KIT_PR_GATE`, `KIT_PASS_PROOF`.
- **Known, not changed here.** The Stage 6 milestone goal asks GitHub for `milestone/<slug>-1`, not the
  unsuffixed branch, so a PR on the unnumbered branch reads `no-pr` (the same on every release).

`test_passes.py` pins the first attempt's failures (a format regex over the writer's source, selective
replace, a stale project pass after a failed rerun, the visual loop reusing the milestone key, two
feature names sharing a key) and runs writer x scope x record x PR on this code and on origin/main's.
