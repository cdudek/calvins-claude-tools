#!/usr/bin/env bash
# Shared by the SDLC hooks: read one key of sdlc.json at the repo root as a shell string.
# Sourced, never run. python3 because the hooks must work on a bare macOS and on a GitHub
# runner, and both ship python3; jq is not guaranteed.
#
#   sdlc_get <python-expression-over-cfg>   e.g. sdlc_get 'cfg["verify"]'
#
# Prints nothing and returns 1 when sdlc.json is missing or the key is absent, so every
# hook degrades to "do nothing" on a repo that has not adopted the chain.
SDLC_ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
SDLC_JSON="$SDLC_ROOT/sdlc.json"

sdlc_get() {
  [ -f "$SDLC_JSON" ] || return 1
  python3 - "$SDLC_JSON" "$1" <<'PY' 2>/dev/null
import json, sys
cfg = json.load(open(sys.argv[1], encoding="utf-8"))
try:
    v = eval(sys.argv[2], {"cfg": cfg})
except Exception:
    sys.exit(1)
if v is None or v == "" or v == []:
    sys.exit(1)
if isinstance(v, (list, dict)):
    print(json.dumps(v))
else:
    print(v)
PY
}

# The tool_input field <name> from the hook payload on stdin (already read into $1).
sdlc_field() {
  printf '%s' "$1" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("tool_input",{}).get(sys.argv[1],"") if sys.argv[1]!="stop_hook_active" else str(d.get("stop_hook_active",False)).lower())' "$2" 2>/dev/null || true
}
