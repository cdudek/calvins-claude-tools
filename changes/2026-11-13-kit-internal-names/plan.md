---
linear: none
type: plan
change: 2026-11-13-kit-internal-names
design: null
author: Calvin Dudek
status: approved
reviewed_by: Calvin Dudek
approved_at: 2026-11-13T21:53
created: 2026-11-13
---

# Plan: Keep internal names out of the sdlc-run kit

> One sentence. What this change does.

A person with no context builds from this file alone. [intent](intent.md) and
[facts](facts.md) are for the gate, not for the build.

## Approach

- **What changes:** the two presets set `linear.team` to "". The Decision4 example and two test fixtures use placeholder names. The name test also catches the two names that slipped through.
- **What stays the same:** every other preset key, the behavior of `adopt.py` and `tracker.py`, and the adopted copies in this repo.
- **Why this way:** an empty team makes adopt ask which tracker to use; the wider pattern makes a return of the names fail the test.
- **Rejected:** a placeholder team name in the presets — it would still count as a set team and skip the tracker question.

## Rules check

- Before design: pass
- After design: pass

### Justified violations

none

## Design changes

none

## Where things go

| New file or kind | Folder |
|---|---|
| change folders | `changes/<id>/` |

## Feature PRs

Hotfix: one row, one PR straight into `main`, feature checks only.

| # | Feature | Facts | Branch | State |
|---|---|---|---|---|
| 1 | Remove internal names from the kit | F1 to F4 | `kit-internal-names/1-fix` | todo |

## Files that change

| File | Change |
|------|--------|
| `plugins/cct/skills/sdlc-run/templates/presets/node.json`, `python.json` | `linear.team` is "" |
| `plugins/cct/skills/sdlc-run/templates/decision4/AGENTS-section.md` | example uses `other-repo #1931` and `ABC-1344` |
| `plugins/cct/skills/sdlc-run/scripts/test_adopt.py`, `test_tracker.py` | fixtures use `ABC-947` and `ABC` |
| `tests/test_plugin.py` | `test_no_private_or_internal_names` pattern also catches the two names |
| `changes/2026-11-13-kit-internal-names/*` | this change's intent, facts and plan |

## Order of work

- [x] 1. Empty `linear.team` in both presets — proof: F3
- [x] 2. Replace the names in the Decision4 example and both test fixtures — proof: F1 and F2
- [x] 3. Widen the pattern in `test_no_private_or_internal_names` — proof: F1
- [ ] 4. Run the unit tests — proof: `python3 -m unittest discover -s tests` exits 0 (F1)
- [ ] 5. Run the adopt and tracker tests — proof: `python3 -m pytest -q plugins/cct/skills/sdlc-run/scripts/test_adopt.py plugins/cct/skills/sdlc-run/scripts/test_tracker.py` exits 0 (F2)
- [ ] 6. Check the presets — proof: the python3 one-liner in F3 exits 0
- [ ] 7. Run the plugin tests — proof: `scripts/run-plugin-tests.sh` exits 0 (F4)
- [ ] 8. Run the gate — proof: `python3 scripts/verify_gate.py feature 2026-11-13-kit-internal-names` prints `VERIFY PASS`

## Milestones

| Milestone | Features | needs |
|-----------|----------|-------|
| M1 hotfix | F1 to F4 | none |

## Risks

| Risk | What we do | Where it lands |
|------|------------|----------------|
| A repo with a set team loses nothing, but adopt now asks the tracker question for every new repo | accepted, it is the intended behavior | accepted |
| A name stays in a file the pattern does not scan | the pattern runs over the whole repo | step 4, F1 |

## Out of scope

- Cleaning the adopted copies in this repo — done by hand in the adopt change.

## Done

What must hold, as data in [done.json](done.json) (facts, test tags, pages, states). The goal
below ends on the status line of `sdlc_status.py goal`, which reads the verify gate and the PRs,
so every line here is proven by a check, not by a claim.

- `python3 scripts/verify_gate.py feature 2026-11-13-kit-internal-names` ends `VERIFY PASS` for every feature.
- Both presets have `linear.team` equal to "".
- F1 to F4 pass by their named check.
- Nothing outside `## Files that change` is edited.
- Stop and report as soon as a step cannot proceed. Never work around a blocker.
- Stop after 40 turns if not met. Report what is missing.

## How to run

The process of the build. The `/goal` below holds only the end state; everything the run does
lives here, in the skill's stages and in the hooks. Read the [local-first
contract](https://github.com/cdudek/calvins-claude-tools/blob/main/plugins/cct/skills/sdlc-run/references/local-first.md)
before any check or push: it owns local iteration, failures and the final full gate.

- **Scope:** deliver this change in one go, per this plan and `facts.md`.
- **Milestones:** every row of `## Milestones`, in order. Each one is a local branch
  `milestone/<slug>-<n>`, cut from fresh `origin/<parent>`. `<parent>` is `project/<slug>` when
  the project has a branch, else `<default>`. A milestone with `needs:` is cut from that local
  milestone instead. Building never waits for a merge. Nothing is pushed before its gate passes.
- **Sync:** the first row of a milestone is a local `git fetch origin && git merge
  origin/<default>` (also `git merge origin/project/<slug>` when the project has a branch).
  Repeat it right before each close, and after any earlier milestone merges. It is never a PR.
  The milestone gate fails `check=parent-sync` without it. The merge may run in the supervisor's
  worktree.
- **Features:** write the tests for the feature's facts, build in the folders of `## Where things
  go`, commit. Between features run the touched tests, their directly affected suite and the
  required pre-commit checks, then start the next feature at once.
- **Builders:** feature builds and fix parts go to `cct:sdlc-feature-builder` agents. Each prompt
  carries a context pack: the feature's facts, its plan excerpt and the text of the rule IDs
  those facts cite, not whole files. Dispatch with isolation `worktree` and a `Base: <milestone
  head sha>` line after you commit your records. Merge their branches back one at a time. When
  `sdlc.json` `builders` is `codex`, use the kit's `scripts/codex-build.sh` instead; with codex
  the close builder runs checks and the gate only. Either way use `builderModel` and
  `builderEffort`, or the pair this plan's Approach names (`stages.md`).
- **Records:** plans, handover, findings, validation, gate output and every fix or test repair are
  commits on the milestone branch. Open no other PR and push nothing else (`pr-gate.sh` refuses
  it). A record that can only be written after a merge goes in the next milestone's first commit.
- **Questions:** an open question never stops the build. Write it to `questions.md` with the
  default you took, tell the engineer in one line, and carry on.
- **Close:** once a milestone's features are committed, hand its local pipeline to one
  `cct:sdlc-feature-builder` subagent with `Mode: close` and the head it runs on. It spawns no
  agents and nothing merges into the milestone while it runs. It runs the unit tests, the full
  E2E suite once (changed and flaky specs ×3, the committed `e2e/flaky-specs.txt` per
  `cct:test-e2e-policy`, `suite-speed-and-reliability.md` section G), the one fix round on the
  blocking findings, then `python3 scripts/verify_gate.py milestone 2026-11-13-kit-internal-names`. Its full output
  is pasted.
- **Meanwhile:** dispatch the Stage 6 reviews on the milestone diff in parallel. Validate every
  fact and ask of the milestone against the built app into `validation.md` (expected, observed,
  evidence, verdict). Run the append-only converge pass from `quality-passes.md` into
  `findings.md` (ticked boxes are not evidence; repeat after the fix round until it adds nothing
  and writes `Converged: round <n>`). Write one `findings.md` section for the subagent's fix
  round. Keep building the next milestone where it does not depend on this one.
- **Publish:** only on `VERIFY PASS milestone 2026-11-13-kit-internal-names <sha>` with `<sha>` equal to the local
  head: one push, one PR `milestone/<slug>-<n>` to its parent, auto-merge armed with a merge
  commit (`gh pr merge <n> --merge --auto`). Ask first when a Critical or High is deferred. A
  milestone that needs another opens its PR after that one merges.
- **Red CI:** CI is the last check, not the test loop. Read the exact failed job or test and its
  reason, reproduce it locally, fix it, then run only the failing tests plus the directly affected
  suite until green, the full local gate once, and one batched push. Never a pipeline retry or a
  speculative push.
- **Scope the owner adds:** it re-locks (`verify_gate.py approve 2026-11-13-kit-internal-names`) and gets one more
  close. Log it under `## Revisions`.
- **Blocked:** on `VERIFY BLOCKED`, stop and summarize `verify/report.md` for the engineer. Never
  edit protected paths (`facts.md`, `done.json`, `lock.json`, baselines, allowlists, `sdlc.json`
  `checks`) or accept baselines.
- **Bookkeeping:** tick plan tasks as they land. Log departures under `## Revisions`.
- **Agents:** every build, fix, test, capture, restack or records agent is
  `cct:sdlc-feature-builder` (Sonnet). Review and checks use their typed agents
  (`cct:review-code-reviewer`, `cct:test-behavior-verifier`, `cct:review-criteria-auditor`,
  `cct:ux-usability-reviewer`, `cct:review-finding-validator`). Never launch general-purpose for
  this work: it inherits the session's model. Any other subagent gets `model: sonnet` explicitly.
  The session's own model is only for the gate's visual judgement and for decisions. Dispatch
  builders yourself, never through a closer agent that spawns its own.
- **One milestone** (`/goal` from `templates/goal/milestone.txt`): close it per `milestone.md`.
  Sync first, one fix round, diagnose locally with failing tests and affected suites until green,
  then the full local gate once before the push: unit, E2E (changed and flaky specs ×3) and
  `python3 scripts/verify_gate.py milestone 2026-11-13-kit-internal-names`, output pasted. Then one push and PR. Records and
  repairs are commits there, never separate PRs.
- **Feature PRs** (`delivery: "feature-prs"`): each feature is its own `/goal` from
  `templates/goal/feature.txt`: `cct:sdlc-feature-builder`, or `codex-build.sh` when `builders` is
  `codex`, with `builderModel` and `builderEffort`. Run the touched tests and affected suites until
  green, then the full local gate before the push, `python3 scripts/verify_gate.py feature
  2026-11-13-kit-internal-names`, output pasted. Use this worktree's E2E slot. After opening the PR run
  `cct:ux-assessment-run` unless `ux` is off, and fix Critical and High before arming auto-merge.
  Tick plan tasks and log departures under `## Revisions`. Stages 5 and 6 in `stages.md` have the
  steps.

## Goal handover

Two blocks, filled when the gate returns approved and committed verbatim, so the handover is not
one chat message. The kickoff prompt tells the run what to do. The `/goal` line holds only the end
state: the status command prints `GOAL <ID> DONE` or `GOAL <ID> BLOCKED`, and the run stops after
`40` turns (`goal.runTurns`). Feature PRs: one `/goal` per feature from
`templates/goal/feature.txt`.

The guardrail test fails an approved plan whose section is empty. Write `none —
<why>` rather than leaving it blank: an empty section is a skip, a section that
names itself empty is a decision. The usual reason is a document-shaped change,
where the artifact is this PR's diff and there was never a build to hand over.

Kickoff prompt:

```
Run change 2026-11-13-kit-internal-names: follow `## How to run` in changes/2026-11-13-kit-internal-names/plan.md to the end, then
print `python3 <plugin>/scripts/sdlc_status.py goal 2026-11-13-kit-internal-names`.
```

The goal:

```
/goal `python3 <plugin>/scripts/sdlc_status.py goal 2026-11-13-kit-internal-names` printed `GOAL 2026-11-13-kit-internal-names DONE` or `GOAL 2026-11-13-kit-internal-names BLOCKED` as its last run in this conversation, or stop after 40 turns.
```

## Revisions

Only after approval. One line per change: `YYYY-MM-DD — what changed, and why`.

Verification follows the [local-first contract](https://github.com/cdudek/calvins-claude-tools/blob/main/plugins/cct/skills/sdlc-run/references/local-first.md).
