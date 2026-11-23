#!/usr/bin/env bash
# Runs the E2E specs changed since <base> plus e2e/flaky-specs.txt three times (the milestone `e2e-repeat` check).
#   bash scripts/e2e-repeat.sh <base>
# A name is accepted only if it matches the spec pattern and is a file; anything else fails the run, so a stale flaky
# list or a hostile name never reaches the runner. Specs go after `--`; an empty set runs nothing and exits 0.
# E2E_REPEAT_RUNNER replaces the runner command (tests use it). Written by `sdlc-run adopt` from the kit.
set -euo pipefail

base="${1:?usage: e2e-repeat.sh <base>}"
pattern='^[A-Za-z0-9._/-]+\.spec\.(ts|tsx|js|mjs)$'

# Run before the pipe: an unknown base is an error, never an empty selection.
changed="$(git diff --name-only --diff-filter=d "$base"...HEAD -- 'e2e/*.spec.*')"
listed=""
if [ -f e2e/flaky-specs.txt ]; then
  listed="$(sed -e 's/[[:space:]]*#.*//' -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' e2e/flaky-specs.txt)"
fi

specs=()
while IFS= read -r name; do
  [ -n "$name" ] && specs+=("$name")
done < <(printf '%s\n%s\n' "$changed" "$listed" | sort -u)

bad=0
for name in ${specs[@]+"${specs[@]}"}; do
  if [[ "$name" == -* || ! "$name" =~ $pattern ]]; then
    echo "e2e-repeat: not a spec path: $name" >&2; bad=1
  elif [ ! -f "$name" ]; then
    echo "e2e-repeat: no such spec (stale e2e/flaky-specs.txt?): $name" >&2; bad=1
  fi
done
[ "$bad" = 0 ] || exit 1

if [ "${#specs[@]}" = 0 ]; then
  echo "e2e-repeat: no changed or flaky specs, nothing to run"
  exit 0
fi

# shellcheck disable=SC2086 -- the runner is a command line (word-split on purpose); the specs are quoted
exec ${E2E_REPEAT_RUNNER:-pnpm exec playwright test} --repeat-each=3 -- "${specs[@]}"
