---
allowed-tools: "mcp__claude_ai_Linear__*"
---

# Update Project

Updates an existing Linear Project's description, dates, team, priority, or status.

## Usage

```
/cct:linear-manage update-project <project-name>
```

## Instructions

### Step 1: Find the project

Use `list_projects` or `get_project` to find the project. Confirm with the user if ambiguous.

### Step 2: Show current state

Display the current project details:
- Description (or note if empty)
- Status, priority, dates
- Lead, teams
- Linked initiatives

### Step 3: Gather changes

Ask the user what they want to update. Common updates:
- Description (use template from `references/project-template.md` if starting fresh)
- Target date or start date
- Status (Planned → Started → Completed)
- Priority
- Lead or team assignments
- Add/remove initiative links

### Step 4: Apply updates

Use `save_project` to update the fields:
- `description`: updated content
- `state`: new state if changed
- `priority`: new priority if changed
- `targetDate` / `startDate`: new dates
- `lead`: new lead
- `addTeams` / `removeTeams`: team changes
- `addInitiatives` / `removeInitiatives`: initiative links

### Step 5: Confirm

Show the user:
- What was changed
- Project link
- Any sections still needing content
