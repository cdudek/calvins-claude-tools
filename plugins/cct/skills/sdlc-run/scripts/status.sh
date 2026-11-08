#!/usr/bin/env bash
# List every open change and where it is in the chain.
#
#   status.sh            open changes: id · linear · state · PR
#   status.sh --current  the change for the checked-out branch (slug match), or "none"
#   status.sh --shipped [n]  the archive, newest SHIPPED first (default 20)
#   status.sh <id>       one change, plus `git log --follow` of its plan.md (the revision history)
#
# Every run first says whether this repo's copied hooks, workflows and guardrail test still
# match the installed kit. They are copies because CI has no plugin to read.
set -uo pipefail
root="${CLAUDE_PROJECT_DIR:-$(pwd)}"
cfg="$root/sdlc.json"
[ -f "$cfg" ] || { echo "no sdlc.json at $root -- run: sdlc-run adopt"; exit 1; }
changes=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("changesDir","changes"))' "$cfg")

# -#-#- TEMPLATES -#-#-  stale means: the kit moved, this repo's copies did not.
have=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("kitTemplates",""))' "$cfg")
want=$(python3 "$(dirname "$0")/adopt.py" --templates-hash 2>/dev/null || echo "")
if [ -n "$want" ] && [ "$have" != "$want" ]; then
  # A repo adopted before the stamp existed has no kitTemplates at all; "( -> abc123)"
  # reads like a bug rather than an answer.
  echo "templates=stale (${have:-never stamped} -> $want) -- run: /cct:sdlc-run adopt"
else
  echo "templates=current"
fi
# -#-#- VERSION -#-#-  one line when sdlc.json sdlcVersion is missing, older or newer than the kit.
python3 "$(dirname "$0")/../templates/scripts/sdlc_version.py" "$root" 2>/dev/null || true
branch=$(git -C "$root" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
mode="${1:-}"

# --- --shipped ------------------------------------------------------------------------
# Ship order is NOT folder order. The name carries the day the work started and never
# changes, so `ls` answers "what did we pick up when". 18 of 52 folders in one repo sit
# somewhere else under ship order (max lag 7 days), and that answer lives in `archived_at`.
# A view, deliberately: encoding it in the name would break "archiving moves the folder, it
# never renames it", which is what keeps `git log --follow` readable across the boundary.
if [ "$mode" = "--shipped" ]; then
  limit="${2:-20}"
  find "$root/$changes/archive" -mindepth 1 -name plan.md -print 2>/dev/null | while read -r plan; do
    d=$(dirname "$plan")
    shipped=$(sed -n 's/^archived_at: *//p' "$plan" | head -1)
    linear=$(sed -n 's/^linear: *//p' "$plan" | head -1)
    printf '%s\t%s\tlinear=%s\n' "${shipped:-0000-00-00}" "$(basename "$d")" "${linear:-none}"
  done | sort -r | head -n "$limit" | while IFS=$'\t' read -r shipped id lin; do
    printf 'shipped=%s\t%s\t%s\n' "$shipped" "$id" "$lin"
  done
  exit 0
fi

state_of() {
  local d="$1"
  local decisions="$d/decisions.json"
  if [ -f "$d/intent.md" ] && grep -q '^status: in-review' "$d/intent.md"; then echo "intent-in-review"; return; fi
  if [ -f "$decisions" ] && python3 - "$decisions" "$d" <<'PY'
import json, pathlib, sys
dec = json.load(open(sys.argv[1], encoding="utf-8"))
d = pathlib.Path(sys.argv[2])
if "size" not in dec or dec.get("size") == "none":
    sys.exit(1)
skips = dec.get("skips", {})
files = {
    "brief": d / "spec" / "brief.md",
    "ia": d / "spec" / "ia.md",
    "interaction": d / "spec" / "interaction.md",
    "screens": d / "spec" / "screens.md",
    "prototype": d / "spec" / "prototype" / "index.md",
    "conformance": d / "spec" / "conformance.md",
}
missing = [
    name for name, path in files.items()
    if not path.exists() and not str(skips.get(name, "")).startswith("skip")
]
sys.exit(0 if missing else 1)
PY
  then echo "design"; return; fi
  if [ ! -f "$d/facts.md" ]; then echo "intent"; return; fi
  if [ -f "$decisions" ] && python3 - "$decisions" "$d" <<'PY'
import json, pathlib, sys
dec = json.load(open(sys.argv[1], encoding="utf-8"))
d = pathlib.Path(sys.argv[2])
if "size" not in dec or str(dec.get("skips", {}).get("validation", "")).startswith("skip"):
    sys.exit(1)
val = d / "spec" / "validation.md"
if not val.exists():
    sys.exit(0)
front = {}
for line in val.read_text(encoding="utf-8").splitlines():
    if ":" in line:
        k, v = line.split(":", 1)
        front[k.strip()] = v.strip()
sys.exit(1 if front.get("verdict") == "ready" and front.get("status") == "approved" else 0)
PY
  then echo "spec-review"; return; fi
  if [ ! -f "$d/plan.md" ]; then echo "facts"; return; fi
  if ! grep -q '^status: approved' "$d/plan.md"; then echo "plan-draft"; return; fi
  echo "build"
}

found=""
for d in "$root/$changes"/*/; do
  [ -d "$d" ] || continue
  id=$(basename "$d")
  [ "$id" = "archive" ] && continue
  slug=${id#????-??-??-}               # strip the date; 2026-09-15-REV-947-adopt-sdlc -> REV-947-adopt-sdlc
  case "$slug" in [A-Z]*-[0-9]*-*) slug=${slug#*-*-} ;; esac   # strip the Linear key when there is one
  case "$mode" in
    --current) case "$branch" in *"$slug"*) ;; *) continue ;; esac ;;
    "") ;;
    *) [ "$id" = "$mode" ] || continue ;;
  esac
  found=1
  linear=$(grep -m1 '^linear:' "$d/plan.md" "$d/facts.md" "$d/intent.md" 2>/dev/null | head -1 | sed 's/^.*linear: *//')
  st=$(state_of "$d")
  pr="none"
  if command -v gh >/dev/null 2>&1; then
    pr=$(gh pr list --search "$id in:body" --state open --json number,labels --jq '.[0] | "#\(.number) \((.labels|map(.name)|map(select(.=="ask" or .=="show" or .=="ship"))|.[0]) // "unlabelled")"' 2>/dev/null || true)
    [ -n "$pr" ] || pr="none"
  fi
  printf '%s\tlinear=%s\tstate=%s\tpr=%s\n' "$id" "${linear:-none}" "$st" "$pr"
  if [ -n "$mode" ] && [ "$mode" != "--current" ] && [ -f "$d/plan.md" ]; then
    echo "plan.md history:"
    git -C "$root" log --follow --format='  %ad  %h  %s' --date=short -- "$changes/$id/plan.md"
  fi
done
[ -n "$found" ] || echo "none"
