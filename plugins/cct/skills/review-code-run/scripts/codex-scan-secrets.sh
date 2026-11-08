#!/usr/bin/env bash
# Usage: codex-scan-secrets.sh <root> [--no-prune]
#        codex-scan-secrets.sh --match-names   (reads paths from stdin, one per line)
# Purpose: Lists the paths under <root> that `codex-review.sh` must withhold from the
#          sanitized mirror it sends to Codex, one relative path per line. Two kinds:
#            1. regular files whose NAME says secret (`.env`, `*.pem`, `.npmrc`, ...);
#            2. EVERY symlink, whatever its name. A link can point anywhere, and Codex
#               follows it when it reads. `logo.svg -> ~/.ssh/id_rsa` has no secret in
#               its name, and `rsync -a` copies the link as a link. Resolving each target
#               and keeping the in-tree ones would be more precise; withholding all of
#               them is smaller and errs the safe way.
#               ponytail: resolve targets (readlink) and keep in-tree links if Codex
#               visibly loses context it needs.
#          Single source of truth for the name patterns — do not duplicate them.
#
# `--match-names` applies the SAME name patterns to paths read from stdin and prints the
# ones that match. It touches no file. `codex-filter-diff.sh` uses it to drop the hunks
# of secret-shaped files from the diff `codex-review.sh` embeds in the prompt: the
# mirror is sanitized, but a diff that adds `.env` carries the secret in its own `+`
# lines, and a diff that deletes one carries it in the `-` lines.
#
# Name matching only. This script NEVER opens or reads a file's contents: that is an
# organization rule about secrets, not a performance shortcut. Use `find -name`;
# never `cat`, `grep` or `head` a candidate.
#
# Output sections (both modes):
#   -#-#- BEGIN SECRET_PATHS -#-#-
#   <relative path>            (one per line; empty section when none found)
#   -#-#- END SECRET_PATHS -#-#-
#   -#-#- SECRET_SCAN -#-#-
#   - status: ok|failed
#   - count: <N>
#   - pruned: <comma-separated directory names this walk skipped; empty for --match-names>
#   - reason: <why it failed — only when status is failed>
#
# `--no-prune` walks everything, skipping nothing. Use it to VERIFY a tree you control
# and expect to be clean — `codex-review.sh` verifies the finished mirror this way.
# Pruning is a speed-up for the source scan, but it makes the scan blind inside the
# skipped directories; verifying with the same blind spots would mean a secret that
# reached the mirror through a mis-built prune argument goes unseen. The mirror is
# already small, so a full walk of it costs nothing worth saving.
#
# `- pruned:` exists to enforce an invariant, not to inform: a directory this scan
# skips is a directory it cannot vouch for, so the caller MUST also keep it out of
# whatever it sends to Codex. Widening the prune set without honouring that turns a
# speed-up into a fail-open hole. `codex-review.sh` builds its rsync excludes from
# this field for exactly that reason — one source, so the two cannot drift.
#
# FAIL CLOSED. Exit status is 0 on `ok` and 1 on `failed`, and the caller MUST refuse
# to send anything to Codex on a failure. An empty list has to mean "nothing
# secret-shaped is here" and never "the scan did not run": under the mirror design the
# list IS the exclusion set, so a silently empty result would ship the very files it
# exists to withhold.

set -uo pipefail

ROOT="${1:-}"
NO_PRUNE=0
MATCH_NAMES=0
[ "${2:-}" = "--no-prune" ] && NO_PRUNE=1
[ "$ROOT" = "--match-names" ] && MATCH_NAMES=1

emit_failure() {
  printf -- '-#-#- BEGIN SECRET_PATHS -#-#-\n'
  printf -- '-#-#- END SECRET_PATHS -#-#-\n'
  printf -- '-#-#- SECRET_SCAN -#-#-\n'
  printf -- '- status: failed\n'
  printf -- '- count: 0\n'
  printf -- '- pruned: %s\n' "${pruned_csv:-}"
  printf -- '- reason: %s\n' "$1"
  exit 1
}

emit_ok() {   # emit_ok <paths, each with a trailing newline> <count> <pruned_csv>
  printf -- '-#-#- BEGIN SECRET_PATHS -#-#-\n'
  printf -- '%s' "$1"
  printf -- '-#-#- END SECRET_PATHS -#-#-\n'
  printf -- '-#-#- SECRET_SCAN -#-#-\n'
  printf -- '- status: ok\n'
  printf -- '- count: %s\n' "$2"
  printf -- '- pruned: %s\n' "$3"
}

# The name patterns: shell globs matched against the BASENAME. The `find` expression
# and `--match-names` are both built from this one list.
#
# `.env.example` / `.env.sample` are templates, not secrets (SECRET_NAME_EXCEPTIONS).
# `*.ejson` is absent on purpose: keymaster ejson files are encrypted by design, and the
# plaintext `.env` they decrypt into is what the `.env` pattern already catches.
# `.envrc` is direnv (`export AWS_SECRET_ACCESS_KEY=...`); `.flaskenv` is Flask's twin.
SECRET_NAME_GLOBS=(
  '.env' '.env.*' '.envrc' '.flaskenv'
  '*.pem' '*.key' 'id_rsa' 'id_ed25519' '*.p12' '*.pfx'
  'credentials.json' 'service-account*.json'
  '.netrc' '.npmrc' '.pypirc'
  '.zshrc' '.bashrc' '.bash_profile' '.profile'
)
SECRET_NAME_EXCEPTIONS=( '.env.example' '.env.sample' )

name_is_secret() {   # name_is_secret <basename>; returns 0 when the name matches
  local b="$1" g
  for g in "${SECRET_NAME_EXCEPTIONS[@]}"; do
    [ "$b" = "$g" ] && return 1
  done
  for g in "${SECRET_NAME_GLOBS[@]}"; do
    # $g must stay unquoted: quoted, it is a literal string, not a pattern.
    # shellcheck disable=SC2254
    case "$b" in $g) return 0 ;; esac
  done
  return 1
}

# ---------------------------------------------------------------------------
# --match-names: paths in, secret-shaped paths out. No filesystem access.
# ---------------------------------------------------------------------------
if [ "$MATCH_NAMES" -eq 1 ]; then
  pruned_csv=""
  matched=""
  count=0
  while IFS= read -r p; do
    [ -n "$p" ] || continue
    if name_is_secret "${p##*/}"; then
      matched="${matched}${p}"$'\n'
      count=$((count + 1))
    fi
  done
  emit_ok "$matched" "$count" ""
  exit 0
fi

[ -n "$ROOT" ] || emit_failure "no root given (usage: codex-scan-secrets.sh <root> | --match-names)"
# A missing or unreadable root must never read as a clean tree.
[ -d "$ROOT" ] || emit_failure "root is not a directory: $ROOT"
[ -r "$ROOT" ] || emit_failure "root is not readable: $ROOT"

root="${ROOT%/}"

# Directory names skipped by the walk. Vendor, build and cache trees: a dependency's
# fixture is not the user's secret, and walking them dominates the runtime on a large
# repo. Anything added here MUST also be excluded from the mirror — see `- pruned:`.
PRUNE_DIRS=(
  .git node_modules vendor dist
  tmp log coverage
  .nuxt .output .turbo .next .cache
  .pnpm-store .yarn storybook-static
  __pycache__ .venv .tox
)

if [ "$NO_PRUNE" -eq 1 ]; then
  PRUNE_DIRS=()
fi

pruned_csv=$(IFS=,; printf '%s' "${PRUNE_DIRS[*]:-}")

prune_expr=()
for d in "${PRUNE_DIRS[@]:-}"; do
  [ -n "$d" ] || continue
  prune_expr+=( -name "$d" -o )
done
if [ "${#prune_expr[@]}" -gt 0 ]; then
  unset "prune_expr[${#prune_expr[@]}-1]"   # drop the trailing -o
fi

# `( -name A -o -name B ... ) ! -name X ! -name Y`. The exceptions sit OUTSIDE the
# alternatives group: `!` binds tighter than `-o`, so placed inside they would apply to
# the last alternative only.
name_expr=()
for g in "${SECRET_NAME_GLOBS[@]}"; do
  name_expr+=( -name "$g" -o )
done
unset "name_expr[${#name_expr[@]}-1]"       # drop the trailing -o
except_expr=()
for g in "${SECRET_NAME_EXCEPTIONS[@]}"; do
  except_expr+=( ! -name "$g" )
done

# `find` writes into a temp file rather than a process substitution: bash cannot report
# the exit status of a process substitution, and an unreadable subtree makes `find`
# return non-zero with a PARTIAL result. A partial exclusion set is exactly the
# fail-open case this script exists to prevent, so its status has to be checkable.
raw="$(mktemp)" || emit_failure "could not create a temp file for the scan"
trap 'rm -f "$raw"' EXIT

# Two branches: every symlink (`-type l`, no name test), or a regular file whose name
# matches. `find` does not follow links, so a symlink to a directory is one entry here
# and is withheld whole. The pruned set is PRUNE_DIRS above.
if [ "${#prune_expr[@]}" -gt 0 ]; then
  set -- "$root" \( -type d \( "${prune_expr[@]}" \) \) -prune -o
else
  set -- "$root"
fi

find "$@" \
  \( -type l -o \( -type f \( "${name_expr[@]}" \) "${except_expr[@]}" \) \) -print0 > "$raw"
find_status=$?
[ "$find_status" -eq 0 ] || \
  emit_failure "find failed over $root (exit $find_status) — partial scan, refusing"

findings=""
count=0
while IFS= read -r -d '' f; do
  rel="${f#"$root"/}"
  # A newline in a path would corrupt the one-path-per-line contract this script emits
  # and that `rsync --exclude-from` consumes. Refuse rather than mis-split.
  # $'\n' below is a real newline. "$(printf '\n')" would NOT be — command substitution
  # strips trailing newlines, leaving an empty pattern that matches every path.
  case "$rel" in
    *$'\n'*) emit_failure "a matched path contains a newline and cannot be excluded safely" ;;
  esac
  findings="${findings}${rel}"$'\n'
  count=$((count + 1))
done < "$raw"

emit_ok "$findings" "$count" "$pruned_csv"
