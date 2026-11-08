#!/usr/bin/env bash
# Usage: verdicts-collect.sh <state_dir>
# Purpose: Assembles verdicts.json from per-finding verdict-<id>.json files written by
#          the orchestrator after each validate Agent returns. Writes verdicts.json to
#          the state dir and prints structured output to stdout.
#
# Output sections:
#   -#-#- VERDICTS -#-#-
#   - path: <state_dir>/verdicts.json
#   - confirmed: <N>
#   - unverifiable: <N>
#   - rejected: <N>

set -euo pipefail

STATE_DIR="${1:?Usage: verdicts-collect.sh <state_dir>}"
VERDICTS_JSON="$STATE_DIR/verdicts.json"

found=0
tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT
printf '[' > "$tmp"
first=1

for f in "$STATE_DIR"/verdict-*.json; do
  [ -f "$f" ] || continue
  verdict=$(jq -c '.' "$f" 2>/dev/null) || continue
  [ -z "$verdict" ] && continue
  [ "$first" -eq 1 ] && first=0 || printf ',' >> "$tmp"
  printf '%s' "$verdict" >> "$tmp"
  found=$((found + 1))
done
printf ']' >> "$tmp"

if [ "$found" -eq 0 ]; then
  echo '[]' > "$VERDICTS_JSON"
else
  cp "$tmp" "$VERDICTS_JSON"
fi

confirmed=$(jq '[.[] | select(.verdict=="confirmed")] | length' "$VERDICTS_JSON")
unverifiable=$(jq '[.[] | select(.verdict=="unverifiable")] | length' "$VERDICTS_JSON")
rejected=$(jq '[.[] | select(.verdict=="rejected")] | length' "$VERDICTS_JSON")

printf -- '-#-#- VERDICTS -#-#-\n'
printf -- '- path: %s\n' "$VERDICTS_JSON"
printf -- '- confirmed: %s\n' "$confirmed"
printf -- '- unverifiable: %s\n' "$unverifiable"
printf -- '- rejected: %s\n' "$rejected"
