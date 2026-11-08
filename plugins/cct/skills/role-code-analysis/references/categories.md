# Issue Categories

Classify findings using these categories. Priority order depends on context — see the context table below.

Canonical *naming* of dimensions used in finding `dimension:` fields lives in `../../review-code-run/references/dimensions.md`. This file owns the priority matrix; that file owns the names. When the two diverge, prefer the dimension name from `dimensions.md` for the `dimension:` field; use the category name from this file for priority routing.

## Categories

### Security (blocking)
Injection, auth bypass, secrets exposure, mass assignment, OWASP Top 10. Hardcoded API keys, tokens. Missing input validation at system boundaries. Covers the finer-grained `auth` and `authz` dimensions from `dimensions.md`:
- **auth** — session/login/credential flow (login, OAuth, JWT, session cookies).
- **authz** — policies, permission checks, role gates (Pundit/CanCan policies, GraphQL field resolvers).

### Logic & Correctness (blocking)
Bugs, race conditions, edge cases, null handling, off-by-one errors. Broken error handling (swallowed exceptions, missing catches). State mutations causing side effects.

### Design & Structure
Coupling, cohesion, SRP violations, abstraction leaks, layering violations, god functions (>50 lines of logic), deep nesting (>3 levels).

### Complexity & Maintainability
Cognitive complexity, misleading names, unclear intent, functions doing more/less than their name suggests.

### Performance
N+1 queries, missing indexes, blocking operations, memory issues. O(n²) in hot paths, repeated DB calls in loops. Includes the `db-access` and `graphql` dimensions from `dimensions.md`:
- **db-access** — migrations, models, raw SQL, ActiveRecord queries (N+1, missing indexes, unsafe migration patterns like NOT NULL without backfill).
- **graphql** — `app/graphql/**`, schema files (field-level authz, query complexity/depth, N+1 in resolvers, batching, breaking schema changes).

### Dead Code & Redundancy
Unused functions, unreachable branches, duplicated logic. Pattern violations (using raw API calls where a client exists).

### Test Quality
Coverage gaps for new logic. Missing edge case tests. Tests that don't assert meaningful behavior. Behavior vs implementation testing.

### Style & Conventions
Naming inconsistencies, code style, linter compliance. For file-focused reviews: only flag what linters cannot (misleading patterns, inconsistent naming). Skip formatting, import order, whitespace.

### Project Rules
Violations of `agents.md`, `CLAUDE.md`, or repo-specific conventions. Project rules take priority over general best practices. Includes the `patterns-compat` dimension from `dimensions.md` — check new code against existing repo idioms in the same module (naming, error handling, framework patterns) using neighbor-file context. Drift that's clearly a bug → finding; drift that may be intentional → emit at `nit`/`suggestion` with `suppressed_reason: style` so a validator can confirm (demote-don't-delete).

### Completeness
Requirements with no corresponding code (incomplete). Code changes not tied to any requirement (scope creep). Respect ticket scope boundaries.

### Documentation
Missing or stale documentation on public surface: undocumented public symbols/APIs, comments that contradict the code, behavior that needs but lacks a doc/README note. Skip trivial or self-evident code — do not demand docstrings on obvious helpers.

## Context Applicability

| Category | Diff review | File review | Notes |
|----------|:-----------:|:-----------:|-------|
| Security | 1 | 1 | Always top priority |
| Logic & Correctness | 2 | 2 | Always high priority |
| Performance | 3 | 5 | |
| Design & Structure | 4 | 3 | In diff modes, scoped to code the change touches — don't suggest refactors of untouched code |
| Complexity & Maintainability | 5 | 4 | Same scope rule as Design |
| Dead Code & Redundancy | 6 | 6 | In diff modes, flag unused code the change *introduces*; severity is branch-gated (see `reviewer-rules.md` → "Dead-code severity") |
| Test Quality | 7 | 7 | |
| Style & Conventions | 8 | 8 | File review narrows to linter-invisible issues |
| Project Rules | 9 | — | Requires CLAUDE.md/agents.md context; flag only clear violations in file review |
| Completeness | 10 | — | Requires a ticket/requirement to compare against |
| Documentation | 11 | 9 | Public-surface docs only; skip trivial/self-evident code |

Numbers indicate priority order within each context. `—` means skip unless clearly relevant. Design, Complexity, and Dead Code now apply in **every** mode (diff and file); in diff modes they are bounded by scope (touched code only) and, for dead code, by the branch-target gate.

## Category Tags for Triage

Use specific sub-tags when presenting findings: `[security]`, `[logic/sort]`, `[API misuse]`, `[null safety]`, `[test coverage]`, `[convention]`, `[completeness]`, `[design/coupling]`, `[complexity]`, `[dead code]`, etc. The sub-tag should name the specific issue type, not just the broad category.
