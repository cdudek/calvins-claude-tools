---
type: plan
status: proposed
created: 2026-11-14
author: Calvin Dudek
source: the owner's fail-early plan of 2026-11-14, copied here on 2026-11-18 with every private and employer name removed (public repo rule)
---

# sdlc-run: catch a failure where it starts, not after the work is done

This is the umbrella plan. Each milestone below becomes its own change under `changes/`.
M2 is the first: `changes/2026-11-18-gate-loops/`.

## Why

The evidence is from 2026-11-14: a Claude Code insights report (24 sessions, 24 Oct to 14 Nov)
and a CI repair session the same day.

- **Gates bite after the work is done.**
  - **A ticket in an employer's tracker:** an active `/goal` plus `pr-gate.sh` blocked three finished pushes. Claude repeated "type /goal clear", and the gate still blocked after that.
  - **Six runner PRs:** auto mode refused the admin merge and the ruleset bypass, so the merge went back to the owner as a script.
- **CI-only failures.** Three on 2026-11-14, all macOS vs Linux, or worktree vs fresh clone:
  - **A private web app:** a test wrote `GITHUB_ENV` to `/dev/stdout`, which is a socket for a Node child on Linux (ENXIO).
  - **A private repo:** the slop base tree landed in `<repo>/.worktrees`, which `.oxlintrc.json` ignores, so oxlint linted nothing.
  - **The same repo:** the scratch folder did not exist in a fresh clone.
  - **Cost:** each one passed locally and cost blind CI runs until a person's Actions spending limit ran out.
- **Failures that surface last.**
  - **One PR:** failed its final check three times, on risk level, then a stale build, then complexity. The milestone gate checked none of the three.
- **Prose rules that broke anyway.** All four are already in the owner's global agent file, and the report shows each one broken:
  - status in three lines, no "still waiting";
  - never repeat an unblock command;
  - preflight in owner scripts;
  - a question is not an order.
- **Fixtures hid real bugs.** In the tracker plugin, test data hid bugs, and a stale marketplace cache installed 0.1.1 after the fix shipped.
- **The wrong target.** Claude analysed the employer org instead of a private org, and filed a proposal under the wrong team.

## Principles

1. **cct leads, the downstream kit follows** (owner decision 2026-11-12). Each item lands in cct through cct's own sdlc-run change. It is then ported downstream, and the parity check stays clean.
2. **A rule that must hold every time is a hook or a check**, never another agent-file line. Prose is only for judgement calls.
3. **Every check runs at the earliest stage that can run it.**
4. **A block that repeats is a diagnosis task, not a retry.**

## Milestones

### M0. Take stock of the 2026-11-11 retro plan

- [ ] Mark every item of the 2026-11-11 retro plan as shipped (with version), superseded, or open. Carry the open items into M1–M6 or drop them with a reason.

### M1. Pre-flight at session start

`session-check.sh` already reports a missing plannotator and stale repo copies. It gains a single state line:

- [ ] **Repo identity:** the org, and who pays for Actions (a person or a company), with the budget used.
- [ ] **Gate state:** whether HEAD has a passing gate receipt, whether a goal is active and its condition, and whether the heavy lock is held and by which pid.
- [ ] **Auth:** `gh auth status`, and `gcloud` only where `sdlc.json` names a GCP project. Print one fix command per failure.
- [ ] **Budget:** the hook stays under the existing `test_hook_spawns` limit, and it never fails a session.

### M2. Break gate loops

- [ ] `pr-gate.sh`, `chain-gate.sh` and `gate-bash.sh` record each block message in a per-session state file.
- [ ] On the second identical block, the message changes to a stop. It names the hook script and the state it read, gives the one owner command, and says not to retry.
- [ ] A test replays two identical blocks and asserts the second message.
- [ ] **Not enforced:** reply length and "still waiting". Judging a reply is not a hook's job, so those stay prose.

### M3. Linux parity before the first push

- [ ] **`ci-local --linux`:** runs `--ci` in a Linux container (podman or docker, the Node version from `.nvmrc`), with a repo setup command.
- [ ] **Sync tool:** swaps the runner body, keeps the repo config block and re-pins the lock, with a test.
- [ ] **sdlc-run:** the milestone close in repos whose Actions minutes are billed to a person runs `--linux` once on the final head, before the first push of a PR.
- [ ] **Next.js repos:** add `.next` and `node_modules/.cache` to the clean paths.
- [ ] **Roll-out:** one PR per pinned repo, in person-billed repos only after the budget resets.

### M4. Check stages

- [ ] Feature scope runs related tests only, the milestone runs the repo's single list, the Stop hook covers changed files only, and there are profiles for Next.js and Python.
- [ ] **Single list:** it includes complexity and risk level, so nothing the PR checks is new at the PR.

### M5. Verify against real artifacts

- [ ] **Verifier:** for tools and plugins, a run against the owner's real data, not fixtures, and a check that the installed version matches the release.
- [ ] **Tracker plugin:** the release script refreshes the marketplace cache and fails if the installed version differs from the release.

### M6. Text changes (no release)

- [ ] **Owner's global agent file:** private orgs are never the employer org; loops over lists run in `bash -c`, not zsh.
- [ ] **cct CLAUDE.md:** after a tracker release, check the installed version.

## Owner decisions (2026-11-14)

1. **Product proposals** go to the team the owner's global file names.
2. **Private rulesets** get an admin bypass in `pull_request` mode.
3. **Budget alert at 80 %** is in place; M1 still shows the spend.
4. **`--linux` scope:** only repos whose Actions minutes are billed to a person.
5. **Still open:** strict status checks on deploy repos, and Argo sync latency.

## Order

1. M0 and M6 (text only).
2. M1 and M2 share the state file. M2 first (2026-11-18, the owner's pick), then M1.
3. M3, then M4 (the single list needs the new runner), then M5.

## Not in scope

- **Lint and typecheck after every edit:** too slow on large repos; the turn-scoped Stop hook covers it.
- **Headless orchestration runs:** no evidence they would pay off.
