# Audit workflow

Detailed steps for the `docs-audit` skill. The slash command in `references/commands/diff.md` (diff mode) is the canonical entry point for per-change audits; this file expands the rationale and edge cases shared by diff and full modes.

## Why diff-first

A repo can have 50+ markdown files. Reading them all on every audit is wasteful and pollutes context. The diff-first approach restricts the audit surface to docs that *could* be affected by the current change set.

Two consequences:

1. **An audit on a clean branch is fast and reports "no changes".** That's the desired idle state — the auto-reminder hook will fire many times during normal development, and most fires should result in a quick no-op audit, not a slow one.
2. **An audit after a multi-week branch is slower but bounded.** The 50-file cap in step 5 of the command prevents runaway audits on huge merges.

## Diff baselines

In order of preference for the default `branch` scope:

1. `git merge-base HEAD origin/main`
2. `git merge-base HEAD origin/master` (Rails repos historically)
3. `git merge-base HEAD origin/develop` (Reviews team flow)
4. `HEAD~1` (last commit) — last resort

Use `git rev-parse --verify` to check existence before invoking `merge-base`.

## Matching changes to docs

The mapping from changed files to candidate docs is a heuristic. Three layers:

1. **Filename / directory grep** — does any doc mention `app/graphql/mutations/`?
2. **Exported-symbol grep** — for non-trivial code changes, grep docs for newly-added or removed identifiers (class names, GraphQL types, route names). Use `git diff -U0` to extract just the added/removed lines, then run a follow-up symbol-extraction.
3. **Topic match** — if a Dockerfile changed and the doc has a "Docker" or "Development environment" section, audit that section.

When in doubt, include the doc rather than skip it. False positives waste reading time; false negatives miss the bug the skill exists to catch.

## What the audit looks for, by signal type

| Doc claim type | How to verify | Severity if wrong |
|---|---|---|
| Claim type | How to verify | Severity if wrong |
|---|---|---|
| File / dir path | `git ls-files <path>` returns non-empty | Critical |
| Make target | `grep -E '^<target>:' Makefile` finds it (do **not** run `make`) | Critical |
| npm / pnpm script | present in `package.json` `scripts` | Critical |
| Bundler / gem | present in `Gemfile` / `Gemfile.lock` | Critical |
| Docker service named in doc | present in `docker-compose.yml` `services` block | Critical |
| Docker service *count* mismatch (doc says 4, file has 6) | count `services:` entries | Warning |
| Env var | present in `.env.example` (case-sensitive) | Warning |
| Port number | matches `docker-compose.yml` or `.krane/` | Warning |
| GraphQL type / mutation name | grep the schema files | Critical |
| Route path (Rails) | present in `config/routes.rb` (do not run `rake routes`) | Warning |
| Reference to another doc (`see docs/X.md`) | the target doc exists (`git ls-files`) | Critical |
| Code snippet that mirrors source | the source still matches structurally | Warning |
| External URL | do not fetch (out of scope); flag only if obviously stale (e.g. an internal URL pointing to a deprecated service) | Info |
| Version number / date | exact match required | Warning |
| Architecture claim ("X calls Y", "we use Z for W") | grep for the named entities (see "Missing entirely" definition below) | varies |

This table is the **single canonical severity reference** for the whole skill. `references/commands/diff.md` and `references/commands/full.md` both point here — do not duplicate the table in command files; extend it here instead.

The audit must never invoke `make`, `rake`, builders, runners, package managers, or anything that executes code. That violates the read-only contract.

### Architecture claims — "missing entirely" definition

Architecture claims of the form *"X calls Y via Z"* or *"we use Z for W"* involve named entities (services, classes, modules, libraries, file paths, endpoints). Apply this rule:

1. Identify the named entities in the claim.
2. For each entity, run `git grep -li '<entity>' --` over tracked source files (excluding `*.md` and the doc itself).
3. **If every entity matches zero files** → claim references something that doesn't exist anywhere → **Critical**.
4. **If every entity matches at least one file AND the relationship is verifiable by reading one of those files** → mark verified (no finding).
5. **Otherwise** (entity exists but relationship isn't verifiable from grep alone, e.g. doc says "X calls Y via HTTP" but you can't tell from grep whether it's HTTP or gRPC) → **Info: claim not auto-verifiable**.

Do **not** flag Warning on architecture claims you couldn't actually check — Warning implies you verified and found incomplete data; Info honestly reports "I couldn't verify this from grep alone." A human reviewer can take that and either confirm or escalate.

## Edge cases

### Worktree

To detect a worktree: `test -f .git` (worktree) vs `test -d .git` (full clone). OMR worktrees use per-repo prefixes (`ra-`, `rf-`, `em-`, etc., not just `ow-*`) and live as siblings of the main checkout — so prefix-based heuristics aren't reliable. If `.git` is a file, treat the directory as a worktree: use its HEAD; do not cross into the main checkout. The merge-base logic still works because `git merge-base` resolves against the linked repository.

### Submodules and vendored code

Skip `vendor/`, `node_modules/`, `.bundle/`, `.venv/`, `dist/`, `build/`. The audit is for first-party code only.

### Generated docs

Some repos generate API docs from source (e.g. GraphQL introspection). If a doc has a header like `<!-- generated -->` or `<!-- DO NOT EDIT -->`, skip it and add an Info finding: "docs/api.md is generated — regenerate via <command> if stale".

### CLAUDE.md @-imports

`CLAUDE.md` files often `@-import` other files (e.g. `@teams/reviews.md`, `@ENGINEERING-PRINCIPLES.md`). Treat imported files as part of the doc surface — audit them too if they're in the candidate set.

## Reporting

Always report **what's confirmed up-to-date**, not just what's broken. Without that, the user can't tell whether the skill audited everything or missed sections.

The "Confirmed up-to-date" section should list every doc that was read and not flagged.
