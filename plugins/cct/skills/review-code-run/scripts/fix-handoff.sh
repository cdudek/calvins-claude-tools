#!/usr/bin/env bash
# Usage: fix-handoff.sh <findings.json> <verdicts.json>
#
# Buckets validated review-code-run findings by disposition for a fix consumer
# (review-fix-run's review-fixset-triager). Joins each finding to its
# validator verdict and routes by (verdict, suppressed_reason, severity,
# reversibility). Prints a JSON object to stdout. Used by the
# review-fixset-triager, which re-validates the `recheck` bucket before
# anything reaches the fix stage.
#
# Inputs (from review-code-run's $STATE_DIR):
#   <findings.json>  {"findings":[{id,file,line,severity,confidence,dimension,source,
#                     self_proving,evidence,body,failure_scenario,reversibility,
#                     validation_effort,idiomatic_fix?,suppressed_reason?,...}]}
#   <verdicts.json>  [{id,verdict:"confirmed"|"unverifiable"|"rejected",...}]
#
#   The buckets carry WHOLE finding objects, unprojected — every field above, and any
#   field added later, reaches the fix consumer. review-fixset-triager reads
#   `reversibility` and `idiomatic_fix` from here for fix-set.json.
#
# Routing:
#   fix_now  — verdict=confirmed AND NOT out-of-scope AND it blocks the verdict:
#              severity is anything but `suggestion`/`nit`, OR reversibility=entrenches.
#              Same floor as report-sections.md -> Verdict "What blocks", so the loop
#              fixes what would block a ship and reports the rest.
#   discuss  — verdict=confirmed AND (out-of-scope, OR below that blocking floor)
#   recheck  — verdict=unverifiable (re-validated harder by the review-fixset-triager)
#   drop     — verdict=rejected (demonstrably wrong)
#   A finding with no matching verdict defaults to `recheck` (safe — never silently fixed).
#
#   BOTH fields are case-folded. Only `severity` was, and an `Entrenches` from a reviewer
#   then failed the comparison silently: the finding fell back to severity alone and a
#   `suggestion` carrying the one axis that outranks severity routed to `discuss`.
#
#   The severity test is INVERTED on purpose — it names what does NOT block, so an
#   unknown severity (`blocker`, `high`, a future value) routes to fix_now rather than
#   being silently demoted. Erring toward fixing is the safe direction here.
#
# Output: {"fix_now":[...],"recheck":[...],"discuss":[...],"drop":[{id}]}
set -euo pipefail

F="${1:?usage: fix-handoff.sh <findings.json> <verdicts.json>}"
V="${2:?usage: fix-handoff.sh <findings.json> <verdicts.json>}"
[ -f "$F" ] || { echo "missing findings json: $F" >&2; exit 2; }
[ -f "$V" ] || { echo "missing verdicts json: $V" >&2; exit 2; }

jq -n --slurpfile f "$F" --slurpfile v "$V" '
  (reduce ($v[0][]?) as $x ({}; .[($x.id|tostring)] = $x.verdict)) as $vmap |
  def blocks($fn):
    (($fn.severity // "") | ascii_downcase) as $s |
    (($fn.reversibility // "") | ascii_downcase) as $r |
    ($s != "suggestion" and $s != "nit") or ($r == "entrenches");
  def disp($fn):
    ($vmap[($fn.id|tostring)]) as $verd |
    if   $verd == "rejected"     then "drop"
    elif $verd == "unverifiable" then "recheck"
    elif $verd == "confirmed"    then
      (if   (($fn.suppressed_reason // "") == "out-of-scope") then "discuss"
       elif blocks($fn)                                       then "fix_now"
       else "discuss" end)
    else "recheck" end;
  ($f[0].findings // []) as $findings |
  {
    fix_now: [ $findings[] | select(disp(.) == "fix_now") ],
    recheck: [ $findings[] | select(disp(.) == "recheck") ],
    discuss: [ $findings[] | select(disp(.) == "discuss") ],
    drop:    [ $findings[] | select(disp(.) == "drop") | {id} ]
  }
'
