---
name: dependency-review
description: Reviews Dependabot and dependency update PRs — researches changelogs, cross-checks usage, fixes failures, reports risk. Auto-detects ecosystem (Ruby, Node, Python). Use when user says "dependabot", "dependency update", "bump", "review dependabot PR", or asks to review a dependency version update.
allowed-tools: "Bash(gh *), Bash(git *), Bash(make *), Read, Grep, Glob, Agent, WebSearch, WebFetch"
user_invocable: true
metadata:
  version: 1.0.0
  author: calvindudek
context: fork
model: sonnet
effort: high
background: false
---

# Dependabot Review Skill

Reviews dependency update PRs with changelog research, project usage cross-checking, automated fix/lint, and risk assessment. Auto-detects the package ecosystem from changed files.


## Routing

The user input is: $ARGUMENTS

Read the first word as the subcommand and route to its file, passing the rest on as arguments.

| Subcommand | Does |
|---|---|
| `review` | The user input is: $ARGUMENTS → `references/commands/review.md` |

No subcommand, or one that is not in the table: say
`Usage: /cct:dependency-review <review>`
and ask which one they meant. Never guess — the subcommands do different things.

## Workflow Overview

1. **Resolve branch & enter worktree** — fetch PR branch, enter isolated worktree
2. **Gather PR info** — metadata, diff, CI status, parse dependency changes
3. **Detect ecosystem** — inspect changed files to identify lockfile type → load matching `references/ecosystem-*.md`
4. **Research** — search web for changelogs/release notes between old→new versions
5. **Cross-check** — follow `../role-code-analysis/references/generalize-sweep.md` (impact sweep, scope: system) to find all project usage of updated deps and map breaking changes to actual code
6. **Fix + lint** — apply migration fixes, run linter, run tests, report remaining failures
7. **Report** — structured findings with risk assessment

## Command

| Command | Description | Arguments |
|---------|-------------|-----------|
| `/dependabot review` | Full dependency update review | `<pr_number>` |

## Policies

### Posting
**NEVER post anything to GitHub automatically.** Present findings to the user first. Only post when the user explicitly requests it.

### Worktree
Do NOT exit the worktree — the user exits manually after interactive follow-up.

### Error Handling
If any `gh` command or API call fails, report the error to the user and stop. Do not guess, retry, or skip the failed step.

## Ecosystem Detection

Inspect changed files in the PR diff for lockfile patterns:
- `Gemfile.lock` → load `references/ecosystem-ruby.md`
- `package-lock.json` or `yarn.lock` or `pnpm-lock.yaml` → load `references/ecosystem-node.md`
- `requirements.txt` or `poetry.lock` or `Pipfile.lock` → load `references/ecosystem-python.md`

If no known lockfile is found, infer from the diff content and proceed with best-effort defaults.
