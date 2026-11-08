# heydiff-web

Verification follows [local-first](https://github.com/cdudek/calvins-claude-tools/blob/main/plugins/cct/skills/sdlc-run/references/local-first.md). These are legacy workflow examples; migrate
verification before enabling them in a new repo. GitHub keeps cloud and scheduled work.

HeyDiff: the web app, the landing page, the operator area, the API and the MCP server.

## Strategy lives in heydiff-context

Market research, pricing, roadmap, the online-service decisions and the design-system pointers live in [pokbytes/heydiff-context](https://github.com/pokbytes/heydiff-context), checked out at `~/projects/heydiff/heydiff-context`. Read it before any product, pricing or scope decision; write such decisions there, not here.

@~/projects/heydiff/heydiff-context/CLAUDE.md

## Where the UX docs live

- The lasting UX docs for HeyDiff (web app, Chrome extension, landing, operator) live here in `docs/ux/`: `setup.md`, `interaction-guidelines.md`, `glossary-proposal.md`, `owner-words.md`, `sitemap.md`. The UX skills read and write them there.
- The Chrome extension's code is in `pokbytes/heydiff-chrome`, but its UX docs live here, because it is one product with the web app.
- The Mac app keeps its own UX docs in `pokbytes/heydiff-desktop` `docs/ux/`.
- Mockups and visual explorations: `design-explorations/`.

## How work moves: the SDLC

This repo uses `cct:sdlc-run`, configured by `sdlc.json`. A change is one PR and one folder:
`changes/<date>-<KEY>-<slug>/` (no key when there is no Linear issue). Designs that outlive
one PR live in `docs/designs/`, one decision per file. Read `docs/designs/INDEX.md` first and
open only the files it points you to; `python3 scripts/design_index.py write` after adding one.
The seven stages are Intent, UX plan,
Facts, Tech plan, Build, Milestone and Outcome.

The agent drafts intent, UX plan, facts and plan; the engineer confirms the intent, then all
three documents in one gate. After that every feature is built inside `/goal` as a PR into
`milestone/<slug>`, and ends on `python3 scripts/verify_gate.py feature <id>`. Each milestone
gets the heavy checks once, then one PR to its parent.

Branches:

```
<default> ─── milestone/<slug> ─── <feature branches>             one milestone
<default> ─── project/<slug> ─── milestone/<slug> ─── <features>  a project
```

A `project/<slug>` branch exists only for work spanning several milestones; one milestone
needs none.

**Only the PR into the default branch is reviewed.** Feature PRs into `milestone/*` and
milestone PRs into `project/*` are interior merges inside one change — no Claude review, no
code owner, auto-merge on their checks alone.

There are no Ship/Show/Ask tiers here, so that PR auto-merges on green too.

New keys: `checks`, `milestones`, `projects`, `hotfix`, `goal`, `languages`, `responsiveTier`,
`ux`, `protected`. The reference is
**[docs/sdlc.md](docs/sdlc.md)**.

## Terraform and infrastructure naming (owner, 2026-10-31)

The infrastructure lives in [pokbytes/terraform-infra](https://github.com/pokbytes/terraform-infra). Every name that this repo's CI, scripts, tests or docs use follows its rule:

- **Every environment-scoped resource ends in its environment:** `-prod` or `-staging`, or `_prod` and `_staging` where `-` is not allowed (Postgres database names). Examples: `heydiff-web-prod`, `heydiff-web-staging`, `heydiff-web-migrate-prod`, `better-auth-secret-prod`, `heydiff_prod`.
- **A resource used by every environment ends in `-shared`:** `DB_INSTANCE`, `IMAGES_REPO`, `APP-run-shared`, `APP-deploy-shared`. `-dev` (`_dev`) is for local development only: `heydiff-web-signer-dev`, `calvin_dudek_dev`.
- **No bare names.** A name without its environment silently means production. Never `heydiff-web`, `database-url` or `heydiff`.
- The full table, what is exempt (Terraform addresses, domain mappings, IAM users' emails, the GitHub environment `production`) and the policy that enforces it (`policy/terraform/naming.rego`) are in terraform-infra's README, "Naming".

## Development database

Each contributor has their own Cloud SQL database `<firstname_lastname>_dev`; `make dev-db` registers, connects and writes `DATABASE_URL` to `.env.local`. Read [README.md, "Development database"](README.md#development-database) before touching local database setup.

## Verifying your work

    npm run format && npm run lint && npm run typecheck && npm test

Run it before reporting done and before every push under the linked local-first contract. The Stop hook runs
`npm run format && npm run lint && npm run typecheck` for dirty source files.

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:ca08a54f -->

## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

## Session Completion

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run the full local gate before every push** - Follow the linked targeted failure loop first; batch fixes, then run the suite once on the final head.
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd dolt push
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**

- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds

<!-- END BEADS INTEGRATION -->
