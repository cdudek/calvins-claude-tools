# adopt — install the chain into a repo

Verification and every push follow the [local-first contract](local-first.md); read it before running checks or preparing a push.

**Re-run it whenever the kit moves.** `adopt` copies hooks, workflows, the tiers classifier
and the guardrail test into the repo, so local checks and remaining GitHub jobs run
without requiring the plugin to be installed. The copies are what actually enforce the rules, and they do not update
themselves. `adopt` stamps `kitTemplates` in `sdlc.json` with a fingerprint of the templates
it copied; `status.sh` compares it against the installed kit and prints `templates=stale`.
Chain step 0 reads that line, so a stale repo is refreshed before any change starts.

**The repo's formatter wins.** After writing, `adopt` runs the repo's own
`node_modules/.bin/prettier --write` over the `.ts` · `.js` · `.json` · `.yml` · `.md` files
it just wrote. The templates cannot match every repo's printWidth and quote style, and a repo
with a `prettier --check` gate rejects an unformatted file the moment you commit it. No
prettier installed, nothing happens.

    python3 ${CLAUDE_SKILL_DIR}/scripts/adopt.py [--dry-run] [--preset node|python] [--ticket KEY-123] --tiers yes|no

**Ask first, every time.** Before each run, on the first adopt and on every upgrade, ask the
engineer in one `AskUserQuestion`: "Use Ship/Show/Ask merge tiers in this repo?" Say what
`sdlc.json` `tiers` is now, if it is set. Options, the kit default first and marked
(Recommended): "Yes" (a code owner approves risky PRs before merge, the co-owner sees the rest
after) and "No" (every PR auto-merges on green; right for a repo with one owner). Pass the
answer as `--tiers yes|no`; adopt writes it to `sdlc.json` and adds or removes the tier files.
The kit default is `TIERS_DEFAULT` in `scripts/adopt.py`; it is also what a missing key means.

After the first gate has run, `python3 scripts/verify_gate.py audit` checks that every declared
gate is installed, configured, executed and a required status (`references/stages.md`,
"Enforcement audit"); `adopt` prints it as a MANUAL line.

Run from the repo root, on a branch. Idempotent: rerun after editing `sdlc.json` or
`tiers.json`, or after a kit update. Read the three sections; relay **MANUAL** to the user.

| Generated every run (edit the source, not the file) | Created once, then kept |
|---|---|
| `.claude/hooks/*.sh` (6) | `sdlc.json` (from the preset) |
| the SDLC entries in `.claude/settings.json` | `.github/tiers.json` (preset defaults; only while `tiers` is not `false`) |
| | `REVIEW.md` |
| `.github/workflows/ship-show-ask.yml` (only while `tiers` is not `false`); `claude-review.yml`, `claude.yml` and `ci-triage.yml` are removed when present (no Claude in CI since 3.7.0) | `CLAUDE.md` section (appended once) |
| `scripts/ship_show_ask.py` (only while `tiers` is not `false`) | the "Repo-specific" tail of `docs/sdlc.md` |
| `docs/sdlc.md` above the marker | the first change folder |
| the guardrail test | `.github/ISSUE_TEMPLATE/{feature,bug,spike,simple-task}.md` + `config.yml` |
|  | `.github/PULL_REQUEST_TEMPLATE.md` |
|  | anything in `sdlc.json` `keep` |

**One owner? Answer "No" (`tiers: false`).** Ship/Show/Ask needs a second person to
ask and to show. With one owner, `adopt` writes none of the three tier files and removes any
that exist (`git rm`). `docs/sdlc.md` then says "auto-merge on green" instead of the tiers,
and MANUAL drops the App secrets, `SDLC_COOWNER` and the Slack token setup notes. You arm auto-merge on each PR yourself: `gh pr merge <n> --merge --auto` for a milestone or
project PR, `--squash` for anything else.

**CODEOWNERS is a team-repo choice, never installer-managed.** Adopt never creates, edits or
deletes it, including older generated files, regardless of `codeowners`, `tiers`, `keep`,
upgrade or dry-run settings. Team repos maintain their own routing and required owner
review rule; solo-owner repos need no self-approval listing.

The four issue templates mirror the Linear templates in `cct:linear-manage`, so an issue reads
the same whichever tracker it started in. They are kept once written — a team that adds a field to
its own bug form does not lose it on the next run. The PR template carries the requirement-to-proof
table, which is what makes `F1` traceable from `facts.md` through the test to the merge.

## Migrations it performs

- `goals/<date>-<slug>/` (the earlier layout) → `changes/archive/<date>-<KEY>-<slug>/`
  with `goal.md` folded into `plan.md › ## Done`, `goal:` → `change:`, `archived_at` added.
  Then you: check the Done section reads well.
- `.claude/plans/*` → `docs/history/plans/` (git mv). Handovers from now on live in the
  change folder.
- `docs/ux/decisions.md`, the log `cct:ux-decision-log` used to append to → one ADR per decision
  under `designsDir` (nested by `<year>/<year-month>/` when the folder already is), with
  `supersedes` and `superseded_by` read from its "Replaced on … by …" notes. The log becomes
  a pointer. Then `INDEX.md` is written. Then you: link every reference under MANUAL
  (`link by hand: …`) and split any round that still holds several decisions in one file.

## After the script

1. Read `sdlc.json` with the user: `linear.team` / `project`, `verify`, `verifyStop`,
   `planGate`, `testGlobs`, `prototypeDirs`, `feedback`, `blocked`, `codeowners`, `tiers`,
   `claude`, `keep`, `rules` (optional, kept as written), and `ciPaths` (adopt writes the stack's default once and adds keys a newer kit introduced; edit the folder
   names to the repo's own, `ci-blueprint.md`). Read `.github/tiers.json` (skip it with
   `tiers: false`): the `ask` globs must name what really hurts here (migrations, integrations that write, cluster, workflows, deps, the rules).
2. Add the tools target (`toolsCommand`) — Makefile `sdlc-tools` or package.json
   `sdlc:tools`; the commands are in `docs/sdlc.md` "Install once per machine".
3. The first change (`changes/<today>-<KEY>-adopt-sdlc/`, no key when you adopt without a
   ticket): fill intent/facts/plan from this adoption; gate the plan;
   archive it when the PR is green.
4. Run `verify` and the guardrail test. Stage everything (`git ls-files` is part of the
   test). Commit `feat(sdlc): adopt the chain`.
5. GitHub, by the user: secrets `CODE_MANAGER_APP_CLIENT_ID`,
   `CODE_MANAGER_APP_PRIVATE_KEY`; variable `SDLC_COOWNER`; optional
   `SDLC_SLACK_BOT_TOKEN`; ruleset on the default branch per `references/tiers.md`; "Allow
   merge commits" on in the repo settings. With `tiers: false` only the ruleset's required
   checks and merge commits. No `ANTHROPIC_API_KEY`: nothing runs Claude in CI.
6. The adoption PR is `ask` (`.github/**`, `.claude/**`): a human merges it. With
   `tiers: false`, arm auto-merge on it like on any other PR.
7. The CLAUDE.md section it appended states the process and `/goal`; if the repo's
   CLAUDE.md said "ask before merging", change it to "the tier decides".
8. **Local CI gate.** `adopt` preserves existing CI and does not install the legacy full
   remote workflow for a repository without CI. Implement and audit `scripts/ci-local`
   and its pre-push hook using the [local-first contract](local-first.md).
   Require `local-ci` on default and protected interior branches; never post
   it by hand. Verify the script, hook and applied rulesets before retiring any existing
   required checks. Keep GitHub for cloud/GitHub work and scheduled jobs; `ci-blueprint.md`
   describes setup and the legacy template's migration role.
9. **Version.** adopt stamps `sdlcVersion` in `sdlc.json`. `adopt --upgrade` on a repo with an
   older stamp (or none) is the safe path: it adds the missing `sdlc.json` keys with the stack's
   defaults, never overwriting a value, stamps the version, and writes nothing else and moves no
   folder. Every file that differs from the kit's copy (hooks, workflows, `scripts/*.py`,
   `docs/sdlc.md`, the guardrail test) is listed as `review diff`, with the changelog's manual
   migrations since the stamp. `adopt --upgrade --replace <file>` shows one file's diff;
   `--apply --replace <file>` replaces it. A plain `adopt` refreshes all the copies at once.

## A repo that already ran the old `goals/` skill

Same steps. `adopt` migrates the folders; delete the repo-local `.claude/skills/sdlc/`
(the kit skill replaces it) and list hand-tuned workflows in `keep` so they survive.

## The tracker

When `sdlc.json` names no `tracker` (and has no `linear.team`), run
`python3 ${CLAUDE_SKILL_DIR}/scripts/tracker.py detect --linear-mcp yes|no`, ask the one dialog
from `references/trackers.md` with its recommendation first, write the answer into `sdlc.json`,
and walk that tool's setup guide before the first change.

## Decision4 installation

Decision4 is advisory: nothing checks it and it never blocks a merge. `adopt` installs three
things, each only when missing, and never a workflow or a `ci-local` step: a starter
`boundary-map.yaml` (the lowest undo level per path, for the repo to edit), the AGENTS.md
section "Decision4: how hard is this change to undo?" (with `@AGENTS.md` imported by CLAUDE.md
when that exists), and the PR-template section with its Decision record. Existing files and
sections stay the repo's. See [Decision4 in a PR](decision4-pr.md).
