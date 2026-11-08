---
allowed-tools: "mcp__claude_ai_Linear__* Read Write Glob"
---

# Create RFC

Creates an RFC as a Linear Project with an attached Document using the structured RFC template.

## Usage

```
/cct:linear-manage create-rfc <title>
```

## Instructions

### Step 0: The repo file, when there is a repo

An ADR and an RFC live in two places, and the file is the source. If the working directory is a
repo carrying `sdlc.json`, write the document there **first**:

```
docs/designs/<YYYY-MM-DD>-<slug>.md
```

Frontmatter: `status` and, when it replaces an earlier decision, `supersedes`. Commit it on the
branch where the decision is being made — the PR review is what makes it a decision rather than a
note. Then create the Linear document from the same text.

No `sdlc.json` and no `docs/designs/`? Skip this step; the Linear document is the whole record.

### Step 1: Gather context

Ask the user:
1. What is the RFC about? (1-2 sentences)
2. Which team owns it?
3. Who are the reviewers?

If the user already provided enough context, skip straight to creation.

### Step 2: Create the Project

Use `save_project` with minimal fields:
- `name`: "RFC: [Title]"
- `addTeams`: [team]
- `state`: "Planned"

### Step 3: Update the Project

Use `save_project` to add:
- `icon`: ":memo:"
- `description`: Short one-liner about the RFC purpose

### Step 4: Create the Document

Use `create_document`:
- `title`: "RFC: [Title]"
- `project`: the project name from Step 2

### Step 5: Update Document with template

Use `update_document` with the RFC template from `references/rfc-template.md`. Pre-fill any sections the user already provided context for. Leave the rest as structured placeholders.

### Step 6: Confirm

Show the user:
- Project link
- Document link
- Which sections are pre-filled vs need attention
