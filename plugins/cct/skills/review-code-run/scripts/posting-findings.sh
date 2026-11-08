#!/usr/bin/env bash
# Usage: bash .../scripts/posting-findings.sh <findings.json> <verdicts.json>
#
# Builds the postable findings array for posting-pipeline.md. Selects validator-CONFIRMED
# findings only, drops the demoted (suppressed_reason) appendix, drops `severity: nit`, and
# maps each to the shape reconcile-threads.md expects. Prints a JSON array to stdout.
#
# Inputs (from $STATE_DIR or equivalent):
#   <findings.json>  {"findings":[{id,file,line,severity,confidence,dimension,body,failure_scenario,
#                      reversibility,idiomatic_fix?,suppressed_reason?}]}
#   <verdicts.json>  [{id,verdict:"confirmed"|"unverifiable"|"rejected",confidence}]
#
# Output: [{id,path,line,side,severity,category,body,failure_scenario,idiomatic_fix,
#           confidence,reversibility}, ...]
#         (confirmed only, non-suppressed, suggestion severity and above;
#          reversibility is cheap | entrenches | unstated)
#
# Beyond the demoted appendix, two more exclusions decide what a PR author is made to read.
# All three live here, and only here, so every pr path inherits them; `pr-quick` runs no
# script and restates them itself.
#
#   `nit`          — worth a line in the terminal report and worth fixing in the loop, but
#                    a thread costs the author a notification and a reply for a naming
#                    preference. `suggestion` is the floor.
#   `unverifiable` — a validator could not confirm it against the code. It still belongs in
#                    the review body as a short list the author can check (posting-pipeline.md
#                    Phase 3), because an unconfirmed claim asked as a thread reads as a
#                    defect report and is answered as one.
#
# The fix loop is unaffected: it reads fix-handoff.sh, which keeps both buckets.
#
# `body`, `failure_scenario` and `idiomatic_fix` are carried because posting-pipeline.md
# Phase 3 composes the posted comment out of this array and nothing else: `body` and
# `failure_scenario` are the two sentences of finding-format.md Section C, and
# `idiomatic_fix` is its suggestion block. A field missing here cannot reach the PR
# author, and nothing errors — the comment simply posts without its reason or without
# its fix. `failure_scenario` gets no default here: merge.md already resolves a missing
# one to `unstated` before findings.json exists.
#
# `reversibility` is carried because reconcile-threads.md reopens a DECLINED concern
# and treats `entrenches` as the case where "deferred to a follow-up ticket" is least
# acceptable. Drop it here and that rule can never fire.
#
# A MISSING value becomes `unstated`, not `cheap` and not `entrenches`. The field is
# prompt-only for Claude-sourced findings (no schema enforces it), so omission is an
# ordinary event rather than a broken response — unlike codex-review.sh, where the
# schema requires the enum and an off-enum value therefore means the response itself
# broke and erring high is right. Defaulting to `cheap` would silently drop the
# DECLINED-reopen protection; defaulting to `entrenches` would mark nearly every
# finding as entrenching during rollout. `unstated` says what is true: unknown.
#   side is "RIGHT" — review findings target added/context lines (PR head); reconcile-threads.md
#   preserves it through to the posting scripts, which require a non-null DiffSide on every new thread.
set -euo pipefail

F="${1:?usage: posting-findings.sh <findings.json> <verdicts.json>}"
V="${2:?usage: posting-findings.sh <findings.json> <verdicts.json>}"
[ -f "$F" ] || { echo "missing findings json: $F" >&2; exit 2; }
[ -f "$V" ] || { echo "missing verdicts json: $V" >&2; exit 2; }

jq -n --slurpfile f "$F" --slurpfile v "$V" '
  (reduce ($v[0][]? | select(.verdict == "confirmed")) as $x
    ({}; .[($x.id|tostring)] = true)) as $ok
  | [ ($f[0].findings // [])[]
      | select($ok[(.id|tostring)])
      | select((.suppressed_reason // "") == "")
      | select(.severity != "nit")
      | {id, path: .file, line: .line, side: "RIGHT", severity, category: .dimension,
         body, failure_scenario, idiomatic_fix, confidence,
         reversibility: (.reversibility // "unstated")} ]
'
