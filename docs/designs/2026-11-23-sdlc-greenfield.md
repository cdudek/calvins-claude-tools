---
type: design
status: proposal
created: 2026-11-23
author: Claude (Opus 5.5) for the owner
project: sdlc-run
supersedes: sdlc-run 3.x (installed-copies model)
---

# sdlc, greenfield: one approval, machine-checked contract, nothing installed

**Proposal for the owner to annotate.** It is written from three research tracks of 23 Nov 2026 (sources at the end) and from what went wrong in the HeyDiff v1 Beta planning.

## 1. What went wrong with 3.x

- **Copies in every repo.** `adopt` copies scripts, hooks, workflows, tier files and CODEOWNERS into each repo. Every kit change then needs a PR per repo: 18 repos today, and copies drift.
- **The owner as a gate.** The owner had to approve intent, the plan, every milestone gallery, hundreds of screenshots, every package install and every cross-repo push.
- **Gates that block the process itself.**
  - `pr-gate.sh` blocks other repos during a goal, so `/goal clear` hand-offs were invented.
  - `capture.py` rejects milestone 0.
  - The plan gate rejects E2E config it never asked for at adopt.
- **Reviews that never converge.** A broad "up to 40 findings" plan review never says ready, and it took four rounds.
- **Records in odd places.** The change folder lands on main and the next change deletes it. Model choices leaked into plans, issues and `sdlc.json`.
- **Ceremony over evidence.** There are eight documents per change, yet "done" can still be declared without running the app.

## 2. What the research says works

- **One approval up front, then machines check.** The owner approves a plan plus a validation contract; validators report and the orchestrator creates fix tasks (Factory Missions).
- **The contract comes before the code** and is executable. Tests are written first and fail first (Factory, Spec Kit Article III).
- **The builder never declares done.** An independent, sceptical evaluator does, and it drives the real app, not just unit tests (Anthropic harness posts, Factory).
- **Only the evaluator flips `passes`** in a JSON feature list that starts all-false. Agents may not edit tests or scoring; hooks enforce it, because "please don't cheat" barely works (Anthropic harness, METR).
- **One feature per fresh context.** State lives in a progress file plus git, so context resets don't lose it (Anthropic harness, Ralph, Codex long-horizon).
- **Stop-and-fix:** a failed milestone check is fixed before the next one starts (Codex long-horizon).
- **Hard gates are hooks and tests.** Model reviewers are advisory, and exit 2 blocks (Claude Code hooks, Codex review rules).
- **Records retire themselves.** Durable specs and decisions are merged into living docs, and the per-change folder is archived or removed (OpenSpec).
- **UI fidelity is measured, not eyeballed.**
  - Tokens are linted: no raw colours, sizes or fonts.
  - Each component has a story per state with interaction tests and axe.
  - Computed-style asserts check real spacing and size against the tokens.
  - Screens get only a thin structure layer.
  - Vision models misjudge spacing and alignment (under 55% accuracy), and bulk-approving baselines is a named anti-pattern (Chromatic, Percy, Applitools docs; FullFront, ScreenCoder papers).
- **Parallel workers:** no locks, no integrator role, scale effort to the task, and give workers shared decisions (Cursor scaling, Cognition, Anthropic research system).
- **Keep humans out of the loop** with a sandbox and an auto-approval boundary, a kill switch, an iteration cap and git rollback (Anthropic auto mode and sandboxing, Building Effective Agents).

## 3. The new model

### 3.1 Nothing is installed

- The plugin ships the skill, the scripts and the hooks (`hooks/hooks.json`). Every hook is inert unless a run is active in the current repo.
- **A repo holds nothing from sdlc.** Its `AGENTS.md`/`CLAUDE.md` describe the project (how to build, test and run the app), and its own CI stays its own.
- **Optional `.sdlc.json`:** only when a repo differs from what the plugin detects (e.g. an unusual E2E command). Absent means detect.
- **Upgrades** reach every repo by updating the plugin; there is no repo PR.

### 3.2 A run

- **Run:** one approved plan, carried out end to end. It may span several repos and several milestones.
- **Records:** they live in the start repo on the run's branch, in `.sdlc/<run>/`:
  - `plan.md`: intent, scope, milestones, and the repos involved;
  - `contract.json`: executable acceptance checks, written before code. Each is `{id, milestone, how: command | e2e-spec | computed-style, expect}`;
  - `progress.json`: features with `passes: false`, flipped only by the verifier;
  - `log.md`: decisions taken and questions defaulted.
- **Durable outcomes** go to living docs in the same PR: decisions to `docs/designs/`, product rules to `specs/`.
- **Before merge,** the final commit removes `.sdlc/`. The PR body carries the summary and a permalink to the last commit that had the records. Main never holds a run folder.

### 3.3 Touchpoints: one approval, then the end

1. **Plan approval (Plannotator, once).** Plan, contract and every planned dependency change are approved together. An approved dependency change is applied by the orchestrator with no paste blocks, because there is no repo hook to forbid it.
2. **During the run, nothing.** Defaults go to `log.md`. The run stops only for something outside the boundary set in the plan: new money, credentials, an irreversible external action, or a scope change.
3. **At the end, merges,** under each repo's own branch protection. Auto-merge where the repo allows it.

### 3.4 The loop

- **Planner (Opus):** writes the plan and contract. One fresh reviewer then argues against it, reporting blockers only, and there is one fix round. No review loops.
- **Orchestrator (the session):** dispatches; it never builds or reads boards.
- **Workers (Sonnet by default; the kickoff names models):** one feature per worker, each in its own worktree, with declared file ownership. They run in parallel up to the cap set in the kickoff. No locks; the orchestrator merges in dependency order.
- **Verifier (fresh, sceptical):**
  - runs the contract items for the feature against the real app (browser, Electron, extension);
  - flips `passes`;
  - files a fix task when a check fails.
- **Milestone:** all its contract items pass, then the full suite runs once and CI goes green. A failure is fixed before the next milestone (stop-and-fix).
- **Hard rules, enforced by plugin hooks:**
  - workers cannot edit `contract.json`, `progress.json` or existing test assertions;
  - the verifier's diff check flags deleted tests and new skip markers;
  - every goal has an iteration cap.
- **Done** is `sdlc check`: it exits 0 only when every contract item passes and CI is green. That is the Stop hook, so the goal evaluator sees the command's output.

### 3.5 UI and UX verification, with no human looking at images

1. **Tokens:** design variables map one to one to CSS variables. A lint fails on raw values.
2. **Components:** each variant and state has a story with interaction tests and axe set to `error`. Workers reuse kit components; a check flags raw markup where a kit component exists.
3. **Computed-style contract items:** generated from the design boards (spacing, size, colour and type per element, as numbers), run by Playwright in web, the extension and Electron.
4. **Screens:** an accessibility-snapshot structure check per flow, plus a screenshot attached as evidence.
5. **Advisory only:** vision comparison and LLM UX heuristics. Their findings become fix tasks, never pass or fail.
6. **No screenshot baselines and no approvals.** Neither the owner nor agents approve images.

### 3.6 Several repos in one run

- The plan lists the repos. The orchestrator works in all of them, each on its own run branch, and there are no per-repo records.
- **A dependency repo** (e.g. a design-system kit) is built first. Consumers use a packed artifact from a pinned commit, and the orchestrator re-packs when needed.
- **At the end, PRs open in release order:** the dependency first, then the swap to the published version, then the consumers. There is no mid-run push and no `/goal clear`.

### 3.7 Models and size

- **Models** are named only in the kickoff, never in records or config.
- **Size** scales the ceremony. A one-line fix needs a contract of one check and no plan document. A multi-repo program gets the full plan.

## 4. What is deleted from 3.x

- **Copied files:** `adopt` and every copied file (scripts, hooks, workflows, tier files, CODEOWNERS, `docs/sdlc.md`).
- **Owner approvals:** the owner gallery, screenshot baselines, the two-gate intent-then-plan flow (now one gate) and the milestone acceptance.
- **Change folders:** `changes/` on main, the sweep, `lock.json` and its hash checks, which the contract plus hooks replace.
- **Dependency hand-offs:** owner paste blocks for planned dependency changes, the per-repo runner records, and H1/H2 hand-offs mid-run.
- **Process rules:** model names in config, and the fixed "4 builders".

## 5. Migration

- **OMR repos:** being cleared now, with 13 PRs that keep `changes/` and `docs/designs/`.
- **Personal repos** (samplewerk, heapthat, heydiff): `sdlc clean` removes the copies. heydiff goes after its current run.
- **The kits:** 3.27.0 stays as the stopgap for heydiff's run on the old model. The new model ships as 4.0.0 in calvins-claude-tools first, then omr-ai-kit.

## 6. Questions for the owner

1. **Records:** on the run branch only, removed before merge (as proposed), or kept on main as an archive?
2. **Size scaling:** should a small fix skip the plan approval entirely and go straight to contract, build and verify?
3. **Boundary:** is "new money, credentials, irreversible external action, scope change" the right list of things that stop a run?

## Sources

- Factory Missions: https://factory.com/news/missions-architecture
- Anthropic, long-running harness: https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- Anthropic, harness design: https://www.anthropic.com/engineering/harness-design-long-running-apps
- Codex long-horizon: https://developers.openai.com/blog/run-long-horizon-tasks-with-codex
- METR, reward hacking: https://metr.org/blog/2025-06-05-recent-reward-hacking
- Cursor, scaling agents: https://cursor.com/blog/scaling-agents
- Cognition: https://cognition.com/blog/dont-build-multi-agents
- Claude Code /goal: https://code.claude.com/docs/en/goal
- Claude Code hooks: https://code.claude.com/docs/en/hooks
- Spec Kit: https://raw.githubusercontent.com/github/spec-kit/main/spec-driven.md
- OpenSpec: https://raw.githubusercontent.com/Fission-AI/OpenSpec/main/docs/overview.md
- Chromatic baselines: https://www.chromatic.com/docs/branching-and-baselines
- FullFront: https://arxiv.org/html/2505.17399v1
- Storybook accessibility testing: https://storybook.js.org/docs/writing-tests/accessibility-testing
- Playwright, Electron: https://playwright.dev/docs/api/class-electron
- Anthropic, auto mode: https://www.anthropic.com/research/claude-code-auto-mode
