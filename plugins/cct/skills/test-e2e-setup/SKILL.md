---
name: test-e2e-setup
description: "Configures the named E2E harness (Playwright) and its guards in a repo: installs the lint preset, the copy-catalogue rule, the t() copy fixture, the token helper, the persona and journey templates and the assertion guard, and covers Playwright install, config, auth setup, CI and debugging. It detects the spec directory and copy catalogue, never overwrites an existing file and prints what is left by hand. Use when someone says 'set up Playwright', 'install the e2e lint preset', 'install the assertion guard', 'configure the e2e harness', 'add the copy-catalogue lint rule'. Skip for: the rules the harness enforces, owned by cct:test-e2e-policy; writing the tests, owned by cct:test-e2e-coverage-run."
allowed-tools: "Bash(npx:*) Bash(npm:*) Bash(node:*) Bash(bash */test-e2e-setup/scripts/*) Read Edit Write Grep Glob"
user_invocable: true
metadata:
  version: 1.0.0
  author: calvindudek
---

# Set up the e2e harness

Verification and every push follow the [local-first contract](../sdlc-run/references/local-first.md); read it before running checks or preparing a push.

Installs the mechanical half of the e2e standard. The rules it enforces are written in
`cct:test-e2e-policy` (`${CLAUDE_SKILL_DIR}/../test-e2e-policy/references/`); this skill
does not restate them. It writes no specs and edits no application source.

## Install the lint preset and templates

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/install-lint.sh <repo-root>
```

Writes into the repo's spec directory: the lint preset `eslint.config.e2e.mjs`, the
copy-catalogue rule `eslint-rules/no-catalogue-copy.js`, the `t()` copy fixture `i18n.ts`
(only when a copy catalogue is found), the token helper `tokens.ts`, and the `personas.md`
and `journeys.md` templates. It prints three sections: DETECTED (spec directory, catalogue,
Playwright version, `eslint-plugin-playwright`), INSTALLED (each file written or skipped
because it exists) and NEXT (what is left by hand). Do the NEXT items:

1. Install `eslint-plugin-playwright` when missing.
2. Point `CATALOGUES` at the copy catalogue and fix the imports in `i18n.ts`; leave it empty for a single-locale product.
3. Set `FILES` in the preset to the repo's spec glob and merge the preset into `eslint.config.mjs`.
4. Fill in `personas.md` and `journeys.md`. The journey inventory itself is drafted by `cct:test-journeys-write`.
5. Expect failures on the existing suite and fix them by rule, one rule per PR.

## Gate pull requests on the assertion guard

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/assertion-guard.sh origin/main e2e
```

Fails a diff that removes assertions or adds `.skip`, `.fixme` or `.only`. Wire it into
CI as a required check.

## Self-tests

`scripts/test_lint_rules.sh`, `scripts/test_assertion_guard.sh` and
`scripts/test_no_catalogue_copy.sh` prove the preset and the guard fail on known-bad input.
Run them after changing a template or a script, with `bash ${CLAUDE_SKILL_DIR}/scripts/<name>`.

## Playwright install, config, auth, CI, debugging

`references/setup-and-tools.md` has the installation, config reference, the project
layout (which files are installed), persona sign-in setup, CI and debugging.

## Two upstream tools this setup does not use, and why

**Playwright's own test agents** (`npx playwright init-agents`) scaffold a second planner,
generator and healer beside ours. Their healer prompt says to "do the most reasonable thing
possible to pass the test" and to mark a test `test.fixme()` when it believes the test is
correct and keeps failing, which is exactly the case most likely to be a real bug. Its edit
tool is unscoped. Its generator works from the accessibility snapshot, so it binds every
assertion to visible English copy. Borrow the planner's plan format; use nothing else.

**Playwright MCP** streams the full accessibility tree into context on every step: about
114K tokens per task against about 27K for a CLI, by Playwright's own measure. This setup explores
pages with the `agent-browser` CLI (`cct:browser-automate`). The committed spec is plain
`@playwright/test` either way, so this is a cost decision. If you are debugging by hand and
MCP is already connected, use it; do not build a skill or agent on it.
