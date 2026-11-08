---
name: Feature
about: Work an agent or a developer can pick up and execute without asking a question
labels: type/feature
---

## Why this matters

**User problem:** <what problem this solves, and in which context>
**User benefit:** <what users can do once this is built>

## Context

- **Codebase area:** `src/path/to/module/`
- **Related files:** `src/file1.ts`
- **Related issues:** #NNN

## Source of truth

> Inline the load-bearing constraints first, then link. A repo-relative doc path means nothing to a
> reader outside the checkout.

- <constraint the implementation must not violate>
- Full spec → <permalink pinned to a commit, or a Linear document URL>

## Requirements (EARS, one behaviour per line)

- **F1** When <trigger>, the system shall <response>.
- **F2** If <error condition>, then the system shall <response>.
- **N1** The system shall <non-functional property, with a number>.

## Acceptance criteria (Gherkin, optional per requirement)

> Only where the EARS line leaves a branch or an unhappy path ambiguous.

```gherkin
Scenario: <name> — proves F2
  Given <context with concrete data>
  When  <action>
  Then  <observable outcome, with a number where one exists>
```

## Scope

- **In:** <bullets>
- **Out:** <bullets>

## Implementation anchors

- Start at `src/path/to/file.ts:functionName`
- Follow the pattern in `src/existing/example.ts`

## Boundaries

- **Always:** run tests before marking done
- **Ask first:** schema changes, new dependencies, auth changes
- **Never:** modify tests to make them pass; touch unrelated modules; force-push

## Definition of Done

- [ ] `<exact verify commands>` exit 0
- [ ] Every requirement F1..Fn is covered by a named test
- [ ] No `[NEEDS CLARIFICATION]` marker is left in this issue

## Open questions

- [ ] [NEEDS CLARIFICATION: <question>] — do not guess these
