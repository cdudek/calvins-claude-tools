# Git hooks: cheap local checks, set up once per repo at intake

The fast checks run as git hooks, not as steps the agent has to remember. CI is the real gate; hooks only make failures show up seconds after a commit instead of minutes after a push.

## Budget
- **pre-commit:** seconds. Formatter and linter on the staged files only.
- **pre-push:** about a minute at most. Lint, typecheck, and only the unit tests related to files changed against the base branch.
- **Never local:** the full unit suite, build, migrations, e2e, visual tests. They run in CI.

## Setup
1. Use the repo's tool if it has one (lefthook, husky, pre-commit). Otherwise add lefthook as a dev dependency (`npm i -D lefthook`; Python: `pre-commit`).
2. Copy `templates/git-hook-env.sh` to `scripts/git-hook-env.sh` and run every hook command through it. Git exports `GIT_DIR` and friends into hooks; a test that builds a temp repo then writes commits, branches and `core.bare=true` into the real repo. This happened on 2026-11-24.
3. If `core.hooksPath` points somewhere stale, `git config --unset core.hooksPath`, then `npx lefthook install`. Worktrees share the install.
4. Add one "Git hooks" section to AGENTS.md: the install line, what each hook runs, and "never `--no-verify`".
5. Prove it: stage a badly formatted file and see the commit fail; time `npx lefthook run pre-push`.

## Example (Node, biome, vitest)
```yaml
pre-commit:
  parallel: true
  commands:
    format-lint:
      glob: "*.{js,jsx,ts,tsx,mjs,cjs,json,jsonc,css}"
      run: bash scripts/git-hook-env.sh npx biome check --no-errors-on-unmatched --files-ignore-unknown=true {staged_files}
pre-push:
  parallel: true
  commands:
    lint:
      run: bash scripts/git-hook-env.sh npm run -s lint
    typecheck:
      run: bash scripts/git-hook-env.sh npm run -s typecheck
    unit-changed:
      run: bash scripts/git-hook-env.sh npx vitest run --changed origin/main --passWithNoTests
```
A change to `package.json` makes `vitest --changed` run every test; that is expected and rare.
