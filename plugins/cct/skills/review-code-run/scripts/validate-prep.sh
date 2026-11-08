#!/usr/bin/env bash
# Usage: validate-prep.sh <findings_json>
# Purpose: Reads findings.json and outputs the validation queue as a JSON array,
#          sorted heaviest-first (validation_effort desc; ties: self_proving=false first,
#          then severity weight critical=3 warning=2 suggestion=1 nit=0).
#          The orchestrator iterates this array and spawns one validate Agent per entry
#          following validate-agent.md.
#
# Output sections:
#   -#-#- BEGIN VALIDATE_QUEUE -#-#-
#   [{id, file, line, body, failure_scenario, evidence, self_proving, validation_effort,
#     executable_claim?, probe_kind?, probe_pattern?, probe_input?}, ...]
#   -#-#- END VALIDATE_QUEUE -#-#-
#   The four probe fields appear together, and only when executable_claim is true — the
#   orchestrator reads them from this queue to run probe-pattern.sh (pipeline-tail.md).
#   -#-#- COUNT -#-#-
#   - count: <N>

set -euo pipefail

FINDINGS_JSON="${1:?Usage: validate-prep.sh <findings_json>}"

[ -f "$FINDINGS_JSON" ] || { echo "ERROR: $FINDINGS_JSON not found" >&2; exit 1; }

queue=$(jq '[
  .findings
  | map(select(. != null))
  | sort_by(
      -((.validation_effort // 0)),
      (if .self_proving then 1 else 0 end),
      -({"critical":3,"warning":2,"suggestion":1,"nit":0}[.severity] // 1)
    )
  | .[]
  | {id, file, line, body, failure_scenario, evidence, self_proving, validation_effort}
    + (if .executable_claim == true
       then {executable_claim, probe_kind, probe_pattern, probe_input}
       else {} end)
]' "$FINDINGS_JSON")

count=$(printf '%s' "$queue" | jq 'length')

printf -- '-#-#- BEGIN VALIDATE_QUEUE -#-#-\n'
printf '%s\n' "$queue"
printf -- '-#-#- END VALIDATE_QUEUE -#-#-\n'
printf -- '-#-#- COUNT -#-#-\n'
printf -- '- count: %s\n' "$count"
