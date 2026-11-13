<!--
Scannable layout: What, Why, Proof, Before merge (only if open).
Every section heading is H2. Sections use lists with bold labels; one idea per bullet, at most two lines.
Proof names each check and result. Links belong on labels or results.
Keep repo-specific requirements and human checklists; never tick human attestations.
-->
## What

- **Change:** <what changes for the user or system>
- **Issue:** Fixes <LINEAR-ID>

- **Excluded:** <what this PR deliberately does not do>

## Why

- **Reason:** <the problem and why this change resolves it>

## Proof

- **Local gate:** <verify command and actual result on this head>

- **Traceability:** One row per requirement from `changes/<id>/facts.md` or the issue; every requirement needs proof and every proof needs a requirement.

  | Requirement | Proof |
  |---|---|
  | F1 | `<test file> › <test name>` |
  | F2 | manual: <who checked, and how> |

## Before merge

<!-- Remove this section only when no checks or actions remain open. -->
- [ ] **Verify:** `<verify command>` exits 0.
- [ ] **Requirements:** Every `F`/`N` above has a proof in the table.
- [ ] **Clarifications:** No `[NEEDS CLARIFICATION]` marker is left in the change folder or issue.
