# Conventional Branch Naming

Fallback convention when the repo has no branch naming docs. Based on https://conventional-branch.github.io.

## Format

```
<type>/<description>
```

## Types

| Type | Purpose |
|------|---------|
| `feat` or `feature` | New features |
| `fix` or `bugfix` | Bug fixes |
| `hotfix` | Urgent production fixes |
| `release` | Release preparation |
| `chore` | Non-code tasks (deps, docs, config) |
| `refactor` | Code restructuring without behavior change |
| `test` | Adding or updating tests |
| `docs` | Documentation only |
| `ci` | CI/CD configuration changes |

## Naming Rules

- **Lowercase only** — `feat/add-login`, not `feat/Add-Login`
- **Hyphens to separate words** — `fix/resolve-timeout`, not `fix/resolve_timeout`
- **No consecutive hyphens or dots**
- **No leading or trailing hyphens**
- **No spaces, underscores, or special characters**
- **Dots allowed only in release versions** — `release/v1.2.0`

## Including Ticket Numbers

When a ticket or issue number is available, include it after the type:

```
feat/issue-123-add-user-auth
fix/BUG-456-null-pointer-exception
chore/PROJ-789-update-deps
```

## Examples

```
feat/add-user-authentication
feat/issue-42-search-filters
fix/resolve-login-timeout
fix/BUG-123-null-reference
hotfix/critical-payment-bug
chore/update-dependencies
refactor/extract-auth-middleware
test/add-payment-integration-tests
docs/update-api-reference
ci/add-deploy-workflow
release/v2.1.0
```
