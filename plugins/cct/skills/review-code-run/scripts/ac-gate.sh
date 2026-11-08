#!/usr/bin/env bash
# Usage: ac-gate.sh <state_dir> [<input_md>]
#        ac-gate.sh <state_dir> --not-applicable
#
# Decides whether this review can audit acceptance criteria, and extracts them.
# Pure text extraction from INPUT.md — no model, no judgement, so the gate answers
# the same way on every run. Writes <state_dir>/ac.json and prints one section.
#
# `--not-applicable` is for `files` mode, which reviews code as it is and has no
# ticket by design. It is a separate reason from `no-reference` on purpose:
# `no-reference` names a gap someone could close, `not-applicable` names one nobody
# can.
#
# ac.json, one of two shapes:
#   {"mode":"ac","source":"ENG-123","criteria":[{"id":"AC-1","text":"…"}]}
#   {"mode":"none","reason":"<see below>","detail":"…"}
#
# A ticket often writes its criteria as a task list. The leading `[x]` / `[ ]` marker is
# stripped: it is the ticket author's own claim that the criterion is done, and handing it
# to the auditor anchors the grading toward `covered` before it reads a line of code.
# Observed on SUPPLY-572, whose four criteria all arrive as `- [X] Given ... then ...`.
#
# reason values:
#   no-reference    no INPUT.md, or it resolved no ticket at all
#   unresolved      a reference was found but could not be fetched (see INPUT.md
#                   -> "## Unresolved references"); re-running may fix it
#   no-criteria     a reference resolved but states no acceptance criteria
#   not-applicable  files mode
#
# Output sections:
#   -#-#- AC_GATE -#-#-
#   - mode: ac|none
#   - reason: <only when mode is none>
#   - source: <only when mode is ac>
#   - criteria: <count, only when mode is ac>
#   - file: <path to ac.json>
set -euo pipefail

STATE_DIR="${1:?usage: ac-gate.sh <state_dir> [<input_md>|--not-applicable]}"
ARG2="${2-}"
[ -d "$STATE_DIR" ] || { echo "missing state dir: $STATE_DIR" >&2; exit 2; }
OUT="$STATE_DIR/ac.json"

emit_none() {
  jq -n --arg r "$1" --arg d "${2-}" \
    '{mode:"none", reason:$r} + (if $d == "" then {} else {detail:$d} end)' > "$OUT"
  printf -- '-#-#- AC_GATE -#-#-\n'
  printf -- '- mode: none\n'
  printf -- '- reason: %s\n' "$1"
  printf -- '- file: %s\n' "$OUT"
  exit 0
}

if [ "$ARG2" = "--not-applicable" ]; then
  emit_none not-applicable "files mode reviews code as it is; there is no ticket"
fi

INPUT="$ARG2"
if [ -z "$INPUT" ] || [ ! -f "$INPUT" ]; then
  emit_none no-reference "no INPUT.md — nothing resolved a ticket for this review"
fi

# Collect the bullets under every `Acceptance criteria:` label INSIDE a [REF] block. A
# wrapped bullet keeps its continuation lines; one of the block's own labels, a new [REF]
# block or a markdown heading ends the list. Rule order is the logic — awk takes the first
# match that calls next.
#
# Three things this state machine is deliberate about:
#
#   * `inref` — the label is only a trigger inside a [REF] block. Unscoped, a user pasting
#     ticket text under "## User commentary" had it graded as the ticket's own criteria,
#     with an empty source, and it could floor the verdict on text nobody wrote as a
#     criterion. INPUT.md's commentary is untrusted DATA everywhere else; it is here too.
#   * Bullet forms — `-`, `*`, `1.` and `1)`. A ticket writing its criteria as a numbered
#     list used to extract ZERO of them and report `no-criteria`: the whole audit skipped,
#     announced as "the ticket states none". That is the failure this gate exists to
#     prevent, produced by the gate.
#   * `ref` travels with the criterion. Emitting `<ref>\t<text>` per line means the source
#     is the block that actually fed the list. A separate pass that stopped at the first
#     `Acceptance criteria:` line credited the wrong ticket whenever an earlier block said
#     "none stated".
#
# The label set is COUPLED to reference-resolution.md § 3. Add a label there, add it to
# is_label() here, or a real label will be swallowed into the criterion above it.
ROWS="$(awk '
  function flush() { if (cur != "") { print ref "\t" cur; cur = "" } }
  # The labels that end the list are the CLOSED set reference-resolution.md writes into a
  # [REF] block. A generic /^Word:/ rule read an ordinary line — "Note: a tenant with no
  # rows still gets an empty file." — as a label and dropped every criterion after it,
  # while still reporting mode: ac. A line outside this set now joins the criterion above
  # it: visible noise in one row, never a silent loss of the rows below.
  function is_label(s,   l) {
    l = tolower(s)
    return (l ~ /^title:/ || l ~ /^status:/ || l ~ /^purpose:/ ||
            l ~ /^constraints\/decisions:/ || l ~ /^out of scope:/)
  }
  /^\[REF\]/                                  { flush(); inref = 1; inac = 0
                                                ref = $2
                                                next }
  /^##/                                       { flush(); inref = 0; inac = 0; next }
  inref && /^[Aa]cceptance [Cc]riteria:/      { flush(); inac = 1; next }
  inac && /^[[:space:]]*([-*]|[0-9]+[.)])[[:space:]]+/ {
                                                flush()
                                                line = $0
                                                sub(/^[[:space:]]*([-*]|[0-9]+[.)])[[:space:]]+/, "", line)
                                                sub(/^\[[ xX]\][[:space:]]*/, "", line)
                                                cur = line
                                                next }
  inac && is_label($0)                        { flush(); inac = 0; next }
  inac && /^[[:space:]]*$/                    { next }
  inac && cur != ""                           { line = $0
                                                sub(/^[[:space:]]+/, "", line)
                                                cur = cur " " line
                                                next }
  END { flush() }
' "$INPUT")"

CRIT="$(printf '%s' "$ROWS" | cut -f2-)"

COUNT=0
[ -n "$CRIT" ] && COUNT=$(printf '%s\n' "$CRIT" | grep -c . || true)

if [ "$COUNT" -eq 0 ]; then
  if grep -qi '^## Unresolved references' "$INPUT"; then
    emit_none unresolved "$(grep -A2 -i '^## Unresolved references' "$INPUT" | tail -n +2 | tr '\n' ' ' | cut -c1-200)"
  elif grep -q '^\[REF\]' "$INPUT"; then
    emit_none no-criteria "a reference resolved but states no acceptance criteria"
  else
    emit_none no-reference "INPUT.md carries no resolved reference"
  fi
fi

# The ref of the block that fed the first criterion. Informational only — the audit reads
# `criteria`, never `source` — but a wrong ticket in the report is still a wrong report.
SRC="$(printf '%s' "$ROWS" | head -1 | cut -f1)"

printf '%s\n' "$CRIT" | jq -R -s --arg src "$SRC" '
  {mode: "ac",
   source: $src,
   criteria: (split("\n")
              | map(select(length > 0))
              | to_entries
              | map({id: ("AC-" + ((.key + 1) | tostring)), text: .value}))}' > "$OUT"

printf -- '-#-#- AC_GATE -#-#-\n'
printf -- '- mode: ac\n'
printf -- '- source: %s\n' "${SRC:-unknown}"
printf -- '- criteria: %s\n' "$COUNT"
printf -- '- file: %s\n' "$OUT"
