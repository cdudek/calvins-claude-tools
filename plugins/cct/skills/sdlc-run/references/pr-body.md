## Pull requests, issues and PR comments: scannable, never a text blob

- **Order:** `## What` → `## Why` → `## Proof` → `## Before merge` (only while something is open) → the repo's Decision4 section (only with `boundary-map.yaml`) → `## Decision record` (at Repair/Migrate/Answer).
- **Bullets:** Every section is a list; start each bullet with a bold label (`- **Source plan:** 0 adds, 8 updates, 38 destroys.`). Keep one idea per bullet, at most two lines, and no paragraph longer than two sentences. Keep checklist syntax and bold-label the item.
- **Proof:** Name the check and result (`- **Unit tests:** 1,320 passed.`). Put links on the label or result, never a bare URL in prose. Preserve claims and human checklist attestations when restructuring an existing body.
- **Decision4:** When the repo has a boundary map, read it and copy the exact readable section from its PR template. Select its highest applicable class in bold with one colour circle and a sentence explaining recovery; use bold-labelled Recovery steps (numbered for multiple steps), optional Work preserved, Responsible for recovery (a named person at Answer), and Classification change. Keep the Recovery levels legend collapsed. Never author old plain `Decision-Class:` lines.
- **Decision record:** Follow the shared Decision4 PR writing reference: Repair choice story; Migrate options or forced constraint; Answer labelled evidence and challenges with no recommendation. Omit at Undo.
- **Milestone and review text:** The same layout covers milestone-close PRs, issue bodies and PR comments. Put addressed feedback under What, its rationale under Why and its check results under Proof. A short thread reply can be one bold-labelled bullet; include only applicable sections.
- **Validation:** Validate the proposed body before pushing and the actual body after creation or edits through the repo's Decision4 gate when installed. Use `--body-file`; scannable formatting applies even without Decision4.

Full example for a repository whose boundary map requires Repair (illustrative evidence, not claims to copy). Omit Before merge when nothing is open; omit both Decision4 sections entirely when the repo has no boundary map, and omit Decision record at Undo.

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

## How hard is it to undo this PR after merging?

**🟡 Repair** — The team must correct stored filters and redeploy the compatible reader.

**Recovery steps**

1. Pause writes and convert saved filters back with the reverse migration.
2. Redeploy the previous reader and verify existing filters.
- **Work preserved:** The migration retains each original filter until rollout completes.
- **Responsible for recovery:** Service owner
- **Classification change:** None

<details>
<summary>Recovery levels</summary>

Undo — a revert puts it right
Repair — real work, contained to this team
Migrate — coordinated change involving other people
Answer — someone outside the team with standing to ask is affected, and nothing unmakes it

</details>

## Decision record

- **Chose:** A versioned format with a reversible migration.
- **Over:** Replacing stored filters in place without a compatibility window.
- **Because:** Existing clients must keep reading their saved filters.
- **Commits us to:** Retain the reverse migration until rollout is verified.

🤖 Generated with Codex
```
