# Monthly whole-harness audit

- **Reminder:** Once each month, an agent runs `scripts/harness-audit --issue` on the owner's Mac in each adopting repository.
- **Scheduling:** Keep this reminder in the consumer's engineering docs; no Actions schedule, cron or launchd job is needed.
- **Canonical code:** `${CLAUDE_SKILL_DIR}/scripts/harness-audit.py` and `${CLAUDE_SKILL_DIR}/scripts/legacy-guards-test.py` own the executable behavior; consumers receive pinned copies.

## What the command proves

- **Installed:** Explicit version probes succeed, and the older checker or hook source exists with any required executable bit.
- **Configured:** Every declared local check has a manifest row, actual configuration files are hashed, and older hooks have registration or caller evidence.
- **Executed:** The owned `scripts/ci-local --check` runs once, and each checker leaves a fresh log for the frozen head and comparison base.
- **Passed:** That invocation reports success; stale logs, skipped checks and empty suites cannot supply a pass.
- **Applied:** Ruleset checks must exercise real refusal and allowed fixtures against the production configuration; exit zero alone is insufficient.
- **Older guards:** Each inventoried hook/check gets its own five-state result. A registration or file on disk cannot substitute for fixture execution.
- **Unproved claims:** Missing evidence becomes an owner-assigned gap in the report and issue; it never becomes a successful state.
- **Operator checks:** Do not guess commands that access live systems. Inventory their invocation, and report the missing local evidence until an approved adapter exists.

## Adopt in a consumer worktree

- **Sync:** Run `python3 ${CLAUDE_SKILL_DIR}/scripts/sync-harness-audit.py <consumer-worktree> --pin <merged-source-sha>` and inspect its dry-run diff.
- **Apply:** Add `--write` to copy only the auditor, legacy fixtures and `.harness-audit.lock`; local owners and gate commands stay in the consumer.
- **Manifest:** Commit `.harness-audit.json` with `version: 1`, an explicit GitHub `owner`, `default_branch`, `checks`, `legacy`, and optional ignored cache paths in `reset`.
- **Check rows:** Each row names its actual `ci-local` check ID, owner, version-probe argument arrays in `tools`, configuration paths in `configs`, and claimed `rules`.
- **Kinds:** Use `ruleset` for policy enforcement, `suite` for tests, or `execution` for artifact/build checks; explain the non-policy claim in `reason`.
- **Ruleset proof:** `applied.command` runs the real fixture suite; `applied.required_output` names both refusal and permitted evidence that it must emit.
- **Legacy inventory:** Record every older hook/check path, owner, role in `kind`, reason, `invoked_by`, and source paths in `via` that actually register/call it.
- **Legacy execution:** Set `via_check` to the gate step that runs its fixtures and `required_output` to their real result markers; absent evidence remains a gap.
- **Git hook registration:** Use `git:core.hooksPath` in `via` for `.githooks/pre-push`; the auditor checks the installed Git setting.
- **Gate wiring:** Add `python3 scripts/legacy-guards-test.py` and `python3 scripts/harness-audit --verify-config` as cheap local steps; inventory both new check IDs.
- **Existing negatives:** Keep migration, architecture and scanner refusal suites in the full gate when adding these steps.

## Monthly execution and evidence

- **Preparation:** Fetch the default branch and release tags, install locked dependencies and required tools, then use a clean committed worktree.
- **Command:** Run `scripts/harness-audit --issue`; it performs the full local harness once and opens or updates the repository's single continuing audit issue.
- **Ownership:** Each gap carries its explicit row owner; all gap owners are assigned on the issue. A closed continuing issue is reopened when gaps are observed.
- **Cache reset:** Only declared ignored/untracked caches may be erased. Tracked files, credential paths and links are refused.
- **Evidence:** The common Git directory retains `harness-audit/<run>/report.json`, fresh logs, the checked head/tree/base, tool versions and configuration hashes.
- **Source sync:** `.harness-audit.lock` binds the copied executables to an immutable source commit and SHA-256 hashes; drift fails the cheap gate check.
- **Safety:** The auditor never pushes or publishes commit statuses; its configuration hashing refuses environment/credential paths. `--issue` is the explicit issue-publication action.
- **Failure loop:** Read the named failing checker and reproduce only that checker locally. Fix it, rerun the affected suite, then run the full gate once before pushing.
- **No retry pipeline:** The auditor never retries the whole harness automatically to investigate one failure.

## Legacy refusal fixtures

- **Forbidden edit:** A dirty source tree cannot publish using a previously green receipt; approved chain criteria cannot be edited silently.
- **Missing evidence:** An unverified head must run the actual owned runner, whose failing checker blocks publication; a missing chain lock blocks source edits.
- **Stale lock:** An old head's green receipt cannot authorize a new source commit; a lock over a draft plan does not permit a chain source edit.
- **Allowed:** A clean head verified by the real runner is accepted without a redundant suite; an approved active chain permits its source edit.
- **Isolation:** Fixtures copy the installed guards into disposable repositories, clear parent Git/gate context, and never run product deployments or production commands.
- **Targeted development:** `python3 scripts/legacy-guards-test.py --case prepush`, `--case chain`, and `--case config` select the directly affected fixture group.

## Source development

- **Focused tests:** `python3 -m pytest -q -p no:cacheprovider ${CLAUDE_SKILL_DIR}/scripts/test_harness_audit.py` exercises freshness, missing tools, ruleset evidence, issue upserts and source sync.
- **Required checks:** Run this skill's pinned Ruff format/lint checks and the repository's complete local unit/plugin suites before every push.
- **Consumer rollout:** Merge the canonical change first, sync from its merged SHA, then run each consumer's full local gate on its exact proposed head.
