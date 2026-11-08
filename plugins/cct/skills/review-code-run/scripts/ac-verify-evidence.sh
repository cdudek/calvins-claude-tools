#!/usr/bin/env bash
# Usage: ac-verify-evidence.sh <review_root> <ac-coverage.json>
#
# Checks that every acceptance criterion graded `covered` or `partial` cites code that is
# really there: the quoted text must occur in the cited file, and the cited line must exist.
# Deterministic — it reads files and compares strings, and calls no model.
#
# Why a quote and not just a location. In the findings pipeline `evidence` is verbatim code
# and `review-finding-validator` checks it sits at the cited line; that is what makes a finding
# falsifiable. An AC row used to carry only `file:line`, so "is the evidence non-empty" was
# the only check anyone could write, and a fabricated `covered` citing an unrelated place
# passed every one of them. A quote can be checked against the file. This closes fabrication.
#
# What it does NOT do: judge whether the quoted code has anything to do with the criterion.
# That needs a model. `ac-check.md` records it as the open half.
#
# Input — <ac-coverage.json>, as `ac-check.md` collects it from the review-criteria-auditor agent:
#   {"ac":[{"id","text","status","evidence":[{"file","line","quote"}],"note"}]}
#
# Rules, in the order they fail:
#   * `covered`                  must carry at least one evidence entry
#   * `missing`                  must carry none
#   * every entry, any status    `file` resolves INSIDE <review_root> (model output shaped by
#                                untrusted ticket text never reads outside the tree)
#   * every entry, any status    the file exists, `line` is 1..<lines in file>, and `quote`
#                                occurs in the file as a fixed string
#
# Output sections:
#   -#-#- AC_EVIDENCE -#-#-
#   - rows: <graded rows>
#   - entries: <evidence entries checked>
#   - ok: yes|no
#   - problem: <AC-n: what failed>   (one line per failure, only when ok is no)
#
# Exit: 0 every entry checks out, 1 any did not, 2 bad input.
set -euo pipefail

ROOT="${1:?usage: ac-verify-evidence.sh <review_root> <ac-coverage.json>}"
COV="${2:?usage: ac-verify-evidence.sh <review_root> <ac-coverage.json>}"
[ -d "$ROOT" ] || { echo "missing review root: $ROOT" >&2; exit 2; }
[ -f "$COV" ] || { echo "missing coverage json: $COV" >&2; exit 2; }
jq -e '.ac | type == "array"' "$COV" >/dev/null 2>&1 || { echo "not an ac-coverage document: $COV" >&2; exit 2; }

ROOT_ABS="$(cd "$ROOT" && pwd -P)"
PROBLEMS=()
ROWS=0
ENTRIES=0

# One TSV line per evidence entry, plus one per row so a row with no entries is still seen.
# `@tsv` escapes tabs and newlines inside the quote, so a multi-line quote cannot forge a row.
while IFS=$'\t' read -r id status file line quote; do
  [ -n "$id" ] || continue
  if [ "$file" = "-" ]; then
    ROWS=$((ROWS + 1))
    case "$status" in
      covered) PROBLEMS+=("$id: status is covered but the row cites nothing") ;;
    esac
    continue
  fi
  ENTRIES=$((ENTRIES + 1))
  case "$status" in
    missing) PROBLEMS+=("$id: status is missing but the row cites $file"); continue ;;
  esac

  # Resolve without following the path out of the tree. A citation is model output shaped by
  # untrusted ticket text; it never reads outside the review root.
  dir="$(cd "$(dirname -- "$ROOT_ABS/$file")" 2>/dev/null && pwd -P || true)"
  if [ -z "$dir" ]; then
    # The directory does not exist. Say that, rather than blaming the path for escaping —
    # a typo and an escape attempt need different answers from whoever reads this line.
    PROBLEMS+=("$id: cited file does not exist: $file"); continue
  fi
  inside=no
  case "$dir" in
    "$ROOT_ABS"|"$ROOT_ABS"/*) inside=yes ;;
  esac
  if [ "$inside" != yes ]; then
    PROBLEMS+=("$id: cited path resolves outside the review root: $file"); continue
  fi
  target="$dir/$(basename -- "$file")"
  if [ ! -f "$target" ]; then
    PROBLEMS+=("$id: cited file does not exist: $file"); continue
  fi

  total="$(wc -l < "$target" | tr -d ' ')"
  case "$line" in
    ''|*[!0-9]*) PROBLEMS+=("$id: cited line is not a number: $line"); continue ;;
  esac
  if [ "$line" -lt 1 ] || [ "$line" -gt "$total" ]; then
    PROBLEMS+=("$id: cited line $line is outside $file (1..$total)"); continue
  fi

  # Interpret the escapes @tsv introduced, so the comparison is against the real text.
  needle="$(printf '%b' "$quote")"
  if [ -z "$needle" ]; then
    PROBLEMS+=("$id: evidence entry carries no quote"); continue
  fi
  if ! grep -qF -- "$needle" "$target"; then
    PROBLEMS+=("$id: the quoted text is not in $file")
  fi
done < <(jq -r '
  .ac[]? |
  . as $row |
  (if (($row.evidence // []) | type) == "array" then ($row.evidence // []) else [] end) as $ev |
  if ($ev | length) == 0
  then [$row.id, $row.status, "-", "-", "-"]
  else ($ev[] | [$row.id, $row.status, (.file // ""), ((.line // "") | tostring), (.quote // "")])
  end | @tsv' "$COV")

# A row with entries was not counted above; count rows once, from the document.
ROWS="$(jq '.ac | length' "$COV")"

printf -- '-#-#- AC_EVIDENCE -#-#-\n'
printf -- '- rows: %s\n' "$ROWS"
printf -- '- entries: %s\n' "$ENTRIES"
if [ "${#PROBLEMS[@]}" -eq 0 ]; then
  printf -- '- ok: yes\n'
  exit 0
fi
printf -- '- ok: no\n'
for p in "${PROBLEMS[@]}"; do printf -- '- problem: %s\n' "$p"; done
exit 1
