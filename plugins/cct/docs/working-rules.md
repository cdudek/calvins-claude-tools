# Working rules

How Calvin works with coding agents. Each rule came from a real mistake; the reason is next to it.

## Asking and acting

- **Act, don't ask,** when the step is cheap and can be undone: research, data pulls, drafts, refactors inside the agreed scope. Ask first only for things that reach an audience, cannot be undone, or cost real money.
- **A question is a question.** "Why is this failing?" asks for an answer, not a fix. Answer, then act when told to go.
- **Full freedom about how, none about what.** Never swap the agreed stack (TypeScript to JavaScript, one UI library for another) without asking.
- **Done means done.** Five things asked means five delivered. If one is truly blocked, finish the rest and name the blocker in one sentence.
- **Something broken that you can fix, fix it.** Reporting it instead turns your work into the owner's to-do list.

## Requirements

- **Critical and High requirements of a goal are hard.** Never defer one on your own; ask.
- **UX findings go to the owner first.** Never auto-fix a UX finding; the owner decides which ones to take.

## Branches, worktrees and PRs

- A worktree lives at `<repo>/.worktrees/<name>`, always. `.worktrees/` is git-ignored globally and in `.git/info/exclude`. If one appears anywhere else, stop and fix the hook first.
- Branch from a freshly fetched base: `git fetch origin && git checkout -b <name> origin/main`. Local `main` is usually behind.
- Before handing over a PR, read `gh pr view <n> --json mergeStateStatus,autoMergeRequest`. `BEHIND` → `gh pr update-branch <n>` (a merge; never `--rebase` a milestone or project branch) and wait for CI; `BLOCKED` → name the missing check or review; `CLEAN` → hand it over. Green CI is not the same as mergeable.
- Arm auto-merge on anything that can merge itself: `gh pr merge <n> --merge --auto` for a milestone or project PR (a merge commit keeps its Conventional Commit history and spares a stacked milestone a rebase), `--squash --auto` for anything else. On a milestone PR arm it once the gate passed and no Critical or High finding is open; ask only when one would be deferred.
- Stack branches only for a real code dependency, and say "Stacked on #A, merge after it" in the body.
- **One milestone, one push, one PR.** Records, fixes, test repairs and CI tweaks are commits on `milestone/<slug>`. A record written after a merge is the next milestone's first commit; a fix for a merged milestone goes into the next one. No `records/*`, `fix/*` or `chore/merge-main-*` PR, ever. `pr-gate.sh` (sdlc-run 3.4) refuses them.
- **Every milestone starts by merging `origin/main`** (and `origin/project/<slug>` when the project has a branch) into its worktree locally. The milestone gate fails `check=parent-sync` without it.
- **The close runs locally first.** One `cct:builder` subagent runs unit tests, the full E2E suite, the one fix round and `verify_gate.py milestone`; the supervisor runs the reviews and builds the next independent milestone meanwhile. Only a `VERIFY PASS milestone` head is pushed, once, with one PR and auto-merge armed. CI is the last check: a red check gets one fix commit after reading its log, never a rerun.
- **A milestone branch is local until its gate passes,** then one push and one PR. Milestones are independent and cut from `main`; only a plan row with `needs: M<k>` stacks one on another. A project is planning, not a branch, unless you ask for one.
- **Parallel builders start from the milestone head:** commit the records, dispatch each builder with `Base: <sha>`, and merge them back one at a time. Nothing merges while the close runs.
- Wait on another PR only when the code depends on it. Across repos, build against a local copy (`npm pack`, an uncommitted `file:` link) until that repo's next milestone publishes.
- One change, one PR. Always give the full PR URL, never a bare number.
- Format, lint and typecheck before every commit. CI rejects anything that skips them.

## Releases

- Every finished milestone goes straight to `main` and becomes a release the owner can install the same day. No project branch holding finished work back.
- Versions come from Conventional Commit PR titles via semantic-release. Title PRs precisely: `fix:` for fixes, `feat:` only for real features.
- At every milestone close, say which release it became and whether it is installed.

## Tests

- The full E2E suite runs in CI and locally only at the end of a milestone, in the background. Never per commit. Agents run only the tests they touched (command per stack: `skills/e2e-test-run/references/suite-speed-and-reliability.md` section K).
- Which files run which CI step (lint, unit, build, e2e, deploy) is `ciPaths` in `sdlc.json`: `include` and `exclude` globs per step, `docs` runs nothing, a file in no include runs everything. Agents pick touched tests from the same lists.
- CI skips build, tests and previews for docs-only PRs behind one required `check` status, runs E2E against the built artifact, sharded, with one retry, and runs the full E2E suite only on PRs into the default branch or `project/*` and on milestone heads (`skills/sdlc-run/references/ci-blueprint.md`). Measured 2026-10-31: 22 of 39 runs red, 13 of 22 PRs docs-only.
- Never mark something done without proof: tests run, output read, behaviour seen in the real app.

## Plans, handovers, sharing

- Plans and handovers are committed to the project repo (`changes/` or `.claude/plans/` named `YYYY-MM-DDTHHMM-<type>-<topic>.md`), never only in `~/.claude/plans/`.
- Never put a local file path into anything another person reads (tickets, PRs, Slack, email). Push the content itself, for example as a Linear document.
- Close each subagent once its report is in.

## Writing

- Concise, direct, plain words, no emojis, no buzzwords. Front-load the point.
- Replies are read on a phone too: no hard-wrapped lines, no wide tables, anything to copy goes in a fenced block.
