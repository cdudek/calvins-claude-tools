# Generalize and Sweep

When an issue is found in one location, check if the same issue applies elsewhere.

## Sweep Types

### Pattern sweep
Given an abstract principle from one finding, check if the same pattern applies elsewhere.
1. Extract the root cause abstractly (from root-cause-analysis): not "add :gamma here" but "all multi-iteration tests must include a representative value from each distinct equivalence class"
2. Define a structural predicate: "does this code satisfy P?"
3. Check each location matching the structural signature within scope

### Impact sweep
Given a known change (API rename, removed parameter, behavior change), find all affected call sites.
1. Identify the changed interface or symbol
2. Search for all usages within scope
3. For each usage: does it rely on the old behavior?

## Scope

The consuming skill specifies the scope:

| Scope | What's checked | Typical use |
|---|---|---|
| `diff` | Only lines in the PR/branch diff | review-feedback-run, fix-flaky |
| `files` | All changed files fully (not just diff lines) | reviewer |
| `system` | Broader codebase following imports and call chains | dependabot, reviewer files |

## Systemic patterns

If the pattern appears systemic beyond the current scope, flag it for the user to decide whether to expand the sweep rather than silently expanding scope.

## Output

Mark each finding as:
- **INSTANCE** — unique to one location
- **PATTERN** — same root cause in multiple locations; list all affected locations and treat as a single compound fix
