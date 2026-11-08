# Project Template

**Linear object:** Project
**Source:** this file. A Linear workspace template `Project Template` exists as a copy of it for
people filing by hand; edit this file first, then paste it across.
It carries two corrections to the deleted version, noted below.

**No EARS.** A project frames coordinated work. The behaviour is specified in its issues, and in
the PRD or RFC attached to it.

## MCP Steps

```
save_project:
  name: "<project name>"
  team: "<team>"
  summary: "<one line, max 255 chars>"
```

Then `save_project` again with `description` to add the body. Minimal first, content second.

## Template

```markdown
# [Project name]

> For coordinated work that needs more than one issue.

## Goal

> One sentence describing what this project delivers when it is complete.

[What will exist that does not exist now]

## Non-Goal

> One sentence describing what this project deliberately does not deliver, even though a reader
> might reasonably expect it to.

[What we are explicitly not doing here]

## Why this project

**Problem:** [What specific problem are we solving?]
**Success:** [How will we know this worked?]

## Scope

**In scope:**

- [Deliverable 1]
- [Deliverable 2]

**Out of scope:**

- [What we are not doing]
- [Future phase]

## Success Metrics

**Primary:** [The one metric that matters most]
**Secondary:** [One or two supporting metrics]

## Approach

**How we will build it:** [High-level technical approach]
**Key components:** [Main parts]
**Integrations:** [Existing systems this touches]

## Definition of Done

**Must have (M):**

- [ ] [Core requirement 1]
- [ ] [Core requirement 2]

**Should have (S):**

- [ ] [Important but not critical]

**Could have (C):**

- [ ] [Enhancement if time allows]

**Won't have (W):**

- [ ] [Explicitly out of scope this phase]

## Key Decisions

> Decisions taken while framing this project, each with a one-line reason. A decision that gets an
> ADR is linked here rather than restated.

- [Decision] — [why]

## Resources

- [Designs, PRD, RFC, ADRs — attach documents to the project rather than pasting them]

---

*This project breaks down into individual issues. Create one issue per piece of work.*
```

## Two corrections against the Linear version

1. **Non-Goal had the wrong prompt.** The Linear template repeats the Goal's instruction under
   Non-Goal ("One sentence describing what this project will deliver when complete"), which tells
   the author to write the Goal twice. Fixed above.
2. **Key Decisions was missing.** It came from this kit's earlier template and is worth keeping:
   it is where a reader finds why the project is shaped the way it is, without opening every ADR.

Both are fixed above, and in the Linear copy that was typed from this file on 2026-09-12.

## Why Non-Goal earns its own section

"Out of scope" lists work we are not doing. A Non-Goal names an *outcome* we are deliberately not
chasing, which is the thing stakeholders argue about three weeks in. They are different, and
folding one into the other loses the more expensive of the two.
