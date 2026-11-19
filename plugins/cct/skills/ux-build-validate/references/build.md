# Build QA

## Purpose

Compare the built UI against the approved spec and prototype.
Write the verdict. Run as the build loop of a screen, it allows two fix rounds per screen per
design-system release; run at milestone close it is report-only, because there is one fix round at
milestone close and the supervisor owns it.

## Inputs

- Approved `<spec>/readiness.md` (`<spec>/validation.md` in a folder written before the rename),
  unless the `validation` skip is recorded and a `visualSource` is supplied: then the intent
  approval authorises the run.
- `<spec>/brief.md`.
- `<spec>/ia.md`.
- `<spec>/interaction.md`.
- `<spec>/screens.md`.
- The declared `visualSource`, when `decisions.json` names one: the reference.
- `<spec>/prototype/index.md` and its screenshots, when present: advisory only.
- The running build from `docs/ux/setup.md`.
- the shared `finding-format.md`.
- the shared `checklist.md`.
- the shared `writing.md`.

## Steps

1. Load the approved spec, the visual source (else the prototype screenshots), and the build.
2. If either side cannot be captured, set `verdict: fail` and name the blocker.
3. For each screen and state, drive the build to the same state.
4. Match content, theme, and zoom.
5. Record viewport, zoom, and pixel density.
6. Capture the build at 100 percent and 150 percent.
7. Open every reference and build image with the image-reading tool. Follow the shared
   `visual-pass.md`, using `<spec>/visual/build/<round>/` as the run; compare both sets of pixels.
8. Check full view first.
9. Then check focused regions.
10. Screenshot menus, selects, popovers, and dialogs open.
    Walk every journey in `<spec>/ia.md` in the build, Back included, and check what each Back
    restores. Exercise every cell of the elements x interactions matrix; a cell that does
    something other than the spec says is a finding.
11. Run the mandatory surface pass.
12. Write one finding per flaw with P0-P3 severity.
13. Validate every issue against the repo's conventions with exactly one verdict from
    `visual-pass.md`. Keep quoted violations and uncovered problems; report permitted
    departures as removed from the fix list. Propose uncovered rules to `cct:ux-decision-log`.
14. Write the measurements table.
15. Let the builder fix and recapture (build loop only; at the close, report and stop).
16. Recompare at the same state.
17. Stop after two rounds.
18. Run `visual-check.py` on this round before writing `qa.md`; link the ledger and check
    result in Coverage Matrix and carry each convention verdict into Findings or notes.
    Failure means the review did not run and `verdict: fail`. Pass only when the check passes
    and no P0-P2 remains.

## Layers and tolerances

A screen passes on six layers. These are the defaults; a repo may tighten them in its config and
never loosen them without a decision record. Write the tolerance used in each Measurements row.

| Layer | Tolerance |
|---|---|
| Structure | Same headings in the same order, same landmarks, nothing lost at 320 px. |
| Copy | Same words after normalising quotes and spaces; sample data and ruled lines excluded. |
| Tokens | Same design token for colour, type, weight, radius, background; sizes within 0.5 px. |
| Geometry | Gaps use a spacing token and are within 2 px of the reference; anchors within 4 px desktop, 2 px phone; order and alignment exact. |
| Rules and access | The repo's UI rules and WCAG 2.2 AA, zero violations. |
| Review | Only High and Medium defects fail; Low is listed, not blocking. |

A pixel diff is advisory only: sample data in designs is meant to differ. Severity: High blocks a
task or fails contrast (P1), Medium is noticed at a glance (P2), Low is only visible when
measuring (P3, does not fail). The defect list per screen is frozen after the first review (later
rounds may add only High items or regressions), and the budget is two fix rounds per screen per
design-system release. Full rules: the sdlc-run `convergence.md`.

## Mandatory Surface Pass

- Typography.
- Spacing and rhythm.
- Tokens and colour.
- Icons and imagery.
- Copy against `<spec>/screens.md` and the glossary.
- States and behaviour against `<spec>/interaction.md`.
- Moves and Back target against `<spec>/ia.md`.
- Accessibility focus ring, contrast, and keyboard route.

## Output Template

Write `<spec>/qa.md`.

```markdown
---
type: qa
change: <id>
verdict: pass | fail
rounds: <n>
created: YYYY-MM-DD
---

# Build QA

## Header

| Spec | Prototype | Build commit | Viewports | Zoom |
|---|---|---|---|---|

## Coverage Matrix

| Screen | State | Zoom | Result | Evidence |
|---|---|---|---|---|

## Findings

| Severity | Location | Evidence | Impact | Fix |
|---|---|---|---|---|

## Measurements

| Layer | Item | Spec value | Built value | Tolerance | Result |
|---|---|---|---|---|---|

## Mock Shortcomings

| Shortcoming | Impact | Follow-up |
|---|---|---|

## Round History

| Round | Changes checked | Result |
|---|---|---|

## Open Questions

| Question | Recommended answer | Why it matters |
|---|---|---|

## Verdict

pass | fail
```

## Checks

- Frontmatter keys are exactly `type`, `change`, `verdict`, `rounds`, and `created`.
- `verdict` is `pass` or `fail`.
- Blocked capture is reported as `fail`.
- Every screen-state-zoom cell is pass, fail, or n/a.
- Findings use P0-P3.
- No P0-P2 remains when verdict is `pass`.
- Overflow hiding persistent controls is P2 or worse.

## Skip Rule

Skip when the `prototype` skip is set (the shared `spec-folder.md`, section 2).
Skip when the size is `none`.
Say the skip and its reason in one line.

## Optional Skills

Used only when installed; the activity runs fully without them.

- `cct:ux-responsive-audit`.
- `cct:ux-accessibility-audit`.

Sources: github.com/openai/plugins · github.com/ratacat/claude-skills · nngroup.com/articles/wireflows
