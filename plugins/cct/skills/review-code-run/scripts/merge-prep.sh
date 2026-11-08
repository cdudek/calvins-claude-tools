#!/usr/bin/env bash
# Usage: merge-prep.sh <state_dir>
# Purpose: Assembles the merge input for the orchestrator from every review source in the
#          state dir — the per-dimension Claude reviews, plus the Codex co-review when one
#          ran. Nothing is written — output goes to stdout.
#
# Output sections:
#   -#-#- BEGIN DIMENSION REVIEW: <name> -#-#-
#   <raw review text from dim-<name>.json .result>
#   -#-#- END DIMENSION REVIEW: <name> -#-#-
#   (repeated for each dim file found)
#
#   -#-#- BEGIN CODEX FINDINGS -#-#-
#   <contents of codex-findings.json — already structured, already stamped source: codex>
#   -#-#- END CODEX FINDINGS -#-#-
#   (emitted only when codex-findings.json exists and holds at least one finding)
#
# At least one source must be present. Every lane writes one dim-*.json per reviewer —
# the deep lane writes dim-full-spectrum.json — even when that reviewer found nothing.
# So a state dir with no dim file and no Codex source is a broken run, not an empty
# review, and the error below fires only then.

set -euo pipefail

STATE_DIR="${1:?Usage: merge-prep.sh <state_dir>}"

found=0
for f in "$STATE_DIR"/dim-*.json; do
  [ -f "$f" ] || continue
  name=$(basename "$f" .json | sed 's/^dim-//')
  content=$(jq -r '.result // ""' "$f" 2>/dev/null)
  if [ -z "$content" ]; then
    echo "WARNING: $f has an empty .result field — skipping dimension '$name'" >&2
    continue
  fi
  printf -- '-#-#- BEGIN DIMENSION REVIEW: %s -#-#-\n' "$name"
  printf '%s\n' "$content"
  printf -- '-#-#- END DIMENSION REVIEW: %s -#-#-\n\n' "$name"
  found=$((found + 1))
done

# The Codex source is already normalized JSON in the canonical pre-identity shape, so it
# is passed through verbatim rather than re-rendered as prose. The merge step reasons over
# both forms; merge.md owns the collapse and provenance rules.
CODEX_JSON="$STATE_DIR/codex-findings.json"
if [ -f "$CODEX_JSON" ]; then
  # `jq -e` first: a parse failure means a broken source, which must NOT print the same
  # "ran clean" note a genuine zero-findings pass does. The two are different outcomes and
  # the merge step has to be able to tell them apart.
  if ! jq -e 'type == "object" and (.findings | type == "array")' "$CODEX_JSON" >/dev/null 2>&1; then
    # Exit non-zero rather than warn. A broken source cannot be told from a clean one by
    # its absence of findings, and leaving it on disk is worse than the bad merge: the
    # lane's "already done" checkpoint reads its presence as a completed pass, so the
    # revision would never retry Codex. Failing here surfaces it while the file can
    # still be deleted and the pass re-run.
    echo "ERROR: $CODEX_JSON is not readable as {\"findings\":[...]}" >&2
    echo "ERROR: the Codex source is broken, not clean. Delete it and re-run to retry the pass." >&2
    exit 1
  else
    codex_count=$(jq '(.findings // []) | length' "$CODEX_JSON")
  fi
  if [ "$codex_count" -gt 0 ]; then
    printf -- '-#-#- BEGIN CODEX FINDINGS -#-#-\n'
    jq -c '.findings' "$CODEX_JSON"
    printf -- '-#-#- END CODEX FINDINGS -#-#-\n\n'
    found=$((found + 1))
  else
    echo "NOTE: $CODEX_JSON holds no findings — codex ran clean on this surface" >&2
  fi
fi

if [ "$found" -eq 0 ]; then
  echo "ERROR: no review sources found in $STATE_DIR (no dim-*.json, no codex-findings.json)" >&2
  exit 1
fi
