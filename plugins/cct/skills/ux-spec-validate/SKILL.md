---
name: ux-spec-validate
description: "Returns a spec-readiness verdict (ready or not-ready) for one design spec from completed specialist evidence: three independent reviewers (Nielsen heuristics, every Laws of UX check, and a screen critique against the audience and job stories), a definition of ready and one owner gate. Writes validation.md into the spec folder. Use when the user says 'validate the spec', 'is the design ready', 'is this spec ready for approval', 'write validation.md'. Skip for: comparing the built UI with the approved spec, which belongs to cct:ux-build-validate."
user_invocable: true
allowed-tools: "Bash(python3 */ux-assessment-run/scripts/*)"
metadata:
  version: 1.0.0
  author: calvindudek
---

# cct:ux-spec-validate

**Arguments:** `<change>`, a change id, a change folder or a spec folder.

Validate one design spec and write `<spec>/validation.md` with a verdict. The method is in
`references/spec.md`; follow it. Comparing the built UI with the approved spec is
`cct:ux-build-validate`, not this skill.

Shared files are in `references/`, two levels up from this skill's base directory.

## Prerequisites

| Need | For | Without it |
|---|---|---|
| Python 3.10+ and an image-reading tool | Prototype gate | Report `not-ready` |

## Read first

1. Read `docs/ux/setup.md`. Missing: stop and run `cct:ux-setup`.
2. Resolve the spec folder and the mode with the shared `references/spec-folder.md`. No spec
   folder exists: stop and say `cct:ux-design-run` makes one.
3. Read the size and skips: `decisions.json` in sdlc mode, the frontmatter of `<spec>/brief.md` in
   standalone mode. Never require a key the mode does not have. The `validation` skip is set: do
   not run; say the skip and its reason in one line.
4. Read the asks (`intent.md` `## Asks`, or the brief's `## Owner Asks`), `facts.md` when present,
   and every file in the spec folder.
5. Read shared files as needed: `finding-format.md`, `laws-of-ux.md`, `lenses.md`, `checklist.md`,
   `writing.md`, and `usability-heuristics.md` from `${CLAUDE_SKILL_DIR}/../ux-assessment-run/references/`.
6. Whenever images exist, follow the shared `references/visual-pass.md`: open each with the
   image-reading tool, write the ledger and validate each issue against the repo's conventions.
   Before reporting, run
   `python3 "${CLAUDE_SKILL_DIR}/../ux-assessment-run/scripts/visual-check.py" "$run" --repo "$PWD"`.
   Failure means the review did not run: the spec is `not-ready`. The text-only spec loop and
   recorded prototype skips claim no visual compliance.

## Evidence

The verdict is built from completed specialist evidence, not from this skill's own judgement:
heuristic and Laws of UX findings from `cct:ux-usability-audit`, accessibility from
`cct:ux-accessibility-audit`, responsive behaviour from `cct:ux-responsive-audit`, conformance
from `cct:ux-rules-validate`, and the independent critique from `cct:ux-usability-reviewer`. This
skill reads that evidence, applies the definition of ready in `references/spec.md` and decides.

## Ask once

Ask open questions once, in one batch, each with a recommended answer. Never ask the user to
resolve what the spec already decides.

## Severity

0-4 (Nielsen's scale), the kit's one scale: `finding-format.md` maps 4 to Critical, 3 to High, 2 to
Medium, 1 to Low. Reuse its format where it fits.
