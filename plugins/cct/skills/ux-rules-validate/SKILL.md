---
name: ux-rules-validate
description: "Returns a conformance verdict for a design spec or a change (a PR, a branch or files) against the product's accepted interaction guidelines, glossary and design system, using the enforcement map; reports missing documents instead of skipping, every departure, and new behaviour no rule covers. Use when the user says 'does this follow our guidelines', 'run a conformance check', 'check this change against the accepted rules', 'is this ui rule-conformant'. Skip for: the multi-lens assessment that runs it as one pass, which belongs to cct:ux-assessment-run."
user_invocable: true
allowed-tools: "Bash(python3 */review/scripts/*)"
metadata:
  version: 1.0.0
  author: calvindudek
context: fork
model: sonnet
effort: high
background: false
---

# cct:ux-rules-validate

**Arguments:** `spec <change>` or `[pr-number | pr-url | branch | paths]  (defaults to the current branch's open PR)`

Keeps the accepted rules from drifting. It checks; it does not fix.

Shared files are in `references/`, two levels up from this skill's base directory. Read
`docs/ux/setup.md`, then the interaction guidelines, the glossary, the design system and the
current `ux` ADRs listed in `<designsDir>/INDEX.md` (default `docs/designs`; open those the change
touches). Use the old `docs/ux/decisions.md` only where it remains.

## Prerequisites

| Need | For | Without it |
|---|---|---|
| Python 3.10+ and an image-reading tool | Visual pass when images are captured or judged | Report BLOCKED for visual conformance |

## 0. The documents

Conformance is only as good as the documents it checks against, so look for every one of them
first: the interaction guidelines (and a router such as `INTERACTION.md` that points at them),
the glossary, the design system, `writing.md`'s voice rules as the repo applies them, and the
recorded decisions, exceptions register and `PRODUCT.md`. Take paths from `setup.md`; otherwise search `docs/ux/`, `docs/` and the repo
root. When called from `cct:ux-assessment-run`, use its documents table instead of searching again.

Mark each **found** or **missing**. A missing document never stops the check and is never
skipped silently: check against what exists, and for each missing one name the checks that could
not run (no guidelines: no rule checks; no glossary: no vocabulary check; no design system: no
component or token check). `cct:ux-setup` creates the UX documents a repo lacks.

## Spec mode

When the target is `spec <change>` (a change id, a change folder or a spec folder), check the
design spec before facts and build. Resolve the spec folder with the shared
`references/spec-folder.md`, then follow `references/spec.md` with the documents from step 0. It
reads `<spec>/brief.md`, `ia.md`, `interaction.md`, `screens.md`, and `prototype/index.md` when
present, and writes `<spec>/conformance.md` with these seven sections, exactly in order:

1. **Interaction model**
2. **Design system**
3. **Component inventory**
4. **Words**
5. **Screen goals, audience, taxonomy**
6. **Deliberate inconsistencies**
7. **Missing guidelines**

For the component inventory, search the code for each component's callers, give the count and
the files, and state the implication for other screens. If prototype images exist, open each
and run the shared `references/visual-pass.md`, including its script check, before reporting.
Without images, label the result text-only. Then stop: steps 1 to 3 are for code.

## 1. What changed

Resolve the target: a PR (`gh pr view`, `gh pr diff`), a branch against the default branch, or
the given paths. Keep interface files only; if none changed, say so and stop.

## 2. Check

For every accepted rule whose "Applies to" touches a changed screen or component:
- Does the change follow it? Read the code; run the app on the change and look where behaviour
  is involved (open every changed dialog, menu, popover or select and screenshot it open). When
  called from `cct:ux-assessment-run`, use its build and screenshots instead of building again.
- Does the change bypass the component or test the enforcement map names (for example a
  hand-built dialog where the shared one is required)?

Also check:
- every new or changed component, colour, size and spacing against the design system: the
  shared component the design system names, not a hand-built copy; its tokens, not literal
  values;
- every new or changed string against the glossary and `writing.md`;
- every new interaction that no accepted rule covers: report it as "new behaviour, no rule" with
  the nearest proposed rule, so it can go to the next `cct:ux-decision-log` round;
- rules marked "not enforced" in the map that this change touches: say so.

Deferred and unresolved rules are not enforced; mention them only when the change decides one
implicitly.

Run the shared `references/visual-pass.md` on every captured image. Reuse the caller's run or
create the standalone run it defines. Open each image, write `visual.json`, and give every
issue exactly one convention verdict. Run
`python3 "${CLAUDE_SKILL_DIR}/../ux-assessment-run/scripts/visual-check.py" "$run" --repo "$PWD"`
before reporting. Failure means the review did not run: report BLOCKED, never compliant.

## 3. Report

First the documents: found (with path) or missing, and what each missing one stopped. Then
findings in the format of `finding-format.md`, one per departure, each naming the rule it breaks
(quoted) in the main text and the rule's section in the supporting notes. Use the three verdicts
in `visual-pass.md` for every issue; permitted departures leave the fix list with a note,
and uncovered problems go to `cct:ux-decision-log`. Link the ledger and check result.
Then: rules checked and
passed; new behaviour with no rule; enforcement gaps. If there are no departures, say so plainly.

When called from `cct:ux-assessment-run`, return the findings instead of printing them.
