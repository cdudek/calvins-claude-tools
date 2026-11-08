---
allowed-tools: "mcp__claude_ai_Linear__*"
---

# Create Bug Report

Creates a structured bug report issue with reproduction steps, impact assessment, and acceptance criteria.

## Usage

```
/cct:linear-manage create-bug-report <summary>
```

## Instructions

### Step 1: Gather context

Ask the user:
1. What's broken? (expected vs actual behavior)
2. How do you reproduce it?
3. What's the severity? (Critical / Major / Minor / Cosmetic)
4. Which team?

If the user already described the bug in detail, extract the info and skip to creation.

### Step 2: Create the issue

Use `save_issue` with minimal fields:
- `title`: "Fix: [what's broken] in [where]"
- `team`: team name
- `priority`: 1=Critical, 2=Major, 3=Minor, 4=Cosmetic
- `labels`: ["bug"]

### Step 3: Update with structured description

Use `save_issue` to update with the bug report template from `references/bug-report-template.md`.

Pre-fill:
- Steps to reproduce from user input
- Expected vs actual behavior
- Environment details if provided
- Severity and impact assessment

### Step 4: Add metadata

Update the issue with:
- `project`: if this belongs to a project
- Additional labels for the affected area

### Step 5: Confirm

Show the user:
- Issue identifier and link
- Severity and priority
- Ask if reproduction steps are accurate
