# Deploy: images, Cloud Run, CI

Verification follows [local-first](https://github.com/cdudek/calvins-claude-tools/blob/main/plugins/cct/skills/sdlc-run/references/local-first.md). These are legacy workflow examples; migrate
verification before enabling them in a new repo. GitHub keeps cloud and scheduled work.

How heydiff-web becomes a running service. Modelled on a golden-path app blueprint, with Cloud Run instead of Kubernetes, and GitHub Actions doing what ArgoCD does there. The infrastructure is in [pokbytes/terraform-infra](https://github.com/pokbytes/terraform-infra). The design is section 13 of [the HeyDiff design](designs/2026-10-27-snapmark-online.md) once the plan lands here.

## Region and domain

Compute runs in `europe-west1` (Belgium): Cloud Run, Cloud SQL, Artifact Registry. Cloud Storage and BigQuery stay in the EU multi-region. heydiff.com reaches production through Cloud Run domain mapping, which Google offers in Belgium but in no German region (owner, 2026-10-28: "ok do belgium then", "ok move cloud sql too"). No load balancer, no Firebase. DNS is in AWS Route53; the records come from terraform-infra's `dns_records` output.

## Names

`.github/workflows/*.yml`, `.github/actions/cloud-run-deploy` and `scripts/` name Cloud Run services, jobs, the registry, the Cloud SQL instance and the deploy identity. Every such name follows terraform-infra's naming rule (owner, 2026-10-31; CLAUDE.md, "Terraform and infrastructure naming"):

- **Every environment-scoped resource ends in its environment:** `-prod` or `-staging`, or `_prod` and `_staging` where `-` is not allowed (Postgres database names). Examples: `APP-prod`, `APP-staging`, `APP-migrate-prod`, `better-auth-secret-prod`, `heydiff_prod`.
- **A resource used by every environment ends in `-shared`:** `DB_INSTANCE`, `IMAGES_REPO`, `APP-run-shared`, `APP-deploy-shared`. `-dev` (`_dev`) is for local development only: `heydiff-web-signer-dev`, `calvin_dudek_dev`.
- **No bare names.** A name without its environment silently means production. Never `heydiff-web`, `database-url` or `heydiff`.
- The full table, what is exempt (Terraform addresses, domain mappings, IAM users' emails, the GitHub environment `production`) and the policy that enforces it (`policy/terraform/naming.rego`) are in terraform-infra's README, "Naming".

A new name here is chosen in terraform-infra first, never invented in a workflow.

## The images

One `Dockerfile`, two images, both in `europe-west1-docker.pkg.dev/GCP_PROJECT_ID/IMAGES_REPO/`:

| Image     | Target    | Tag                                                           | Runs as                                                             |
| --------- | --------- | ------------------------------------------------------------- | ------------------------------------------------------------------- |
| `web`     | `runtime` | the git sha                                                   | Cloud Run services `APP-prod`, `APP-staging`             |
| `migrate` | `migrate` | `m-<hash>` of Dockerfile, manifests, migrations, scripts, src | Cloud Run jobs `APP-migrate-prod`, `APP-migrate-staging` |

What makes them hardened:

- **Multi-stage.** The build toolchain never ships. The runtime is Google distroless `nodejs24-debian13`: no shell, no package manager.
- **Non-root.** uid 65532, numeric, so a platform can verify it.
- **Pinned.** Every base is pinned by digest; Dependabot bumps them weekly. Node 24 is the active LTS. When distroless retires a Debian release, Dependabot does not follow; check the Node version inside the new digest.
- **Frozen installs.** `npm ci --ignore-scripts`: a drifted lockfile fails, and no dependency install script runs.
- **No secrets.** `.dockerignore` keeps `.env*`, keys, `.git`, `.worktrees` and agent folders out of the context. Secrets come from Secret Manager at runtime.
- **Read-only friendly.** The app writes nothing to its filesystem; `scripts/docker-smoke.sh` runs it with a read-only root, no capabilities and `no-new-privileges`.
- **Small migrate image.** The migration runner is bundled with esbuild into one `.cjs` file, so the image holding database DDL rights carries no `node_modules`.
- **Scanned and attested.** Trivy fails the build on any fixable HIGH or CRITICAL; images are pushed with an SBOM and SLSA provenance.

Checked on 2026-10-28 against a Next.js 16.4 app: both images built, the smoke test passed, Trivy found 0 HIGH or CRITICAL, hadolint, actionlint and shellcheck were clean.

## What the app must provide (milestone 1)

The images build only when the app meets this contract:

- `next.config.ts` sets `output: 'standalone'`.
- `GET /healthz` answers 200 while the process is alive.
- `GET /readyz` answers `{"status":"ready","sha":"<GIT_SHA>"}` when its dependencies answer, and 503 otherwise. The deploy waits for this sha; it is the definition of done.
- The server listens on `PORT` (8080).
- `scripts/migrate.ts` runs the Drizzle migrations from `./drizzle/migrations`; `esbuild` is a dev dependency.
- `src/` and `public/` exist.
- Migrations are expand and contract: a release only adds; removals ship a release later. Old and new revisions always run on the same schema, so a rollback never touches the database.

## Environment the app needs in production

| Variable                  | Value on Cloud Run | Why                                                                                                                                                                                  |
| ------------------------- | ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `AUTH_TRUST_PROXY_HOPS`   | `1`                | Cloud Run's front end appends the client address to `X-Forwarded-For`. Sign-in rate limits count per address. In production the app refuses to sign anyone in when this is unset or `0`. |
| `MAIL_PROVIDER`           | `resend`           | The `console` provider prints sign-in links to the log, so production refuses it.                                                                                                    |

`AUTH_TRUST_PROXY_HOPS` is not a secret. `deploy.yml` sets it on every deploy (`--update-env-vars` in `.github/actions/cloud-run-deploy`); terraform-infra should hold the same value so a plain `terraform apply` does not drift from it. A request that arrives without a valid client address is refused with 403; it never shares a rate-limit bucket with other people.

## Database development and migrations

Use Node 24 and `make dev-db` to connect to your own Cloud SQL database. The app
listens on `127.0.0.1:3000`; a phone uses staging. Database commands load
`.env.local`, then `.env`, and preserve environment variables supplied by the
shell or Cloud Run. There is no second local Postgres setup.

```bash
npm run db:migrate
npm run db:seed       # optional demo data; never runs during deployment
npx drizzle-kit generate --name=describe_the_addition
```

The first migration enables the trusted `citext` extension in `public`; the
migration role needs permission to install it. The second migration, generated
by Drizzle Kit 0.31.11 from `src/server/db/schema/index.ts`, creates the release-1
schema. Commit generated SQL, snapshots and the journal together. ORM 0.45.4
and postgres.js 3.4.9 stay pinned. `DATABASE_URL` is required when connecting,
but generating SQL does not need a connection.

`getDatabase()` creates one lazy postgres.js pool, also used by the readiness
probe. Application inserts get UUIDv7 ids from `uuidv7()`; SQL migrations do not
require a Postgres version-specific UUID function. Direct SQL writers must
provide a UUIDv7 id themselves. Future Better Auth setup must use:

```ts
database: drizzleAdapter(getDatabase(), { provider: 'pg', schema: authSchema }),
advanced: { database: { generateId: 'uuid' } },
```

Not a function: with `uuidv7` Better Auth's deterministic ids (the magic-link
reservation) are base64url and fail on the `uuid` columns; with `'uuid'` they are
UUID-shaped and rows still get their UUIDv7 id from Drizzle's `$defaultFn`.

Import `authSchema` from `src/server/db/auth-schema.ts`. Its keys and column
properties use Better Auth's model names (`user`, `organization`, `member`,
etc.); Drizzle maps them to the British plural SQL names `users`,
`organisations`, `memberships`, and `invitations`. No `usePlural` or field-name
overrides are needed. Auth sign-ins use `session`; review passes use
`review_sessions`. The A59 changes supersede the older ER diagram: comments,
revisions, decisions and connected apps replace feedback, versions, reviews,
decision requests and devices. `connected_apps` is the revocable client row;
there is no separate `devices`, `device_tokens` or `shared_sessions` table.
OAuth tables declare the [provider's model fields](https://github.com/better-auth/better-auth/blob/v1.7.14/packages/oauth-provider/src/schema.ts); provider runtime wiring
belongs to feature 4.1. Its package is not required by the database layer.

Create comments through `insertComment()` or `insertCommentInTransaction()`
after policy resolution. Both allocate with `UPDATE workspaces ... RETURNING`
inside the insert transaction. `(workspace_id, number)` is unique, including
tombstones. The counter is never reset when a comment is deleted or purged;
failed transactions roll back allocation along with the insert. The old ADR's
`next_feedback_number` is named `next_comment_number` after A59.

The explicit seed creates organisation `heydiff-demo`, two workspaces, an
owner, member and guest, five comments covering every status, a decision with
two options and a vote, a revision and a review session. It is transactional
and repeatable; rerunning it does not consume more comment numbers. Demo
addresses use `.test`, and the seed grants no platform operator role.

Run database tests with `npx vitest run test/server/db`. Schema and SQL checks
need no database. Integration tests read only `TEST_DATABASE_URL` and are
clearly skipped when it is unset. They create and drop uniquely named
disposable databases on that test server so the original generated
public-schema migrations run unchanged. The test role therefore needs
`CREATEDB` and permission to install `citext`; the database named in the URL is
used only as the administrative connection and its tables are never reset.

## The pipeline

| Workflow       | When                        | What                                                                                                                                                                                                            |
| -------------- | --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ci.yml`       | every PR and push to `main` | format, lint, typecheck, test; lockfile and secret scan; hadolint, Trivy config; image build, scan and smoke test once the app exists. Legacy remote example: migrate checks locally and require `local-ci` + `decision4` before use.                                      |
| `preview.yml`  | PR opened or updated        | builds, deploys a tagged revision `pr-<n>` of staging with no traffic, comments its address; removes the tag when the PR closes. No migrations; no previews for forks.                                          |
| `deploy.yml`   | push to `main` (merge)      | **CD**: verify → build → **staging**: migrate, deploy with no traffic, wait for the sha, 100% traffic, wait again → **production**: the same images and steps on the public service, only after staging passed. |
| `rollback.yml` | by hand                     | routes 100% of traffic to an earlier revision (default: the one before the serving revision).                                                                                                                   |
| `release.yml`  | push to `main`              | semantic-release: a tag and GitHub Release per `feat`, `fix` or `perf`. Tags are decorative; deploys use sha images.                                                                                            |

Where ArgoCD would act, the workflow acts instead:

- **Promotion** is staging passing: production deploys the same images right after, on every merge to `main` (owner, 2026-10-28: "I want a CI and a CD on merge to Master"). The `production` environment allows only `main`. The gate before production is the PR: CI must be green to merge.
- **Rollout** is a revision with no traffic, checked on its tagged URL, then a traffic switch.
- **Health gate** is `/readyz` serving the pushed sha, three reads in a row on the service URL.
- **Self-heal** is an automatic traffic switch back to the revision that served before, when the check after promotion fails.
- **Drift** is Terraform's drift workflow in terraform-infra; Terraform ignores the image and traffic, which CI owns.

No ship, show or ask: every PR auto-merges on green (`sdlc.json` `tiers: false`).

Authentication is Workload Identity Federation, no keys: provider `projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/WIF_POOL/providers/WIF_PROVIDER_NAME`, service account `deployer@GCP_PROJECT_ID.iam.gserviceaccount.com` for staging and production. Previews use their own `preview-deployer@GCP_PROJECT_ID.iam.gserviceaccount.com`, allowed to deploy the staging service only and never the production one; restrict the provider's attribute condition to this repository. Staging is private: CI calls it with an identity token, people sign in with an allowed Google account. Production is public.

## Turning it on

1. Apply terraform-infra (bootstrap by hand, then its CI).
2. In this repo's settings, create the environments `staging`, `preview` and `production`; limit `production` to the `main` branch (Deployment branches).
3. Set the repository variable `DEPLOY_ENABLED` to `true`. Until then `deploy.yml` and `preview.yml` skip every job.
4. Make `check` the required status on `main`.

## Building locally

```bash
docker build --target runtime --build-arg GIT_SHA=$(git rev-parse HEAD) -t heydiff-web:local .
SMOKE_DATABASE_URL=postgres://postgres:postgres@host.docker.internal:5432/postgres scripts/docker-smoke.sh heydiff-web:local $(git rev-parse HEAD)
```

`/readyz` needs a database, so `SMOKE_DATABASE_URL` must name a Postgres the container reaches through `host.docker.internal`. `DOCKER=podman` runs the smoke test with Podman.
