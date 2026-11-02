# File → doc mappings, per OMR repo

When the `docs-audit` skill is run, it consults this file to find the section for the current repo and uses the listed patterns to scope the audit. **Read only the section for the current repo** — don't load the whole file. Always also read the *Generic rules* section, which applies to every repo.

This file is the **single source of truth** for which file patterns trigger which doc audits in each OMR repo. Both `references/commands/diff.md` (when invoked manually or by `cct:pr-create`) and `references/commands/full.md` consult it. Per-repo `.claude/settings.json` does not duplicate this information.

## Generic rules (apply to every repo)

These triggers apply in **any** OMR repo. Per-repo sections supplement them with repo-specific patterns. Do not repeat generic patterns in per-repo sections.

| Changed pattern | Docs to audit |
|---|---|
| `CLAUDE.md`, `AGENTS.md`, `README.md` itself | full re-read of itself; consistency-check against changed files in the same commit |
| `Dockerfile`, `docker-compose*.yml`, `Makefile` | `CLAUDE.md` (Setup/Dependencies/How to run), `README.md` |
| `.krane/**` | `CLAUDE.md` (Deployment section), any `docs/deploy*.md` |
| `.env.example` | `CLAUDE.md` (Setup), `README.md` (Setup), `docs/setup*.md` |
| `.github/workflows/**` | `CLAUDE.md` (CI section if any), `docs/ci*.md` |
| `.github/PULL_REQUEST_TEMPLATE.md` | any doc that duplicates the PR checklist (commonly `docs/git*.md`, `CONTRIBUTING.md`, `REVIEW.md`) |
| `.github/ISSUE_TEMPLATE/**` | any doc that explains issue conventions (commonly `CONTRIBUTING.md`) |
| Lockfiles (`*.lock`, `package-lock.json`, `pnpm-lock.yaml`, `Gemfile.lock`, `uv.lock`) | `CLAUDE.md` (Dependencies, Setup), `README.md` (Install) — usually only when a major version moves |

## reviews-api (Rails)

Repo type: Rails GraphQL backend; consumed by `reviews-frontend`, `eventmanager`, `hub-frontend`.

| Changed pattern | Docs to audit | Why |
|---|---|---|
| `app/graphql/**/*.rb` | `CLAUDE.md`, `docs/graphql*.md`, any consumer references in workspace `CLAUDE.md` | GraphQL is a contract with multiple frontends; downstream callers depend on it |
| `app/controllers/**/*.rb` | `CLAUDE.md` (Routes section), `README.md` | REST/admin surface |
| `config/routes.rb` | `CLAUDE.md` (Routes), `README.md` | Route definitions |
| `db/migrate/**`, `db/schema.rb` | `CLAUDE.md` (Data model), `docs/data*.md` | Schema changes |
| `Gemfile`, `Gemfile.lock` | `CLAUDE.md` (Dependencies, Setup) | Dependency drift |
| `app/admin/**/*.rb` | `CLAUDE.md` (ActiveAdmin / Admin panel) | Admin surface |
| `app/models/**/*.rb` (associations, validations) | `CLAUDE.md` (Data model section, if present) | Model contract |
| `lib/tasks/**/*.rake` | `CLAUDE.md` (Common tasks), `README.md` (How to run) | Rake task surface |
| `Makefile` | `CLAUDE.md` (Setup, How to run), `README.md` | Build targets |

## reviews-frontend (Nuxt 3 SSR)

Repo type: Nuxt 3 SSR consuming `reviews-api`, `myomr`, Hygraph, and serving widget/badge endpoints used by `eventmanager`.

| Changed pattern | Docs to audit | Why |
|---|---|---|
| `nuxt.config.ts` | `CLAUDE.md` (Architecture, Modules), `README.md` (Setup) | Top-level config |
| `server/**/*.ts` | `CLAUDE.md` (Server routes), workspace `CLAUDE.md` (cross-repo gotchas — widget endpoint coupling) | Server routes serve cross-repo consumers |
| `pages/**/*.vue`, `app/**/*.vue` (route files only) | `CLAUDE.md` (Routes / URL structure), `README.md` | URL surface |
| `composables/**`, `utils/**` (public API) | `CLAUDE.md` (Architecture) | Reusable surface |
| `package.json` | `CLAUDE.md` (Dependencies, Setup), `README.md` | Dependency / script drift |
| `i18n/**`, `locales/**` | `CLAUDE.md` (Localization), `README.md` | i18n contract |
| `app.config.ts`, `app.vue` | `CLAUDE.md` (Architecture) | App-level config |
| `Dockerfile`, `Makefile`, `.krane/**` | as per generic rules above | |

## myomr (Rails — central identity)

Repo type: Rails identity provider; consumed by virtually every OMR app.

| Changed pattern | Docs to audit | Why |
|---|---|---|
| `app/graphql/**/*.rb` | `CLAUDE.md`, downstream consumer notes | GraphQL contract — high blast radius |
| `config/initializers/doorkeeper*.rb`, `config/initializers/omniauth*.rb` | `CLAUDE.md` (Auth section) | Auth flow contract |
| `app/controllers/oauth/**`, `app/controllers/doorkeeper/**` | `CLAUDE.md` (Auth section) | OAuth surface |
| `db/schema.rb`, `db/migrate/**` | `CLAUDE.md` (Data model) | Schema changes |

## eventmanager (Vue 3 SPA)

| Changed pattern | Docs to audit | Why |
|---|---|---|
| `src/router/**`, `src/views/**` | `CLAUDE.md` (Routes / URL structure) | Route surface |
| `src/stores/**` (Pinia) | `CLAUDE.md` (State management) | Store contract |
| `src/graphql/**` (queries/mutations) | `CLAUDE.md` (API consumers) | API consumer contract |
| `vite.config.ts`, `package.json` | `CLAUDE.md` (Setup, Modules) | Top-level config |

## platform-api (Rails)

Same patterns as `reviews-api` (Rails app), with the addition of:

| Changed pattern | Docs to audit | Why |
|---|---|---|
| `app/services/payments/**` | `CLAUDE.md` (Payments / Unzer) | Payment integration surface |
| `app/services/notifications/**` | `CLAUDE.md` (Notifications) | Used by `eventmanager` |

## hub-frontend / festival-pages / omj-frontend (Nuxt 3)

Use the `reviews-frontend` patterns as a template.

## festival-companion (Vue 3 SPA)

Use the `eventmanager` patterns as a template, plus:

| Changed pattern | Docs to audit | Why |
|---|---|---|
| `src/main.ts` (host-based sub-app dispatch) | `CLAUDE.md` (Sub-app architecture) | Critical — non-obvious from filenames |

## festival-mobile-app (React Native)

| Changed pattern | Docs to audit | Why |
|---|---|---|
| `app.json`, `app.config.{js,ts}` | `CLAUDE.md` (App config) | Deep-link & build config |
| `package.json` | `CLAUDE.md` (Dependencies) | |
| `ios/Podfile`, `ios/Podfile.lock` | `CLAUDE.md` (iOS setup) | Native deps |
| `android/build.gradle`, `android/app/build.gradle` | `CLAUDE.md` (Android setup) | Native deps |

## omr-js (turbo monorepo)

| Changed pattern | Docs to audit | Why |
|---|---|---|
| `packages/*/package.json` | top-level `CLAUDE.md`, package `README.md` | Publishing contract |
| `packages/*/src/index.ts` (public exports) | package `README.md`, Storybook docs | Public API of each `@ramp106/*` package |
| `turbo.json` | `CLAUDE.md` (Build) | Build graph |

## data-orchestration (Airflow + dbt)

| Changed pattern | Docs to audit | Why |
|---|---|---|
| `dags/**/*.py` (DAG definitions) | `CLAUDE.md` (Pipelines), `docs/dags*.md` | DAG contract |
| `dbt/models/**/*.sql` | `CLAUDE.md` (Models), dbt `schema.yml` | Model contract |
| `dbt/sources.yml`, `dbt/dbt_project.yml` | `CLAUDE.md` (Sources / project config) | |

---

When adding a new OMR repo: append a section here. The skill discovers the repo's patterns by reading this file at audit time; no other registration is needed.
