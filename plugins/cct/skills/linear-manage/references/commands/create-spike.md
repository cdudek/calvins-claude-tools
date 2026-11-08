---
allowed-tools: "mcp__claude_ai_Linear__*"
---

# Create Spike

Creates a time-bounded investigation ticket with a clear deliverable (PoC, RFC, ADR, or recommendation).

## Usage

```
/cct:linear-manage create-spike <question>
```

## Instructions

### Step 1: Gather context

Ask the user:
1. What question are we trying to answer?
2. What's the time box? (hours / days)
3. What should the deliverable be? (PoC, RFC, ADR, recommendation)
4. Which team?

If the user already described the spike in detail, extract the info and skip to creation.

### Step 2: Create the issue

Use `save_issue` with minimal fields:
- `title`: "Spike: [Question]"
- `team`: team name
- `priority`: based on urgency
- `labels`: ["spike"]

### Step 3: Update with structured description

Use `save_issue` to update with the spike template from `references/spike-template.md`.

Pre-fill:
- Question, time box, deliverable type
- Context and scope from user input
- Due date based on time box

### Step 4: Add metadata

Update the issue with:
- `dueDate`: calculated from time box
- `project`: if this belongs to a project

### Step 5: Confirm

Show the user:
- Issue identifier and link
- Time box and due date
- Expected deliverable
- Ask if anything needs adjustment
