#!/usr/bin/env bash
# Usage: state-codex-check.sh <state_dir> <codex_mode>
# Purpose: Makes a resumed run honour the current `$CODEX` value. Both lanes skip their
#          review when `findings.json` exists, and `codex-lane.md` runs inside that review
#          step — so on a resume the Codex gate is never reached. Without this check:
#            - a revision reviewed with `auto` and rerun with `--no-codex` reuses a merge
#              that holds Codex findings, and the report says Claude-only;
#            - a revision degraded under `auto` and rerun with `--codex` reuses a
#              Claude-only merge, although the user required Codex.
#
#   <state_dir>    $STATE_DIR
#   <codex_mode>   auto | on | off — the `$CODEX` value
#
# Resets the MERGE, not the review: removes findings.json, verdicts.json, every
# verdict-<id>.json and every probe-<id>.* scratch file (a re-merge renumbers the ids, so
# an old probe file would describe a different finding); for `off` also
# codex-findings.json, so merge-prep.sh cannot pick it up. The dim-*.json reviewer outputs stay, so the lane skips its reviewers and only
# merge + validation run again. `auto` never resets: it accepts whatever the cached
# merge holds, because a resume under `auto` is the common limit-stop restart.
#
# Output section:
#   -#-#- CODEX_STATE -#-#-
#   - reset: yes|no
#   - reason: <why — only when reset is yes>
#
# Exits non-zero only on bad input.

set -uo pipefail

STATE_DIR="${1:?Usage: state-codex-check.sh <state_dir> <auto|on|off>}"
CODEX="${2:?Usage: state-codex-check.sh <state_dir> <auto|on|off>}"

die() { printf -- '-#-#- CODEX_STATE -#-#-\n- error: %s\n' "$1" >&2; exit 1; }

case "$CODEX" in auto|on|off) ;; *) die "codex_mode must be auto|on|off, got '$CODEX'" ;; esac
[ -d "$STATE_DIR" ] || die "not a directory: $STATE_DIR"
command -v jq >/dev/null 2>&1 || die "jq not on PATH"

FINDINGS="$STATE_DIR/findings.json"
CODEX_JSON="$STATE_DIR/codex-findings.json"
reset=no
reason=""

if [ -f "$FINDINGS" ]; then
  case "$CODEX" in
    off)
      # `jq -e` is false on a broken file too; a broken merge is left for merge-prep.sh
      # and validate-prep.sh to reject loudly.
      if jq -e '[.findings[]? | select(.source != "claude")] | length > 0' "$FINDINGS" >/dev/null 2>&1; then
        reset=yes
        reason='findings.json holds Codex findings but $CODEX is off'
        rm -f "$CODEX_JSON"
      fi
      ;;
    on)
      if [ ! -f "$CODEX_JSON" ]; then
        reset=yes
        reason='findings.json was merged without a Codex pass but $CODEX is on'
      fi
      ;;
  esac
fi

if [ "$reset" = "yes" ]; then
  rm -f "$FINDINGS" "$STATE_DIR/verdicts.json" "$STATE_DIR"/verdict-*.json \
        "$STATE_DIR"/probe-*.kind "$STATE_DIR"/probe-*.pattern "$STATE_DIR"/probe-*.input
fi

printf -- '-#-#- CODEX_STATE -#-#-\n'
printf -- '- reset: %s\n' "$reset"
[ "$reset" = "yes" ] && printf -- '- reason: %s\n' "$reason"
exit 0
