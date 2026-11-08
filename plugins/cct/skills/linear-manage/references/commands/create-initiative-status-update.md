---
allowed-tools: "mcp__claude_ai_Linear__*"
---

# Create Initiative Status Update

Posts a status update on a Linear Initiative, summarizing progress across projects, key results, and strategic direction.

## Usage

```
/cct:linear-manage create-initiative-status-update <initiative-name>
```

## Instructions

### Step 1: Identify the initiative

If the user didn't specify an initiative, use `list_initiatives` to find it. Confirm with the user if ambiguous.

### Step 2: Gather context

Ask the user:
1. What progress was made across projects this period?
2. Any changes to key results or targets?
3. Any strategic shifts or escalations?
4. What's the overall health? (on track / at risk / off track)

If the user already described progress in detail, extract the info and skip to creation.

### Step 3: Gather project statuses (optional)

Use `list_projects` filtered by the initiative to see current project health and progress. Use `get_status_updates` on each project to pull recent updates. This enriches the initiative update with concrete project-level detail.

### Step 4: Post the status update

Use `save_status_update` with minimal fields:
- `initiative`: initiative name
- `health`: "onTrack", "atRisk", or "offTrack"

### Step 5: Update with content

Use `save_status_update` to add the body using the template from `references/initiative-status-update-template.md`.

Pre-fill with:
- Project health summaries from step 3
- Key results progress
- Risks or strategic shifts the user mentioned

### Step 6: Confirm

Show the user:
- Status update link
- Health status
- Summary of project statuses included
- Ask if anything needs adjustment
