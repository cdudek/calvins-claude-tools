#!/usr/bin/env bash
# Usage: scripts/git-hook-env.sh <command> [args...]
# Runs a git-hook command without the GIT_* variables git exports into hooks.
# Tests that build temp repos would otherwise write commits, config and branches into this repo.
set -euo pipefail
# shellcheck disable=SC2046
unset $(env | sed -n 's/^\(GIT_[A-Za-z0-9_]*\)=.*/\1/p')
exec "$@"
