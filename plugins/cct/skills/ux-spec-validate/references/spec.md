# Spec Validation

## Purpose

Decide whether the design spec is ready for owner approval.
The output is the owner-readable gate summary.

## Inputs

- The size, skips and asks for the mode (the shared `spec-folder.md`, section 2).
- The change's `facts.md`, when present.
- `<spec>/brief.md`.
- `<spec>/ia.md`.
- `<spec>/interaction.md`.
- `<spec>/screens.md`.
- `<spec>/prototype/index.md`.
- `<spec>/conformance.md`.
- Prototype screenshots under `<spec>/prototype/`.
- the shared `laws-of-ux.md` and `lenses.md`.
- `usability-heuristics.md` from `cct:ux-assessment-run` (its `references/`).

## When It Runs: Twice, Loop First

1. **Spec loop, before the prototype.** Reviewers read the spec text: brief, IA,
   interaction, screens, conformance. There are no images yet; reviewer 3 critiques
   `<spec>/screens.md` and the state tables against the audience scenes and job stories. This pass
   runs as a `/goal` loop:

   ```
   /goal Validate <spec> as cct:ux-spec-validate spec. Each round: run the reviewers
   (independent, merged after all finish), fix every severity 3-4 finding and every contradiction
   between spec files in the spec, then re-check the fixes and look for contradictions the fixes
   made. Ask the owner open questions once, in one batch, each with a recommended answer. Done when
   <spec>/validation.md says verdict: ready (no open 3-4, no contradiction, every ask maps to a
   job story, a screen, and a fact, an out-of-scope line or, in standalone mode, an Ask Map line).
   ```

   The loop never draws images and never asks the owner to approve. It ends at `verdict: ready`,
   `status: draft`.
2. **Gate pass, after the prototype** (and, in sdlc mode, after `facts.md`). Do not re-run the
   full review. Open every prototype image with the image-reading tool and run the shared
   `visual-pass.md`, using `<spec>/visual/spec/<round>/` as the run. Check that the images match the validated spec (image loop result,
   `known-image-faults.md`), in sdlc mode that every fact cites an ask, and that no spec file
   changed since the loop. A spec change since
   then sends the change back to the loop. Then fill the Prototype Screenshots section and hand
   `<spec>/validation.md` to the owner gate.

## Steps

1. Check every activity is done or skipped with a reason.
2. Spawn the reviewers. Size L: three independent subagents in parallel. Size M: one
   subagent that runs the three lenses in turn, to keep the cost in proportion.
3. Do not let one reviewer see another reviewer's output before all finish.
4. Reviewer 1 checks Nielsen's ten with severity 0-4.
5. Reviewer 2 runs the shared `laws-of-ux.md` against the spec: every law, every check that a
   spec can answer. A spec has no pixels and no timings, so a check whose evidence codes are all
   S, I, T or M is `n/a: no build yet` unless the spec states the value (a count of options, a
   target size, a step count); a check with C or N runs on the spec text instead of the diff. Each law gets pass, fail or n/a, a
   failed check becomes a finding that cites its id (for example `L10.2`), and the reviewer
   returns the coverage table with all thirty rows and the B rows filled. Cognitive load is
   L5.
6. Reviewer 3 critiques the screen specs (loop pass) or the prototype screenshots (gate pass)
   against audience scenes and job stories.
7. Merge the reviews after all finish.
8. Apply the definition of ready.
9. Collect open questions.
10. Ask them once in one batch, each with a recommended answer.
11. Write each answer into the spec file it changes, quoted with its date.
    Re-run the checks that answer touches.
12. For the image gate, run `visual-check.py` from the shared `visual-pass.md` before writing
    `<spec>/validation.md`. Link the ledger and check result in Prototype Screenshots; carry
    the convention verdicts and quotes into Findings, allowed issues into Deliberate
    Inconsistencies, and uncovered problems into Decisions Needed. Failure is `not-ready`
    with “the review did not run” in Did Not Run.

## Definition Of Ready

| Check | Pass Rule |
|---|---|
| Activities | Every activity ran or was skipped with a reason. |
| Asks | Every ask maps to a job story, a screen, and a fact or out-of-scope line (sdlc mode) or an Ask Map line (standalone mode). |
| Findings | No open severity 3 or 4 finding remains. |
| Laws of UX | The coverage table has all thirty rows and the B rows filled; no row is blank. |
| Concerns | Every conformance concern is resolved or listed for the owner. |
| Questions | Every open question has a recommended answer. |
| Prototype | Gate pass only: every required image has been opened and has a checked visual row and convention verdicts; `visual-check.py` passed. Recorded skips are n/a, never compliant. Remaining faults are in `known-image-faults.md`. The loop pass writes `not yet: prototype follows`. |

## Output Template

Write `<spec>/validation.md`.

```markdown
---
type: validation
change: <id>
verdict: ready | not-ready
status: draft | approved
reviewed_by: null | <owner>
approved_at: null | YYYY-MM-DD
created: YYYY-MM-DD
---

# Validation

## Verdict

ready | not-ready

## Definition Of Ready

| Check | Result | Evidence |
|---|---|---|

## Asks To Screens To Facts

| Ask | Job story | Screen | State | Fact or out of scope |
|---|---|---|---|---|

## Prototype Screenshots

| Screen | State | 100 % | 150 % |
|---|---|---|---|

## Laws Of UX Coverage

| # | Law | Verdict | Failed checks | Evidence |
|---|---|---|---|---|

## Deliberate Inconsistencies

| Rule | Where | Why | Owner decision needed |
|---|---|---|---|

## Findings

| Severity | Location | Finding | Status |
|---|---|---|---|

## Decisions Needed

| Question | Recommended answer | Why it matters |
|---|---|---|

## Did Not Run

| Check | Reason |
|---|---|
```

## Checks

- Frontmatter keys are exactly `type`, `change`, `verdict`, `status`, `reviewed_by`, `approved_at`, and `created`.
- `verdict` is `ready` or `not-ready`.
- `status` starts as `draft`.
- The body can be read by the owner without opening reviewer notes.
- Questions are batched once.

## Skip Rule

Skip when the `validation` skip is set (the shared `spec-folder.md`, section 2).
The reason is already recorded; write no file.

## Optional Skills

Used only when installed; the activity runs fully without them.

- `cct:ux-ai-heuristics`.
- `cct:ux-usability-audit`.
- `cct:design-surface-review`.

Sources: github.com/openai/plugins · nngroup.com/articles/wireflows
