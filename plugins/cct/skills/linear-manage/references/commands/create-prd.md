---
allowed-tools: "mcp__claude_ai_Linear__*"
---

# Create PRD

Creates a Product Requirements Document as a Linear Document attached to a Project.

## Usage

```
/cct:linear-manage create-prd <product or feature name>
```

## Instructions

### Step 1: Fetch the canonical template

Read `references/prd-template.md`. It is the source — the Linear workspace template of that
name was deleted on 2026-09-12, so do not call `get_template`.

### Step 2: Gather context

Ask the user:
1. What is being built, in one sentence?
2. Which project does it belong to? (Create one if it does not exist.)
3. What is the north-star metric, and what is it today?

Skip anything the user already gave you.

### Step 3: Ensure the project exists

Use `save_project` with `name` and `team` only. Minimal first.

### Step 4: Create the Document

Use `create_document`:
- `title`: "PRD: [Product / Feature Name]"
- `project`: the project from Step 3
- `icon`: ":page_facing_up:"

### Step 5: Update with the template

Use `update_document` with the body from `references/prd-template.md`. When the problem is not yet
agreed, write page one only (Problem, Who it is for, Success metric, Non-goals) and leave the rest
of the template out: the document grows one section per product review (`cct:product-prd-write`).

**Write the Requirements section in EARS**, one numbered sentence per line, inside the MoSCoW
buckets. The grammar is in `cct:product-workitem-write` → `references/requirements-grammar.md`. Replace
every adjective with a number. Mark anything unresolved as `[NEEDS CLARIFICATION: <question>]`
rather than guessing it.

### Step 6: Confirm

Show the user the document link, and name which requirements are still marked
`[NEEDS CLARIFICATION]`.
