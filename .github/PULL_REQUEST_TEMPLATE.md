<!--
Scannable layout: What, Why, Proof, Before merge (only if open), then How hard is it to undo and the Decision record (Decision4, advisory).
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

<!-- Decision4 is advisory, not a merge gate. Rules: AGENTS.md. Plain words; write the fact instead of citing a PR, issue or Linear number. -->
## How hard is it to undo this PR after merging?

**🟡 Repair** — <one sentence: what goes wrong if this is wrong, and who fixes it>

**Recovery steps**

1. <first concrete step>
2. <next step>

- **Responsible for recovery:** <role; at Answer, a named person>

## Decision record

<!-- Undo: delete this section. Repair: the four bullets below. Migrate: at least two options, each with what it commits us to, and who chose. Answer: facts marked observed / inferred / asked / unknown, open questions, no recommendation. -->

- **Chose:** <what was decided>
- **Over:** <the real alternative>
- **Because:** <the reason>
- **Commits us to:** <what this ties us to>

<details>
<summary>Levels</summary>

🟢 Undo — a revert fixes it
🟡 Repair — real work, only this team
🟠 Migrate — other teams or people must change something
🔴 Answer — someone outside the team is affected and it cannot be unmade

</details>
