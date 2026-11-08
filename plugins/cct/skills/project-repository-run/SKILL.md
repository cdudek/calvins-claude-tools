---
name: project-repository-run
user_invocable: true
description: Brings a new or existing repo to the blueprint baseline - declares the workflow plugins in .claude/settings.json (cct, optionally pinned), runs the sdlc adopt step, points to the anti-slop install for TypeScript, adds the Decision4 handoff contract and a starter boundary-map.yaml, then checks it all. Use when someone says "set up this repo", "project setup", "init the project", "declare the plugins", "add Decision4", "boundary map", "bring this repo to the blueprint", or a session start reports setup drift. For a brand-new product's context, brand and design system use project-kickoff-run.
---

# Project setup

Wires a repo to the rulebook at https://github.com/cdudek/blueprints (`core/BLUEPRINT.md`, `references/agent-files.md` AGENT-23 to AGENT-27). `cct:project-kickoff-run` writes the product, brand and UX documents; this skill wires plugins and gates. Run it on a branch in the repo root.

The script `${CLAUDE_SKILL_DIR}/scripts/project_setup.py` is deterministic, stdlib only, and writes nothing without `--yes`. Without it, it prints the plan.

## Ask first (one AskUserQuestion, recommended option first)

- **Plugins:** `cct@cct` only (recommended), or more as `name@marketplace` (a non-cct marketplace also needs `NAME=OWNER/REPO`).
- **Pin the cct marketplace?** No, follow `main` (recommended), or a tag or ref.
- **Decision4 contract and boundary map?** Yes (recommended) or no.
- **Anti-slop?** Only when the repo is TypeScript. Yes (recommended) or no.
- **sdlc?** Yes (recommended) or no. `adopt` asks its own tiers question.

## Order

1. Plan, show it, then apply:

   ```bash
   python3 ${CLAUDE_SKILL_DIR}/scripts/project_setup.py [--plugins A,B] [--marketplace-ref REF] [--no-decision4] [--no-anti-slop] [--no-sdlc]
   python3 ${CLAUDE_SKILL_DIR}/scripts/project_setup.py <same options> --yes
   ```

   This merges `extraKnownMarketplaces` and `enabledPlugins` into `.claude/settings.json` (existing keys stay), adds the Decision4 v1 section to the canonical agent file (CLAUDE.md, else AGENTS.md; only a pointer line when an imported file already carries it) and writes `boundary-map.yaml` unless one exists.
2. `/cct:sdlc-run adopt` (skip with `--no-sdlc`).
3. Anti-slop, TypeScript only: `npx skills add dmmulroy/anti-slop --skill install-anti-slop`, then run that skill. The script never vendors code.
4. Review `boundary-map.yaml` with the owner: add floors for the repo's schema, contracts, credentials and production ground (`core/references/structure.md`, STR-26).
5. `python3 ${CLAUDE_SKILL_DIR}/scripts/project_setup.py <same options> --check` must exit 0. Commit as one change.

Tell the user to restart Claude Code and trust the folder: `extraKnownMarketplaces` and plugin installs wait for trust.

## Options

`--root DIR`, `--plugins` (repeatable or comma list, default `cct@cct`), `--marketplace-ref REF` (cct only), `--marketplace-source NAME=OWNER/REPO`, `--decision4/--no-decision4`, `--anti-slop/--no-anti-slop` (default on for TypeScript), `--sdlc/--no-sdlc`, `--check`, `--yes`, `--dry-run`. Exit 1 means drift or a problem (a marketplace pointing elsewhere, a wrong contract version, a malformed map); invalid settings JSON exits 2 and changes nothing.

## Drift check at session start

`--check` is read-only and prints one line per missing piece. cct ships no SessionStart hook; a repo adds one to its own `.claude/settings.json`:

```json
{"hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/skills/project-repository-run/scripts/project_setup.py\" --check"}]}]}}
```

Plugin hooks run only once cct is installed, so use the path of a vendored copy if the repo must check before that.

## Settings schema

Verified against the Claude Code docs: `extraKnownMarketplaces.<name>.source` is `{"source": "github", "repo": "owner/repo", "ref": "<branch or tag>"}` (`ref` optional) and `enabledPlugins["<plugin>@<marketplace>"]` is `true`.
https://code.claude.com/docs/en/plugins/marketplace-reference.md (marketplace sources) and https://code.claude.com/docs/en/settings-example.md (a team's shared settings).

## Session notice

The plugin's SessionStart hook (`hooks/project-drift-check.py`) runs `--check --no-decision4` on a repo that declares cct and prints one line when `.claude/settings.json` has drifted from the declared plugins. It is silent when the settings are fine or the repo does not declare cct, and it never blocks. Fix the drift by running this skill again.

