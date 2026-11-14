## Pull requests, issues and PR comments: scannable, never a text blob

- **Order:** `## What` → `## Why` → `## Proof` → `## Before merge` (only while something is open) → `## How hard is it to undo this PR after merging?` → `## Decision record` (Repair, Migrate and Answer only).
- **Bullets:** Every section is a list; start each bullet with a bold label (`- **Source plan:** 0 adds, 8 updates, 38 destroys.`). Keep one idea per bullet, at most two lines, and no paragraph longer than two sentences. Keep checklist syntax and bold-label the item.
- **Proof:** Name the check and result (`- **Unit tests:** 1,320 passed.`). Put links on the label or result, never a bare URL in prose. Preserve claims and human checklist attestations when restructuring an existing body.
- **Decision4 (advisory):** Copy the section from the repo's PR template. Pick one level (🟢 Undo, 🟡 Repair, 🟠 Migrate, 🔴 Answer) at or above the lowest level `boundary-map.yaml` gives the changed paths; unsure, take the higher. Give concrete recovery steps and who is responsible. Nothing checks it and it never blocks a merge.
- **Decision record:** Only above Undo, as `AGENTS.md` says: Repair names what was chosen, over what, why and what it commits us to; Migrate lists at least two options; Answer lists facts marked observed, inferred, asked or unknown and recommends nothing.
- **Milestone and review text:** The same layout covers milestone-close PRs, issue bodies and PR comments. Put addressed feedback under What, its rationale under Why and its check results under Proof. A short thread reply can be one bold-labelled bullet; include only applicable sections.
- **Validation:** Validate the proposed body before pushing and the actual body after creation or edits against these rules. Use `--body-file`.

Full example for a Repair change (illustrative evidence, not claims to copy). Omit Before merge when nothing is open, and omit Decision record at Undo.

```markdown
## What

- **Change:** Move saved filters to the versioned format.
- **Requirement F1:** Existing filters remain readable during rollout.

## Why

- **Compatibility:** Clients need time to adopt the new format.

## Proof

- **Migration tests:** 12 passed, including reading the old format.
- **Checks:** The repo's verify command passed on the proposed head.

## Before merge

- [ ] **Owner review:** Confirm the rollout window.

## How hard is it to undo this PR after merging?

**🟡 Repair** — The team must correct stored filters and redeploy the compatible reader.

**Recovery steps**

1. Convert saved filters back with the reverse migration.
2. Redeploy the previous reader and check that existing filters load.

- **Responsible for recovery:** Service owner

## Decision record

- **Chose:** A versioned format with a reversible migration.
- **Over:** Replacing stored filters in place without a compatibility window.
- **Because:** Existing clients must keep reading their saved filters.
- **Commits us to:** Keeping the reverse migration until rollout is verified.

🤖 Generated with Codex
```
