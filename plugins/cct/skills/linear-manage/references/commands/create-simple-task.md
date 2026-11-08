---
allowed-tools: "mcp__claude_ai_Linear__*"
---

# Create Simple Task

Creates a small, unambiguous issue with no requirement grammar.

## Usage

```
/cct:linear-manage create-simple-task <what needs doing>
```

## Instructions

### Step 1: Check it is actually simple

Use this command only when the change can be described in one sentence and that sentence leaves
nothing open.

Switch to `/cct:linear-manage create-issue` if any of these is true:
- the change has a branch, a state, or an unhappy path worth naming
- more than one file of behaviour changes
- a person would have to ask a question before starting
- it goes to an agent that cannot ask

The test is ambiguity, not size.

### Step 2: Create the issue

Use `save_issue` with `title`, `team` and `priority`. Then update with the body from
`references/simple-task-template.md`.

Do **not** add EARS requirements or Gherkin scenarios. That is the point of this template.

### Step 3: Confirm

Show the issue link.
