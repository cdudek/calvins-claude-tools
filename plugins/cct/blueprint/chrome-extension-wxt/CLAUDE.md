# heydiff-chrome

Verification follows [local-first](https://github.com/cdudek/calvins-claude-tools/blob/main/plugins/cct/skills/sdlc-run/references/local-first.md). These are legacy workflow examples; migrate
verification before enabling them in a new repo. GitHub keeps cloud and scheduled work.

HeyDiff: the Chrome extension (element picker, comments on the live page, side panel, devices). The product was called Snapmark until 2026-10-28 ([decision](https://github.com/pokbytes/heydiff-context/blob/main/strategy/2026-10-28-name-heydiff.md)).

## Strategy lives in heydiff-context

Market research, pricing, roadmap, the online-service decisions and the design-system pointers live in [pokbytes/heydiff-context](https://github.com/pokbytes/heydiff-context), checked out at `~/projects/heydiff/heydiff-context`. Read it before any product, pricing or scope decision; write such decisions there, not here.

@~/projects/heydiff/heydiff-context/CLAUDE.md

## Where the plan and the UX docs live

- The extension is one product with the web app. Its changes, plans and lasting UX docs live in [pokbytes/heydiff-web](https://github.com/pokbytes/heydiff-web) (`~/projects/heydiff/heydiff-web`): `changes/` for plans, `docs/ux/` for setup, interaction guidelines, glossary, owner's words and sitemap.
- Read the web repo's `docs/ux/` before changing any screen of the extension.
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

## Verifying your work

    npm format && npm lint && npm typecheck && npm test

Run it before reporting done and before every push under the linked local-first contract. The Stop hook runs
`npm format && npm lint && npm typecheck` for dirty source files.


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
2. **Run the full suite before every push** - Follow the linked targeted failure loop first; batch fixes, then run the suite once on the final head.
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
