#!/usr/bin/env bash
# Usage: state-dir.sh <mode> <lane> <key> [files-list]
# Purpose: Computes the review state dirs for one run and creates them. Replaces the
#          prose recipe that every mode used to follow by hand.
#
#   <mode>        pr | changes | files
#   <lane>        deep | max
#   <key>         pr:      the PR number
#                 changes: the branch name as-is (the script makes the slug)
#                 files:   ignored — the session id is the key
#   [files-list]  files mode only: a file holding the newline-separated review file list.
#                 The revision id is a digest of those files' CONTENTS, so run this from
#                 the review root ($ROOT) and list paths relative to it. A missing file is
#                 an error, not a partial digest.
#
# Layout:
#   STATE_BASE = <base>/review-<mode>-<lane>-<key>     stable per target; accumulators live here
#   STATE_DIR  = STATE_BASE/rev-<revid>                one dir per reviewed revision
#
#   mode     base                 key                              revid
#   pr       dirname($TMPDIR)     <repo>-pr-<number>               git HEAD (12 chars)
#   changes  dirname($TMPDIR)     <repo>-<branch-slug>             git HEAD (12 chars)
#   files    $TMPDIR              $CLAUDE_CODE_SESSION_ID          digest of the file list
#
# pr and changes resume across sessions (dirname($TMPDIR) is stable). files does not.
# A new commit or a changed file set gives a new STATE_DIR, so a resumed run never
# reads stale artifacts.
#
# Output sections:
#   -#-#- STATE -#-#-
#   - state_base: <path>
#   then state-restart.sh's RESTART section (state_dir, revid, status, pruned)
#
# Exits non-zero with `- error:` on bad input.

set -euo pipefail

MODE="${1:-}"; LANE="${2:-}"; KEY="${3:-}"; FILES_LIST="${4:-}"

die() { printf -- '-#-#- STATE -#-#-\n- error: %s\n' "$1" >&2; exit 1; }

case "$MODE" in pr|changes|files) ;; *) die "mode must be pr|changes|files, got '${MODE}'" ;; esac
case "$LANE" in deep|max) ;; *) die "lane must be deep|max, got '${LANE}'" ;; esac

TMP="${TMPDIR:-/tmp}"
TMP="${TMP%/}"

case "$MODE" in
  pr)
    [ -n "$KEY" ] || die "pr mode needs the PR number as <key>"
    repo=$(basename "$(git rev-parse --show-toplevel)") || die "not inside a git repo"
    base="$(dirname "$TMP")"; key="${repo}-pr-${KEY}"
    revid=$(git rev-parse --short=12 HEAD)
    ;;
  changes)
    [ -n "$KEY" ] || die "changes mode needs the branch name as <key>"
    repo=$(basename "$(git rev-parse --show-toplevel)") || die "not inside a git repo"
    # Every char outside [a-zA-Z0-9_-] becomes '-', so shell metacharacters never reach
    # the path. The trailing sed removes the '-' that tr leaves for the final newline.
    slug=$(printf '%s' "$KEY" | tr -c 'a-zA-Z0-9_-' '-' | sed 's/-*$//')
    base="$(dirname "$TMP")"; key="${repo}-${slug}"
    revid=$(git rev-parse --short=12 HEAD)
    ;;
  files)
    [ -r "${FILES_LIST:-/nonexistent}" ] || die "files mode needs a readable files-list file as 4th argument"
    base="$TMP"; key="${CLAUDE_CODE_SESSION_ID:-$$}"
    # Every listed file must exist here: the digest is of contents, and a missing file
    # would otherwise abort mid-pipeline with only shasum's stderr to explain it.
    while IFS= read -r f; do
      [ -z "$f" ] && continue
      [ -f "$f" ] || die "listed file not found from $(pwd): $f"
    done < "$FILES_LIST"
    # shasum -a 256 exists on macOS and Linux; sha256sum does not ship on macOS.
    revid=$(sort "$FILES_LIST" | tr '\n' '\0' | xargs -0 shasum -a 256 | shasum -a 256 | cut -c1-12)
    ;;
esac

STATE_BASE="${base}/review-${MODE}-${LANE}-${key}"

printf -- '-#-#- STATE -#-#-\n'
printf -- '- state_base: %s\n' "$STATE_BASE"
exec bash "$(dirname "${BASH_SOURCE[0]}")/state-restart.sh" "$STATE_BASE" "$revid"
