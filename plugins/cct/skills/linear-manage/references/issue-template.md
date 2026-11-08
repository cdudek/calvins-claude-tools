# Agent-Ready Issue Template

**Linear object:** Issue
**Merged from:** the Linear workspace template "Feature Issue Template" (the human-facing frame)
and this kit's agent-ready body. The whole thing is owned here; the Linear `Feature Issue`
template is a copy typed from this file on 2026-09-12.

**Requirements are EARS, acceptance criteria are optional Gherkin.** The grammar lives in
`../sdlc-run/references/requirements-grammar.md`. Read it before filling sections 3
and 4. Do not restate the patterns here.

The point of this template: an agent or a developer picks the issue up and executes without asking
a question. Every section below exists because its absence produced a wrong implementation.

## MCP Steps

```
save_issue:
  title: "[Verb] [what] [where]"
  team: "team-name"
  priority: 3
  labels: ["type/feature"]
```

Then update with the structured description.

## Template

```markdown
## Why this matters

**User problem:** [What problem does this solve, and in which context?]
**User benefit:** [What can users do once this is built?]

## Context

- **Codebase area:** `src/path/to/module/`
- **Related files:** `src/file1.ts`, `src/file2.ts`
- **Dependencies:** [packages or services involved]
- **Related issues:** LIN-XXX, LIN-YYY

## Source of truth

> Inline the load-bearing constraints first, then link. A repo-relative doc path resolves to
> nothing for a reader outside the checkout.

- [Inlined constraint that the implementation must not violate]
- Full spec → [GitHub permalink pinned to a commit, or a Linear document URL]

## Requirements (EARS, one behaviour per line)

- **F1** When [trigger], the system shall [response].
- **F2** If [error condition], then the system shall [response].
- **N1** The system shall [non-functional property, with a number].

## Acceptance criteria (Gherkin, optional per requirement)

> Add a scenario only where the EARS line leaves a real ambiguity, a branch, or an unhappy path.
> A scenario that restates its requirement is noise.

Scenario: [name] — proves F2
  Given [context with concrete data]
  When  [action]
  Then  [observable outcome, with a number where one exists]

## Technical notes

- [Implementation approach, constraint, or consideration worth knowing up front]
- Must not break existing API contracts
- Must stay backward compatible with [version]

## Scope

- **In:** [bullets]
- **Out:** [bullets — this is what prevents scope drift and over-building]

## Implementation anchors (in-repo, for the coding agent)

- Start at `src/path/to/file.ts:functionName`
- Follow the pattern in `src/existing/example.ts`
- Verify with `npm test -- --grep "relevant suite"`

> Strong heuristics, not a dictated algorithm. Over-specifying the how is as damaging as leaving
> the what vague.

## Boundaries

- **Always:** run tests before marking done; follow repo conventions
- **Ask first:** schema changes, new dependencies, auth changes
- **Never:** modify tests to make them pass; touch unrelated modules; force-push

## Definition of Done

- [ ] `[exact verify commands]` pass, e.g. `pnpm typecheck && pnpm lint && pnpm test`
- [ ] Every requirement F1..Fn is covered by a test, named in the test or the PR
- [ ] Every Gherkin scenario passes, unhappy paths included
- [ ] No `[NEEDS CLARIFICATION]` marker is left in this issue

## Resources

**Design:** [Figma link if available]
**Open questions:** [NEEDS CLARIFICATION: <question>] — the agent must not guess these

```

## Why this format works for agents

| Element | Purpose |
|---|---|
| Why this matters | Grounds the reader in the outcome, and reads as a proper issue to the PM |
| Codebase area and files | The agent knows where to look instead of searching |
| Requirements (EARS, numbered) | One universal rule per line, with a handle a test can name |
| Acceptance criteria (Gherkin, optional) | The concrete case, where the rule alone is ambiguous |
| Scope, Out | Prevents scope creep, which is the most common agent failure |
| Implementation anchors | Cuts exploration time without dictating the algorithm |
| Boundaries | Three tiers, because "do not" in prose gets prompted away |
| `[NEEDS CLARIFICATION]` | The only mechanism that stops a silent guess |

## What this template does not do

Irreversible and security-relevant limits must be enforced **outside** the issue text. Text in a
ticket can be ignored or argued away; a branch protection rule, a hook or a CI gate cannot. The
Boundaries section is a reminder, never the enforcement.
