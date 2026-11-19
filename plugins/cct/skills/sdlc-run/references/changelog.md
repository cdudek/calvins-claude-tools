# sdlc-run changelog

One entry per version, newest first. `adopt --upgrade` reads it: the headlines go into the
version warning, the **Mechanical** lines are what `adopt` does for you (it adds missing keys
with the stack's defaults and never overwrites a value), the **Manual** lines are printed for
the engineer. A version with no migration lines needs nothing but a re-run of `adopt`.

## 3.21.0 — a fast close, three-document changes and a living spec, a heavy-job queue, kept heads and handoffs, pass records that outlive the worktree

- **One owner for the full suite.** `verify_gate.py milestone` is the only runner of the full suite and the full E2E at the close. The extra full runs before it are gone, and the early review starts without a browser run. Targeted runs for a failure or a fix stay.
- **Cheap checks first.** The gate runs the offline evidence checks (owner marks, visual checkers) before the suites, so a missing screenshot costs seconds, not a full E2E run.
- **UX assessment without a PR.** `ux-assessment-run scope=change` takes a local `base`, `head` and `worktree` and hands them to every pass. The milestone close uses it before the gate, so it no longer waits for a PR that only exists after the gate. The PR form is unchanged.
- **One capture manifest.** One assessment owns every capture, keyed by build, reference revision, screen, state, width and zoom. After a fix only the changed cells are captured again, and a `qa.md` or a capture is stale when its inputs changed. `marks.py check` enforces it when `verify/shots/manifest.json` exists.
- **One fix round at the close, fed what already exists.** Remediation gets the joined findings and the code review's state directory and never starts a fresh review. Two fix rounds per screen stay for visual work while a screen is built.
- **Leftovers are settled by the owner's answer the gate reads.** The supervisor asks one `AskUserQuestion` per leftover (`Change <id>, finding <finding id>: ...`; options Fix it now, Accept as is, Defer to milestone <n>, Block the close). The gate reads the structured answer from the session transcript: Accept and Defer settle, Fix keeps it open, Block is terminal (`findings-blocked`). Hooks refuse writes into the session transcripts. A fact that is only partly met is never cleared this way.
- **The gate names the full E2E.** `checks.milestone` must hold a full E2E entry when the repo has an E2E suite; `approve` refuses a list without one and the presets carry the full E2E plus a ×3 repeat of changed and flaky specs. An older lock gets an `upgrade gap` line, never a failure.
- **Visual evidence cannot be skipped by omission.** The gate derives the required visual runs from the UX decision and the sources and fails `ux-visual-required` before the suites when none was given and no `skips.visual` is recorded; a loose reference image or a capture manifest now also starts `owner-marks`.
- **Sign-off beats auto-merge.** Status never reports DONE for an Ask PR, armed or not, without the owner's `Accept milestone` answer (`Change <id>, finding PR<n>: ...`), a recorded `Hold` blocks DONE and arming, and no recommendation to arm comes before the tier label. The Ship/Show/Ask workflow arms nothing while the PR carries `awaiting-owner` or `hold`.
- **The derived records cannot be removed.** A current-format change needs `done.json` and `decisions.json`; the plan's `## Milestones` section joins the approval lock (an older lock reports an `upgrade gap`); a milestone branch whose plan row lists no facts blocks; `skips.visual` counts only with the owner's `Skip visual evidence` answer. The change id and default branch must be plain names before they reach a shell, and the change folder must sit inside the changes folder.
- **Visual and converge findings reach the fix round.** `scripts/close_findings.py` appends the open non-advisory items of `findings.md` (ids kept) to the review state directory's `findings.json` and `verdicts.json`, so the triager no longer sees an empty fix set when the code review is clean.
- **The capture manifest is strict for new changes.** A change approved from 3.21.0 (`manifest: required` in its lock) must have `verify/shots/manifest.json` when it holds visual work, with full commit shas, reference digests, per-cell `sources` plus `shared` dependencies and a `qa.md` that records its own `Build:`. Staleness is per cell. Older changes keep the lenient check.
- **Feature PRs use the one-go order too.** Failing contract assertion, then the build, then live browser coverage; the E2E generator no longer runs before the surface exists.
- **The close passes its required UX checks.** `ux-assessment-run require=responsive,accessibility` overrides the dispatch matrix, so a route-only or words-only change keeps the 320 px reflow and accessibility checks; each is `ran` or a recorded skip, or the review is BLOCKED.
- **Adoption cleans the old close text.** `adopt` replaces the one known `REVIEW.md` sentence that started `review-fix-run` and keeps the repo's own rules, and the plan template's one-milestone branch no longer tells the closer to run unit and E2E beside the gate. In-flight plans keep their old text: edit the `One milestone` bullet of `plan.md` by hand (the gate is the only runner of the full suite and the full E2E).
- **Arming waits for the owner.** Auto-merge is armed only after the owner and visual dispositions are recorded. Status never tells anyone to arm a closed or Ask PR.
- **Tests that can start before the UI exists.** Stage 5 writes the smallest failing assertion from the fact first; browser E2E with live selectors comes after the surface exists. The runner is named; `test-e2e-policy` is the rulebook.
- **Fact proof is collected once.** Builders return evidence by fact, tag and tested commit. The close reuses it and exercises only what no evidence covers and the seams. The criteria auditor gets an explicit `verify/ac.json`.
- **The transcript guard runs everywhere.** `chain-gate.sh` refuses a Write into `~/.claude/projects` even in a repo without `sdlc.json`, and `gate-bash.sh` normalises quotes, `//`, `/./`, `~` and `$HOME` before it matches.
- **One way across versions: `adopt.py --migrate`.** Run `python3 adopt.py --migrate`, then re-run the milestone gate on the changes it lists. It replaces every kit-owned file (scripts, hooks, helpers, guardrail tests, workflows) as one set, keeps a file listed in `keep` (with a MANUAL line), removes `changes/archive/<id>` folders when gh confirms a merged PR from the change's own branch, tracked files only (the others are kept and listed), removes the old Claude workflows only when they match a kit version (a changed one stays, with a MANUAL line), stamps `sdlcVersion`, and prints the exact gate command for each change still in flight. `adopt --upgrade --replace` of one gate, hook or helper file now says "use --migrate" and stops, because a gate beside another version's hook reads a pass another way.
- **A repo's own script is never overwritten.** `adopt` writes `spec.py`, `heavy.py`, `db.py`, `evidence.py`, `preflight.py` and `helper-guard.sh` only where the path is free or the file is a kit version; a file of your own stays and a MANUAL line names it. `--migrate` leaves it untouched and prints a MANUAL line. The gate refuses a `heavy.py` that is not a kit version with `VERIFY BLOCKED reason=env`, so a repo script can never record a check as passed.
- **The newest gate report wins.** A failure newer than the pass receipt blocks the goal; it no longer reads DONE.
- **A merged Ask PR stays done.** The owner's recorded answer is read for merged PRs too, so an accepted Ask PR does not reopen after the merge, and a Hold on a merged PR still holds.
- **`--migrate` is safe to preview and to run.** `--migrate --dry-run` changes nothing; archives are removed only for a merged PR from the change's own branch.
- **`--migrate` keeps what is yours.** A hook or script that matches no shipped kit version stays, with a MANUAL line and a diff hint; `--migrate --force-kit <path>` replaces it (`kit-hashes.json` lists every shipped version, `kit_hashes.py` rebuilds it). It needs no preset when `sdlc.json` exists, adds no `ciPaths` or `ciCommands`, creates no change folder, and lists as in flight only a change with an unmerged branch or an open PR, with the branch and the gate command. `gate-bash.sh` matches case-insensitively and joins backslash-newline continuations, and the guardrail test reads the docs path from `sdlc.json`.
- **`--migrate` reads every `decisions.json` shape and reads before it writes.** A `milestone` that is a string, a dict or missing all work; a shape adopt cannot read means the branch is unknown and the archive is kept and listed. gh, the branches and every decisions.json are read first, and the archives are removed before the layout moves, so a failed read leaves the tree untouched.
- **`--migrate` sees every merged PR.** The merged heads come from all pages of closed PRs, not the latest 200, and a branch the change's own `plan.md` names (a feature branch) counts as its own. The in-flight list drops branches whose PR merged, and a flat-layout archive is removed in the same run.
- **A customised `claude-review.yml` stays, and the MANUAL line names the guardrail test that fails until you remove it.**
- **A removed folder is done only when the project is.** One merged milestone no longer ends a project: every planned milestone (read from `plan.md`, or `tasks.md` in layout 4, in history) must be merged, or the project's own PR merged into the default branch; with no plan left, a milestone merged into the default branch or the project PR is needed.
- **`spec.py outcome write` works on the default layout.** It reads the success measure from `intent.md`, and from `spec.md` on layout 4.
- **The guardrail suites accept layout 4.** Python and Node suites choose the required documents by the change's layout (S: `spec.md`; M adds `tasks.md`; L adds `design.md`), and they pass when the last change folder has been removed.
- **A scope-S layout-4 change builds.** `chain-gate.sh` no longer asks for a `## Handover` in a `tasks.md` that scope S does not have.
- **A retry-cap handoff is shown.** `goal` prints the HANDOFF (exit 4) while a handoff is open, even when the gate report is blocked.
- **The heavy queue never loses a ticket.** `heavy.py` writes tickets inside the queue lock and atomically, so a status scan cannot delete one half written.
- **`status.sh --current` knows layout 4.** The stage comes from `spec.md`, `design.md`, `tasks.md` and the lock, not from `facts.md`.
- **Finding a rule by words works on the whole rule.** `spec.py find` used to read only the 120-character summary, so an owner who described a rule in other words got nothing. It now reads the full rule text (the summary counts more), counts a rare word far more than a word that sits in half the rules, caps what a capability name can add, and orders ties by how many words matched, then by how old the rule is. `eval_corpus.py` also reads `asks/` and `spec/` folders, so more changes yield test cases.
**Review fixes.** The Codex review of the first 3.21.0 build found 17 gaps, all closed before release; the bullets above carry each one. In short: an owner answer to a structured dialog replaces quoted text as the only way to settle a finding, a visual row, a skipped visual run or a milestone acceptance; the gate derives what it must see (full E2E entry, one met row with evidence per approved fact, visual runs, a strict capture manifest) instead of trusting what is present; names that reach a shell are plain; and status, the workflow and the close text agree that sign-off beats auto-merge. An older lock reports an `upgrade gap` and keeps working; approving again picks up the new locks.

**Stricter locks and clearer status.** `approve` writes a lock `format: 3`; only then does a milestone need one met row with evidence per approved fact. The lock also fixes `size` and `visualSource`, and approval needs `facts.md`, `plan.md`, `done.json`, a buildable milestone graph and a delivery mode that can be served. A format-3 close needs a `findings.md` with its `Converged:` line. Checks have a timeout (`checkTimeout`, 1800 s) and their process group is killed. Status names one PR phase (merged, awaiting CI, published, awaiting owner, held, failed, closed) and never reports DONE without proof. `references/states.json` lists every state `goal` can print, and a test keeps it equal to the code. A report decides strict or legacy reading: a report with no `format` and no binding key is read by its result line, as 3.18 did.

**Three documents and a living spec (layout 4, opt-in).** A repo that sets `"layout": 4` in `sdlc.json` writes `spec.md`, `design.md` and `tasks.md` per change instead of intent, facts, plan, checklist, analyze, challenge, milestone and the reading map. What the product does is one file per rule, `specs/<capability>/rules/R123.md`, and the PR's diff is the delta. `scripts/spec.py` finds, shows, renumbers and checks rules; `check` needs a changed test for a changed rule and does not count skipped ones. In layout 4 `R<n>` is a rule and `V<n>` a review finding. A change already on the old layout finishes on it. `adopt` never moves a root `specs/` folder that holds rules.

**No archive.** After the merge, `spec.py outcome write` copies the success measure to `.sdlc/outcomes/<id>.json`, and the change folder is removed in one records-only PR. Older `changes/archive/` folders stay readable. A removed folder with a merged PR from the change's milestone branch is DONE for `goal`, not "no change folder".

**A heavy-job queue and fail-fast.** New scripts `heavy.py`, `db.py`, `evidence.py` and `preflight.py` are installed by `adopt`. One heavy job runs at a time per machine; waiters are told who holds the slot, and a dead process never blocks the line. Every milestone check runs through the queue, offline preflight runs first, and a slot that never frees is a handoff (`VERIFY BLOCKED reason=env`). `helper-guard.sh` refuses a subagent's heavy command outside the queue. A feature-PR repo with local milestones is refused. A failed stop leaves a status that `status` prints. The CI example gets a `preflight` job and separates deploy eligibility from path selection.

**Heads, handoffs and hotfixes.** A passing gate writes its head, base and gated commit to `state/heads.json`, so a custom prefix, a gap in the numbers or an unnumbered branch is found by what the gate saw. A change whose record says `milestone.kind: hotfix`, with a feature pass on its `hotfix/*` head, is pushed and read as a hotfix PR into the default branch. In PR mode `project/<slug>` may be pushed once, for the final sync. A branchless project is DONE only with the integrating commit and the owner's acceptance (`sdlc_status.py record <id> project --sha <sha>`, then the dialog). A hit cap writes one `state/handoff.json` and `goal` prints `HANDOFF cap=<cap>` with the new exit code 4. A milestone PR whose head cannot be resolved is refused by the hook. `goal --milestone 1` after M2 passed reads M1's own receipt.

**Pass records.** The gate also writes its bound report to `<git-common-dir>/sdlc/passes/<change>/<scope>-<key>.json` (atomic rename), keyed by milestone number, percent-encoded feature branch, or `0` for the project. The copy survives `wt remove` and branch deletion. `pr-gate.sh` and `sdlc_status.py` read the checkout report and the copy through `pass_proof.py` only; the newest report wins and a newer failure or block ends the walk whichever copy holds it. A writer from before this release writes no copy and is read as before. This brings back the pass records withdrawn in 3.20.5, bound to change, owner and milestone.

**Known issues.** One change joining another's milestone legitimately shares its slug, so the hook cannot bind a receipt to a single change (F4). A retained old writer that fails after a new pass updates only the checkout report; if that checkout is removed, only the older shared pass is left. The Stage 6 milestone goal asks GitHub for `milestone/<slug>-1`, so a PR on the unnumbered branch reads `no-pr` while the delivery is milestone PRs (feature-PR delivery looks for the unnumbered name). Back-fill of `specs/` and removal of old archives are not built.

- Mechanical: re-running `adopt` refreshes `scripts/verify_gate.py`, `scripts/marks.py` and `REVIEW.md` (the old `review-fix-run` sentence is replaced, custom rules stay), and stamps `sdlcVersion`.
- Mechanical (more): `adopt` installs `spec.py`, `heavy.py`, `db.py`, `evidence.py`, `preflight.py` and `helper-guard.sh` and registers the hook; it refreshes `verify_gate.py`, `pr-gate.sh`, `pass_proof.py` and the other gate files together (one kit version).
- Manual: a repo with a pending milestone asks the owner through the dialog instead of filling a `## Dispositions` table. An in-flight `plan.md` keeps the old text of its `One milestone` bullet (unit and E2E beside the gate): edit it by hand, the gate is the only runner of the full suite and the full E2E. A repo with an E2E suite and no full E2E entry in `checks.milestone` gets a MANUAL line; the engineer approves the change again. In-flight work needs a fresh milestone gate run: old reports carry no heads, handoff or shared copy, so run `verify_gate.py milestone <id>` once more before the goal reads DONE. Layout 4 is opt-in (`"layout": 4`); nothing changes without it. Callers that parse the goal line must treat exit code 4 (`HANDOFF`) as a stop, like BLOCKED.

## 3.20.5 — Pass records withdrawn from 3.20.x; they return in a later release

Pass records (shared receipts under `<git common dir>/sdlc/receipts/`, and everything that wrote or read them) were withdrawn from 3.20.x. Four review rounds kept finding regressions in that layer, all on the upgrade path: `sdlc_status.py` ships in the plugin and updates for everyone, while `verify_gate.py`, `pr-gate.sh` and `pass_proof.py` are per-repo copies that change only when someone runs `adopt`. Pass records come back in their own release.

- **A pass is read as 3.20.0 read it:** from the gate's report in the checkout (`verify/report.json`, a project's report in the git common dir, and a milestone's `verify/milestone-<n>.json`). The gate no longer writes a receipt, no gate or hook reads one, and `--milestone` and `RECEIPT_FORMAT` are gone. A receipt file already in a git dir is ignored, never an error; delete the `sdlc/receipts/` folder whenever you like.
- **What a pass covers is unchanged from 3.20.1:** `pass_proof.proves()` stays, the one rule for what a pass proves at a later head (a post-gate edit to `facts.md`, `done.json`, `lock.json` or evidence voids it; the archive move with a valid `archived_at` date is allowed; a live and an archive copy of one path void it).
- **The owner is read from the change record at the gated commit**, not from the branch tip.
- **A report names what it passed.** The gate writes `change`, `owner` (the project branch) and, for a milestone, `milestone` (the number its branch has through `milestones.branchPrefix`; the unnumbered `<prefix><slug>` is 1) into `verify/report.json` and `verify/milestone-<n>.json`. The hook and `goal` count a pass only when those match the change, the number of the target branch and the owning project, so M1's pass never admits M2 and another project's pass never admits a merge. A report from an older gate has none of them and is no pass for a numbered milestone: run the gate again. `goal` also requires a local milestone's receipt to cover its branch tip (`gate-sha-not-tip`).
- **Kept from 3.20.1 to 3.20.4:** PR `--base` hints and the wrong-base remedy first; tier-aware auto-merge advice; hotfix retarget to the default branch; the gate loads `marks.py` only where needed; `adopt --replace` takes partners only when they are unedited kit copies; the readiness fallback and mirror; the marks ledger migration, bundle screens matched by relative path, and the legacy `marks.py` block only with bundle inputs; a `[NEEDS CLARIFICATION]` marker in a Gherkin fence blocks; build QA follows `decisions.json` skips with size as the default; templates pass their own lint; no `__pycache__` from hooks; the PR hook reads each change record once per command.
- **`adopt --replace` keeps the three gate files at one version.** Replacing `verify_gate.py`, `pr-gate.sh` or `pass_proof.py` takes the other two along when they are unedited kit copies (a copy that matches a version in the kit's git history); an edited one is left and listed.
- Mechanical: re-running `adopt` refreshes `verify_gate.py`, `pr-gate.sh`, `pass_proof.py` and `marks.py`.
- Manual: a repo that keeps its own `pass_proof.py` must give it `proves(repo, changes_dir, gated, head)` (or take the kit's copy). A repo that took 3.20.1 to 3.20.4 files by hand should run `adopt --upgrade --apply --replace scripts/verify_gate.py` so the gate, the hook and the helper match.

## 3.20.4 — Fourth review round: one key, one reader, and a reader that follows the installed gate

_Pass records were withdrawn in 3.20.5 (see above); the receipt parts of this entry no longer apply._

The earlier rounds fixed findings one at a time. This one makes three things true, each with a test that fails if it breaks.

- **One name for a gate run's record.** A single function in `pass_proof.py` turns the branch, the scope and `--milestone` into the record's name. The gate, the PR hook and `goal` all call it, and nothing else works out a milestone number. Each feature has its own record (`feature-<branch>`), so two features no longer overwrite each other. The unnumbered `milestone/<slug>` branch and a plan with no milestone rows both mean milestone 1, so the feature-PR milestone can close. A visual run can no longer move a milestone's record to another number.
- **One reader.** Only `pass_proof.holds()` opens a record, and the goal check calls it with the owner, the commit, the name and the change. A test fails if any other shipped script or hook reads the records folder. A record missing any field it is bound by (change, scope, name, number, owner, commit, verdict) does not count, and another project's record never counts, `goal --milestone <n>` included.
- **The reader follows the writer, not the files.** `scripts/verify_gate.py` now says `RECEIPT_FORMAT = 2`. `goal` and the hook read that line in the repo's own copy. A gate without it (3.20.1 to 3.20.3, which `adopt --upgrade` keeps) is read the old way: `report.json` and the old `milestone-<n>.json`. A gate with it is read by its records alone, and a newer `report.json` can only block, never finish a goal. The version stamp in `sdlc.json` is used only when the gate file cannot be read.
- **A milestone merged without a record is done only if it merged before the change's first record.** One merged later without its own PASS is never done, and the done line no longer prints a PR head as the gate commit (`gate=none` when every milestone predates records). The gate writes a marker once, with the change's first record, to tell the two apart.
- **A deleted milestone branch is proven against the merge that brought it in.** `goal` finds the newest merge on the project branch that holds the gated commit and belongs to no later milestone, and checks that nothing but records changed after the gate. A second merge that carries a post-gate edit is not done, and a later milestone's merge cannot stand in for an earlier one. The history is listed once per poll.
- **The gate refuses instead of guessing.** If `pass_proof.py` is too old to name the key, or a feature run is on a detached HEAD, the gate stops with `reason=env` and says what to run.
- **The PR hook reads each change record once** per command, not twice.
- **Build QA follows the owner's record.** An activity is skipped when `decisions.json` `skips` lists it, so a restored preset skip is checked and a waived activity is not failed. The size is only the default.
- Mechanical: re-running `adopt` refreshes `verify_gate.py`, `pass_proof.py` and `pr-gate.sh`. `--replace scripts/verify_gate.py` now takes `pass_proof.py` along when it is an unedited kit copy.
- Manual: none that still applies; 3.20.5 withdrew the pass records.

## 3.20.3 — Third review round: one record of a pass, read in one place

_Pass records were withdrawn in 3.20.5 (see above); the receipt parts of this entry no longer apply._

- **Every gate run writes one receipt, and only the receipt is proof.** A passed, failed or blocked run writes `<git common dir>/sdlc/receipts/<change>/<scope>-<n>.json`: the verdict, the one commit the run started on, the scope, the milestone number, the project that owns the change, the time and the checks. It is written in one piece, and the `PASS` line names the same commit. `verify/report.json` stays as something to read and counts for nothing.
- **One reader, three callers.** The PR hook, `sdlc_status.py goal` and the stop check all ask `pass_proof.holds()`. The newest run of a change, scope and number wins, whichever worktree ran it. A later failed run now ends a pass, and M1's pass can no longer admit M2.
- **A pass is for one owner.** A change moved to another project needs a fresh gate run: an older pass for the former project does not let a merge or a PR through.
- **A milestone run needs its number.** On a detached HEAD, pass `--milestone <n>`; without it the gate refuses (`reason=env`) instead of writing a record that could stand in for a milestone.
- **Old changes keep working.** A change with no receipt at all keeps using its `verify/report.json` until its first receipt. A milestone that merged before receipts existed is never reopened as `milestone-gate-pass`.
- **Local milestones are proven against what merged.** With the milestone branch gone, `goal` checks the merge commit on the project branch (the second parent of a `--no-ff` merge). A fast-forward, or an edit made after the gate, is not done. A local `goal` with only receipts no longer crashes.
- **`--replace` knows every kit version.** The lists of unedited `marks.py` and `pass_proof.py` copies come from the git history, so a stock 3.20.0 `marks.py` is replaced with the new one. Replacing `pr-gate.sh` never overwrites an edited `pass_proof.py`; it lists it.
- **A kept old `marks.py` blocks only a milestone with design bundles.** The message says to take `scripts/marks.py` out of `keep` first, then run the replace command.
- **Screen names match the renderer.** Only the renderer's own `--<viewport>@2x` comes off an image name: `home--compact.html` is satisfied by `home--compact--desktop@2x.png`.
- **`archived_at` must be a real date** written `YYYY-MM-DD`. Anything else voids the pass.
- **An open question in a Gherkin step always blocks approval.** Only the template's own `<question>` and `...` placeholders are skipped.
- **Build QA fails on a missing required UX file.** `ia.md` and `interaction.md` may be absent only for the sizes whose preset skips them (S skips both, M skips `ia`). For size L a missing `interaction.md` is a QA failure.
- **A goal poll is cheaper.** The git directory is resolved once and each receipt is read once.
- Mechanical: re-running `adopt` refreshes `pr-gate.sh`, `pass_proof.py`, `verify_gate.py` and `marks.py`.
- Manual: none that still applies; 3.20.5 withdrew the pass records.

## 3.20.2 — Second review round: archive keeps its pass, no wrong merges, no silent skips

_Pass records were withdrawn in 3.20.5 (see above); the receipt parts of this entry no longer apply._

- **The archive commit keeps its pass.** Stage 7 adds `archived_at` to `facts.md`. That one added line, in a commit that moves the change into the archive, no longer voids the milestone pass. Any other edit to `facts.md`, `done.json` or the evidence still does.
- **A failed or blocked gate can no longer read as done.** The newest receipt of a milestone wins, so a later failed run is not hidden by an older pass. `goal <id>` without a number reads every milestone's own receipt, so it still works after the builder worktree is gone.
- **Local milestones follow the same pass rule as PR mode.** A criteria or evidence edit after the gate voids the pass there too.
- **A wrong base is fixed first.** Status prints the retarget command before anything about arming auto-merge, and a wrong-base hotfix PR is told to go to the default branch.
- **One milestone's receipt never admits another.** The PR hook matches the receipt's milestone number to the branch. It also reads the owning project from the change record at the gated commit, and still checks the parent and the pass when `gh pr create --repo` names this same repo.
- **An old `marks.py` blocks loudly.** A milestone gate with a `marks.py` that cannot list design bundles stops with `VERIFY BLOCKED reason=env` and names the upgrade, instead of passing an unrendered bundle.
- **`--replace` is careful.** Replacing `verify_gate.py` replaces `marks.py` only when it is an unedited kit version, and otherwise lists it for you. Replacing `pr-gate.sh` also installs `pass_proof.py`.
- **Rendered screens match by path.** `settings/index` and `index` are two screens. A legacy image row folds into its bundle only when the image still exists.
- **An open question inside a Gherkin step blocks approval.** Only the template's own placeholder is skipped there.
- **Size S build QA asks only for what size S makes.** `ia.md` and `interaction.md` are checked only when they exist. The readiness verdict is also written to `spec/validation.md` while an older hook may be reading it.
- Mechanical: re-running `adopt` refreshes `pr-gate.sh`, `pass_proof.py`, `verify_gate.py` and `marks.py`.
- Manual: a repo that keeps its own `marks.py` must give it a `bundles(change)` function (or take the kit's copy) before its next milestone gate.

## 3.20.1 — Review fixes: PR bases, receipts that survive, upgrades in either order

_Pass records were withdrawn in 3.20.5 (see above); the receipt parts of this entry no longer apply._

- **A PR opens against its real parent.** A feature goes into its milestone branch, a milestone into its project branch (or the default branch when there is none), a project into the default branch. The missing-PR hint now says `--base`, the hook refuses a milestone PR whose base is not its project, and `goal` is not DONE on any other base.
- **Recovery hints read the tier.** An unarmed `ask` PR names the human decision when `askGatesMerge` is on and is never told to arm auto-merge. A PR into the default branch is left to the workflow. Milestone and project PRs keep `--merge`.
- **Old and new files can sit side by side.** The gate loads `marks.py` only where it needs it, so an old `marks.py` never breaks `approve`, `audit` or `lint`. Replacing `verify_gate.py` or `marks.py` with `adopt --upgrade --apply --replace` replaces both. When the repo's `verify_gate.py` has no `--pr-body`, the PR skill lints with the plugin's own copy.
- **The readiness rename works in both directions.** Every reader prefers `spec/readiness.md` and falls back to `spec/validation.md`; renaming is optional.
- **Milestone receipts live in the common git directory** (`sdlc/receipts/<change>/milestone-<n>.json`), so every linked worktree sees them and removing a worktree cannot remove them. `goal --milestone <n>` reads that receipt first and uses the shared last report only when none exists. `milestones.branchPrefix` is honoured. The old `verify/milestone-<n>.json` stays readable.
- **One rule for what a pass proves.** After the gated head only close records and archive moves are allowed. A change to `facts.md`, `done.json`, `lock.json`, the marks ledger or the evidence folders voids the pass. The status check and the PR hook share it (`templates/hooks/pass_proof.py`).
- **The merge check finds the owner from the gated ref's own change record** and refuses when no single project owns the milestone.
- **`marks.py init` migrates an old ledger.** Rows for generated mockups (`ref:spec/prototype/...`) move to `retired` with their evidence, and rows for images inside a design bundle fold into the bundle row with their owner decisions. The rendered-folder check needs one image per screen by name, not a count.
- **The shipped templates pass the gate they ship with.** The intent example brackets its id, and the lint no longer reads `[NEEDS CLARIFICATION]` inside code as an open question.
- **Build QA resolves size and skips first.** A supplied visual source with a recorded spec-validation skip is authorised by the intent approval, so it never loops back to `validate spec`.
- **Hooks leave no `__pycache__`.** They run Python with bytecode writes off, as does the gate.
- Mechanical: re-running `adopt` refreshes the hooks (new file `pass_proof.py` beside `pr-gate.sh`), `verify_gate.py` and `marks.py`.
- Manual: a repo that replaces `pr-gate.sh` by hand must also take `pass_proof.py`; without it the hook blocks and says so.

## 3.20.0 — UI review rounds that end

- **Six layers with written tolerances.** A screen passes on structure, copy, tokens, geometry, rules and access, and review. The defaults are in `ux-build-validate` (the Measurements table gains a tolerance column) and the shared visual pass. A repo may tighten them, never loosen them without a decision record.
- **A pixel diff is advisory only**, because sample data in designs is meant to differ.
- **Severity for visual defects.** High blocks a task or fails contrast, Medium is noticed at a glance, Low is only visible when measuring and does not fail. These are the existing levels (P1, P2, P3) with examples, not a new scale; the build gate already failed only on P0 to P2.
- **One frozen defect list per screen and a budget.** Later reviews tick items off and add only High items or regressions. After two fix rounds per screen per design-system release, the owner gets a side-by-side list to accept or send back.
- **Design-system audit for big UI changes.** Over about 20 screens, stage 2 audits every reference screen against the design system, ships one release with all gaps, then freezes it. `marks.py` has a new reference status, `waits-on-design-system`, for a screen done in the app that waits only on the design system; it is not a failure.
- **Capture from one pinned commit.** Visual evidence comes from one build per milestone version, from a worktree pinned to one commit, never the live milestone branch. Each screen is captured in one batch, twice.
- New `references/convergence.md` holds the detail.
- Mechanical: re-running `adopt` refreshes `scripts/marks.py`. Nothing is written to `sdlc.json`.
- Manual: none.

## 3.19.0 — one visual source of truth, clear rules for each kind of design input

- **Stage 1 records one visual source of truth.** `decisions.json` gets an optional `visualSource` (`kind` and `path`); a change with no interface leaves it out. Every other input is a reference.
- **New `references/design-inputs.md`.** A table for each kind of input (export bundle, design-tool canvas, Figma file, image only, annotated screenshot, generated mockup): where it is stored, what is extracted, which checks apply. It also states what wins when inputs disagree (the owner's words and decisions, the declared source, the spec, the design system, then images) and the challenge rule: quote both sides, say what it means for the user, recommend one; ask outside a goal run, take the safer option and list it for review inside one.
- **The prototype ban is scoped.** The "no HTML, no Figma" rules in `ux-design-run` and `design-mockups-create` now say they cover prototypes the agent makes, not designs the team supplies.
- **`marks.py` sees export bundles.** A folder under `asks/` with an `index.html` is one input (kind `bundle`) with the hash of its files; a changed hash fails the check. It shows as "needs rendering" and fails until its screens are rendered to images in a folder under asks/ and the row's `rendered` names that folder; the images then become reference rows.
- **Review fixes.** `marks.py` hashes a bundle's files by their path inside the bundle, so a repo under a `.worktrees` folder no longer hashes nothing. A bundle is also found through `visualSource.path` (a React export has no `index.html`), and `verify_gate.py milestone` runs the marks check whenever a bundle exists, with or without a ledger. The `rendered` folder must be separate from the bundle and hold at least one image per HTML screen, checked in stage 2 before any build. Generated mockups under `spec/prototype/` are advisory: they are no longer `marks.py` rows. Build QA follows `visualSource` and is skipped for a skipped prototype only when no source is declared. The renderer is named from the installed plugin and run on a copy, so the pinned hash never changes. `design-inputs.md` lists the six layers, gives a reason for each precedence step, renames the challenge rule "Question the design source" (it writes `questions.md`, separate from the stage 4 `challenge.md`), and is now the only full statement of the visual-source rule.
- Mechanical: re-running `adopt` refreshes `scripts/marks.py` and `scripts/verify_gate.py`. Nothing is written to `sdlc.json`.
- Manual: none. A change with an export bundle renders it once and sets `rendered`.

## 3.18.0 — fast hooks, cheapest-first gates, local milestones, one build-validation name

- **The build comparison is `cct:ux-build-validate`.** Six places (the sdlc-run stages, chain, playbook and Stage 6 row, the design-mockups skill, `ux-run`, the dispatch reference) called a "build mode" of `cct:ux-spec-validate` that never existed. They name the skill that writes `qa.md` now, and a test fails if the old phrase comes back.
- **Hooks start the interpreter once per call.** `gate-bash.sh`, `chain-gate.sh`, `lint-on-edit.sh` and the Stop hook read the payload and `sdlc.json` in one process, not three to five, each 0.25-1 s behind a version-manager shim. `sdlc-config.sh` resolves `SDLC_PY`: `/usr/bin/python3` when it is usable without a spawn (on macOS only when the Command Line Tools or Xcode stand behind it), else `python3`; `SDLC_PYTHON=<path>` overrides it. The hooks need Python 3.7 or newer. `sdlc_field` stays in `sdlc-config.sh`, and each hook falls back to `python3` when an older `sdlc-config.sh` does not set `SDLC_PY`, so replacing one file at a time never leaves a gate failing open. A malformed `blocked[]` rule in `sdlc.json` is reported on stderr and skipped; the valid rules still apply. The repeat-block message of 3.16.0 is unchanged.
- **`verify_gate.py` runs checks cheapest first.** A passing check records its seconds in `verify/durations.json`; the next run sorts by them, and a check with no record sorts by a guess from its name and command (lint, format, typecheck, secrets, docs, then everything else, then build, e2e, docker). Equal costs keep their `sdlc.json` order; `"after": ["<check name>"]` keeps a check behind the one it needs (codegen before `tsc`) and `"serial": true` pins a check in place. An approval made before this version has no `"order": "cost"` in `lock.json` and keeps its declared order; a new approval records it. The first failure still stops the run; `--keep-going` runs every check and reports the first failure's verdict.
- **Local milestones (opt-in).** `sdlc.json` `milestones.merge: "local"` (default `"pr"`, absent means `pr`) keeps milestone branches and `project/<slug>` on the engineer's machine: no milestone push, PR or auto-merge, only the project's PR into the default branch goes online. New `verify_gate.py project <slug>` runs `checks.milestone` on the checked-out project branch and records `VERIFY PASS project`. `pr-gate.sh` refuses a milestone push when its change has a project branch, a milestone PR into a project branch, a project push without `VERIFY PASS project`, and a merge of a milestone ref into a project branch without `VERIFY PASS milestone`. `sdlc_status.py goal` calls a milestone done when its gated head is in the local project branch; `goal --project` reads the project's own record and PR; new `templates/goal/project.txt`. See `references/local-first.md`, "Local milestones".
- **One list.** `checks.milestone` is the repo's one local check list, the same one CI runs (`references/local-first.md`, `references/ci-blueprint.md`).
- **`adopt` takes out the generated Decision4 workflow** (`.github/workflows/decision4.yml` and `.decision4.lock`) that 3.9.x to 3.11.x wrote: Decision4 has been advisory since 3.12.0 and the workflow failed on every PR event. Only a file that matches the generated one exactly goes, and not when `sdlc.json` `keep` lists it; any other `decision4.yml` is the repo's own and stays.
- **The unused `SDLC_COOWNER` variable is gone** (adopt prints a notice when the old workflow had the step) from `ship-show-ask.yml`, `docs/sdlc.md`, `adopt`'s MANUAL lines and the references: nothing set it, so the "request the co-owner" step always skipped.
- Smaller: the builder greps tests and scripts for the old value when a requirement changes a timing or behaviour contract; Stage 7 greps for references into `changes/<id>/` before the archive move.
- **Review fixes.** A review of this release found and fixed: `goal` now checks every planned local milestone branch, the project PR's base and a records-only archive commit after the gate; a local merge needs a gate that ran against the current project tip and the milestone's own project; `adopt` refuses `delivery: "feature-prs"` together with local milestones, and the plan and milestone templates describe the local route; the blueprint copies of the scripts are refreshed and a test fails when they drift; `--keep-going` no longer stops at a blocked check; a milestone gate also writes its own `verify/milestone-<n>.json`, and a local milestone counts as done by that receipt, so deleting a merged milestone branch no longer reopens the goal. The receipt is bound to its milestone and change (`milestone`, `change`, an exact `VERIFY PASS milestone <id>` result) so a copied or foreign receipt does not count, and the branch merge is still required while the branch exists; `pr-gate.sh` reads reports only in the three supported layouts, admits a push, PR or merge only on the pass of the change that owns the branch, and refuses a local merge into a project branch it cannot resolve.
- Mechanical: re-running `adopt` refreshes the hooks, `scripts/verify_gate.py`, `ship-show-ask.yml` and `docs/sdlc.md` above its marker, and takes out the generated Decision4 workflow. Nothing is written to `sdlc.json`.
- Manual: restart open Claude Code sessions. A repo that lists a hook under `keep` in `sdlc.json` copies `sdlc-config.sh` and that hook by hand. A repo that lists `.github/workflows/ship-show-ask.yml` under `keep` deletes the "Request the co-owner (show)" step. A repo that set `SDLC_COOWNER` loses the automatic reviewer request on Show PRs; to restore it, add the reviewer to CODEOWNERS or add a workflow step that runs `gh pr edit "$PR" --add-reviewer <login>` for Show PRs (and list the file under `keep`). Set `checks.milestone` to the repo's single check script where one exists. Opt in to local milestones with `"milestones": {"merge": "local"}` before stage 1.2 of the next project.

## 3.17.0 — a change folder a newcomer can read

- A change folder starts with `README.md`, a reading map the status script writes: three entry points (understand, review, pick up the work), one row per document (the question it answers, who writes it, at which stage, whether a newcomer needs it) and the working files below a "For agents" line. `sdlc_status.py readme <id>` regenerates it.
- Plain words first, the id in brackets after ("Designs win over today's app (Q202)", never "per Q202"). The change templates say so, and `verify_gate.py lint` now flags a bare id in `intent.md`, `plan.md`, `milestone.md`, `questions.md` and a drafted `pr-body.md`.
- `sdlc_status.py ids <id>` prints every id with its one-line meaning and the file that decides it.
- `sdlc_status.py goal <id>` adds a second line when the goal is not done: the one thing in the way, why, who acts and the exact step.
- `docs/designs/INDEX.md` gives each entry a "Read when:" line, from a `read_when` field in the design's frontmatter or built from its type and tags.
- The spec's readiness verdict is now `spec/readiness.md`, so it no longer shares a name with the milestone's `validation.md`, which stays. The skip key `validation` in `decisions.json` is unchanged.
- `docs/sdlc-run.md` describes all seven stages as of this version, and a test fails when its stated version falls behind `SKILL.md`.
- Mechanical: re-running `adopt` refreshes `scripts/verify_gate.py`, `scripts/design_index.py`, the chain-gate hook and the change templates.
- Manual: a change in flight keeps working with `spec/validation.md` (the readers prefer `spec/readiness.md` and fall back to the old name); renaming it is optional, and a rename is never needed to keep a change working. Run `python3 scripts/design_index.py write` to add the "Read when:" lines.

**Review fixes.** `readme` writes only inside a change folder directly under `changesDir`, only over a README it generated, and only when the content changed; `status` never writes it. The id lint counts only ids the change defines, treats table prose as prose, flags `**B19 blocks the build.**`, follows a bracket across a line wrap, and runs on the drafts before reviewers, before the owner gate, first in `approve` (which refuses on failure) and on the PR body you publish (`lint <id> --pr-body <file>|-`). The blocker sentence uses the resolved gate scope, covers every reason the goal and the gate emit, and names the plugin path of `sdlc_status.py`. The reading map lists the standard spec files and any other file, picks the newest handover by date or number, and the glossary reads the `Finding` or `Challenge` column. The id lint skips the verbatim `Words` column of the intent's Asks table, where the owner's sentence is quoted as said.

## 3.16.0 — the gate hooks stop looping

- An ended goal (met, failed or `/goal clear`) no longer blocks: one shared helper, `goal_active.py`, reads the transcript for `pr-gate.sh`, `chain-gate.sh` and `verify-on-stop.sh`. `SDLC_GOAL_OFF=1` in the environment Claude starts with is the only off switch; there is no file switch.
- `pr-gate.sh` ignores shell redirects such as `2>&1` when it reads a push, applies the goal rule only to the session's repo (any worktree of it), and honours the session repo's `prExceptions`.
- A block that repeats exactly starts `STOP: this block repeated.`, names the hook and what it read, gives one owner action and says not to retry. Block history lives in `<git-common-dir>/sdlc-blocks/<session>.jsonl` and is kept 14 days.
- Mechanical: re-running `adopt` copies the new `goal_active.py` and `block_state.py` to `.claude/hooks/` and allow-lists `.claude/hooks/*.py`. A hook without its helper blocks and names `sdlc-run adopt`.
- Manual: restart open Claude Code sessions so they load the new hooks. A repo that lists a `.claude/hooks/` script under `keep` in `sdlc.json` copies the new `goal_active.py` and `block_state.py` by hand.

## 3.15.1 — verify-on-stop runs only after a turn that changed code

- The Stop hook ran `verify` (up to 300 s) after every turn, even a chat reply, because it asked "is anything uncommitted?" and not "did this turn change anything?". It also read the whole transcript on every Stop and re-ran a failing `verify` after every later turn.
- A new `UserPromptSubmit` hook, `turn-start.sh`, snapshots the source diff hash when you send a prompt. `verify-on-stop.sh` runs `verify` only when the hash differs at Stop.
- A state that was verified, pass or fail, is not verified again. A red state blocks once; it does not block again until the code changes.
- The `/goal` check reads the transcript last, only when `verify` would otherwise run.
- Mechanical: re-running `adopt` refreshes `verify-on-stop.sh` and `sdlc-config.sh`, adds `turn-start.sh` and registers the `UserPromptSubmit` hook in `.claude/settings.json`.
- Manual: restart open Claude Code sessions so they load the new hook. A repo that lists `.claude/hooks/verify-on-stop.sh` under `keep` in `sdlc.json` copies the new `verify-on-stop.sh` and `sdlc-config.sh` by hand.

## 3.15.0 — the local gate is removed; GitHub's required checks are the gate

- The local CI gate from 3.9.1 and 3.11.0 is gone: the plugin's Bash `PreToolUse` hook (`hooks/local-gate.py`) no longer blocks `git push`, `gh pr create` or `gh pr ready` without a `scripts/ci-local` receipt, and nothing posts a `local-ci` status. Merge protection is the repository's required GitHub Actions checks.
- `references/local-first.md` keeps the local iteration and failure loop (reproduce locally, batch fixes, no speculative pushes); `references/ci-blueprint.md` now says required checks are the gate, not confirmation.
- `adopt` no longer tells a repo to implement `scripts/ci-local`, a pre-push hook or a `local-ci` ruleset; it points at the required checks. The PR templates' "Local gate" line is now "Checks".
- Mechanical: re-running `adopt` refreshes `docs/sdlc.md` above its marker; the CLAUDE.md section and the PR template are written once, so edit "Local gate" and "full local gate" wording in them by hand.
- Manual: a repo that adopted the local gate deletes `scripts/ci-local`, the receipt-checking pre-push hook (`.githooks/pre-push`) and the `prepare` script that sets `core.hooksPath` (then runs `git config --unset core.hooksPath`), and replaces the required `local-ci` status in its rulesets with its GitHub Actions check.

## 3.14.0 — sdlc_status.py runs from the plugin

- The script lives in the plugin (`scripts/sdlc_status.py`) and runs from there with the working directory inside the repo: `python3 ${CLAUDE_SKILL_DIR}/scripts/sdlc_status.py map|goal ...`. No repo carries a copy; `/goal` conditions and `plan.md` name its absolute path through `<STATUS>` / `{{STATUS}}`.
- Mechanical: re-running `adopt` deletes `scripts/sdlc_status.py` and its docs paragraph is replaced (`/sdlc-run status`).
- Manual: `--upgrade` deletes nothing; `adopt --migrate` (or `adopt`) removes `scripts/sdlc_status.py` and names every Makefile or package.json line that still runs it. Point the `/goal` line of a change in flight at the plugin's script (`python3 <plugin>/scripts/sdlc_status.py goal <ID>`).

## 3.13.0 — Decision4 back as advisory

- Decision4 returns without any gate: no workflow, no `ci-local` step, no required `decision4` status, no hook that reads a PR body, and no `class` in `intent.md` or blocker in `verify_gate.py approve` (those stay removed from 3.12.0).
- Back, in plainer words: `boundary-map.yaml` (the lowest undo level per path), the AGENTS.md section "Decision4: how hard is this change to undo?", and the PR-template section "How hard is it to undo this PR after merging?" with the Decision record (Repair, Migrate and Answer only). New `references/decision4-pr.md`; the PR-body guidance in the skills points to it.
- `adopt` installs the map, the AGENTS.md section (and `@AGENTS.md` in CLAUDE.md when it exists) and the PR-template section, each only when missing. `project-repository-run` does the same through `--decision4`; `--check` never requires them.
- Mechanical: re-running `adopt` adds the three pieces where missing and refreshes `scripts/verify_gate.py` and `docs/sdlc.md` above its marker; existing files and sections are not rewritten.
- Manual: edit the starter `boundary-map.yaml`; a repo that kept the old Decision4 text from 3.9.x replaces it with the new section by hand.

## 3.12.0 — Decision4 removed

- Decision4 is gone: the PR-body sections "How hard is it to undo this PR after merging?" and "Decision record", the `boundary-map.yaml` scaffold, the AGENTS.md handoff contract, the shared `decision4` check and the `decision4` commit status. `references/decision4-pr.md`, `templates/decision4/` and `scripts/decision4_assets.py` are deleted; PR text keeps What, Why, Proof and Before merge.
- The intent `class` (Undo, Repair, Migrate, Answer) goes with it: `intent.md` no longer carries it, `verify_gate.py approve` neither requires nor locks it, and the build is no longer capped at an approved class.
- `adopt` no longer installs the workflow, boundary map, AGENTS section, ci-local snippet or PR-template section; it writes the kit's PR template once when the repo has none. `local-ci` is the only required status.
- Mechanical: re-running `adopt` refreshes `scripts/verify_gate.py` and `docs/sdlc.md` above its marker; it deletes nothing Decision4 installed.
- Manual: delete `.github/workflows/decision4.yml` (or `scripts/decision4-shared.sh` and its `--decision4` dispatch in `scripts/ci-local`), `.decision4.lock`, `boundary-map.yaml`, the Decision4 section of `AGENTS.md` and the Decision4 sections of the PR template; drop `decision4` from the required statuses in rulesets; remove `class:` from open `intent.md` files.

## 3.10.0 — goal conditions are end states

- `/goal` conditions are end states a small model can confirm from the transcript: `templates/goal/*.txt` are one sentence under 600 characters that name `python3 scripts/sdlc_status.py goal <ID>` and its `GOAL <ID> DONE` / `GOAL <ID> BLOCKED` line. The old paragraphs could not be satisfied after a merge, so the Stop hook blocked every turn.
- New `sdlc_status.py goal <ID> [--milestone <n> | --feature <n>]`: one line, exit 0 DONE (every milestone PR merged or armed, the last `VERIFY PASS` sha equal to the PR head, no open record), exit 3 BLOCKED, exit 1 OPEN. `gh` missing or failing is `OPEN gh-unavailable`, never DONE.
- The process moved into `plan.md` `## How to run` (sync with the parent right before each close; owner-added scope re-locks and gets one more close, logged under Revisions; the parent merge may run in the supervisor's worktree). `## Goal handover` holds a kickoff prompt and the `/goal` line.
- `stages.md` gains a "Waiting" section: CI by a background watch or `Monitor`, post-merge by a self-paced `/loop`, the success measure by `/schedule`, never a `/loop` inside a running `/goal`. `chain.md` flags the undocumented `goal_status` transcript entry the hooks read.
- Mechanical: adopt refreshes `scripts/sdlc_status.py`, where `goal` lives (an adopted repo already has the file; the goal templates are read from the installed skill).
- Manual: a running `/goal` keeps its old condition; start the next change from the new templates, and copy the kickoff prompt and `/goal` line from the new `plan.md` handover.

## 3.9.7 — preserve repository-owned CODEOWNERS

- CODEOWNERS is repository-owned: adopt never creates, edits or deletes it, including older generated files and tier changes. Generated guards no longer impose owner routing.
- Mechanical: none; every existing CODEOWNERS file is preserved.
- Manual: refresh generated SDLC guard tests with adopt; manage CODEOWNERS and required owner-review rules as a team-repo choice.

## 3.9.6 — upstream-faithful Decision4 by reference

- One contract in AGENTS.md, one PR section, a boundary-map scaffold and a pinned shared caller or checksum-verified local fetch; checker code and fixtures stay in the shared host.
- Repair returns its choice story; Migrate returns options; Answer returns labelled evidence and challenges, with no recommendation.
- Mechanical: no existing boundary map is overwritten.
- Manual: remove obsolete vendored Decision4 checker/fixtures after wiring the shared reference; local gates dispatch --decision4 through the fetch helper.

## 3.9.5 — scannable PR bodies, comments and decision records

- PR writers, milestone close and review feedback use bold-labelled What, Why and Proof lists and a full example; Before merge is conditional and Decision record appears at Repair/Migrate/Answer.
- Blueprint and adopting templates keep their readable recovery section and human checklists; refreshing recovery text preserves the existing decision record without duplicating it.
- Mechanical: none.
- Manual: refresh copied CLAUDE, SDLC docs and PR templates with `adopt --upgrade`; apply the same scannable shape to issues and review replies.

## 3.9.4 — gate branch publication on a clean, verified HEAD

- The plugin's Bash PreToolUse hook blocks `git push`, `gh pr create` and `gh pr ready` in repositories declaring a local gate unless the common Git directory holds `ci-local/<HEAD>.ok` and the worktree is clean.
- Tag-only and deletion pushes remain allowed; repositories without a gate retain the local-first policy.
- Regression fixtures cover linked worktrees, current and stale markers, package gates, dirty trees, command working directories and exemptions.
- Mechanical: none (the hook ships with the plugin).
- Manual: ensure the repository-owned full local gate writes its marker for the final clean committed HEAD after all checks pass; run the gate and publication as separate Bash calls.

## 3.9.3 — readable Decision4 PRs and offline scaffolding

- Project setup and adopt share the final blueprints PR #20 checker and regression cases, with the readable PR section and its writing-rules comment.
- Every blueprint PR template and PR creation, milestone close and review guidance uses the same recovery contract; legacy fields remain readable.
- Mechanical: new installs receive the template section, checker, fixtures and a starter boundary map. Existing maps and check runners remain repo-owned; other PR-template content is retained.
- Manual: use `adopt --upgrade` to review changed assets and `--apply --replace <path>` to accept them; install PyYAML, run `bash tests/decision4/run.sh` and keep actual body/changed-path validation in the repo's own gate.

## 3.9.2 — Worktrunk-first worktree lifecycle

- Worktrunk when installed; a single installation question in preflight/setup, with Git fallback on decline.
- Shared policy covers exact paths, fresh bases, PR heads, noninteractive JSON, local builder integration and cleanup.
- Remove hooks refuse dirty worktrees, never force removal, and retain unmerged branches.
- Mechanical: none.
- Manual: none.

## 3.9.1 — local-first verification and local gate adoption

- One shared local-first contract: reproduce the exact failure locally, run only failing tests and the directly affected suite until green, then the full local gate once before a batched push.
- Builders, milestone close, review fixes, flaky/E2E work, PR creation and copied instructions link the contract; no speculative pushes or pipeline retries for flakes.
- `adopt` preserves existing CI and no longer installs the legacy full remote workflow in a new repo. GitHub retains cloud/GitHub operations and scheduled work.
- Mechanical: none.
- Manual: implement and audit the repo-owned `scripts/ci-local` and pre-push hook; apply rulesets requiring exact-SHA `local-ci` and `decision4` statuses before removing existing required checks. Refresh copied agent/docs templates; see `references/local-first.md`.

## 3.9.0 — challenge, enforcement audit, negative fixtures, reflection, metrics

Ideas from Habitat-Thinking/ai-literacy-superpowers (Apache-2.0); no text copied. Mechanisms in `references/quality-passes.md` and `references/stages.md`.

- Challenge pass before gate 2: a fresh reviewer argues against the change (existence, simpler alternative, failure assumptions, implicit choices, who else is affected) into `challenge.md`. `verify_gate.py approve` refuses an open CRITICAL; no file blocks nothing. It is not analyze: analyze checks the documents agree, challenge asks whether the change should exist.
- `verify_gate.py audit`: read-only; per sdlc.json check and installed hook it reports installed, configured, executed and passed apart, plus whether the CI job is a required status on the default branch (`yes`, `no`, `local`, `unknown`). Run at adopt, at the milestone close and monthly from CI.
- Every `verify/report.json` and `report.md` gains operational metrics: checks run and outcomes, retries, review rounds, elapsed seconds, open findings.
- Stage 7 writes one short `reflection.md` per change; repeated lessons are listed for the owner to promote to the repo's agent file.
- The code reviewer and the `REVIEW.md` template gain four design questions (hidden dependencies, surprising side effects, domain vocabulary, composability). Tally line and the one fix round are unchanged.
- Tests: negative fixtures for chain-gate, pr-gate, gate-bash, plan-gate and verify_gate; `test_contract.py` (template sections, references, version, blocked reasons, hook wiring) and a keyword-heuristic trigger check. Sandboxed end-to-end runs are future work.
- Mechanical: none.
- Manual: refresh the gate script with `adopt`; run `python3 scripts/verify_gate.py audit` once; add the monthly audit job from `references/ci-blueprint.md` if wanted.

## 3.8.0 — rules, clarify, checklist, analyze, converge, class

Ideas from github/spec-kit (MIT); the mechanisms are in `references/quality-passes.md`.

- Rules: optional `sdlc.json` `rules` lists the repo's standing-rule files (default `CLAUDE.md`, `PRODUCT.md`, `DESIGN.md`, `docs/rules.md`, the designs index, `boundary-map.yaml`, `docs/architecture-policy.md`). Intent lists the rule IDs that apply, each fact cites the IDs it touches, and `plan.md` gains `## Rules check` and a `### Justified violations` table.
- Clarify is budgeted: at most 5 questions over nine areas, each with a recommended answer; defaults go under `## Assumptions`, at most 3 open `[NEEDS CLARIFICATION]`, leftovers under `## Deferred`.
- A reviewer writes `checklist.md`, items that test how the facts are written; an analyze pass writes `analyze.md` before gate 2. `verify_gate.py approve` refuses an unchecked item, an open CRITICAL, an unjustified violation and an intent without a valid `class`.
- Builders get a context pack (their facts, plan excerpt and cited rule text) instead of whole files.
- The milestone close runs an append-only converge pass. `verify_gate.py milestone` blocks with `validation-not-met`, `findings-open` and `not-converged`.
- Decision4 v1: `intent.md` records `class` (Undo, Repair, Migrate, Answer); the `/goal` closes only work up to the class approved at gate 2 and sends anything higher to `questions.md`.
- Mechanical: none (`rules` is optional; `adopt` only validates it).
- Manual: refresh the gate script and the goal text with `adopt`; add `class: <Undo|Repair|Migrate|Answer>` to the intent of a change that has not passed gate 2 yet; list the repo's rule files in `rules` when they are not the defaults.

## 3.7.0 — local milestones, builders that see them, no Claude in CI

- A milestone branch is local until its gate passes; Stage 1.2 no longer pushes it empty, which `pr-gate.sh` refused in one go. Its first push is the close push.
- Milestones are independent: each is cut from fresh `origin/<parent>` and merges on its own. Only a `## Milestones` row with `needs: M<k>` stacks one on another. The plan template gains that section.
- Milestone and project PRs merge with a merge commit (`ship-show-ask.yml`, the docs, the goal text), so a stacked milestone needs no rebase. Builders write Conventional Commit subjects, since the release now reads every commit.
- Parallel builders start from the milestone head: a `Base: <sha>` line, reset to before any edit, because a worktree hook cuts from the trunk. The supervisor commits its records first and merges builder branches one at a time.
- `cct:sdlc-feature-builder` gains `Mode: close`, so the agent Stage 5 gives the close to may run the full suite and the gate.
- `verify_gate.py` fails `check=moved` when HEAD or the tree changes during its checks. `pr-gate.sh` also finds a PASS under `changes/archive/`.
- A project is planning by default: `decisions.json` `project.branch` is `false` for a new one, its milestones go to the default branch, and Stage 6p checks the whole project there with no PR. A project without the key keeps its branch.
- No Claude in CI: `claude-review.yml` with `merge-gate`, `claude.yml` and `ci-triage.yml` are gone, and so is `ANTHROPIC_API_KEY`. The code review runs once, locally, at the milestone close.
- Mechanical: `adopt` removes the three Claude workflows (`git rm`) and the `claude` key from `sdlc.json`.
- Manual: drop `merge-gate` from the default branch's ruleset and classic branch protection, and delete the `ANTHROPIC_API_KEY` secret if nothing else uses it.
- Manual: turn on "Allow merge commits" in the repository settings; milestone PRs merge with one.

## 3.6.1 — reflow is checked at 320 CSS px wide, not in a 320 × 256 window

- The milestone verification checks WCAG 1.4.10 as written: 320 CSS px wide (1280 at 400 %) at an ordinary height, tested at 320 × 640. Its 256 px height is only for content that scrolls sideways (vertical writing); a fact or test that sets a 320 × 256 window, or asks for 400 % of every screen size, is stricter than WCAG and is corrected. Same rule in `ux-accessibility-audit`, `ux-responsive-audit` and the ux conflicts table (W17). Source: https://www.w3.org/WAI/WCAG22/Understanding/reflow.html
- Manual: a repo whose facts or E2E specs test reflow at 320 × 256 changes them to 320 × 640.

## 3.6.0 — builders: the model is a setting

- `sdlc.json` `builderModel` and `builderEffort` say which model builds and how hard. The default is `sonnet` at `high`: the `cct:sdlc-feature-builder` agent's own frontmatter, so nothing changes until a repo sets `opus` (or any Claude Code model alias or id), or `builders: "codex"` with a Codex model (default `gpt-5.5`). Every builder dispatch carries the pair; `codex-build.sh` gets it as `--model` and `--reasoning`. A plan's Approach may name another pair for that one change. Before this, a Codex build had no model unless the plan named one, so the wrapper refused to start.
- Mechanical: `builderModel` and `builderEffort` are added when missing (`sonnet` or `gpt-5.5` by `builders`, `high`); set values are kept; an effort outside `low`, `medium`, `high`, `xhigh` or an empty model stops adopt.
- Manual: nothing for the default. A repo on `builders: "codex"` checks that the added `builderModel` (`gpt-5.5`) is the Codex model it wants; a plan that already names a model keeps it, as the per-change override.

## 3.5.0 — builders: codex, an option

- `sdlc.json` `builders`: `claude` (default, `cct:sdlc-feature-builder` agents) or `codex`. With `codex`, feature rows and fix parts run through the kit's `scripts/codex-build.sh`: the Codex CLI in the feature worktree, `--sandbox workspace-write` with the network off, the builder's rules as the prompt, a schema-checked result, a check before the commit (the tree changed; no protected path, lockfile, manifest or locked test among the changes), and the commit made by the wrapper, since the sandbox keeps `.git` read-only. The supervisor, the milestone close (checks and gate only in this mode) and the gates stay Claude.
- Mechanical: `builders` is added as `claude` when missing; a set value is kept; another value stops adopt.
- Manual: to use it, set `builders` to `codex`, install and sign in the Codex CLI (`npm i -g @openai/codex`, `codex login`), and name the model and reasoning in the plan's approach section.

## 3.4.1 — the milestone close: one builder runs the local pipeline

- The goal text and stages.md give unit tests, the full E2E suite, the fix round and the gate to one `cct:sdlc-feature-builder` subagent that spawns no agents; the supervisor dispatches the reviews and the validation (a subagent cannot start its own).
- Manual: a `/goal` already running keeps its old condition; start the next one from the new `templates/goal/run.txt`.

## 3.4.0 — one milestone, one push, one PR: enforced, not described

- Mechanical: a new hook `.claude/hooks/pr-gate.sh` (PreToolUse on Bash). It refuses a PR into `project/*` or `milestone/*` from anything but a milestone branch, a push or PR of a milestone head without `VERIFY PASS milestone` on it (records-only commits after the PASS are fine), any push to `project/*` after its creation, any push to the default branch, and inside `/goal` any other PR or push. `decisions.json` `prExceptions` holds the engineer's words for a one-off exception.
- Mechanical: `verify_gate.py milestone` fails with `check=parent-sync` while `origin/<default>` (and `origin/project/<slug>` in a project) has commits the milestone lacks. Each milestone starts with a local merge of both, its row 0, never a `chore/merge-main-*` PR.
- Mechanical: the goal texts hand each milestone close to one subagent that runs the pipeline locally; the supervisor builds the next independent milestone meanwhile. Stage 6p no longer rebases or pushes `project/<slug>`; a blocking 6p finding becomes one more milestone.
- Manual: `adopt --upgrade --apply --replace .claude/hooks/pr-gate.sh`, `--replace .claude/settings.json` (registers it), `--replace scripts/verify_gate.py` and the goal texts. A run already in flight picks the hook up at once; restart Claude Code so the settings load.
- Manual: if branch protection on `project/*` requires PRs, keep it: nothing in the chain pushes there any more.

## 3.3.1 — `adopt --upgrade` never overwrites or moves anything

- Mechanical: nothing new. `--upgrade` adds missing `sdlc.json` keys, stamps `sdlcVersion` and writes no other file, moves no folder.
- Manual: every file that differs from the kit's copy is listed as `review diff`; read it with `adopt --upgrade --replace <file>` and replace it with `--apply --replace <file>`. A plain `adopt` still refreshes every kit-owned copy.

## 3.3.0 — the CI workflow ships as a template, ciPaths by file type, versioned repos

- Mechanical: `sdlc.json` gets `sdlcVersion`, `ciCommands` (per stack, from `templates/ci-commands.json`) and, inside an existing `ciPaths`, the missing `code`, `config` and `specs` (no value you set is touched).
- Mechanical: a repo with no CI gets `.github/workflows/ci.yml` from `templates/ci/github-actions.yml`.
- Manual: a repo that has its own CI copies the `changes` and `check` jobs from `templates/ci/github-actions.yml`, or replaces its `ci.yml` with the template.
- Manual: a changed file that is neither code nor config now runs nothing, so check `ciPaths.code` and `ciPaths.config` name the repo's own folders and file types; `ciPaths.docs` is now only the "never runs anything" list.

## 3.2.0 — CI step paths live in sdlc.json

- Mechanical: `sdlc.json` gets `ciPaths` (the stack's defaults, from `templates/ci-paths.json`).
- Manual: the repo's `changes` job reads `ciPaths` with `jq` instead of env strings.

## 3.1.2 — milestone work stays in the milestone PR

- Fixes, test and flaky-spec repairs, CI timeout tweaks and records are commits on `milestone/<slug>`, never their own PR. Re-run `adopt` to refresh the goal texts.

## 3.1.1 — CI blueprint gates every step on changed paths

- Manual: gate each CI job on the files a PR changes behind one aggregating `check` status (`references/ci-blueprint.md`).

## 3.1.0 — records ride along, no idle on CI, per-stack CI blueprint

- Records (plans, handovers, gate lines, validation, findings) ship in their milestone's PR; agents run only the tests they touched; `references/ci-blueprint.md` and the per-stack command table (`test-e2e-policy` section K) arrive. Re-run `adopt` to refresh the goal texts.

## 3.0.0 — the milestone process

- Milestones, projects, one `/goal`, `done.json`, `lock.json`, `verify_gate.py`, `docs/designs/`.
- Manual: a change in flight from v2 finishes on its own process (`references/chain.md`, History).
