<!-- Fragment of the core stream (gate, status, marks, hooks, adopt). The integrator folds it into one version entry; this file sets no version. -->

## Core stream: Speed A closed, Speed B core

**Speed A, round-3 fixes**

- **Strict rows only under an explicit lock format.** `approve` writes `"format": 3` into `lock.json`; a lock without it (even one that holds `done.json`) gets an `upgrade gap` line, every approved fact and no row, record or manifest block. The plan parser reads `F1 to F132`, `F1-F7, F71`, `F8-F20, F22-F34`, an en dash and bare-number milestone rows; a one-milestone plan whose cell names no id owns every fact. Fixtures follow real plans.
- **Routing cannot be waived.** `decisions.json` `size` and `visualSource` are locked at approval (`decisions.routing`); an explicit visual source needs its run whatever `size` says; a milestone passes `--visual-check` only with the shipped `visual-check.py` over an existing run folder.
- **Owner answers.** A `(Recommended)` suffix is ignored; a finding id removed and reused needs a fresh answer (the answer must be newer than the current incarnation of the id); `Fix it now` passes only after the box is ticked again later; transcripts are parsed once per process and only from sessions newer than the change folder.
- **PR status.** One function (`pr_flag`) names the phase: merged, awaiting CI, published, awaiting owner, held, failed, closed. An accepted Ask PR leaves `awaits-owner` (the workflow never arms Ask, so the agent does); a merged Ask PR is not DONE without the owner; a Hold blocks at any tier; red CI is `ci-failed`. A table test walks tier x armed x merged x answer x labels x workflow x CI and fails on a state that is DONE without proof or names no command.
- **Tier workflow.** The hold lookup fails closed, `labeled` re-runs it and a held, armed PR is disarmed.
- **E2E.** `approve` needs the full E2E and its x3 repeat; a suite added after a format-3 approval blocks the milestone. The preset repeats run the diff before the pipe (a git error fails), diff against the real parent (the project branch for a project milestone) and the python preset keeps `e2e/` out of the plain pytest run; `audit` understands the fragment and `{base}`.
- **Capture matrix.** Every capture names screen, state, width and zoom and has both zooms (100, 150); `qa.md` may record its build in a `Build commit` column; changed paths are read with `-z`; build QA writes `spec/qa.md` for a visual change with no spec folder.
- **Close findings** keep any id (`RC-1`) and label the rest (`U<position>`); the local project review uses the local project ref.
- **`adopt --upgrade`** lists the E2E gap and the old `REVIEW.md` sentence; a selective `--replace` brings the helpers a hook imports.

**Regressions found against what users run (fixed here)**

- A visual run on `milestone/<slug>-2` no longer records milestone 1 (the loop shadowed the number).
- A report decides strict or legacy: `format: 2` reports (and any report carrying a binding key) must carry change, owner and milestone; a report with neither is read the way the old reader did. The gate text in the checkout is never read.
- A joining change with no project is not a second owner; the README never links a git-ignored path; the readiness writer also checks the installed guardrail test.
- A deleted milestone branch is proven by the first-parent merge that brought it in (`pass_proof.proves` against its second parent); a fast-forward is `receipt-not-merged`.

**Speed B, core parts**

- One change resolver (`pass_proof.change_paths`: live, flat archive, `archive/<year>/<month>`; nothing left after the folder was removed) for the PR hook and `goal`.
- Approval needs `facts.md`, `plan.md` and `done.json`, a buildable milestone graph (unique ids, defined `needs`, no cycle) and a delivery mode that can be served (`feature-prs` with local milestones and a project branch is refused at approval).
- A format-3 close needs a `findings.md` with its `Converged:` line; an unreachable `origin/<default>` is a `reason=env` handoff; a check has a timeout (`checkTimeout`, per-check `timeout`, 1800 s) and its process group is killed; a check that ran while the tree moved is never cached.
- The security review runs at every milestone close from the goal's recorded start (`sdlc_status.py base <id>`).
- `goal --milestone 99` is `no-such-milestone`; the project recovery step names the project slug.
- `references/states.json` lists every state `goal` can print, how it is left and by whom; a test keeps it equal to the code and fails on a dead end.

**Known issues, not fixed here**

- F4 and hook caching: see the Group C notes below. Pass records stay out of this release.

- Mechanical: re-running `adopt` refreshes `verify_gate.py`, `marks.py`, `pass_proof.py`, `pr-gate.sh`, the presets and the tier workflow.
- Manual: re-approve in-flight changes that should get strict rows (`verify_gate.py approve <id>`, the owner's step); a repo that keeps its own `pass_proof.py` needs `change_paths` and `LAYOUTS`.

## Core stream: Group C (heads, handoff, removed folder)

**Plain words**

- **A removed change folder is DONE, not "no change folder".** The owner's rule removes the folder after merge. When a PR from the change's milestone branch merged (the number is read with the one `milestone_of` rule of the gate and the hook; the unnumbered branch is milestone 1), `goal` prints `DONE pr=<n> state=merged folder=removed`. With no merged PR, or when `gh` fails, an unknown id stays `no-change-folder`; the `.sdlc/outcomes` record alone is not proof of a merge, so it is not used.
- **Heads and bases are kept.** A passing milestone gate writes its head, base and gated commit to `state/heads.json` (new place first, old place second); a feature pass on `hotfix/*` writes the hotfix head. `goal` looks for the PR of the recorded head and compares its base with the recorded base, so a custom prefix, a nonconsecutive number or a unnumbered branch no longer invents a name.
- **Hotfix.** A change whose record says `milestone.kind: hotfix`, with a feature gate pass on its `hotfix/*` head, is pushed inside a one-go goal; `goal` then reads a feature gate and a hotfix PR into the default branch. The hook checks the recorded head, the kind and the feature report. An ordinary feature, a disabled hotfix or another head opens nothing.
- **Final project sync.** In PR mode `project/<slug>` may be pushed once: the default branch merged in and `VERIFY PASS project` on that head. Any other push still goes through milestone PRs.
- **Branchless project.** `sdlc_status.py record <id> project --sha <sha> [--accepted]` stores the default-branch commit that holds every milestone and the owner's acceptance. `goal --project` is DONE only with both (`project-not-integrated`, `project-not-accepted` say what is missing). The acceptance is the owner's answer to the dialog `Change <id>, finding PROJECT-<slug>: ...` (Accept milestone | Hold), read like an ask PR's; the `--accepted` flag alone is refused and a hand-written flag does not count.
- **HANDOFF on a cap.** `sdlc_status.py handoff <id> --cap turns|fix-rounds|retries` writes one `state/handoff.json` (what, why, exact next command); the gate's retry and no-progress caps write it themselves. `goal` prints `HANDOFF cap=<cap>` (new exit code 4: callers that parse the goal line must treat it as a stop like BLOCKED) while the work is open; a passing gate or `--resume` clears it. The goal templates stop on it and the plan's turn caps run it first. The project goal has its own cap, `goal.projectTurns` (default: the milestone cap).
- **PR hook.** A milestone PR whose head cannot be resolved to a commit here is refused instead of skipping the gate comparison.
- **The gate leaves the head and handoff records alone** when it checks the tree is clean; they ride along in the next commit.

**Fixed known issues**

- `goal --milestone 1` after M2 passed reads M1's own receipt.
- `after` never moves a check across a `serial` check.
- `lint <id> --pr-body` finds an archived folder, and for a removed one checks ids the body itself puts in brackets.
- Feature-PR delivery looks for `milestone/<slug>` without a number.

**Not done**

- F4 beyond the unresolved head: one change joining another's milestone legitimately shares its slug, so a receipt cannot be bound to a single change in the hook without breaking joins.
- Hook caching (the hooks already exit before any work).
