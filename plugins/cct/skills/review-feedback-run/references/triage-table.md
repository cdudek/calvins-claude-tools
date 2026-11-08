---
description: Triage table format, classification rules, and user override syntax
---

# Triage Table

Present a single flat-numbered table with investigated items. Actions come from investigation — the user can override any action. A caller may prepend a context header before the table — e.g. a `## PR #{number}` block above these rows; render it first when the caller supplies one.

```
 #  | Category            | Behavior (what should happen)                                   | Diagnosis (why it's broken)                          | Action
----|---------------------|-----------------------------------------------------------------|------------------------------------------------------|---------------
 1  | [security] INSTANCE | query builder escapes user input                                | unescaped interpolation in WHERE clause              | INVESTIGATE
 2  | [logic/sort] PATTERN| swapping declarations moves leading comments with them          | source_range excludes comments (2 locations)         | ADD TEST
 3  | [test coverage]     | test covers edge case with 3+ items                             | reviewer suggests adding a test — targets test file  | ADD TEST
 4  | [convention]        | variable name matches project conventions                       | reviewer suggests rename for clarity                 | SKIP
 5  | [scope]             | extract helper into shared module                               | defer to follow-up PR                                | DEFER → Linear

Select actions (e.g. "1-5", "all", "2,3 fix rest skip"):
```

## Classification Rules

Triage classification rules are defined in `../../role-review-vocabulary/SKILL.md` (see Triage Classification Rules section).

## User Overrides

The user can override any action inline:
- `"3 fix"` overrides the suggested action for item 3 to FIX
- `"5 skip"` downgrades item 5 to SKIP
- `"all"` accepts all suggested actions
- `"1-3,5"` selects items 1, 2, 3, and 5 with their suggested actions
- `"2,3 fix rest skip"` sets items 2 and 3 to FIX, all others to SKIP

Wait for user selection before proceeding to execution.
