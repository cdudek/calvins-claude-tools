---
allowed-tools: "mcp__claude_ai_Linear__*"
---

# Create Issue

Creates a structured, agent-ready issue in Linear that any developer or AI agent can pick up and execute.

## Usage

```
/cct:linear-manage create-issue <title>
```

## Instructions

### Step 1: Gather context

Ask the user:
1. What needs to be done? (the objective)
2. Which team?
3. Priority? (Urgent / High / Normal / Low)
4. Any specific files or codebase area?

If the user already described the task in detail, extract the info and skip to creation.

### Step 2: Create the issue

Use `save_issue` with minimal fields:
- `title`: Start with a verb — "Add ...", "Fix ...", "Refactor ...", "Update ..."
- `team`: team name
- `priority`: 1=Urgent, 2=High, 3=Normal, 4=Low

### Step 3: Update with structured description

Use `save_issue` to update with the agent-ready issue template from `references/issue-template.md`.

Write the description in the structured format:
- **Objective**: 1-2 sentences
- **Context**: codebase area, related files, dependencies
- **Requirements**: numbered, specific, testable
- **Acceptance Criteria**: Given/When/Then format
- **Technical Constraints**: if any
- **Out of Scope**: explicitly state what's excluded
- **Implementation Hints**: file paths, patterns to follow, test commands
- **Boundaries**: Always / Ask first / Never

### Step 4: Add metadata

Update the issue with:
- `labels`: appropriate type labels (feature, bug, improvement, etc.)
- `project`: if this belongs to a project
- `estimate`: if the team uses estimates

### Step 5: Confirm

Show the user:
- Issue identifier and link
- The structured description for review
- Ask if anything needs adjustment

## Examples

```
/cct:linear-manage create-issue "Add rate limiting to the public API"
```

```
/cct:linear-manage create-issue "Fix duplicate webhook events in Stripe integration"
```
