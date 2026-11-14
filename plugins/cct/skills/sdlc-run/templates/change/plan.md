---
linear: {{LINEAR}}
type: plan
change: {{CHANGE}}
design: {{DESIGN}}
author: {{AUTHOR}}
status: draft
reviewed_by: null
approved_at: null
created: {{DATE}}
---

# Plan: {{TITLE}}

> One sentence. What this change does.

A person with no context builds from this file alone. [intent](intent.md) and
[facts](facts.md) are for the gate, not for the build.

## Approach

- **What changes:** <one sentence>
- **What stays the same:** <one sentence>
- **Why this way:** <one sentence>
- **Rejected:** <option> — <why not, one clause>

## Rules check

The rules in `intent.md` → "Rules that apply", checked twice: before the design (can the approach
obey them?) and after it (does the design?). `pass` or the rule ID that fails.

- Before design: <pass | rule IDs>
- After design: <pass | rule IDs>

### Justified violations

One row per rule the plan breaks. A row with an empty cell blocks the gate; `none` when clean.

| Violation | Why needed | Simpler alternative rejected because |
|---|---|---|
| none | | |

## Design changes

<Which sections of `design:` this change edits, or "none". Edit them in the same PR.>

## Where things go

The folder for every new file, so the build cannot invent a place. A file outside these folders
is `scope-growth`.

| New file or kind | Folder |
|---|---|
| <component, route, test> | `<path>/` |

## Feature PRs

In order, grouped under `### Milestone <n> — <what a user can do after it>`. One go (the
default): each row is a commit on `milestone/<slug>-<n>` with touched tests and required pre-commit checks between rows; each
milestone gets the checks and validation once, and one PR that releases it. For E2E, run
the full suite once, ×3 only for changed and flaky specs. Use the committed
`e2e/flaky-specs.txt` list per `cct:test-e2e-policy`, `suite-speed-and-reliability.md`
section G (selection and line format). `delivery: "feature-prs"`: each row is one PR into
`milestone/<slug>` (a hotfix: into the default branch), the next starts when it auto-merges.

| # | Feature | Facts | Branch | State |
|---|---|---|---|---|
| 1 | <what it delivers> | F1, F2 | `<slug>/1-<feature>` | todo |

## Files that change

| File | Change |
|------|--------|
| `path` | <one line> |

## Order of work

Each step has a proof. The proof is a command, a file, or a fact.

- [ ] 1. <step> — proof: `<command>` exits 0
- [ ] 2. <step> — proof: `<file>` exists
- [ ] 3. <step> — proof: F<n> passes

## Milestones

One row per milestone, in order; a change small enough for one has one. Each milestone is cut
from the default branch and merges on its own, unless `needs` names one whose code it calls.
Different files do not prove independence: an API and its caller conflict without a merge
conflict.

| Milestone | Features | needs |
|-----------|----------|-------|
| M1 <name> | F1, F2 | none |
| M2 <name> | F3 | M1 (<what of M1 it calls>) |

## Risks

| Risk | What we do | Where it lands |
|------|------------|----------------|
| <what could break> | <the action> | <step number, test name, or "accepted"> |

## Out of scope

- <what this change does not do, on purpose>

## Done

What must hold, as data in [done.json](done.json) (facts, test tags, pages, states). The goal
below ends on the status line of `sdlc_status.py goal` (from the sdlc-run plugin), which reads the verify gate and the PRs,
so every line here is proven by a check, not by a claim.

- `python3 scripts/verify_gate.py feature {{CHANGE}}` ends `VERIFY PASS` for every feature.
- `python3 scripts/verify_gate.py milestone {{CHANGE}}` ends `VERIFY PASS` once, on the milestone.
- <file> exists / contains `<string>`.
- F1 to F<n> pass by their named check.
- Nothing outside `## Files that change` is edited.
- Stop and report as soon as a step cannot proceed. Never work around a blocker.
- Stop after 40 turns if not met. Report what is missing.

## How to run

The process of the build. The `/goal` below holds only the end state; everything the run does
lives here, in the skill's stages and in the hooks. Read the [local-first
contract](https://github.com/cdudek/calvins-claude-tools/blob/main/plugins/cct/skills/sdlc-run/references/local-first.md)
before any check or push: it owns local iteration, failures and the final full check.

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
  blocking findings, then `python3 scripts/verify_gate.py milestone {{CHANGE}}`. Its full output
  is pasted.
- **Meanwhile:** dispatch the Stage 6 reviews on the milestone diff in parallel. Validate every
  fact and ask of the milestone against the built app into `validation.md` (expected, observed,
  evidence, verdict). Run the append-only converge pass from `quality-passes.md` into
  `findings.md` (ticked boxes are not evidence; repeat after the fix round until it adds nothing
  and writes `Converged: round <n>`). Write one `findings.md` section for the subagent's fix
  round. Keep building the next milestone where it does not depend on this one.
- **Publish:** only on `VERIFY PASS milestone {{CHANGE}} <sha>` with `<sha>` equal to the local
  head: one push, one PR `milestone/<slug>-<n>` to its parent, auto-merge armed with a merge
  commit (`gh pr merge <n> --merge --auto`). Ask first when a Critical or High is deferred. A
  milestone that needs another opens its PR after that one merges.
- **Red CI:** CI is the last check, not the test loop. Read the exact failed job or test and its
  reason, reproduce it locally, fix it, then run only the failing tests plus the directly affected
  suite until green, the full suite once, and one batched push. Never a pipeline retry or a
  speculative push.
- **Scope the owner adds:** it re-locks (`verify_gate.py approve {{CHANGE}}`) and gets one more
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
  then the full suite once before the push: unit, E2E (changed and flaky specs ×3) and
  `python3 scripts/verify_gate.py milestone {{CHANGE}}`, output pasted. Then one push and PR. Records and
  repairs are commits there, never separate PRs.
- **Feature PRs** (`delivery: "feature-prs"`): each feature is its own `/goal` from
  `templates/goal/feature.txt`: `cct:sdlc-feature-builder`, or `codex-build.sh` when `builders` is
  `codex`, with `builderModel` and `builderEffort`. Run the touched tests and affected suites until
  green, then the full suite before the push, `python3 scripts/verify_gate.py feature
  {{CHANGE}}`, output pasted. Use this worktree's E2E slot. After opening the PR run
  `cct:ux-assessment-run` unless `ux` is off, and fix Critical and High before arming auto-merge.
  Tick plan tasks and log departures under `## Revisions`. Stages 5 and 6 in `stages.md` have the
  steps.

## Goal handover

Two blocks, filled when the gate returns approved and committed verbatim, so the handover is not
one chat message. The kickoff prompt tells the run what to do. The `/goal` line holds only the end
state: the status command prints `GOAL <ID> DONE` or `GOAL <ID> BLOCKED`, and the run stops after
`<TURNS>` turns (`goal.runTurns`). Feature PRs: one `/goal` per feature from
`templates/goal/feature.txt`.

The guardrail test fails an approved plan whose section is empty. Write `none —
<why>` rather than leaving it blank: an empty section is a skip, a section that
names itself empty is a decision. The usual reason is a document-shaped change,
where the artifact is this PR's diff and there was never a build to hand over.

Kickoff prompt:

```
Run change {{CHANGE}}: follow `## How to run` in changes/{{CHANGE}}/plan.md to the end, then
print `python3 <STATUS> goal {{CHANGE}}`.
```

The goal:

```
/goal `python3 <STATUS> goal {{CHANGE}}` printed `GOAL {{CHANGE}} DONE` or `GOAL {{CHANGE}} BLOCKED` as its last run in this conversation, or stop after <TURNS> turns.
```

## Revisions

Only after approval. One line per change: `YYYY-MM-DD — what changed, and why`.

Verification follows the [local-first contract](https://github.com/cdudek/calvins-claude-tools/blob/main/plugins/cct/skills/sdlc-run/references/local-first.md).
