---
description: Review a Dependabot dependency-update PR — research changes, cross-check usage, fix failures, report
---

The user input is: $ARGUMENTS

Parse the input as: `<pr_number>`

You are reviewing a Dependabot dependency-update PR. Follow these steps exactly:

## Step 1: Resolve PR Branch

Run in parallel:
- `git fetch origin`
- `gh pr view <pr_number> --json headRefName -q .headRefName`

The second command gives you the PR's branch name.

## Step 2: Enter Worktree

`EnterWorktree`'s `name` parameter rejects `@`, and Dependabot branches (`dependabot/<ecosystem>/<pkg>-<version>`) always contain `/` — which the hook mis-derives (it truncates the branch name to the last path segment and nests directories instead of creating a flat sibling). Neither `name=` form works here. Instead:

1. Fetch the branch at the exact PR commit: `git fetch origin <branch_name>:<branch_name>`
2. Create the worktree manually: `git worktree add <workspace-dir>/dependabot-<pkgname>-<pr_number> <branch_name>`
3. `EnterWorktree path="<that-path>"` — accept the one-time confirmation prompt; it's expected and the only correct option for this branch shape.

Fetching first is **critical**: it pulls the branch straight from `origin` at the exact PR commit, so `git worktree add` checks it out directly — no base-branch guessing, no risk of building from the wrong commit.

Example:
```sh
git fetch origin dependabot/bundler/fastly-16.0.0:dependabot/bundler/fastly-16.0.0
git worktree add ../dependabot-fastly-5043 dependabot/bundler/fastly-16.0.0
```
`EnterWorktree(path="/abs/path/to/dependabot-fastly-5043")`

After entering, verify you're on the correct commit:
```
git log --oneline -1
```
The commit message should match the Dependabot PR's latest commit.

Note the worktree path — pass it explicitly to any subagents.

## Step 3: Update Branch if Behind Base

Run: `gh pr view <pr_number> --json mergeStateStatus,baseRefName -q '{status: .mergeStateStatus, base: .baseRefName}'`

If `mergeStateStatus` is `BEHIND` or `DIRTY`:
1. Merge: `git merge origin/<baseRefName> --no-edit`
2. If clean, push: `git push origin <branch_name>`
3. If conflicts, report to user and stop — suggest `@dependabot rebase`

**Note**: Once non-Dependabot commits have been pushed to the branch (e.g. fix commits from later steps), `@dependabot rebase` will no longer work. In that case, always merge the base branch manually and push.

If `CLEAN` or `UNSTABLE`, proceed. Tell user whether the branch was updated.

## Step 4: Gather PR Information

Extract owner/repo from `git remote get-url origin`.

### 4a: Fix PR title
Dependabot often generates titles exceeding 72 characters. Check the title length and if it exceeds 72 chars, fix it with `gh pr edit <pr_number> --title "<shorter title>"` — keep the conventional commit prefix.

### 4b: Fetch PR data
Follow `references/pr-context-loading.md` to fetch metadata, diff, and CI status in parallel.

### 4c: Detect ecosystem
Inspect changed files in the diff for lockfile patterns (see SKILL.md ecosystem detection). Load the matching `references/ecosystem-*.md` for ecosystem-specific parameters.

### 4d: Parse dependency changes
From the PR title, body, and diff, extract every dependency being updated:
```
- name: <package>
  old_version: <x.y.z>
  new_version: <a.b.c>
  version_jump: patch | minor | major
```

If the diff includes a lockfile, parse it to catch transitive dependency updates. Separate direct vs transitive.

### 4e: Present dependency summary
Show a concise table of all changes (direct first, then transitive) with version_jump highlighted. Major bumps get a warning marker.

## Step 5: Research Library Changes

**Adaptive strategy**: For 1-2 direct deps, research inline. For 3+, launch parallel subagents (model: sonnet).

For each **direct** dep update (and transitive deps with **major** bumps), research changes between old and new versions:

1. **Search the web** for changelog, release notes, GitHub releases between old→new. Use ecosystem-specific `registry_url` and `changelog_search` patterns from the loaded ecosystem reference.

2. **Research configuration options**: For libraries that offer configurable behavior (especially those with breaking default changes), look for:
   - Configuration DSL or initializer options
   - Feature flags or opt-in/opt-out settings
   - Compatibility modes (e.g. `config.legacy_mode = true`)
   - Environment variables that control behavior

3. **Return structured summary**:
```
[DEP] name: old → new (version_jump)
Breaking changes: [list, or "none identified"]
Deprecations: [list, or "none"]
Notable new features: [list, or "none relevant"]
Security fixes: [list with CVE if available, or "none"]
Migration steps required: [list, or "none"]
Configuration options: [available settings that can adjust behavior, or "none relevant"]
Confidence: <0-100>
Sources: [URLs consulted]
```

For **patch** updates of transitive deps, skip research — note as low-risk.

### 5b: Present research summary and get user input
Highlight breaking changes, security fixes, and low-confidence research.

**If breaking changes or deprecations were found**, present options for each affected item before proceeding:

```
Breaking change: <description>
Options:
  (a) Fix with code changes — update code to use the new API
  (b) Configure — use <specific config option> to retain old behavior
  (c) Disable — suppress/ignore this change (e.g. disable a new lint rule, pin a sub-dependency)
  (d) Exclude files — exclude specific affected files from the linter config (if only a few files are impacted)
  (e) Skip — leave for manual review later
```

For each option, provide concrete details:
- **(a)**: What code would change and where (files, methods)
- **(b)**: The exact configuration line(s) and where, with tradeoff explanation
- **(c)**: How to disable and what the consequences are
- **(d)**: Which files would be excluded and in which linter config (e.g. `.rubocop_todo.yml`, `.eslintignore`)
- **(e)**: What risk remains if skipped

**Wait for the user to choose** before proceeding to Step 6. Record their decisions — they drive what gets fixed in Steps 7c/7d.

## Step 6: Cross-Check Project Usage

**Adaptive strategy**: For 1-2 deps, cross-check inline. For 3+, use a subagent (model: sonnet).

For each direct dep with breaking changes, deprecations, or major bump:

1. **Find all usage** using ecosystem-specific `import_patterns` and `config_paths` from the loaded ecosystem reference
2. **Cross-check each breaking change** against actual usage — does the project use the deprecated/removed API?
3. **Return structured findings**:
```
[USAGE] package_name
Files using this package: [list]
Affected by breaking changes: yes/no
Details: [specific code locations, or "no impact"]
Risk level: low / medium / high
```

For deps with only patch/minor and no breaking changes, do a quick grep to confirm usage exists but skip deep analysis.

### 6b: Present cross-check results
Show grouped by risk level (high first).

## Step 7: Check CI Status and Fix Failures

### 7a: Check current CI status
Run `gh pr checks <pr_number>`.

### 7b: Fix failing checks
For each failing check:

1. Get failure details: `gh run view <run_id> --log-failed` (extract run_id from the checks URL)
   - **Filter the output**: CI logs are verbose. Use grep to extract actual failures, error messages, and assertion mismatches.
   - **Extract the seed**: Look for randomization seed — critical for reproduction.

2. **Verify flakiness**: Re-run the failing test with a different (random) seed. If it passes with a different seed, it's most likely flaky and unrelated to the PR.

3. Categorize as:
   - **Dependency-related**: Caused by the version update (breaking API, changed behavior) — fails consistently across seeds
   - **Pre-existing/Flaky**: Unrelated to dependency changes — passes with a different seed, or failure references code/packages outside the PR scope

4. For **dependency-related failures**:
   - Read the failing test and the code it tests in the worktree
   - Determine the fix based on changelog research from Step 5
   - Apply the fix in the worktree
   - Run the specific failing test locally using ecosystem-specific test command to verify
   - If the fix requires code changes beyond the test, make those too

5. For **pre-existing/flaky failures**:
   - Note them in the report but do not attempt fixes
   - Re-run failed checks: `gh run rerun <run_id> --failed`
   - Ask the user if they want a Linear issue created to track the flaky test. If yes, create one with: failing test file and line, error message, seed for reproduction, link to CI run

### 7c: Fix cross-check issues
If Step 6 identified code affected by breaking changes but not caught by tests:
- Apply necessary code updates based on user's decisions from Step 5b
- Run related tests to verify
- Run linting on changed files using ecosystem-specific lint command

### 7d: Fix lint failures
Run the ecosystem-specific lint command to check for issues introduced by the dependency update.

If lint fails:
1. Check if failures are in files changed by this PR or caused by updated linter packages (new rules, changed defaults)
2. Run ecosystem-specific lint fix command to auto-fix what the linter can handle
3. Review auto-fixes — ensure they are safe (no behavioral changes)
4. For failures that can't be auto-fixed, apply manual fixes
5. If new rules were enabled by an updated linter package and fixes are too broad (touching many files unrelated to the PR), disable the new rule in the linter config instead and note it in the report

**WARNING — Behavioral rules**: Some linter rules look like style fixes but change runtime behavior. After applying lint fixes, **always run the full test suite** (Step 7e) to catch breakage.

### 7e: Run full test suite
After all fixes (code, lint, cross-check), run the **full** test suite using ecosystem-specific test command, not just targeted tests. Lint fixes from behavioral rules can break tests in unexpected places far from the changed files.

Report pass/fail status.

## Step 8: Report

### Dependency Update Summary
Table of all deps updated with version jumps.

### Research Findings (ordered by risk)
Breaking changes and impact, security fixes, configuration options, confidence level.

### Cross-Check Results
Deps with confirmed impact (file:line references) and deps confirmed safe.

### CI Status & Fixes Applied
Fixes made (if any), current test status, remaining failures.

### Risk Assessment
Per `references/dependency-risk-rubric.md`: **low** / **medium** / **high**

### Findings (if issues remain)
Format per `references/finding-format.md`. Categories: `breaking`, `deprecation`, `security`, `testing`, `compatibility`.

If the update is clean, say so clearly.

## Step 9: Next Steps

Present options:
1. **Fixes applied**: offer to review diff, commit+push, or adjust
2. **No fixes needed**: offer to approve, post review comment, or request changes
3. **Unresolved issues**: explain what needs manual attention

## Step 10: Post (on user request only)

When the user asks to post, follow `references/review-posting.md`. Never post automatically.
