# syntax=docker/dockerfile:1.7
# Hardened images for heydiff-web on Cloud Run, after a golden-path hardened image setup.
# Two images from one file:
#   runtime (default target) → europe-west1-docker.pkg.dev/GCP_PROJECT_ID/IMAGES_REPO/web:<git-sha>
#   migrate                  → europe-west1-docker.pkg.dev/GCP_PROJECT_ID/IMAGES_REPO/migrate:<content-tag>
# Both use Chainguard Node with BusyBox and npm removed: uid 65532, no shell or package manager.
# Bases are pinned by digest; build, runtime and .nvmrc use Node 26.
# Verify the Node major before accepting an update to the public latest tag.
# The contract the app must meet is in docs/deploy.md.

# ── deps: lockfile-frozen install, cached until the manifests change ─────────
FROM node:26.13.0-trixie-slim@sha256:5adad64f9a1fca2d51972caa65983634c8a774eb300d72b20f7f2a0f60368072 AS deps
WORKDIR /app
# .npmrc points @pokbytes at GitHub Packages and reads the token from NODE_AUTH_TOKEN; the token is a BuildKit secret
# (docker build --secret id=npm_token,env=NODE_AUTH_TOKEN), so it is in no layer and no cache.
COPY package.json package-lock.json .npmrc ./
# --ignore-scripts: no install script from a dependency runs during the build.
RUN --mount=type=cache,target=/root/.npm --mount=type=secret,id=npm_token \
    NODE_AUTH_TOKEN="$(cat /run/secrets/npm_token)" npm ci --ignore-scripts --no-audit --no-fund

# ── build: Next.js standalone output ─────────────────────────────────────────
FROM node:26.13.0-trixie-slim@sha256:5adad64f9a1fca2d51972caa65983634c8a774eb300d72b20f7f2a0f60368072 AS build
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# ── migrate-build: bundle the migration runner, so the migrate image needs no node_modules ──
# CJS on purpose: an ESM bundle cannot express a dynamic require and dies at startup.
FROM node:26.13.0-trixie-slim@sha256:5adad64f9a1fca2d51972caa65983634c8a774eb300d72b20f7f2a0f60368072 AS migrate-build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN node_modules/.bin/esbuild scripts/migrate.ts \
      --bundle --platform=node --target=node26 --format=cjs \
      --tsconfig=tsconfig.json --out-extension:.js=.cjs --outdir=/out

# ── runtime-base: the public image includes BusyBox and npm; neither ships ──
# latest: Node 26.13.0, verified 2026-11-08; public Chainguard tags do not pin a Node major.
FROM cgr.dev/chainguard/node:latest@sha256:6a066f8decea77c67ef2772a78fad81df7a78a346d0b22a05fc9dac14537f2b0 AS runtime-base
USER 0
# Use Node directly: the final runtime has no shell or package manager.
RUN ["/usr/bin/node", "-e", "const fs = require('node:fs'); for (const name of fs.readdirSync('/bin')) { const path = '/bin/' + name; if (fs.lstatSync(path).isSymbolicLink() && fs.readlinkSync(path).includes('busybox')) fs.rmSync(path); } for (const path of ['/bin/busybox', '/usr/bin/npm', '/usr/bin/npx', '/usr/lib/node_modules/npm']) fs.rmSync(path, { recursive: true, force: true });"]
USER 65532:65532

# ── migrate: the Cloud Run job APP-migrate-prod (DDL identity) ────────────
FROM runtime-base AS migrate
WORKDIR /app
ENV NODE_ENV=production
# scripts/migrate.ts reads ./drizzle/migrations relative to WORKDIR; keep the two in step.
COPY --from=migrate-build --chown=65532:65532 /out/migrate.cjs ./migrate.cjs
COPY --from=migrate-build --chown=65532:65532 /app/drizzle/migrations ./drizzle/migrations
ARG GIT_SHA=unknown
ENV GIT_SHA=$GIT_SHA
LABEL org.opencontainers.image.source="https://github.com/OWNER/REPO" \
      org.opencontainers.image.revision="$GIT_SHA"
USER 65532:65532
# The Chainguard ENTRYPOINT is `/usr/bin/node`; CMD is the script.
CMD ["migrate.cjs"]

# ── runtime: the Cloud Run services heydiff-web and APP-staging ──────
FROM runtime-base AS runtime
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=8080 HOSTNAME=0.0.0.0
COPY --from=build --chown=65532:65532 /app/.next/standalone ./
COPY --from=build --chown=65532:65532 /app/.next/static ./.next/static
COPY --from=build --chown=65532:65532 /app/public ./public
# The commit this image was built from; /readyz returns it and the deploy waits for it.
ARG GIT_SHA=unknown
ENV GIT_SHA=$GIT_SHA
LABEL org.opencontainers.image.source="https://github.com/OWNER/REPO" \
      org.opencontainers.image.revision="$GIT_SHA"
USER 65532:65532
EXPOSE 8080
CMD ["server.js"]
