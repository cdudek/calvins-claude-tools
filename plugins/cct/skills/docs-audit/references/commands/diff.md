---
description: Audit repository documentation against the current source code and tooling.
---

The user input is: $ARGUMENTS

Parse `$ARGUMENTS` as an optional scope:

- empty → `branch` (default): diff against `git merge-base HEAD origin/main` (fall back to `origin/master`, then `origin/develop`)
- `staged` → `git diff --cached`
- `unstaged` → `git diff`
- `branch` → as default above
- `since=<ref>` → `git diff <ref>...HEAD`
- a path → restrict the audit to docs/files under that path

## Step 1: Determine the change set

Run the appropriate `git diff --name-status` for the chosen scope. Collect the changed paths into three buckets:

- **tooling** — files that drive build/deploy/CI/config or that other docs duplicate:
  - Build: `Dockerfile`, `docker-compose*.yml`, `Makefile`, `.krane/**`
  - Dependencies / lockfiles: `package.json`, `package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `Gemfile`, `Gemfile.lock`, `pyproject.toml`, `uv.lock`, `requirements*.txt`, `Cargo.toml`, `Cargo.lock`
  - Framework config: `nuxt.config.ts`, `vite.config.*`, `next.config.*`, `app.config.ts`
  - Env: `.env.example`
  - CI / repo-hygiene docs that other docs reference: `.github/workflows/**`, `.github/PULL_REQUEST_TEMPLATE.md`, `.github/ISSUE_TEMPLATE/**`, `.github/CODEOWNERS`
- **docs** — `CLAUDE.md`, `AGENTS.md`, `README.md`, `docs/**`, and any other `*.md` not already classified as tooling
- **source** — everything else

If all three buckets are empty for the scope: print **"No crucial changes detected — docs assumed current."** and stop.

> **Bucket overlap precedence** — apply in order: *tooling* first, then *docs*, then *source*. A file in the tooling list is tooling even if its extension is `.md` (e.g. `.github/PULL_REQUEST_TEMPLATE.md` is tooling — it drives downstream doc duplication). A `.md` file not in the tooling list is docs. Anything under `docs/` is always *docs*. Everything else is *source*.

## Step 2: Identify which docs are at risk

For each repo-specific file pattern in `../references/file-mappings.md`, find the docs that mention the changed files or their topics. Use the patterns for the *current* repo only — read its section from `file-mappings.md` lazily. If the repo isn't listed, fall back to the generic rules at the top of that reference.

Concretely:

1. List all docs files in the repo (`git ls-files '*.md' 'CLAUDE.md' 'AGENTS.md' 'README.md'`).
2. If `CLAUDE.md` is a symlink (check via `[ -L CLAUDE.md ]` or `git ls-files -s`), resolve to its target (commonly `AGENTS.md`) and audit the target once — do not double-process both names.
3. For each changed source/tooling file, grep the docs for: the filename, its directory, exported symbol names (functions, classes, GraphQL types, route paths), or commands defined in it.
4. The docs that match are the candidates to audit. Track which docs matched which changes.

## Step 3: Audit each candidate doc

For each candidate doc, read it and compare its claims against the current code. The verification methods and severity assignments live in **`../references/workflow.md`** — that's the canonical table. Apply those rules; do not invent local variants.

In short: every concrete claim a doc makes (commands, paths, schema names, services, ports, env vars, references to other docs, version numbers, architecture claims) is matched against the corresponding source-of-truth file using the verification command in the table. Severity follows the table — never flag a claim a Warning when you couldn't actually check it (use Info for unverifiable claims).

## Step 4: Report

Emit the report format defined in `../SKILL.md` under "Output format". Cite `file:line` for both the doc and the source on every finding.

## Step 5: Offer to fix

After the report, ask the user:

> "Want me to fix any of these? Reply with the finding numbers (e.g. `1,3`), `all critical`, `all`, or `no`."

Only edit docs after explicit user direction. When editing, follow the OMR engineering principles (`ENGINEERING-PRINCIPLES.md` in the workspace): surgical changes, no drive-by improvements.

## Constraints

- **Do not modify source code.** This skill audits docs only.
- **Do not run lints, tests, or builds.** The audit is read-only against git and the filesystem.
- **Stay within the repo.** Do not cross worktree or repo boundaries.
- **Bound the work.** If the change set has more than 50 changed files, audit the top 20 by churn (`git diff --stat`) and flag the rest as "not audited — re-run with a narrower scope".
