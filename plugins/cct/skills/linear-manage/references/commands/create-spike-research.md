---
allowed-tools: "mcp__claude_ai_Linear__*"
---

# Create Research Note

Creates a research note as a Linear Document attached to the spike issue it came from.

## Usage

```
/cct:linear-manage create-spike-research <topic>
```

## Instructions

### Step 1: Fetch the canonical template

Read `references/spike-research-template.md`. It is the source — the Linear workspace template
was deleted on 2026-09-12, so do not call `get_template`.

### Step 2: Gather context

Ask the user:
1. Which spike issue did this research come from?
2. What were the questions, and what did you conclude?

### Step 3: Create the Document

Use `create_document`:
- `title`: "Research: [Topic]"
- `issue`: the spike issue id
- `icon`: ":microscope:"

Attach to the **issue**, never the project. The reader finds it on the spike.

### Step 4: Update with the template

Use `update_document` with the body from `references/spike-research-template.md`.

Fill the **Confidence** block honestly — high, medium and low. A note where everything is high
confidence is a note nobody can act on safely.

### Step 5: Route the outcome

Check the spike's Deliverable Type:
- **ADR** → run `/cct:linear-manage create-adr`
- **RFC** → run `/cct:linear-manage create-rfc`
- **Research Note** → this document is the outcome, nothing further
- **POC Report** → this document is the outcome, link the prototype

### Step 6: Confirm

Show the document link and the routed next step.
