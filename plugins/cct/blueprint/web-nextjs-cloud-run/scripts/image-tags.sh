#!/usr/bin/env bash
# Prints the image references for one commit, as `key=value` lines for $GITHUB_OUTPUT:
#   sha      the full git sha
#   web      <repo>/web:<sha>
#   migrate  <repo>/migrate:m-<hash>, the hash of everything that goes into the migrate image.
# The recipe and the lockfile are inputs too: An earlier incident reused a stale migrate
# image because its tag left out the Dockerfile. Used by build.yml, so every
# workflow agrees on the tag. Usage: scripts/image-tags.sh <commit> [repository]
set -euo pipefail
commit="$1"
repository="${2:-europe-west1-docker.pkg.dev/GCP_PROJECT_ID/IMAGES_REPO}"
sha="$(git rev-parse --verify "${commit}^{commit}")"
hash="$(git rev-parse "${sha}:Dockerfile" "${sha}:package.json" "${sha}:package-lock.json" \
  "${sha}:drizzle/migrations" "${sha}:scripts" "${sha}:src" | sha256sum | cut -c1-16)"
echo "sha=${sha}"
echo "web=${repository}/web:${sha}"
echo "migrate=${repository}/migrate:m-${hash}"
