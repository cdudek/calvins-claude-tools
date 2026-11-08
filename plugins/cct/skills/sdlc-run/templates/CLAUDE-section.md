

Verification and every push follow the [local-first contract](https://github.com/cdudek/calvins-claude-tools/blob/main/plugins/cct/skills/sdlc-run/references/local-first.md); read it before running checks or preparing a push.

## How work moves: the SDLC




This repo uses `cct:sdlc-run`, configured by `sdlc.json`. A change is one PR and one folder:
`{{CHANGES_DIR}}/<date>-<KEY>-<slug>/` (no key when there is no Linear issue). Designs that outlive
one PR live in `{{DESIGNS_DIR}}/`, one decision per file. Read `{{DESIGNS_DIR}}/INDEX.md` first and
open only the files it points you to; `python3 scripts/design_index.py write` after adding one.
The seven stages are Intent, UX plan,
Facts, Tech plan, Build, Milestone and Outcome.

The agent drafts intent, UX plan, facts and plan; the engineer confirms the intent, then all
three documents in one gate. After that every feature is built inside `/goal` as a PR into
`milestone/<slug>`, and ends on `python3 scripts/verify_gate.py feature <id>`. Each milestone
gets the heavy checks once, then one PR to its parent.

Branches:

```
<default> ─── milestone/<slug> ─── <feature branches>             one milestone
<default> ─── project/<slug> ─── milestone/<slug> ─── <features>  a project
```

A milestone branch stays local until its gate passes, then gets one push and one PR, merged
with a merge commit. Milestones are independent unless the plan says `needs:`. A project is
planning; a `project/<slug>` branch exists only when the engineer asked for one.

**The code is reviewed once, locally, at the milestone close** (Claude and Codex). Nothing
reviews in CI. Feature PRs into `milestone/*` and milestone PRs into `project/*` are interior
merges inside one change: no code owner, auto-merge on their checks alone.

{{#TIERS}}That PR is labelled by blast radius: `ask` needs a human, `show` and `ship` auto-merge on green.{{/TIERS}}{{#NO_TIERS}}There are no Ship/Show/Ask tiers here, so that PR auto-merges on green too.{{/NO_TIERS}}


New keys: `checks`, `milestones`, `projects`, `hotfix`, `goal`, `languages`, `responsiveTier`,
`ux`, `protected`. The reference is
**[{{DOCS}}]({{DOCS}})**.

## Verifying your work

    {{VERIFY}}

Run it before reporting done and before pushing. Use the linked targeted local failure loop; the full gate runs once on the final head before push. The Stop hook runs
`{{VERIFY_STOP}}` for dirty source files.

## Pull requests, issues and PR comments: scannable, never a text blob

- **Order:** `## What` → `## Why` → `## Proof` → `## Before merge` (only while something is open) → the repo's Decision4 section (only with `boundary-map.yaml`) → `## Decision record` (only at Migrate/Answer).
- **Bullets:** Every section is a list; start each bullet with a bold label (`- **Source plan:** 0 adds, 8 updates, 38 destroys.`). Keep one idea per bullet, at most two lines, and no paragraph longer than two sentences. Keep checklist syntax and bold-label the item.
- **Proof:** Name the check and result (`- **Unit tests:** 1,320 passed.`). Put links on the label or result, never a bare URL in prose. Preserve claims and human checklist attestations when restructuring an existing body.
- **Decision4:** When the repo has a boundary map, read it and copy the exact readable section from its PR template. Select its highest applicable class in bold with one colour circle and a sentence explaining recovery; use bold-labelled Recovery steps (numbered for multiple steps), optional Work preserved, Responsible for recovery (a named person at Answer), and Classification change. Keep the Recovery levels legend collapsed. Never author old plain `Decision-Class:` lines.
- **Decision record:** At Migrate/Answer use `## Decision record` with bold-labelled bullets: Chose, Over, Because, Commits us to. Never use “Repair, choice story:” headings; Repair needs no decision record.
- **Milestone and review text:** The same layout covers milestone-close PRs, issue bodies and PR comments. Put addressed feedback under What, its rationale under Why and its check results under Proof. A short thread reply can be one bold-labelled bullet; include only applicable sections.
- **Validation:** Validate the proposed body before pushing and the actual body after creation or edits through the repo's Decision4 gate when installed. Use `--body-file`; scannable formatting applies even without Decision4.

Full example for a repository whose boundary map requires Migrate (illustrative evidence, not claims to copy). Omit Before merge when nothing is open; omit both Decision4 sections entirely when the repo has no boundary map, and omit Decision record at Undo/Repair.

```markdown
## What

- **Change:** Move saved filters to the versioned format.
- **Requirement F1:** Existing filters remain readable during rollout.

## Why

- **Compatibility:** Clients need time to adopt the new format.

## Proof

- **Migration tests:** 12 passed, including reading the old format.
- **Local gate:** `scripts/ci-local --check` passed on the proposed head.

## Before merge

- [ ] **Owner review:** Confirm the rollout window.

### How hard is it to undo this PR after merging?

**🟠 Migrate** — Recovering requires moving saved filters back to the previous format before redeploying the old reader.

- **Recovery steps:**
  1. Pause writes and convert saved filters back with the reverse migration.
  2. Redeploy the previous reader and verify existing filters.
- **Work preserved:** The migration retains each original filter until rollout completes.
- **Responsible for recovery:** Service owner
- **Classification change:** None

<details>
<summary>Recovery levels</summary>

Undo — Revert only
Repair — Revert plus fixes or a release
Migrate — Move data, state, or users back
Answer — Cannot fully recover; a named person is accountable

</details>

## Decision record

- **Chose:** A versioned format with a reversible migration.
- **Over:** Replacing stored filters in place without a compatibility window.
- **Because:** Existing clients must keep reading their saved filters.
- **Commits us to:** Retain the reverse migration until rollout is verified.

🤖 Generated with Codex
```
