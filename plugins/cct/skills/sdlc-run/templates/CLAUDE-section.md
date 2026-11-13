

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

- **Order:** `## What` → `## Why` → `## Proof` → `## Before merge` (only while something is open).
- **Bullets:** Every section is a list; start each bullet with a bold label (`- **Source plan:** 0 adds, 8 updates, 38 destroys.`). Keep one idea per bullet, at most two lines, and no paragraph longer than two sentences. Keep checklist syntax and bold-label the item.
- **Proof:** Name the check and result (`- **Unit tests:** 1,320 passed.`). Put links on the label or result, never a bare URL in prose. Preserve claims and human checklist attestations when restructuring an existing body.
- **Milestone and review text:** The same layout covers milestone-close PRs, issue bodies and PR comments. Put addressed feedback under What, its rationale under Why and its check results under Proof. A short thread reply can be one bold-labelled bullet; include only applicable sections.
- **Validation:** Validate the proposed body before pushing and the actual body after creation or edits against these rules. Use `--body-file`.

Full example (illustrative evidence, not claims to copy). Omit Before merge when nothing is open.

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

🤖 Generated with Codex
```
