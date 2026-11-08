---
name: ux-setup
description: "Sets a repo up for the ux skills: writes docs/ux/setup.md (product, audience, design rules, screens, how to run the app, what is read only), the owner's-words file, the as-built sitemap through cct:ux-sitemap-create, and empty guidelines and glossary-proposal files. Use once per project when the user says 'set up ux', 'ux setup', 'prepare this repo for ux assessments', 'write docs/ux/setup.md'. Skip for: the assessment itself, which belongs to cct:ux-assessment-run."
user_invocable: true
allowed-tools: "Bash(python3 */review/scripts/*)"
metadata:
  version: 1.0.0
  author: calvindudek
---

# cct:ux-setup

**Arguments:** `[path to repo]  (defaults to the current repo)`

Make a repo ready for `cct:ux-assessment-run`, `cct:ux-decision-log`, `cct:ux-guidelines-write`, `cct:ux-design-run`,
`cct:ux-spec-validate`, `cct:ux-rules-validate` and `cct:ux-assessment-run`. Everything specific to the product
goes into the repo; the skills stay general.

The plugin's shared files are in `references/`, two levels up from this skill's base directory.

## Prerequisites

| Need | For | Without it |
|---|---|---|
| Python 3.10+ and an image-reading tool | Check the first screenshot | Record BLOCKED in setup and the report |

## 1. Look before asking

Read, if present: `README`, `CLAUDE.md`, `PRODUCT.md`, `AUDIENCE.md`, `DESIGN.md`, a glossary,
`docs/`, the router or route list, the e2e or Playwright setup, `package.json` scripts, and any
existing UX or design documents. If `docs/ux/setup.md` exists, update it instead of replacing it.

Fill in everything you can from the repo. Ask the user only what the repo cannot answer:
- the products the audience already uses (for pattern research), if not written anywhere;
- what must never be written to, if not stated;
- where the owner's earlier requests are, if they exist outside the repo;
- the route source and the guidelines path, if neither is discoverable;
- the screen goals path, if no screen goals document exists;
- where UI components live and which catalogue shows them, if not discoverable;
- the screenshot recipe at 100 percent and 150 percent, if no test harness shows it;
- the feedback folders, if they live outside `docs/ux/`.
Ask these together in one question round.

## 2. Write the files

| File | Content |
|---|---|
| `docs/ux/setup.md` | From `references/setup-template.md`, filled in. Every screen from the router, with the states to capture, and the design inputs `cct:ux-design-run` reads. |
| `docs/ux/owner-words.md` | Every request the owner has made about the interface, verbatim, dated, grouped by topic. Seed it from existing documents and from this conversation. If a requests file already exists, point `setup.md` at it instead of copying. |
| `docs/ux/interaction-guidelines.md` | Title "<Product> interaction guidelines: editing, navigation, dialogs, and feedback"; sections: Principles, Rules (every area of `references/rule-areas.md`, each `status: unresolved`), Flows, Exceptions, Enforcement map. Empty rules, not invented ones. |
| `docs/ux/sitemap.md`, `docs/ux/sitemap.json` | Run `cct:ux-sitemap-create as-built` after `setup.md` exists; it reads the route source and writes both files. Never a hand-written stub. |
| `docs/ux/glossary-proposal.md` | The term × place table heading and the columns; filled in by an audit. |
| `docs/designs/` | Nothing to seed. `cct:ux-decision-log` writes one ADR file here per answer; there is no decision log. |
| `docs/ux/exceptions.md` | Empty exception register in the `EX-<n>` format of `references/conflicts.md` section 2. Ask the owner the WCAG and EAA scope of each surface (consumer-facing or business-only) and write one scope finding per surface into `setup.md`. |

If the repo already keeps design documents elsewhere (for example `docs/designs/`), put the paths
it uses into `setup.md` instead of creating duplicates.

## 3. Check that the audit can run

Run the build and one screenshot of the first screen with the test data and fakes named in
`setup.md`. If it fails, write the failure into `setup.md` under "How to run it" and tell the user
the exact blocker. Never run against real user data or real devices to make it work.
Use the shared `references/visual-pass.md` for this capture: open the image, write the ledger,
validate its issues, then run
`python3 "${CLAUDE_SKILL_DIR}/../ux-assessment-run/scripts/visual-check.py" "$run" --repo "$PWD"`.
A failed check means the visual review did not run. Record BLOCKED in `setup.md` and the
report; never certify the screen from capture alone. Link the ledger and check result.

## 4. Report

List the files written, what was filled from the repo, what the user answered, and anything
still marked `<unknown>`. Do not commit unless the user asks; follow the repo's own commit rules.
