# Blueprint

Working CI/CD and project setup copied from the HeyDiff repos on 2026-10-31. Copy what fits into a new repo, then change the names. Each folder keeps the original repo's paths.

| Folder | From | What it shows |
| --- | --- | --- |
| `web-nextjs-cloud-run/` | heydiff-web | Next.js in Docker on Cloud Run: images, CI, previews, deploy, release, rollback |
| `desktop-electron/` | snapmark-mac (cdudek/snapmark-mac) | Electron: CI, signed and notarized macOS release, semantic-release |
| `chrome-extension-wxt/` | heydiff-chrome | WXT extension: scripts, config, CI |
| `design-system-kit-heroui/` | heydiff-kit | npm workspaces publishing tokens, ui (HeroUI v3) and contracts to GitHub Packages |

Every folder also has the repo's `sdlc.json`, which `cct:sdlc-run` reads.

## The web pipeline

Start with `web-nextjs-cloud-run/docs/deploy.md`; it explains the images, the contract the app must meet and how to turn the pipeline on.

- **`Dockerfile`:** four stages. `deps` installs from the lockfile with `--ignore-scripts` (the npm token arrives as a BuildKit secret, so it is in no layer), `build` makes the Next.js standalone output, `migrate-build` bundles the Drizzle migration runner with esbuild, and two final targets on distroless Node (non-root, no shell): `runtime` and `migrate`. Bases are pinned by digest. `GIT_SHA` is baked in so `/readyz` can report it.
- **`.dockerignore`:** keeps `.git`, `.env*`, keys and docs out of the build context.
- **`.github/workflows/ci.yml`:** on every PR and push: a secrets scan; format check, lint, typecheck, unit tests and the Playwright smoke run; a Trivy scan of dependencies; hadolint, a Docker build and a Trivy scan of the image. `scripts/docker-smoke.sh` runs the built image locally the same way.
- **`build.yml`:** reusable; builds both images with Buildx, scans them with Trivy, pushes them to Artifact Registry with SBOM and provenance, tagged by SHA and content (`scripts/image-tags.sh`).
- **`preview.yml`:** a Cloud Run revision per PR with its own URL, removed when the PR closes.
- **`deploy.yml`:** on merge to `main`, one deploy at a time and never cancelled halfway: verify, build, then staging (run the migrate job, deploy a revision with no traffic, wait until its `/readyz` serves the new SHA via `.github/actions/cloud-run-deploy`, then move 100% of traffic), then production with the same images and steps behind the `production` environment.
- **`release.yml`:** semantic-release from the Conventional Commit PR titles (`.releaserc.json`).
- **`rollback.yml`:** manual; routes all traffic to an earlier revision (by default the one before the serving one). Nothing is rebuilt and no migration is undone, so migrations follow expand-and-contract.
- **`dependabot.yml`:** npm, Docker digests and Actions, grouped.

All actions are pinned by commit SHA with the version in a comment.

## Using it without GCP

The pipeline is Docker plus GitHub Actions; only the push and deploy steps are Google-specific.

- **Registry:** replace `google-github-actions/auth` and `setup-gcloud` with `docker/login-action` for GHCR (`ghcr.io/<owner>/<repo>`, `permissions: packages: write`), Docker Hub, ECR or ACR. `build.yml` keeps working; change the image names in `scripts/image-tags.sh`.
- **Auth:** keep it keyless. GCP uses Workload Identity Federation; AWS has `aws-actions/configure-aws-credentials` with an OIDC role; Azure has `azure/login` with federated credentials.
- **Run:** Cloud Run maps to AWS App Runner or ECS Fargate, Azure Container Apps, Fly.io, Render or Railway. Replace `.github/actions/cloud-run-deploy` with that platform's deploy action. Keep the "wait until `/readyz` reports the new SHA" step; it is what makes a deploy trustworthy.
- **Migrations:** run the `migrate` image as a one-off task before the new revision takes traffic (ECS run-task, a Fly release command, a Kubernetes Job).
- **Secrets:** the app reads them from the environment at runtime. Use the platform's secret store; never bake them into the image.

## Desktop releases

`desktop-electron/.github/workflows/release.yml` imports the Developer ID certificate into its own keychain, builds with electron-builder (`snapmark-app/scripts/electron-builder.sh`), notarizes with an app-specific password, publishes a GitHub release and, logged in keyless through WIF, uploads the ZIP, DMG and `latest-mac.yml` to the update bucket (so the repo itself can stay private). Secrets it expects: `MAC_CERT_P12_BASE64`, `MAC_CERT_PASSWORD`, `APPLE_ID`, `APPLE_APP_SPECIFIC_PASSWORD`, `APPLE_TEAM_ID`. The `sign-macos-app` skill walks through creating them. Export the `.p12` from Keychain Access › My Certificates so it includes the private key (about 3 KB; a 1.5 KB file has no key).

## Infrastructure

Terraform for each product lives in its own `<product>-terraform` repo: the project's APIs, Artifact Registry, Cloud Run services and jobs, Cloud SQL, buckets, the WIF pool and service accounts, and Secret Manager fed from SOPS files encrypted with Cloud KMS. It is not copied here because it is specific to one project; ask for it when starting a new one.
