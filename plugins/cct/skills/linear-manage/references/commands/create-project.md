---
allowed-tools: "mcp__claude_ai_Linear__*"
---

# Create Project

Creates a Linear Project with structured description, native milestones, and team assignments.

## Usage

```
/cct:linear-manage create-project <name>
```

## Instructions

### Step 1: Gather context

Ask the user:
1. What's the goal of this project?
2. Which team(s) own it?
3. Who is the project lead?
4. Target completion date?
5. Does it belong to an initiative?

### Step 2: Create the project

Use `save_project` with minimal fields:
- `name`: project name
- `addTeams`: [team]

### Step 3: Update with details

Use `save_project` to add:
- `description`: use the Project template from `references/project-template.md`
- `lead`: the project lead
- `priority`: based on discussion
- `startDate`: today or specified date
- `targetDate`: target completion
- `addInitiatives`: if linked to an initiative
- `icon`: relevant emoji
- `state`: "Planned" or "Started"

Pre-fill the description template with whatever context the user provided. Include:
- Problem, scope (in/out), success metrics, key decisions

### Step 4: Create milestones (optional)

If the user described phases or milestones, create them using `save_milestone` — **never write milestones as text in the project description**.

```
save_milestone:
  project: "project-name"
  name: "Phase 1: Research"
  description: "What this phase delivers"
```

Do not add `targetDate` unless the user explicitly provides one.

### Step 5: Confirm

Show the user:
- Project link
- List of milestones created (if any)
- Any sections that need filling in
