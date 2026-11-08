#!/usr/bin/env bash
# Usage: codex-filter-diff.sh <diff_in> <diff_out>
# Purpose: Copies a unified diff and drops every file section that must not reach Codex:
#            1. a section whose path is secret-shaped (`codex-scan-secrets.sh --match-names`
#               decides — one source of patterns, shared with the mirror scan);
#            2. a section that touches a SYMLINK (a `120000` mode line). In a git diff the
#               content of a symlink is its target path, so the hunk would send that path.
#               The mirror withholds every symlink; the diff must too.
#          The sanitized mirror keeps such files away from Codex, but the diff is embedded
#          in the prompt as text: a diff that adds `.env` carries the secret in its `+`
#          lines, one that deletes it carries it in its `-` lines, and the mirror does
#          nothing for either.
#
# A dropped section is replaced by one line, so Codex knows a file is missing:
#   [withheld: <path> — secret-shaped file or symlink; its hunks were removed before sending]
#
# Which paths a section names is decided CONSERVATIVELY. The `diff --git a/<a> b/<b>`
# header is ambiguous when a path itself contains " b/" (a rename of `config b/.env` reads
# `diff --git a/config b/.env b/safe.txt`), so every possible split of that header is a
# candidate, and so are the unambiguous one-path-per-line headers that follow it
# (`--- a/`, `+++ b/`, `rename from`, `rename to`, `copy from`, `copy to`). A section is
# withheld when ANY candidate is secret-shaped. Ambiguity therefore errs toward
# withholding, never toward sending.
#
# Output sections:
#   -#-#- DIFF_FILTER -#-#-
#   - status: ok|failed
#   - out: <diff_out — only when status is ok>
#   - withheld: <N file sections removed — only when status is ok>
#   - reason: <why it failed — only when status is failed>
#
# FAIL CLOSED. Exit status is 0 on `ok` and 1 on `failed`. On a failure the caller must
# not send the unfiltered diff. The filtered diff is re-checked with the same conservative
# extraction before it is reported: if any section still names a secret-shaped path or a
# symlink, the filter refuses.

set -uo pipefail

DIFF_IN="${1:?Usage: codex-filter-diff.sh <diff_in> <diff_out>}"
DIFF_OUT="${2:?Usage: codex-filter-diff.sh <diff_in> <diff_out>}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCAN="$SCRIPT_DIR/codex-scan-secrets.sh"

fail() {
  printf -- '-#-#- DIFF_FILTER -#-#-\n'
  printf -- '- status: failed\n'
  printf -- '- reason: %s\n' "$1"
  exit 1
}

[ -r "$DIFF_IN" ] || fail "diff not readable: $DIFF_IN"
[ -f "$SCAN" ] || fail "missing scanner: $SCAN"

WORK="$(mktemp -d)" || fail "could not create a work dir"
trap 'rm -rf "$WORK"' EXIT

# Pass 1 — candidates. Prints `<section>\t<path>` for every path a section may name, and
# `<section>\tSYMLINK` for a section with a 120000 mode line. Sections are numbered from
# 1 in order of their `diff --git` header. "diff --git a/" is 13 characters. A quoted
# path (git quotes names with special characters) loses its surrounding quotes so the
# basename still matches.
extract_candidates() {   # extract_candidates <diff>
  awk '
    function emit(p) {
      if (p ~ /^".*"$/) p = substr(p, 2, length(p) - 2)
      if (p != "") print n "\t" p
    }
    /^diff --git a\// {
      n++
      s = substr($0, 14)
      emit(s)
      start = 1
      while ((i = index(substr(s, start), " b/")) > 0) {
        p = start + i - 1
        emit(substr(s, 1, p - 1))
        emit(substr(s, p + 3))
        start = p + 1
      }
      next
    }
    n == 0 { next }
    /^--- a\//              { emit(substr($0, 7)); next }
    /^\+\+\+ b\//           { emit(substr($0, 7)); next }
    /^rename from /         { emit(substr($0, 13)); next }
    /^rename to /           { emit(substr($0, 11)); next }
    /^copy from /           { emit(substr($0, 11)); next }
    /^copy to /             { emit(substr($0, 9)); next }
    /^(old mode|new mode|deleted file mode|new file mode) 120000/ { print n "\tSYMLINK"; next }
  ' "$1"
}

# Which sections must go: any candidate path that is secret-shaped, plus every symlink
# section. Writes one section number per line to <out>. Fails closed.
withheld_sections() {   # withheld_sections <candidates-file> <out-file>
  local match="$WORK/match.txt" paths="$WORK/paths.txt" secret="$WORK/secret.txt"
  cut -f2 "$1" | grep -vx 'SYMLINK' | sort -u > "$paths"
  if ! bash "$SCAN" --match-names < "$paths" > "$match" 2>&1; then
    fail "name matching failed: $(sed -n 's/^- reason: //p' "$match" | head -1)"
  fi
  grep -qx -- '- status: ok' "$match" || fail "name matching did not report status ok"
  sed -n '/^-#-#- BEGIN SECRET_PATHS -#-#-$/,/^-#-#- END SECRET_PATHS -#-#-$/p' "$match" \
    | sed '1d;$d' > "$secret"
  {
    awk -F'\t' 'NR == FNR { w[$0] = 1; next } ($2 in w) { print $1 }' "$secret" "$1"
    awk -F'\t' '$2 == "SYMLINK" { print $1 }' "$1"
  } | sort -un > "$2"
}

extract_candidates "$DIFF_IN" > "$WORK/cand" || fail "could not read the diff headers"
withheld_sections "$WORK/cand" "$WORK/skip"

# Pass 2 — copy the diff, skipping every withheld section. The marker names the header's
# last `b/` half: the new path in the common case, a best guess when the header is
# ambiguous. The marker is for the reader; the decision above did not depend on it.
awk -v S="$WORK/skip" -v C="$WORK/count" '
  BEGIN { while ((getline l < S) > 0) if (l != "") skipset[l] = 1; close(S); n = 0; k = 0; skip = 0 }
  /^diff --git a\// {
    n++
    skip = (n in skipset) ? 1 : 0
    if (skip) {
      k++
      s = substr($0, 14); b = s
      start = 1
      while ((i = index(substr(s, start), " b/")) > 0) { p = start + i - 1; b = substr(s, p + 3); start = p + 1 }
      print "[withheld: " b " — secret-shaped file or symlink; its hunks were removed before sending]"
      next
    }
  }
  !skip { print }
  END { print k > C }
' "$DIFF_IN" > "$WORK/out.diff" || fail "could not filter the diff"

withheld=$(cat "$WORK/count" 2>/dev/null)
[ -n "${withheld:-}" ] || fail "filter produced no count"

# Verify the OUTPUT the same conservative way, not the list: any remaining section that
# names a secret-shaped path or is a symlink means the filter failed.
extract_candidates "$WORK/out.diff" > "$WORK/cand2" || fail "could not re-read the filtered diff"
withheld_sections "$WORK/cand2" "$WORK/leaked"
leaked=$(grep -c . "$WORK/leaked" || true)
[ "${leaked:-0}" = "0" ] || fail "the filtered diff still holds ${leaked} withheld section(s) — refusing"

mv "$WORK/out.diff" "$DIFF_OUT" || fail "could not write the filtered diff to $DIFF_OUT"

printf -- '-#-#- DIFF_FILTER -#-#-\n'
printf -- '- status: ok\n'
printf -- '- out: %s\n' "$DIFF_OUT"
printf -- '- withheld: %s\n' "$withheld"
