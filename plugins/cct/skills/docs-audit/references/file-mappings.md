# File → doc mappings

When the `docs-audit` skill is run, it consults this file to find the generic rules and any section the repo owner added for the current repo, and uses the listed patterns to scope the audit. **Read only the section for the current repo** — don't load the whole file. Always also read the *Generic rules* section, which applies to every repo.

This file is the **single source of truth** for which file patterns trigger which doc audits. Both `references/commands/diff.md` (when invoked manually or by `cct:git-pr-run`) and `references/commands/full.md` consult it. Per-repo `.claude/settings.json` does not duplicate this information.

## Generic rules (apply to every repo)

These triggers apply in **any** repo. Per-repo sections supplement them with repo-specific patterns. Do not repeat generic patterns in per-repo sections.

| Changed pattern | Docs to audit |
|---|---|
| `CLAUDE.md`, `AGENTS.md`, `README.md` itself | full re-read of itself; consistency-check against changed files in the same commit |
| `Dockerfile`, `docker-compose*.yml`, `Makefile` | `CLAUDE.md` (Setup/Dependencies/How to run), `README.md` |
| `.krane/**` | `CLAUDE.md` (Deployment section), any `docs/deploy*.md` |
| `.env.example` | `CLAUDE.md` (Setup), `README.md` (Setup), `docs/setup*.md` |
| `.github/workflows/**` | `CLAUDE.md` (CI section if any), `docs/ci*.md` |
| `.github/PULL_REQUEST_TEMPLATE.md` | any doc that duplicates the PR checklist (commonly `docs/git*.md`, `CONTRIBUTING.md`, `REVIEW.md`) |
| `.github/ISSUE_TEMPLATE/**` | any doc that explains issue conventions (commonly `CONTRIBUTING.md`) |
| Lockfiles (`*.lock`, `package-lock.json`, `pnpm-lock.yaml`, `Gemfile.lock`, `uv.lock`) | `CLAUDE.md` (Dependencies, Setup), `README.md` (Install) — usually only when a major version moves |

Per-repo sections are added by the repo owner as needed, one `## <repo>` heading per repo, listing only patterns beyond the generic rules.
