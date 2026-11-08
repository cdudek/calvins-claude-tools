# Dimensions

The list of review lenses. A finding's `dimension` field uses a name from this file. A discovered name not listed here is also valid — the selector may add one when the code warrants it. Reviewers do not invent names; they pick the closest.

Max lanes run the 3 core dimensions always. Every other dimension is scored 0-100 for fit to the review and runs only if it passes the cap in `select-agent.md`. Hard cap: 15 reviewers.

The rules for what to flag and what to drop are in `reviewer-rules.md`.

## Core — always run

| Dimension | Applies to | Notes |
|---|---|---|
| security | always | OWASP, injection, secrets, mass-assignment |
| correctness | always | logic bugs, race conditions, edge cases, null handling, broken error handling, off-by-one |
| performance | hot paths, loops, queries | — |

## Scored pool

| Dimension | Applies to | Notes |
|---|---|---|
| complexity | all modes | cognitive complexity, misleading names, unclear intent; in diff modes only for code the change touches |
| design-structure | all modes | coupling, cohesion, SRP, layering; in diff modes only for code the change touches |
| test-quality | spec/test files | — |
| documentation | public API surface, comments, READMEs | missing or stale docstrings, comments that contradict code; skip the self-evident |
| completeness | when a ticket or AC is in `INPUT.md` | delivered code vs intended scope; scores low with nothing to compare against |
| auth | session, login, credential flow | login, OAuth, JWT, session cookies |
| authz | policies, permission checks, role gates | Pundit/CanCan policies, GraphQL field resolvers |
| db-access | migrations, models, raw SQL, ActiveRecord | N+1, missing indexes, unsafe migrations (NOT NULL without backfill) |
| graphql | `app/graphql/**`, schema files | field-level authz, query depth, N+1 in resolvers, breaking schema changes |
| project-rules | always | `CLAUDE.md` / `agents.md` |
| patterns-compat | always, with neighbour files | new code vs the idioms already in the module |
| style-conventions | always, linter-invisible only | misleading patterns, inconsistent naming; skip what linters catch |
| dead-code-redundancy | all modes | unused functions, unreachable branches, duplicated logic. Severity depends on the target branch — `reviewer-rules.md`. |

## Domain and surface tags — files mode

When the path shows it, add `domain:` and `surface:` to a finding.

| Path | Domain |
|---|---|
| `app/<layer>/<domain>.rb`, `app/<layer>/<domain>/*.rb` | `<domain>` |
| `db/migrate/*_<domain>_*.rb` | `<domain>` |
| `pages/<domain>/...`, `components/<domain>/...` | `<domain>` |
| `composables/use<Domain>.ts` | `<domain>` lowercased |
| `app/graphql/types/<domain>_type.rb`, `app/graphql/mutations/<domain>/...` | `<domain>` |

No match → group by directory, read the file header, else `misc`.

| Path | Surface |
|---|---|
| `app/admin/**` | admin |
| `app/controllers/api/**`, `app/graphql/**` | api |
| `app/views/**`, `pages/**`, `components/**` | web |
| `app/mailers/**`, `app/views/*_mailer/**` | email |
| `app/jobs/**`, `app/workers/**` | jobs |
| `bin/**`, `lib/tasks/**` | cli |

A file can have more than one surface. Tag all that apply.
