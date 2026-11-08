# syntax=docker/dockerfile:1.7
# Hardened images for heydiff-web on Cloud Run, after a golden-path hardened image setup.
# Two images from one file:
#   runtime (default target) → europe-west1-docker.pkg.dev/GCP_PROJECT_ID/IMAGES_REPO/web:<git-sha>
#   migrate                  → europe-west1-docker.pkg.dev/GCP_PROJECT_ID/IMAGES_REPO/migrate:<content-tag>
# Both run on Google distroless: non-root (uid 65532), no shell, no package manager.
# Bases are pinned by digest; Dependabot bumps them. When a distroless Debian release is
# retired, check the Node version inside the new digest (seen once: nodejs22-debian12
# froze at 22.22.0 and missed two security releases while its digest kept moving).
# The contract the app must meet is in docs/deploy.md.

# ── deps: lockfile-frozen install, cached until the manifests change ─────────
FROM node:24.22.1-trixie-slim@sha256:89c5244bc22a9bc3287d89ebc7e49b9cb5bb84cd40e6175ac3421d5a9f68b95a AS deps
WORKDIR /app
# .npmrc points @pokbytes at GitHub Packages and reads the token from NODE_AUTH_TOKEN; the token is a BuildKit secret
# (docker build --secret id=npm_token,env=NODE_AUTH_TOKEN), so it is in no layer and no cache.
COPY package.json package-lock.json .npmrc ./
# --ignore-scripts: no install script from a dependency runs during the build.
RUN --mount=type=cache,target=/root/.npm --mount=type=secret,id=npm_token \
    NODE_AUTH_TOKEN="$(cat /run/secrets/npm_token)" npm ci --ignore-scripts --no-audit --no-fund

# ── build: Next.js standalone output ─────────────────────────────────────────
FROM node:24.22.1-trixie-slim@sha256:89c5244bc22a9bc3287d89ebc7e49b9cb5bb84cd40e6175ac3421d5a9f68b95a AS build
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# ── migrate-build: bundle the migration runner, so the migrate image needs no node_modules ──
# CJS on purpose: an ESM bundle cannot express a dynamic require and dies at startup.
FROM node:24.22.1-trixie-slim@sha256:89c5244bc22a9bc3287d89ebc7e49b9cb5bb84cd40e6175ac3421d5a9f68b95a AS migrate-build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN node_modules/.bin/esbuild scripts/migrate.ts \
      --bundle --platform=node --target=node24 --format=cjs \
      --tsconfig=tsconfig.json --out-extension:.js=.cjs --outdir=/out

# ── migrate: the Cloud Run job APP-migrate-prod (DDL identity) ────────────
FROM gcr.io/distroless/nodejs24-debian13:nonroot@sha256:cb606325b7ec4af55462cb0b424a53b452a5b4a894ffe841fcf1048d216fb9f8 AS migrate
WORKDIR /app
ENV NODE_ENV=production
# scripts/migrate.ts reads ./drizzle/migrations relative to WORKDIR; keep the two in step.
COPY --from=migrate-build --chown=nonroot:nonroot /out/migrate.cjs ./migrate.cjs
COPY --from=migrate-build --chown=nonroot:nonroot /app/drizzle/migrations ./drizzle/migrations
ARG GIT_SHA=unknown
ENV GIT_SHA=$GIT_SHA
LABEL org.opencontainers.image.source="https://github.com/OWNER/REPO" \
      org.opencontainers.image.revision="$GIT_SHA"
USER 65532:65532
# The distroless ENTRYPOINT is `node`; CMD is the script.
CMD ["migrate.cjs"]

# ── runtime: the Cloud Run services heydiff-web and APP-staging ──────
FROM gcr.io/distroless/nodejs24-debian13:nonroot@sha256:cb606325b7ec4af55462cb0b424a53b452a5b4a894ffe841fcf1048d216fb9f8 AS runtime
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=8080 HOSTNAME=0.0.0.0
COPY --from=build --chown=nonroot:nonroot /app/.next/standalone ./
COPY --from=build --chown=nonroot:nonroot /app/.next/static ./.next/static
COPY --from=build --chown=nonroot:nonroot /app/public ./public
# The commit this image was built from; /readyz returns it and the deploy waits for it.
ARG GIT_SHA=unknown
ENV GIT_SHA=$GIT_SHA
LABEL org.opencontainers.image.source="https://github.com/OWNER/REPO" \
      org.opencontainers.image.revision="$GIT_SHA"
USER 65532:65532
EXPOSE 8080
CMD ["server.js"]
