---
name: ux-usability-audit
description: "Judges one flow, screen or pattern decision against the 30 Laws of UX, from a single quick verdict to a full audit that marks every law pass, fail or not applicable with evidence; for AI-driven surfaces it also applies the selected criteria from cct:ux-ai-heuristics. Owns the heuristic usability verdict. Use when someone asks 'does Hick's law apply here', 'run a Laws of UX audit', 'give me a heuristic usability verdict', 'modal or inline for this flow', 'defend this UX choice'. Skip for: WCAG verdicts (cct:ux-accessibility-audit); viewport adaptation (cct:ux-responsive-audit); whole-app or PR UX assessment (cct:ux-assessment-run); backend or copy-only work."
user_invocable: true
source: https://github.com/cite-me-in/skills
---

# Apply UX Laws

Grounded in the 30 laws of [lawsofux.com](https://lawsofux.com) (Jon Yablonski). The checks live
in `references/laws-of-ux.md`: per law, numbered observable checks (`L<n>.<m>`), thresholds with
their sources, the evidence each needs, severity, and when the law does not apply. It is a mirror
of `plugins/cct/references/laws-of-ux.md`; edit that one and copy it across. Worked examples and
stakeholder scripts are in `references/examples-and-scripts.md`. Read the sections you need, not
the whole file.

## Workflow

**Mode A, quick question** (one law, yes or no): find the law, run only its checks, answer with
the principle, a pass or fail verdict, and one concrete suggestion.

**Mode B, design session**: pick the laws the reference routes to for this kind of screen, run
their checks, resolve conflicts with `references/conflicts.md` (the precedence ladder and the
conflict table, also a mirror of the copy in `plugins/cct/references/`), and give a prioritized
list: law and check id, what is wrong, the concrete fix, severity.

**Mode C, audit**: every law, every check, on every screen and state you were given. Fill the
reference's coverage table: all thirty rows, each pass, fail or not applicable, with evidence (a
screenshot, a `file:line`, a count or a timing). "Not applicable" names the law's applicability
rule. A blank row is a check that did not run, so say so instead of leaving it blank.

To defend a decision, use `references/examples-and-scripts.md`.

## Scope boundary

Where the repo declares a design system, token and component decisions stay with it;
this skill judges interaction and layout psychology, not visual token choices. Accessibility
conformance is `cct:ux-accessibility-audit`; where a law and a WCAG criterion overlap, the
reference names the criterion and the WCAG audit owns the verdict.
