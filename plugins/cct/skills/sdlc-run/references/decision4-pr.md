# Write and read the Decision4 PR section

Read the repository's PR template, including its Decision4 writing-rules HTML comment,
and `boundary-map.yaml` before composing a body. Compute the highest changed-path floor
against the PR's actual base, across the entire diff. Use the highest applicable class;
record any lowering with from -> to, who authorized it and why. An intent or milestone's
approved class does not replace the PR's boundary-map floor.

Use exactly `### How hard is it to undo this PR after merging?` and one coloured circle
beside the chosen class: 🟢 Undo, 🟡 Repair, 🟠 Migrate or 🔴 Answer. Follow the class with a
specific sentence explaining what recovery needs beyond a revert. Do not write
"contained fix-up", repeat the sentence in steps, or invent steps to fit a class.

List **Recovery steps:** in order, numbered when there is more than one. Undo may use
only its sentence and omit steps. Include **Work preserved:** only when this change
actually keeps something recoverable; claim backups only with evidence in the PR.
**Responsible for recovery:** is a role; Answer requires a named person.
**Classification change:** is `None` unless the class changes; then say from -> to,
by whom and why. Choose one class per PR; split work requiring very different classes.

Read legacy fields as aliases: `Decision-Class` selects the class, `Put-right` means
Recovery steps, `Answerer` means Responsible for recovery (`Accountable person` is also
accepted), and `Class-Change` means Classification change. New bodies use the readable
section. Remove unfilled legacy placeholders when adopting that section; if a filled
legacy class is retained it must agree. HTML comments never supply a class or field.

Validate the proposed body before the first push, using the repository's checker and
own gate. The bundled checker needs Python and PyYAML; its inputs are `BODY` (body text),
`FILES` (path to newline-separated changed paths), and `MAP` (repo boundary-map path).
Use a body file and `gh pr create --body-file` / `gh pr edit --body-file`; revalidate the
actual body after creation or edits. Keep the repo's check invocation and required
statuses. `bash tests/decision4/run.sh` checks synthetic regression cases against a
fixture-only map; it never substitutes for validating this PR against repo policy.

Reviewers compare the declaration, recovery sentence, steps and responsibility with the
whole diff and map. A passing checker proves syntax and minimum fields, not the truth
of recovery or backup claims, ordered steps, authorization to lower a class, or a named
Answer owner. Report any mismatch. When feedback changes recovery requirements, update
this section and revalidate it before publishing success.

## Pull requests, issues and PR comments: scannable, never a text blob

- **Order:** `## What` → `## Why` → `## Proof` → `## Before merge` (only while something is open) → the repo's Decision4 section (only with `boundary-map.yaml`) → `## Decision record` (only at Migrate/Answer).
- **Bullets:** Every section is a list; start each bullet with a bold label (`- **Source plan:** 0 adds, 8 updates, 38 destroys.`). Keep one idea per bullet, at most two lines, and no paragraph longer than two sentences. Keep checklist syntax and bold-label the item.
- **Proof:** Name the check and result (`- **Unit tests:** 1,320 passed.`). Put links on the label or result, never a bare URL in prose. Preserve claims and human checklist attestations when restructuring an existing body.
- **Decision4:** When the repo has a boundary map, read it and copy the exact readable section from its PR template. Select its highest applicable class in bold with one colour circle and a sentence explaining recovery; use bold-labelled Recovery steps (numbered for multiple steps), optional Work preserved, Responsible for recovery (a named person at Answer), and Classification change. Keep the Recovery levels legend collapsed. Never author old plain `Decision-Class:` lines.
- **Decision record:** At Migrate/Answer use `## Decision record` with bold-labelled bullets: Chose, Over, Because, Commits us to. Never use “Repair, choice story:” headings; Repair needs no decision record.
- **Milestone and review text:** The same layout covers milestone-close PRs, issue bodies and PR comments. Put addressed feedback under What, its rationale under Why and its check results under Proof. A short thread reply can be one bold-labelled bullet; include only applicable sections.
- **Validation:** Validate the proposed body before pushing and the actual body after creation or edits through the repo's Decision4 gate when installed. Use `--body-file`; scannable formatting applies even without Decision4.

Read the full [scannable body example](pr-body.md), including the Decision record, before composing or editing a body.
