---
allowed-tools: "mcp__claude_ai_Linear__*"
---

# Create Initiative

Creates a Linear Initiative representing a strategic goal that spans multiple projects.

## Usage

```
/cct:linear-manage create-initiative <name>
```

## Instructions

### Step 1: Gather context

Ask the user:
1. What's the strategic goal?
2. Who owns this initiative?
3. Target date?
4. Is this a sub-initiative of something larger?
5. What key results define success?

### Step 2: Create the initiative

Use `save_initiative` with minimal fields:
- `name`: initiative name (frame as an outcome, e.g., "Reduce Churn by 20%" not "Churn Project")

### Step 3: Update with details

Use `save_initiative` to add:
- `description`: use the Initiative template from `references/initiative-template.md`
- `status`: "Planned" or "Active"
- `owner`: the initiative owner
- `targetDate`: target completion
- `parentInitiative`: if this is a sub-initiative
- `icon`: relevant emoji (e.g., ":dart:", ":chart_with_upwards_trend:")

Pre-fill the description with:
- Vision, strategic context, key results, project table, timeline, owner

### Step 4: Link existing projects (optional)

If the user mentions existing projects that belong under this initiative, use `save_project` to add the initiative link:
- `addInitiatives`: [initiative name]

### Step 5: Confirm

Show the user:
- Initiative link
- Key results summary
- Linked projects (if any)
