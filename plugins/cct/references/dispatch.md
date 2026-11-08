# Dispatch: which passes a change needs

Read by `cct:ux-assessment-run` before it starts any reviewer, and by anything else that composes
passes. A copy-only PR does not need the responsive or motion passes; a new screen needs all of
them. The matrix decides, so the choice is the same on every review and every round.

Every pass returns one JSON file in the shape of `findings.schema.json`. The scripts in
`skills/ux-assessment-run/scripts/findings.py` validate, merge, render and compare those files. Do not type
the report by hand.

## 1. The passes today

| Pass (the `skill` value it writes) | What runs | Lens values it uses |
|---|---|---|
| `documents` | The orchestrator itself: looks for the design documents (review step 2) | `documents` |
| `visual` | The orchestrator opens every image and validates each issue with `visual-pass.md`; checks `<run>/visual.json` before reporting | `conformance` |
| `conformance` | `cct:ux-rules-validate` against whatever documents exist | `conformance` |
| `laws` | Every law in `laws-of-ux.md` on every changed screen and state, plus B1-B14 | `laws` |
| `ux-usability-reviewer` | `cct:ux-usability-reviewer` in `MODE: review` | any |
| `heuristics` | Nielsen's ten and the dark patterns from `skills/ux-assessment-run/references/usability-heuristics.md` | `heuristics` |
| `accessibility` | `cct:ux-accessibility-audit` (WCAG 2.2) and the accessibility block of `checklist.md` | `wcag` |
| `lenses` | Shneiderman, Maze, the six questions, the rest of `checklist.md`, `writing.md` | `lenses`, `writing` |
| `responsive` | `cct:ux-responsive-audit`: code audit always, viewport shots when a server is up | `responsive` |
| `e2e-coverage` | Read-only search of the e2e suite for specs that exercise the changed surfaces | `e2e-coverage` |
| `sitemap` | `cct:ux-sitemap-create diff base:<base ref>`: the head's routes against the base's | `sitemap` |
| `spec` | `cct:ux-spec-validate build <change>`, when the change has a spec folder | `spec` |

## 2. Always run

These four run on every UX review, whatever the change. The owner required them; the matrix
can add passes, never remove these.

- **`documents`.** Every review looks for the design documents and reports each missing one,
  so a review that never found the rules cannot claim the change follows them.
- **`visual`.** Open every screenshot with the image-reading tool, write the image ledger and
  the three-way convention verdicts from `visual-pass.md`. Run `visual-check.py` before merge.
  Failure blocks the review; it cannot be demoted to an optional pass that did not run.
- **`conformance`.** Against missing guidelines it still checks the glossary and the design
  system, and lists the rule checks it could not run under `did_not_run`.
- **`laws`.** All thirty laws and B1-B14 on the changed screens, each one passed, failed, not
  applicable or did not run. Its file must pass
  `findings.py validate <file> --expect L1-L30,B1-B14`; a law nobody accounted for is a blank
  coverage row, and the file is re-dispatched.

## 3. The matrix

Find every row the change matches; the passes to run are the always-run set plus the union of
those rows. `x` means run. A change that matches no row, or that you are unsure about, runs
everything.

| The change touches | ux-usability-reviewer | heuristics | accessibility | lenses | responsive | e2e-coverage | sitemap |
|---|---|---|---|---|---|---|---|
| Words only (strings, locale files, no markup or layout) | | | | x | | | |
| A route: new, renamed, moved or removed page, navigation, page header | x | x | x | | | x | x |
| A form, a create or edit flow | x | x | x | x | x | x | |
| A table, list, filter, sort or bulk action | x | x | x | x | x | x | |
| An overlay: dialog, side panel, menu, popover, select | x | x | x | | x | x | |
| Visual only: tokens, colour, type, spacing, icons | x | | x | | x | | |
| A money, consent, access or mail action | x | x | x | x | x | x | |
| Motion: transitions, animation, loading indicators | x | | x | | | | |
| A new screen | x | x | x | x | x | x | x |

- `spec` runs whenever the change has a spec folder, whatever the row.
- `sitemap` writes its checks (`SM-<n>`, `RC-<n>`) as findings; a moved address with no
  redirect is at least High, as `cct:ux-sitemap-create` says.
- The rows follow "Which laws matter most, by what changed" in `laws-of-ux.md`; that table
  says where the `laws` pass looks hardest first, this one says which other passes run.

## 4. What every pass is told

Never paste a skill's or a reference's body into the prompt; name it and let the pass read it.
Each pass gets:

1. Its name from section 1 and the task: the PR, the interface files, the screenshots folder,
   the documents table, and `finding-format.md` for how to write each field.
2. The scope it must cover and the rules that apply (`conflicts.md` for rungs and exceptions).
3. The output path, `<run>/passes/<pass>.json`, and the instruction: "Write ONLY JSON matching
   `findings.schema.json`. Put every criterion you checked and found clean in `passed`, every one
   that does not apply in `not_applicable` with the rule that excludes it, and everything you
   could not check in `did_not_run` with the reason. Then run `findings.py validate` on your
   file and fix it until it passes."
4. Do not report what you would mark speculative, unless it would be Critical; then report it
   with `verified: assumption`. The merge never drops a finding, so the pass decides.
5. Open every screenshot you judge with the image-reading tool. Give the orchestrator the
   exact paths, observations and issue verdicts from `visual-pass.md`. Save additional captures
   inside the same run so the final inventory includes them.

A pass whose file is missing or fails `validate` is re-dispatched once with the errors. If it
fails again, it goes under `did_not_run` in the orchestrator's own file with the reason, never
silently. Exception: a missing or invalid `visual` pass blocks the review; never drop it.
A pass that ran without its agent (for example `ux-usability-reviewer` run from `lenses.md`)
sets `degraded` to say so, and the report prints a banner.

## 5. The orchestrator's own files

The review writes two files itself, before any reviewer starts.

`<run>/passes/00-review.json` (`skill: review`): the scope, `method` for how the build was seen
(running build, or code only and why), every pass the matrix did not pick under `did_not_run`
with the reason `not dispatched: <row>` (so a clean report never looks like nobody looked), and
every pass that could not load.

`<run>/passes/documents.json` (`skill: documents`), one id per document: `DOC-guidelines`,
`DOC-glossary`, `DOC-design-system`, `DOC-decisions`, `DOC-exceptions`, `DOC-product`.

- Found: the id goes in `passed`, and a note gives its path (`DOC-glossary: docs/ux/glossary.md`).
- Missing: a finding with that id, `lens: documents`, `impact: Medium`, `rung: R4`,
  `verified: code`, `location: repository root`, the paths searched as `evidence`, what could
  not be checked without it as `current`, and `cct:ux-setup` as the `recommendation`. A missing
  document is reported on every review until it exists, and the round comparison shows it
  Fixed the day it is created.
