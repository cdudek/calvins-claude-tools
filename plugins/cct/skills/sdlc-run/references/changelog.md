# sdlc-run changelog

One entry per version, newest first. `adopt --upgrade` reads it: the headlines go into the
version warning, the **Mechanical** lines are what `adopt` does for you (it adds missing keys
with the stack's defaults and never overwrites a value), the **Manual** lines are printed for
the engineer. A version with no migration lines needs nothing but a re-run of `adopt`.

## 3.7.0 — local milestones, builders that see them, no Claude in CI

- A milestone branch is local until its gate passes; Stage 1.2 no longer pushes it empty, which `pr-gate.sh` refused in one go. Its first push is the close push.
- Milestones are independent: each is cut from fresh `origin/<parent>` and merges on its own. Only a `## Milestones` row with `needs: M<k>` stacks one on another. The plan template gains that section.
- Milestone and project PRs merge with a merge commit (`ship-show-ask.yml`, the docs, the goal text), so a stacked milestone needs no rebase. Builders write Conventional Commit subjects, since the release now reads every commit.
- Parallel builders start from the milestone head: a `Base: <sha>` line, reset to before any edit, because a worktree hook cuts from the trunk. The supervisor commits its records first and merges builder branches one at a time.
- `cct:builder` gains `Mode: close`, so the agent Stage 5 gives the close to may run the full suite and the gate.
- `verify_gate.py` fails `check=moved` when HEAD or the tree changes during its checks. `pr-gate.sh` also finds a PASS under `changes/archive/`.
- A project is planning by default: `decisions.json` `project.branch` is `false` for a new one, its milestones go to the default branch, and Stage 6p checks the whole project there with no PR. A project without the key keeps its branch.
- No Claude in CI: `claude-review.yml` with `merge-gate`, `claude.yml` and `ci-triage.yml` are gone, and so is `ANTHROPIC_API_KEY`. The code review runs once, locally, at the milestone close.
- Mechanical: `adopt` removes the three Claude workflows (`git rm`) and the `claude` key from `sdlc.json`.
- Manual: drop `merge-gate` from the default branch's ruleset and classic branch protection, and delete the `ANTHROPIC_API_KEY` secret if nothing else uses it.
- Manual: turn on "Allow merge commits" in the repository settings; milestone PRs merge with one.

## 3.6.1 — reflow is checked at 320 CSS px wide, not in a 320 × 256 window

- The milestone verification checks WCAG 1.4.10 as written: 320 CSS px wide (1280 at 400 %) at an ordinary height, tested at 320 × 640. Its 256 px height is only for content that scrolls sideways (vertical writing); a fact or test that sets a 320 × 256 window, or asks for 400 % of every screen size, is stricter than WCAG and is corrected. Same rule in `accessibility-audit`, `responsive-audit` and the omr-ux conflicts table (W17). Source: https://www.w3.org/WAI/WCAG22/Understanding/reflow.html
- Manual: a repo whose facts or E2E specs test reflow at 320 × 256 changes them to 320 × 640.

## 3.6.0 — builders: the model is a setting

- `sdlc.json` `builderModel` and `builderEffort` say which model builds and how hard. The default is `sonnet` at `high`: the `cct:builder` agent's own frontmatter, so nothing changes until a repo sets `opus` (or any Claude Code model alias or id), or `builders: "codex"` with a Codex model (default `gpt-5.5`). Every builder dispatch carries the pair; `codex-build.sh` gets it as `--model` and `--reasoning`. A plan's Approach may name another pair for that one change. Before this, a Codex build had no model unless the plan named one, so the wrapper refused to start.
- Mechanical: `builderModel` and `builderEffort` are added when missing (`sonnet` or `gpt-5.5` by `builders`, `high`); set values are kept; an effort outside `low`, `medium`, `high`, `xhigh` or an empty model stops adopt.
- Manual: nothing for the default. A repo on `builders: "codex"` checks that the added `builderModel` (`gpt-5.5`) is the Codex model it wants; a plan that already names a model keeps it, as the per-change override.

## 3.5.0 — builders: codex, an option

- `sdlc.json` `builders`: `claude` (default, `cct:builder` agents) or `codex`. With `codex`, feature rows and fix parts run through the kit's `scripts/codex-build.sh`: the Codex CLI in the feature worktree, `--sandbox workspace-write` with the network off, the builder's rules as the prompt, a schema-checked result, a check before the commit (the tree changed; no protected path, lockfile, manifest or locked test among the changes), and the commit made by the wrapper, since the sandbox keeps `.git` read-only. The supervisor, the milestone close (checks and gate only in this mode) and the gates stay Claude.
- Mechanical: `builders` is added as `claude` when missing; a set value is kept; another value stops adopt.
- Manual: to use it, set `builders` to `codex`, install and sign in the Codex CLI (`npm i -g @openai/codex`, `codex login`), and name the model and reasoning in the plan's approach section.

## 3.4.1 — the milestone close: one builder runs the local pipeline

- The goal text and stages.md give unit tests, the full E2E suite, the fix round and the gate to one `cct:builder` subagent that spawns no agents; the supervisor dispatches the reviews and the validation (a subagent cannot start its own).
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

- Records (plans, handovers, gate lines, validation, findings) ship in their milestone's PR; agents run only the tests they touched; `references/ci-blueprint.md` and the per-stack command table (`e2e-test-run` section K) arrive. Re-run `adopt` to refresh the goal texts.

## 3.0.0 — the milestone process

- Milestones, projects, one `/goal`, `done.json`, `lock.json`, `verify_gate.py`, `docs/designs/`.
- Manual: a change in flight from v2 finishes on its own process (`references/chain.md`, History).
