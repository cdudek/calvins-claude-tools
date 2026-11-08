# Visual pass: inspect, then validate

Required whenever a UX run captures or judges images. The run owner is accountable for every
image, including images added by other passes. DOM inspection, source code, a screenshot path,
and the existence of a prototype are not visual evidence.

## 1. Open every image

1. Keep every captured screenshot under the run directory, normally `shots/`. Include every
   screen, state and width in scope, and open dialogs, menus, popovers and selects. Copy
   prototype and supplied reference images into `shots/prototype/` and `shots/reference/` when
   comparing them. Keep the originals; record their paths in the method notes.
2. Open **each file with the image-reading tool** (for example `Read` on the image or
   `view_image`). Inspect the returned pixels. Record the tool call reference in `opened_with`.
   A filename in a prompt or a DOM snapshot does not count. If an image cannot be opened,
   report the blocker; do not write a compliant row.
3. Inspect hierarchy, spacing and alignment, contrast and legibility, copy and terminology,
   and consistency between screens. Inspect the responsive layout at each captured width.
   Check empty, loading, error, disabled, selected and captured hover/focus states. Look for
   overlap, clipping, truncation, misalignment and wrong colours. Record concrete observations,
   including clean areas. Missing states are coverage gaps, not inferred passes.
4. Write one row per image in `<run>/visual.json` using the contract below. List each visible
   issue separately and tie it to that exact file. Measure uncertain values separately;
   pixels alone do not prove a contrast ratio, keyboard behaviour or an uncaptured state.
5. After recapture, open the replacement image again and update its row and digest. Retained
   before-images still need rows. Never reuse a row just because the filename stayed the same.

## 2. Validate every issue against our conventions

Read the product's documents, using configured paths from `docs/ux/setup.md` and `sdlc.json`.
Resolve `designsDir` (default `docs/designs`), read `<designsDir>/INDEX.md`, and open the relevant
ADR files whose `tags` include `ux`. Read `docs/ux/decisions.md` only where the old log still
exists. Also read the interaction guidelines and their routed pages, `DESIGN.md` / the adopted
design system, glossary, exceptions register (normally `docs/ux/exceptions.md`), and `PRODUCT.md`.
Record found paths and missing documents. A missing document never means compliance.

For **each** issue, choose exactly one verdict after reading the applicable rules:

| Verdict | Required evidence and disposition |
|---|---|
| `violates <document>#<section or decision id>` | Quote the exact convention line. Keep the finding and its screenshot in the fix list. Never call something a violation without that quote. |
| `allowed by <document>#<section or decision id>` | Quote the accepted decision or recorded exception permitting this exact situation. Remove it from the fix list and say so in the report notes; retain the issue in the ledger. List any `EX-<n>` used. |
| `no convention` | A real observed UX problem remains. Keep it as a finding, explain the user impact, and propose a rule or decision for `cct:ux-decision-log`. Never turn a general heuristic or reviewer taste into an invented product rule. |

Use `conflicts.md` to resolve precedence, scope and superseded decisions. Proposed rules,
out-of-scope exceptions and deferrals do not permit a defect. Resolve competing rules before
assigning the single verdict. A source quote must actually support the issue, not merely exist.
Apply these verdicts to visual issues from **all** passes before merging, not only this pass.
Code-only conformance findings use the same three verdicts, with their source evidence instead
of an invented screenshot.

## 3. Output and check

The ledger lives at `<run>/visual.json`, outside `passes/` so the findings merger never mistakes
it for a findings pass. Its `screenshots` array is the image table: one object per file, with
run-relative POSIX paths and viewport widths in CSS pixels. `observations` describes the visible
UX. `sha256` is the file's SHA-256 at inspection time (use Python's `hashlib`).

```json
{
  "screenshots": [
    {
      "file": "shots/settings-error-390.png",
      "screen_state": "Settings / error / 100% zoom",
      "width": 390,
      "opened_with": "Read image, tool call <actual call reference>",
      "sha256": "<64 hex characters for the opened bytes>",
      "observations": "Heading and fields align; the error label is clipped by the footer.",
      "verdict": "issues",
      "issues": [
        {
          "id": "VIS-001",
          "summary": "The footer hides the error label",
          "verdict": "violates DESIGN.md#error-states",
          "quote": "Error labels must remain fully visible."
        }
      ]
    }
  ]
}
```

`compliant` requires an opened image and an empty `issues` array. `issues` requires at least
one issue, each with `id`, `summary`, and one `verdict` string. An allowed issue stays in this
array even though it leaves the fix list. `violates` and `allowed by` require `quote`, a literal
line from the cited repo document, without added quotation marks. `no convention` requires a
`proposal` for `cct:ux-decision-log`. IDs are unique within the ledger.

Before any report, and again after recapture or a late pass adds images, run:

```bash
python3 "<cct plugin>/skills/ux-assessment-run/scripts/visual-check.py" "$run" --repo "$repo"
```

Resolve the script inside the installed **cct** plugin, not relative to another plugin's
cache. From review it is `${CLAUDE_SKILL_DIR}/scripts/visual-check.py`; from a sibling skill it
is `${CLAUDE_SKILL_DIR}/../ux-assessment-run/scripts/visual-check.py`. Python 3.10+ and image-reading
capability are prerequisites. A missing capability is a blocker.

The check inventories images recursively, rejects missing/duplicate/stale rows, missing issue
verdicts and missing or fabricated convention quotes. It fails on an empty capture set. Its
PASS means **coverage checked**, not “UX compliant”: findings still determine the UX verdict.
It cannot prove a tool call happened or that a quoted rule applies; the reviewer must inspect
the pixels and validate the rule. Never fabricate `opened_with` to satisfy the check.

**Any failure means “the review did not run”.** Fix and rerun, or report BLOCKED (build QA:
`fail`; spec gate: `not-ready`). Do not merge a clean report, claim compliance, approve a gate,
or treat a previous `VERIFY PASS` as overriding this failure. Code-only notes may still be
delivered, explicitly labelled incomplete. Do not delete screenshots to make the check pass.

## 4. Feed the existing reports

- Review: `$run/visual.json` and `$run/passes/visual.json`.
- Audit: `<scratch>/visual.json` and `<scratch>/passes/visual.json`, after independent
  evaluators finish. The run owner opens every shared screenshot and reconciles all issues.
- Standalone conformance or init: a fresh `${TMPDIR:-/tmp}/cct/<skill>/<run-id>/` run.
  Link its ledger and check result from the skill's report.
- Spec/prototype: `<spec>/visual/spec/<round>/`; link it from `validation.md`, `conformance.md`
  or `prototype/index.md`. Before images exist, report “text only; visual pass not yet run”.
  An explicitly skipped prototype is “not applicable” with its recorded reason, never compliant.
- Build QA: `<spec>/visual/build/<round>/`; link it from `qa.md`. Include both prototype and
  build images. Check each round separately; an earlier round cannot certify a later build.
- A nested skill may reuse its caller's run and ledger for unchanged images. Add new images
  and rows there, then rerun the check; never assume an earlier `qa.md` covers new pixels.

`passes/visual.json` uses `findings.schema.json`, `skill: visual`, `lens: conformance`.
Carry each retained issue's ID, exact screenshot in `evidence`, screen/state/width in `location`,
and verdict plus quote or decision proposal in `supporting_notes`. Put allowed issues and the
reason they left the fix list in `notes`. Record the ledger path and check result in `method`
and `notes`. Use `finding-format.md` for severity; “no convention” does not mean harmless.
Include clean image coverage in `passed`. Other reports carry the same information in their
existing findings and notes sections. Preserve the ledger alongside every delivered report.
Return the absolute run directory and checker script path to an SDLC caller. It passes these
as `verify_gate.py ... --visual-check "<checker>" --visual-run "<run>"` so the check runs again
inside the final gate and its failure appears in the gate report. Multiple runs use repeated
`--visual-run` flags. Keep run artifacts available until that gate finishes.
