#!/usr/bin/env bash
# Proves the hardening of a built web image: non-root user, no shell, runs on a read-only root
# filesystem with every capability dropped, and serves /healthz and /readyz with the build sha.
# /readyz needs a database: SMOKE_DATABASE_URL names a Postgres the container can reach through
# host.docker.internal (CI: the postgres service on the runner's port 5432). The smoke test
# fails without it rather than skip the readiness check.
# Usage: SMOKE_DATABASE_URL=postgres://... scripts/docker-smoke.sh <image> <expected-sha>. DOCKER=podman works too.
set -euo pipefail
image="$1"
sha="$2"
: "${SMOKE_DATABASE_URL:?set SMOKE_DATABASE_URL to a reachable Postgres: /readyz needs a database}"
docker="${DOCKER:-docker}"
port="${PORT:-18080}"

user="$("$docker" image inspect -f '{{.Config.User}}' "$image")"
[ "$user" = nonroot ] || [ "$user" = 65532 ] || [ "$user" = 65532:65532 ] || { echo "FAIL: image user is '${user}', expected nonroot"; exit 1; }
echo "ok: runs as ${user}"

if "$docker" run --rm --entrypoint /bin/sh "$image" -c true >/dev/null 2>&1; then
  echo "FAIL: the image has a shell"
  exit 1
fi
echo "ok: no shell"

name="smoke-$$"
"$docker" run -d --name "$name" --read-only --tmpfs /tmp --cap-drop ALL \
  --security-opt no-new-privileges --add-host host.docker.internal:host-gateway -e DATABASE_URL="$SMOKE_DATABASE_URL" \
  -p "127.0.0.1:${port}:8080" "$image" >/dev/null
trap '"$docker" rm -f "$name" >/dev/null 2>&1 || true' EXIT

for _ in $(seq 1 30); do
  curl -fsS "http://127.0.0.1:${port}/healthz" >/dev/null 2>&1 && break
  sleep 1
done
curl -fsS "http://127.0.0.1:${port}/healthz" >/dev/null || { "$docker" logs "$name"; echo "FAIL: /healthz"; exit 1; }
echo "ok: /healthz"

ready="$(curl -fsS "http://127.0.0.1:${port}/readyz")" || { "$docker" logs "$name"; echo "FAIL: /readyz (is the database reachable?)"; exit 1; }
[ "$(printf '%s' "$ready" | jq -r '.status')" = ready ] || { echo "FAIL: /readyz says ${ready}"; exit 1; }
live="$(printf '%s' "$ready" | jq -r '.sha')"
[ "$live" = "$sha" ] || { echo "FAIL: /readyz sha is '${live}', expected '${sha}'"; exit 1; }
echo "ok: /readyz is ready against the database and serves ${sha} on a read-only root filesystem with no capabilities"
