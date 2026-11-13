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
