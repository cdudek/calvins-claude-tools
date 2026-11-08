#!/usr/bin/env bash
# Usage: files-exist.sh <path> [path2 ...]
#
# Classify every argument as dir / file / missing in ONE call — arg validation for the
# files-* review modes. Replaces per-token `ls` round-trips (slow) and free-form `ls`
# output parsing (fragile): one deterministic, greppable row per arg, in arg order.
# Used to (a) confirm review targets exist and (b) disambiguate trailing flag words
# (`sonnet`/`select`) from real paths — a reserved word that classifies as dir/file is
# ambiguous and the caller asks. Always exits 0 (status reporter).
#
# Output: one "- <dir|file|missing>: <path>" row per argument.
set -euo pipefail

for p in "$@"; do
  if   [ -d "$p" ]; then echo "- dir: $p"
  elif [ -e "$p" ]; then echo "- file: $p"
  else                   echo "- missing: $p"
  fi
done
