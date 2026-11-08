#!/usr/bin/env bash
# Usage: review-threads-cleanup.sh <path>
# Removes a threads tmp file created by review-threads.sh. Idempotent.
#
# Safety: path must be under ${TMPDIR:-/tmp} or /tmp/.
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <path>" >&2
  exit 2
fi

TARGET="$1"

case "$TARGET" in
  "${TMPDIR:-/tmp}"/*|/tmp/*) ;;
  *)
    echo "Error: path must be under \${TMPDIR:-/tmp} or /tmp/ (got: $TARGET)" >&2
    exit 2
    ;;
esac

rm -f "$TARGET"
