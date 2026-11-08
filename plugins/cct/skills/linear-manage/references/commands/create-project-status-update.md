---
allowed-tools: "mcp__claude_ai_Linear__*"
---

# Create Project Status Update

Posts a status update on a Linear Project, summarizing progress, risks, and next steps.

## Usage

```
/cct:linear-manage create-project-status-update <project-name>
```

## Instructions

### Step 1: Identify the project

If the user didn't specify a project, use `list_projects` to find it. Confirm with the user if ambiguous.

### Step 2: Gather context

Ask the user:
1. What was accomplished this period?
2. Any risks or blockers?
3. What's the overall health? (on track / at risk / off track)

If the user already described progress in detail, extract the info and skip to creation.

### Step 3: Gather recent activity (optional)

Use `list_issues` filtered by the project to find recently completed and in-progress issues. Use this to enrich the update with concrete deliverables.

### Step 4: Post the status update

Use `save_status_update` with minimal fields:
- `project`: project name
- `health`: "onTrack", "atRisk", or "offTrack"

### Step 5: Update with content

Use `save_status_update` to add the body using the template from `references/project-status-update-template.md`.

Pre-fill with:
- Completed items from recent issues
- Risks/blockers the user mentioned
- Next period priorities

### Step 6: Confirm

Show the user:
- Status update link
- Health status
- Summary of what was included
- Ask if anything needs adjustment
