#!/usr/bin/env bash
# Shared by the SDLC hooks: the interpreter, and one key of sdlc.json at the repo root as a shell
# string. Sourced, never run. Python because the hooks must work on a bare macOS and on a GitHub
# runner, and both ship python3; jq is not guaranteed.
#
#   sdlc_get <python-expression-over-cfg>   e.g. sdlc_get 'cfg["verify"]'
#
# Prints nothing and returns 1 when sdlc.json is missing or the key is absent, so every
# hook degrades to "do nothing" on a repo that has not adopted the chain.
#
# Every hook starts the interpreter ONCE per call (it parses the payload and sdlc.json in the same
# process) and does it through $SDLC_PY. A hook fires on every Bash call, every edit and every
# Stop, so the start-up time is the cost: `python3` behind a pyenv/asdf shim is 0.25-1 s a start,
# the system python is 0.03 s. The system one is used when it can be found without a spawn --
# /usr/bin/python3, and on macOS only when the Command Line Tools or Xcode stand behind it (the
# bare stub opens an install dialog). The hooks use the standard library and syntax from Python
# 3.7; `SDLC_PYTHON=<path>` picks another interpreter, and anything else falls back to python3.
SDLC_ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
SDLC_JSON="$SDLC_ROOT/sdlc.json"
SDLC_PY="${SDLC_PYTHON:-python3}"
if [ -z "${SDLC_PYTHON:-}" ] && [ -x /usr/bin/python3 ]; then
  case "$OSTYPE" in
    darwin*)
      if [ -x /Library/Developer/CommandLineTools/usr/bin/python3 ] ||
        [ -x /Applications/Xcode.app/Contents/Developer/usr/bin/python3 ]; then
        SDLC_PY=/usr/bin/python3
      fi
      ;;
    *) SDLC_PY=/usr/bin/python3 ;;
  esac
fi

sdlc_get() {
  [ -f "$SDLC_JSON" ] || return 1
  "$SDLC_PY" - "$SDLC_JSON" "$1" <<'PY' 2>/dev/null
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

# Hash of the source diff: `git diff HEAD` plus every untracked file matching the verifyDirty
# globs in $1 (space separated). One function, so turn-start.sh and verify-on-stop.sh hash
# identically. Run inside the repo, with `set -f` so the globs reach git as patterns.
sdlc_diff_hash() {
  {
    git diff HEAD 2>/dev/null
    for g in $1; do
      git ls-files --others --exclude-standard -- "$g" | while IFS= read -r f; do
        printf '%s\n' "$f"
        cat "$f"
      done
    done
  } | git hash-object --stdin
}
