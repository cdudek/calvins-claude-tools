# Build QA

## Purpose

Compare the built UI against the approved spec and prototype.
Run up to three fix rounds, then write the verdict.

## Inputs

- Approved `<spec>/validation.md`.
- `<spec>/brief.md`.
- `<spec>/ia.md`.
- `<spec>/interaction.md`.
- `<spec>/screens.md`.
- `<spec>/prototype/index.md`.
- Prototype screenshots under `<spec>/prototype/`.
- The running build from `docs/ux/setup.md`.
- the shared `finding-format.md`.
- the shared `checklist.md`.
- the shared `writing.md`.

## Steps

1. Load the approved spec, prototype screenshots, and build.
2. If either side cannot be captured, set `verdict: fail` and name the blocker.
3. For each screen and state, drive the build to the same state.
4. Match content, theme, and zoom.
5. Record viewport, zoom, and pixel density.
6. Capture the build at 100 percent and 150 percent.
7. Open every prototype and build image with the image-reading tool. Follow the shared
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
15. Let the builder fix and recapture.
16. Recompare at the same state.
17. Stop after two or three rounds.
18. Run `visual-check.py` on this round before writing `qa.md`; link the ledger and check
    result in Coverage Matrix and carry each convention verdict into Findings or notes.
    Failure means the review did not run and `verdict: fail`. Pass only when the check passes
    and no P0-P2 remains.

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

| Item | Spec value | Built value | Result |
|---|---|---|---|

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
