---
name: docs-audit
description: "Audits repository documentation against current source code and tooling in two modes: diff (changed files only, for PR prep) and full (every doc, for periodic health checks). Use when the user says 'audit the docs', 'full doc audit', 'are the docs up to date', 'stale docs', 'verify the README'. Skip for: writing release notes (use cct:docs-changelog-write), drawing architecture (use cct:docs-c4-create)."
allowed-tools: "Bash(git diff*), Bash(git log*), Bash(git ls-files*), Bash(git merge-base*), Bash(git rev-parse*), Bash(git show*), Bash(rg*), Bash(grep*), Bash(find*), Read, Grep, Glob, Agent"
user_invocable: true
metadata:
  version: 0.2.0
context: fork
model: sonnet
effort: high
background: false
---

# Audit Docs Skill

Compares the current state of the repository against its documentation and reports staleness — sections that contradict the code, missing coverage of new features/tools, dead references to removed files, or outdated commands.


## Routing

The user input is: $ARGUMENTS

Read the first word as the subcommand and route to its file, passing the rest on as arguments.

| Subcommand | Does |
|---|---|
| `diff` | The user input is: $ARGUMENTS → `references/commands/diff.md` |
| `full` | The user input is: $ARGUMENTS → `references/commands/full.md` |

No subcommand, or one that is not in the table: say
`Usage: /cct:docs-audit <diff | full>`
and ask which one they meant. Never guess — the subcommands do different things.

## Two modes

| Mode | Command | What it audits | When to use |
|---|---|---|---|
| **Diff** (fast) | `/cct:docs-audit diff` (see `references/commands/diff.md`) | Only docs affected by the current change set (default: branch vs `merge-base origin/main`). Bounded — if the change set exceeds 50 files, audit the top 20 by churn and flag the rest. | Pre-PR (runs automatically as a step of `cct:git-pr-run`). Day-to-day, on demand. |
| **Full** (slow, exhaustive) | `/cct:docs-audit full` (see `references/commands/full.md`) | Every documentation file in the repo (or under an optional path), verified against current code/tooling. Requires a path filter when the repo has more than 50 candidate docs (cost guardrail). | Quarterly. After a big refactor. Onboarding prep. When CLAUDE.md feels off but you can't point to a recent change. |

Both modes share the same severity rules (see `references/workflow.md` — the canonical reference), output format, and offer-to-fix flow. They differ only in *what* they audit.

## How it's invoked

1. **Automatically as a pre-PR gate** — the `cct:git-pr-run` skill invokes the diff-mode workflow as Step 4.5 of its flow (between lint and commit). If any staged file matches the crucial-file patterns in `references/file-mappings.md` for the current repo, the audit runs against the staged scope. **Critical findings are auto-fixed** and re-staged into the same commit; **Warning / Info findings are listed and the user is asked** before the workflow proceeds. This is the primary trigger — most users will see audits happen as a normal step of opening a PR, without having to remember anything.
2. **Manually (diff mode)** — `/cct:docs-audit diff` with optional scope: `staged`, `unstaged`, `branch` (default), `since=<ref>`, or a path. Use when you want a check outside the git-pr-run flow.
3. **Manually (full mode)** — `/cct:docs-audit full` with an optional path to restrict the audit (e.g. `/cct:docs-audit full docs/`). On big repos a path filter is required (the command will ask for one if the candidate-doc count exceeds 50). Use for periodic health checks, post-refactor sweeps, or onboarding.

## What counts as documentation

In priority order:

1. **`CLAUDE.md`** at the repo root — the canonical source for Claude-readable architecture, conventions, and dependencies. In some repos `CLAUDE.md` is a symlink to **`AGENTS.md`**; treat them as the same file and read the symlink target once.
2. **`README.md`** — human-facing setup, run, deploy.
3. **`docs/**/*.md`** — long-form docs.
4. **Nested `CLAUDE.md`** files (e.g. `app/services/CLAUDE.md` in `reviews-api`) — path-scoped Claude-readable conventions; treat as canonical for their subtree.
5. **`.krane/**/*.yml` headers** and any `# Why` comments in `Dockerfile`/`Makefile`/`docker-compose.yml` — these are docs-in-config.
6. **Any `*.md` in the repo root** — `CONTRIBUTING.md`, `ARCHITECTURE.md`, etc.

## Workflow

Follow `references/workflow.md`. Key principles:

- **Diff first, read second.** Never re-read every doc from scratch. Determine the *change set* (default: against the merge-base with `main`/`master`/`develop`) and only audit docs that reference touched files or topics.
- **Treat the code as truth.** When code and docs disagree, the docs are stale — never "fix" the code to match the docs without explicit user consent.
- **Don't silently rewrite docs.** Report findings as a list (Critical / Warning / Info). The user decides which to fix. Only edit docs when the user says so.
- **Surgical findings.** Each finding cites a `file:line` in both the doc and the source.

## Commands

| Command | Description | Arguments |
|---------|-------------|-----------|
| `/cct:docs-audit diff` | Diff mode — audit docs against the current change set | `[scope]` — optional: `staged`, `unstaged`, `branch` (default), `since=<ref>`, or a path |
| `/cct:docs-audit full` | Full mode — audit every doc in the repo against current code and tooling | `[path]` — optional but recommended; required when the candidate-doc count exceeds 50 |

## Output format

A markdown report with three sections:

```
## Documentation audit — <repo> @ <branch>

### Critical (3)
- **CLAUDE.md:42** says we use `pnpm install` but `package.json` declares `npm` as the package manager (package.json:8). Confirmed by `engines.npm` constraint.
- ...

### Warning (2)
- **README.md:15** lists 4 services in `docker-compose.yml`, but the file now defines 6 (added `redis`, `mailcatcher`). Incomplete enumeration — flag as Warning per the severity rules in `references/workflow.md` (a *missing* service would be Critical; a *miscounted* service is Warning).
- ...

### Info (5)
- **CLAUDE.md** does not yet mention the new `app/graphql/mutations/agency_widgets/` directory added in this branch.
- ...

### Confirmed up-to-date
- docs/deployment.md
- .krane/staging.yml header
```

If nothing changed in the audited scope: report **"No crucial changes detected — docs assumed current."** and exit. (Same wording used in both `references/commands/diff.md` and `references/commands/full.md`.)

## Repo-specific knowledge

`references/file-mappings.md` lists the generic triggers, plus any per-repo sections the repo owner added, for which file patterns map to which docs. Read it lazily — only the section for the current repo.
