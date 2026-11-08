---
allowed-tools: "mcp__claude_ai_Linear__* Read Write Glob"
---

# Create ADR

Creates an Architecture Decision Record as a Linear Document, optionally attached to a Project.

## Usage

```
/cct:linear-manage create-adr <title>
```

## Instructions

### Step 0: The repo file, when there is a repo

An ADR and an RFC live in two places, and the file is the source. If the working directory is a
repo carrying `sdlc.json`, write the document there **first**:

```
docs/designs/<YYYY-MM-DD>-adr-<slug>.md
```

Frontmatter: `title`, `type: adr`, `status`, `created`, `tags` and, when it replaces an earlier
decision, `supersedes` (and set the old file's `status: superseded` and `superseded_by`). Run
`python3 scripts/design_index.py write` when the repo has it. Commit it on the branch where the
decision is being made — the PR review is what makes it a decision rather than a note. Then
create the Linear document from the same text.

No `sdlc.json` and no `docs/designs/`? Skip this step; the Linear document is the whole record.

### Step 1: Gather context

Ask the user:
1. What decision was made? (1 sentence)
2. Attach to an existing project? (If yes, which one?)
3. Who were the decision makers?

If the user already provided context, skip to creation.

### Step 2: Create the Document

Use `create_document`:
- `title`: "ADR: [Title]"
- `project`: project name (if provided)
- `icon`: ":scales:"

### Step 3: Update with template

Use `update_document` with the ADR template from `references/adr-template.md`. Pre-fill:
- **Decision** section with what the user described
- **Decision makers** with the people mentioned
- **Date** with today's date
- **Status** as "Proposed" (or "Accepted" if the decision is already made)

### Step 4: Confirm

Show the user:
- Document link
- Suggest they fill in Context, Consequences, and Alternatives
