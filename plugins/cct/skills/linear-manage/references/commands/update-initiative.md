---
allowed-tools: "mcp__claude_ai_Linear__*"
---

# Update Initiative

Updates an existing Linear Initiative's description, status, owner, or target date.

## Usage

```
/cct:linear-manage update-initiative <initiative-name>
```

## Instructions

### Step 1: Find the initiative

Use `list_initiatives` or `get_initiative` to find the initiative. Confirm with the user if ambiguous.

### Step 2: Show current state

Display the current initiative details:
- Description (or note if empty)
- Status, owner, target date
- Linked projects

### Step 3: Gather changes

Ask the user what they want to update. Common updates:
- Description (use template from `references/initiative-template.md` if starting fresh)
- Key results (add, modify, or mark complete)
- Status (Planned → Active → Completed)
- Owner
- Target date
- Add/remove project links

### Step 4: Apply updates

Use `save_initiative` to update the fields:
- `description`: updated content
- `status`: new status if changed
- `owner`: new owner
- `targetDate`: new target date
- `icon`: if changing

### Step 5: Confirm

Show the user:
- What was changed
- Initiative link
- Any sections still needing content
