---
name: ux-build-validate
description: "Returns a built-versus-approved-spec verdict (pass or fail) for one change, from state-by-state visual evidence of the running build compared with the spec and prototype at 100 and 150 percent zoom, with two fix rounds per screen per design-system release (report-only at milestone close). Writes qa.md into the spec folder. Use when the user says 'compare the build with the prototype', 'run design QA on the build', 'does the built ui match the spec', 'write qa.md for this change'. Skip for: whether the spec itself is ready, which belongs to cct:ux-spec-validate."
user_invocable: true
allowed-tools: "Bash(python3 */ux-assessment-run/scripts/*)"
metadata:
  version: 1.0.0
  author: calvindudek
---

# cct:ux-build-validate

**Arguments:** `<change>`, a change id, a change folder or a spec folder; with no PR, add the local
form `base=<ref> head=<ref> worktree=<path>` (the build is the worktree at `head`; the diff is
`git -C <worktree> diff <base>...<head>`).

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
   folder exists: when `decisions.json` names a `visualSource` or the change holds a loose
   reference image, create `<change folder>/spec/` holding only `qa.md` (the gate requires it for
   any visual change, and the run compares the build with that source); otherwise stop and say
   `cct:ux-design-run` makes one.
3. **Decide first whether this QA applies, before any readiness file is asked for.** When the
   change has a `spec.md` (sdlc-run layout 4), run `python3 scripts/spec.py qa <change>` and obey
   its exit: `3` the QA is skipped, so say the printed reason in one line and stop, asking for no
   readiness file and no second gate; `2` Stage 2 recorded no `ux` or `prototype` value, so stop
   and say the spec must record it (never read a missing record as a skip); `0` continue, and the
   joint gate's approval of the spec is the approval this run needs. Without a `spec.md`, use the
   rule below.
   Read the size and skips: `decisions.json` in sdlc mode, the frontmatter of
   `<spec>/brief.md` in standalone mode. The size is `none`, or the `prototype` skip is set and
   `decisions.json` names no `visualSource`: do not run; say the skip and its reason in one line.
   With a `visualSource`, compare the build against it (precedence in sdlc-run's
   `design-inputs.md`); a generated prototype is advisory, never the reference.
   Then the approval the run needs: when the `validation` skip is recorded and a `visualSource`
   is supplied, the owner's approval of the intent authorises this QA, and no `readiness.md` is
   asked for (never loop back to `cct:ux-spec-validate`, which honours the skip and writes
   nothing). Otherwise the spec needs an approved `readiness.md` (`validation.md` in a folder
   written before the rename); without one, stop and say `cct:ux-spec-validate` writes it.
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
to Low. Reuse its format where it fits. For visual defects: High (P1) blocks a task or fails
contrast, Medium (P2) is noticed at a glance, Low (P3) is only visible when measuring and does not
fail.

## Convergence

Judge on six layers with written tolerances (`references/build.md`, "Layers and tolerances"). A
pixel diff is advisory only. Only High and Medium fail; Low is listed. Freeze the defect list
after the first review and stop after two fix rounds per design-system release, then hand the
owner a side-by-side list. At milestone close it is report-only: there is one fix round at
milestone close, owned by the supervisor.

## Delegates

Responsive and accessibility evidence come from `cct:ux-responsive-audit` and
`cct:ux-accessibility-audit` when installed; rule conformance from `cct:ux-rules-validate`;
proposed rules the build uncovers go to `cct:ux-decision-log`.
