---
type: design
status: approved
author: Claude (Opus 5.5), revised by Codex gpt-6.2-astra
created: 2026-11-23
project: sdlc-run
supersedes: sdlc-run 3.x (installed-copies model)
---

# sdlc, greenfield: one approval, machine-checked contract, nothing installed

The owner approves what will change and how to prove it. The runner builds across all named repos, verifies the result and prepares the PRs. The owner’s next action is a merge. Screenshots never need approval.

## 1. What went wrong with 3.x

- **Copies drift.** `adopt` copies scripts, hooks and workflow files into product repos. Fixing a gate in the kit leaves old copies enforcing old rules.
- **The owner became the scheduler.** HeyDiff exposed the cost of separate intent and plan approvals, gallery reviews, dependency paste blocks and cross-repo hand-offs.
- **The gates missed prerequisites.** A plan could reach verification before anyone knew whether the E2E setup could run. More plan-review rounds did not catch that.
- **Session state leaked into delivery.** The PR gate interprets `/goal` and the starting repo. A delivery spanning two repos still needs one answer about whether the combined change works.
- **Keep what worked.** The 3.x verifier already distinguishes `FAIL` from `BLOCKED`, binds a pass to a commit and runs the full suite before push. Its design-input guide already distinguishes a renderable board from a picture. Those distinctions belong in 4.0.

## 2. What the research says works

- **Agree on the proof before building.** Write observable acceptance criteria. For a changed behavior, demonstrate that the old behavior fails the intended assertion. [Factory Missions](https://factory.com/news/missions-architecture) · [Spec Kit](https://raw.githubusercontent.com/github/spec-kit/main/spec-driven.md)
- **Separate building from grading.** Give each builder a focused task. Give the evaluator the requirements, a clean candidate and access to the real app. Keep scoring outside the builder’s control. [Anthropic on long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) · [Anthropic on harness design](https://www.anthropic.com/research/harness-design-long-running-apps) · [METR on reward hacking](https://metr.org/blog/2025-06-05-recent-reward-hacking)
- **Parallelize independent work.** Share decisions, isolate edits and integrate in dependency order. Fix a failed milestone before starting work that depends on it. [Cursor](https://cursor.com/blog/scaling-agents) · [Cognition](https://cognition.com/blog/dont-build-multi-agents) · [Codex long-horizon tasks](https://developers.openai.com/blog/run-long-horizon-tasks-with-codex)
- **Measure the UI directly.** Browser geometry, resolved styles, keyboard behavior and accessibility assertions each answer a specific question. A screenshot is useful diagnostic evidence. [FullFront](https://arxiv.org/html/2505.17399v1) · [Storybook accessibility testing](https://storybook.js.org/docs/writing-tests/accessibility-testing) · [Chromatic baselines](https://www.chromatic.com/docs/branching-and-baselines)

## 3. The new model

### 3.1 Nothing is installed

- Enable the plugin once at user scope. It ships the skill, role definitions and runner. `sdlc` below means the plugin’s bundled executable. Product repos receive no SDLC config, scripts, hooks, workflow, records folder or package dependency for the harness.
- Discover commands from the repo’s existing instructions, manifests and CI at the starting commit. Put overrides in the approved run. Keep product tests and durable product decisions in the repo’s usual locations.
- **4.0 needs no new global hook.** Plugin hooks in `hooks/hooks.json` load wherever the plugin is enabled. Plugin subagents cannot set their own `hooks` or `permissionMode`. No hook may grant permission, sign an approval or record a pass. [Plugin reference](https://code.claude.com/docs/en/plugins-reference) · [Hooks](https://code.claude.com/docs/en/hooks) · [Subagents](https://code.claude.com/docs/en/sub-agents)
- **Plan approval and tool permission are separate.** Preflight the runner’s filesystem access, registry access and PR credentials. Use bounded, noninteractive permissions for jobs. A denied operation yields `BLOCKED permission`. Never turn on blanket permission bypass to finish a run. [Permissions](https://code.claude.com/docs/en/permissions) · [Sandboxing](https://code.claude.com/docs/en/sandboxing)

### 3.2 A run

One run has one ID and one approval. Its records live **outside every repo**, in `~/.sdlc/runs/<id>/` on the machine that runs it (owner to confirm, section 6). Nothing is committed and no repo needs a `.gitignore` entry. The PR body carries the plan summary, the contract result and the evidence links, so the record of what was approved and proven lives with the PR.

| Record | Contents |
|---|---|
| `plan.md` | Outcome, exclusions, repo identities and base SHAs, milestones, dependency order, release path and limits. |
| `contract.json` | One row per required check. Each names its ID, repo, milestone, runner, inputs, expected result, prerequisites and execution site. UI rows also name their design source. |
| Approved inputs | Pinned acceptance specs, fixtures, board extracts, token mappings and runner version. The approval identifies the digest of the whole bundle. |
| Checkpoints | Attempt counts, decisions, candidate SHAs, artifact hashes, verifier receipts, PR links and the next unfinished task. Progress is derived from these records. |

**Layout: the run ID is the address, so no index is needed:**

```
~/.sdlc/
  runs/2026-11-23-heydiff-web-v1-beta/   <date>-<start repo>-<slug>
    run.json                              title, status, repos, branches, PRs, checkpoint
    plan.md  contract.json  log.md
    evidence/
  active/2026-11-23-heydiff-web-v1-beta -> ../runs/...   only while the run is live
```

- **Run ID:** `<date>-<start repo>-<slug>`; a number is appended only if the same ID already exists that day. It sorts by date and reads like a sentence.
- **Branch = run ID:** every repo in the run works on `sdlc/<run-id>`. From any repo, `sdlc status` reads the current branch name and opens `~/.sdlc/runs/<run-id>/` directly; no search.
- **Active runs:** `~/.sdlc/active/` holds a link per live run and is cleared when a run ends, so `sdlc list` reads one tiny folder. History is `ls ~/.sdlc/runs`, already sorted by date.

The approval records the digest of the reviewed bundle. Plugin hooks block every agent from writing to `~/.sdlc/runs/`; only the runner's own scripts do. This stops a careless agent, not a hostile process on the same machine, which is an accepted risk for a one-owner setup.

The runner checkpoints after approval, each milestone merge and each external action: attempt counts, decisions, candidate SHAs, verifier receipts, PR links and the next unfinished task. Work itself lives in git on the run's branches.

**After a crash**, `sdlc resume <id>` reads the checkpoint, checks the recorded heads and remotes (an already-pushed branch or open PR is not redone), and continues with the next unfinished task in fresh worktrees. An interrupted check runs again. Resume works on the same machine; moving a run to another machine is out of scope.

### 3.3 Touchpoints: one approval, then the end

1. **Before approval.** The planner drafts the plan and contract together. It probes the required tools, credentials by capability, browser targets, local suites and existing CI. One fresh reviewer reports blockers. The planner gets one correction round. An unresolved blocker stays visible before kickoff.
2. **One approval.** Plannotator shows the plan, the actual checks and their expected values, dependency and lockfile changes, permitted destinations, release effects and caps. The owner approves the frozen bundle once. A small fix uses a short plan on the same screen.
3. **During delivery.** The runner takes approved defaults and records them. Missing authority, new spend, new credentials, wider scope or an unapproved irreversible action ends the attempt as `BLOCKED`. It reports the precise unmet condition. It cannot ask a worker to waive a check or treat silence as approval.
4. **At the end.** The owner merges the ready PRs under each repo’s existing protections. The runner arms auto-merge where the repo allows it and the class permits; otherwise the owner merges. Routine differences between repos are resolved at kickoff.

### 3.4 The loop

**Build.** The orchestrating session owns scheduling, integration and remote writes. Each builder is a Claude Code subagent in its own worktree, which the runner creates at the recorded integration SHA and checks before dispatch. A builder gets the feature, the shared decisions and the paths it owns, and returns a commit. The runner integrates disjoint work in dependency order; overlapping work runs one after the other and is checked again on the integrated head. Plugin hooks keep builders out of the records, the contract and the pinned tests. [Claude Code worktrees](https://code.claude.com/docs/en/worktrees) · [Subagents](https://code.claude.com/docs/en/sub-agents)

**Verify.** A fresh verifier subagent gets the approved checks and a clean checkout of the integrated SHA, and no builder transcript. The plugin's driver script runs the frozen specs and records the result; agent prose or files the candidate writes cannot set `passes`.

- **Protect the test path.** Pin the acceptance assertions, fixtures, command entry points and test-discovery settings at approval. Compare the candidate against the base for removed assertions, skips, changed CI or substituted runners. A planned test migration names the exact change and independent replacement proof. An unexpected change blocks integration.
- **Prove the check works.** For changed behavior, record the expected assertion failure on the base, then its pass on the candidate. For an invariant that already passes, use a known-bad fixture or negative control. A missing executable, zero collected tests or an app that never started cannot supply this proof.
- **Handle unavailable checks.** A real mismatch is `FAIL`. A missing browser, service, credential or supported runtime is `BLOCKED env`, with the prerequisite named. Retry a transient setup failure once. An existing CI job may supply the evidence only if the contract names it, it exercises the same assertion and it reports on the right revision. A CI-only item remains pending until then.
- **Close a milestone.** Run its due contract items and the repo’s full local gate on the integrated head. When they pass, the runner merges the milestone into the project branch automatically (locally, no PR); the only PR per repo is the project branch into the default branch at the end. On failure, rerun the failing check, fix it and run the full gate on the new head. A later integration invalidates receipts for the superseded candidate. Run the full contract on the final heads and dependency artifacts before declaring the PRs ready.
- **Bound the work.** Run up to 8 builders by default, fewer when the dependency graph allows less parallel work (the kickoff can change the cap), one initial build plus two fix attempts per feature, one transient retry per job, and a 30-minute job deadline. Kickoff sets a finite run deadline and total dispatch cap large enough for the plan. Count a dispatch durably *before* launch. CI polling consumes wall time. Exhaustion records `BLOCKED cap` with the failing item. Resume preserves the counters and deadline.
- **Check the graph before building.** At planning, and again before each dispatch, the runner builds the dependency graph of milestones and tasks across repos. A cycle is a planning error the planner must resolve before approval (split the task or move the shared piece earlier). At run time a task that waits on another waiting task, or a milestone whose tasks can never all become ready, is a deadlock: the runner records `BLOCKED deadlock` with the cycle, rather than idling.
- **Stop the work.** `sdlc stop <id>` durably marks the run stopped. The runner checks before dispatch, integration and remote writes, and polls while jobs are live. It cancels its job process groups, then kills survivors after a short grace period. A request already accepted by a remote is reconciled and recorded. Stopping preserves branches, records and evidence. Only an explicit owner restart can clear the stop within the original limits.

**`sdlc check <id>` is the completion test.** It is read-only. It verifies the approved digest, candidate and artifact identities, every required receipt, the full-suite result and current PR checks. It prints one status line with the run ID, heads and first unmet item. It never builds, reruns a suite, edits progress, pushes or merges.

| Exit | Status | Meaning |
|---|---|---|
| `0` | `READY` | All required proof is present for the current candidates. The remaining action is the owner’s merge. Already-merged producers have a recorded merge and matching release artifact. |
| `1` | `FAIL` | A required assertion or CI check ran and failed. |
| `2` | `BLOCKED` or `STOPPED` | Integrity, authority, environment or limits prevent completion, or the owner stopped the run. |
| `3` | `PENDING` | Work, evidence, an expected release or CI is outstanding within its deadline. |

`/goal` is optional. Its evaluator reads the conversation and can clear or pause a goal. It does not run the command. A session using `/goal` calls `sdlc check` explicitly and surfaces its result. There is no second Stop hook, transcript scraping or reliance on `/goal clear` to cancel jobs. [Claude Code `/goal`](https://code.claude.com/docs/en/goal)

### 3.5 UI and UX verification, with no human looking at images

1. **Pin the source.** Before approval, select a versioned design frame, structured export or renderable board. Record its digest, frame, state, viewport, theme and fonts. Render supplied code in an isolated scratch environment. A later edit to a live board cannot move the target.
2. **Derive each expectation from the board.** Map a design node to a stable app locator. For a structured board, extract the variable binding, auto-layout padding or gap, text style or frame bounds. Resolve tokens against the pinned design-system version. For an HTML board, measure the reference element in the pinned browser. Use `getComputedStyle` for resolved CSS and bounding rectangles for positions or gaps. [Figma node properties](https://developers.figma.com/docs/rest-api/file-node-types/) · [Browser computed styles](https://developer.mozilla.org/en-US/docs/Web/API/Window/getComputedStyle)
3. **Freeze a check a builder can implement.** For example, frame `Checkout/Mobile`, node `Pay button`, maps to the button named `Pay` at 390 CSS px in the default state. The node binds horizontal padding to `space-4`, which resolves to 16 CSS px. The verifier requires exactly one matching button and 16 px of left and right padding. Geometry checks state their tolerance in CSS pixels. Expected values never come from the candidate.
4. **Handle incomplete boards honestly.** A bitmap cannot establish a CSS token, DOM role or exact padding. Use explicit product rules and pinned kit tokens where available. List unsupported properties before approval. If exact fidelity is required, obtain structured input before kickoff. An inferred value never becomes a measured fact.
5. **Drive the real surface.** Exercise the flow, state changes, keyboard behavior and relevant accessibility rules. Use existing stories and axe where available. Use bundled Chromium with a fresh persistent context for an extension, and the Electron adapter for a supported Electron app. A web preview cannot prove extension or desktop behavior. Attach sanitized screenshots or traces to failures. No visual baseline or image sign-off enters the gate. [Playwright extensions](https://playwright.dev/docs/chrome-extensions) · [Playwright Electron](https://playwright.dev/docs/api/class-electron)

### 3.6 Several repos in one run

- **One dependency graph.** Kickoff lists each remote, base SHA, allowed branch, CI identity and dependency edge. Each repo gets one integration branch. The runner builds producers first and gives consumers artifacts identified by source SHA and content digest. A changed producer invalidates downstream proof.
- **One safe dependency path.** Before approval, resolve each planned direct change in disposable storage. Show the package, version, source, manifest and lockfile diff, transitive changes and required lifecycle scripts. The runner applies the approved diff with the pinned package manager, then performs a frozen install against approved registries. Disable install scripts unless individually required and approved. Unexpected resolution, integrity drift or an extra manifest change blocks the run.
- **Test what will ship.** A scratch override may point consumers at a packed producer for local integration. Keep local paths and scratch overrides out of the PR. The final consumer head must install from a source its own CI and users can fetch. Verify that artifact’s identity, then rerun the consumer contract and full gate.
- **Settle release order before building.** Prefer an existing immutable artifact or commit pin the repo already accepts. If publishing requires the producer merge, put that merge first in the final merge sequence. The runner then watches the existing release job, validates the published artifact, applies the pre-approved consumer pin and runs its gates. The owner’s only actions are the ordered merges. A release that needs a separate human publish, a new credential or an unknown version is a planning blocker.
- **Use existing CI.** Milestones run locally. Push a locally verified candidate when a PR or declared CI-only check needs it. Read GitHub’s required checks for the current head or test-merge revision and expected provider. A stale green result cannot pass. A skipped job cannot prove a contract assertion. Known absence of required CI may be approved as local-only. An unreadable policy is `BLOCKED`, and a required check that has yet to report is `PENDING` until its deadline. Queue-only checks run when the owner requests the merge. [GitHub required status checks](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks)
- **Keep the merge sequence visible.** Each PR shows its own readiness, current heads, producer dependency and evidence link. A producer can be ready for its final merge while its consumer is still pending publication. The whole run reaches `READY` only when the remaining PRs qualify. There is no cross-repo session hand-off.

### 3.7 Models and size

Model choices appear only in the kickoff. Pass them to the live role invocation. Omit model names from plugin roles, plans, contracts, stored commands, run reports and PRs. A resumed run can inherit the new session’s defaults. Its proof and remaining budget stay the same.

A one-line fix gets one plan paragraph, one executable acceptance check and the repo’s normal gate. A multi-repo change adds only the dependency edges, milestones and evidence it needs. Both get one approval.

## 4. What is deleted from 3.x

- **Installation.** Retire `adopt`, copied helpers, SDLC workflows, tier files and SDLC-owned settings.
- **Approval gates.** Remove separate intent approval, galleries, screenshot baselines, milestone acceptance and owner paste blocks.
- **Run paperwork.** Remove product-repo change folders, cleanup PRs and per-repo run records. Keep living product rules and design decisions in the PR that changes the behavior. [OpenSpec](https://raw.githubusercontent.com/Fission-AI/OpenSpec/main/docs/overview.md)
- **Session rules.** Remove goal-dependent push gates, fixed builder counts and model choices in repo config. Keep frozen criteria, local-first verification and branch protection.

## 5. Migration

- **Existing runs finish on their pinned 3.x installation.** Keep HeyDiff on its active version through its final merge. The inspected skill declares `3.21.0`. Confirm the installed version before treating the proposed `3.27.0` stopgap as available.
- **`sdlc clean <repo>` inventories by default.** Compare installed paths with known shipped hashes. List exact matches, locally edited copies, shared-file fragments and unknown files separately. `--apply` prepares the reviewed removals on a cleanup branch. Remove only matching kit files and exact owned fragments. Preserve mixed or modified files, native CI, `changes/`, living specs and `docs/designs/`. A second run produces no further diff.
- **Roll out once per kit.** Reconcile the work kit's existing cleanup PRs against that inventory. Pilot 4.0 in `calvins-claude-tools` with one personal repo, then a producer–consumer pair. Port the verified runner to the work kit. Later plugin upgrades need no product-repo PR.

## 6. Questions for the owner

1. **Where run records live.** Decided (owner, 23 Nov): `~/.sdlc/runs/<id>/` on the running machine, never committed, with the plan summary and evidence in each PR body. Alternatives: committed on the run branch and dropped before merge, or a gitignored `.sdlc/` in the start repo (needs a `.gitignore` line in every repo, which breaks "nothing installed").

## Sources

- **Current implementation.** [3.x skill](../../../plugins/cct/skills/sdlc-run/SKILL.md) · [Design inputs](../../../plugins/cct/skills/sdlc-run/references/design-inputs.md) · [Local-first checks](../../../plugins/cct/skills/sdlc-run/references/local-first.md) · [Verify gate](../../../plugins/cct/skills/sdlc-run/templates/scripts/verify_gate.py) · [Adoption](../../../plugins/cct/skills/sdlc-run/scripts/adopt.py)
- **Contracts and durable records.** [Factory Missions](https://factory.com/news/missions-architecture) · [Spec Kit](https://raw.githubusercontent.com/github/spec-kit/main/spec-driven.md) · [OpenSpec](https://raw.githubusercontent.com/Fission-AI/OpenSpec/main/docs/overview.md)
- **Agent execution.** [Anthropic long-running harness](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) · [Anthropic harness design](https://www.anthropic.com/research/harness-design-long-running-apps) · [Codex long-horizon](https://developers.openai.com/blog/run-long-horizon-tasks-with-codex) · [METR](https://metr.org/blog/2025-06-05-recent-reward-hacking) · [Cursor](https://cursor.com/blog/scaling-agents) · [Cognition](https://cognition.com/blog/dont-build-multi-agents)
- **Claude Code behavior.** [Plugins](https://code.claude.com/docs/en/plugins-reference) · [Hooks](https://code.claude.com/docs/en/hooks) · [Subagents](https://code.claude.com/docs/en/sub-agents) · [Worktrees](https://code.claude.com/docs/en/worktrees) · [Permissions](https://code.claude.com/docs/en/permissions) · [Sandboxing](https://code.claude.com/docs/en/sandboxing) · [Auto mode](https://www.anthropic.com/research/claude-code-auto-mode) · [`/goal`](https://code.claude.com/docs/en/goal) · [CLI](https://code.claude.com/docs/en/cli-reference)
- **UI and CI.** [Figma nodes](https://developers.figma.com/docs/rest-api/file-node-types/) · [Computed styles](https://developer.mozilla.org/en-US/docs/Web/API/Window/getComputedStyle) · [Storybook accessibility](https://storybook.js.org/docs/writing-tests/accessibility-testing) · [Playwright extensions](https://playwright.dev/docs/chrome-extensions) · [Playwright Electron](https://playwright.dev/docs/api/class-electron) · [Chromatic baselines](https://www.chromatic.com/docs/branching-and-baselines) · [FullFront](https://arxiv.org/html/2505.17399v1) · [GitHub required checks](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks)

## Build order for 4.0.0

1. Define the contract, approval digest, receipt format and `sdlc check` exit codes. Test a stale pass and a missing receipt.
2. Ship discovery, capability probes and one approval screen. Run them against a repo with no SDLC files.
3. Implement local checkpoints in `~/.sdlc/runs/` and `sdlc resume`. Kill a run mid-milestone and resume it on the same machine.
4. Deliver one feature through a builder subagent and an independent verifier. Prove that changing an assertion or forging a result cannot pass.
5. Add the dependency graph with cycle and deadlock detection, parallel worktrees (up to 8), automatic milestone merges into the project branch, deadlines, attempt caps and `sdlc stop`. Test cancellation during a job and recovery after a push.
6. Add board extraction and real-surface checks. Demonstrate a spacing failure, an image-only input and an unavailable browser.
7. Open one product PR and read its existing CI. Test pending, stale, skipped and failed checks.
8. Run a producer–consumer pilot through the final merge sequence. Verify the published consumer install and both final revisions.
9. Ship cleanup with dry-run fixtures for mixed files. Release from `calvins-claude-tools`, then port to the work kit.