---
name: ux-build-validate
description: "Returns a built-versus-approved-spec verdict (pass or fail) for one change, from state-by-state visual evidence of the running build compared with the spec and prototype at 100 and 150 percent zoom, with up to three fix rounds. Writes qa.md into the spec folder. Use when the user says 'compare the build with the prototype', 'run design QA on the build', 'does the built ui match the spec', 'write qa.md for this change'. Skip for: whether the spec itself is ready, which belongs to cct:ux-spec-validate."
user_invocable: true
allowed-tools: "Bash(python3 */ux-assessment-run/scripts/*)"
metadata:
  version: 1.0.0
  author: calvindudek
---

# cct:ux-build-validate

**Arguments:** `<change>`, a change id, a change folder or a spec folder.

Validate one built UI against its approved spec and write `<spec>/qa.md` with a verdict. The
method is in `references/build.md`; follow it.

Shared files are in `references/`, two levels up from this skill's base directory.

## Prerequisites

| Need | For | Without it |
|---|---|---|
| Python 3.10+ and an image-reading tool | Build QA | Report `fail` |

## Read first

1. Read `docs/ux/setup.md`. Missing: stop and run `cct:ux-setup`.
2. Resolve the spec folder and the mode with the shared `references/spec-folder.md`. No spec
   folder exists: stop and say `cct:ux-design-run` makes one. No approved `validation.md`: stop and
   say `cct:ux-spec-validate` writes it.
3. Read the size and skips: `decisions.json` in sdlc mode, the frontmatter of `<spec>/brief.md` in
   standalone mode. The `prototype` skip is set, or the size is `none`: do not run; say the skip
   and its reason in one line.
4. Read the asks (`intent.md` `## Asks`, or the brief's `## Owner Asks`), `facts.md` when present,
   and every file in the spec folder.
5. Read shared files as needed: `finding-format.md`, `checklist.md`, `writing.md`,
   `visual-pass.md`.
6. Follow the shared `references/visual-pass.md` for every image: open each with the image-reading
   tool, write the ledger, validate each issue against the repo's conventions. Before reporting,
   run `python3 "${CLAUDE_SKILL_DIR}/../ux-assessment-run/scripts/visual-check.py" "$run" --repo "$PWD"`
   (this is the `visual-check.py` that `references/build.md` names). Failure means the review did
   not run: the verdict is `fail`.

## Ask once

Ask open questions once, in one batch, each with a recommended answer. Never ask the user to
resolve what the spec already decides.

## Severity

P0-P3, the kit's one scale: `finding-format.md` maps P0 to Critical, P1 to High, P2 to Medium, P3
to Low. Reuse its format where it fits.

## Delegates

Responsive and accessibility evidence come from `cct:ux-responsive-audit` and
`cct:ux-accessibility-audit` when installed; rule conformance from `cct:ux-rules-validate`;
proposed rules the build uncovers go to `cct:ux-decision-log`.
