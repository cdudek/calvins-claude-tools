#!/usr/bin/env bash
# PreToolUse hook on Bash: block what sdlc.json `blocked[]` names -- dependency changes,
# cluster writes, database pushes -- each with the route a human takes instead.
#
# Exit 2 blocks the call and sends stderr to Claude, which then tells the user the
# route. Everything else exits 0 untouched. A block explains itself (playbook rule).
#
# One interpreter start per call: it parses the payload and sdlc.json and prints the command,
# the docs path and the rules as NUL-separated fields. The matching stays `grep -E`, because the
# rules are POSIX ERE (`[[:space:]]`), which Python's `re` does not read.
set -uo pipefail
export PYTHONDONTWRITEBYTECODE=1 # a hook must not leave __pycache__ in a clean checkout
. "$(dirname "$0")/sdlc-config.sh"
: "${SDLC_PY:=python3}" # an older sdlc-config.sh (one-file upgrade) does not set it

payload=$(cat)

# The session transcripts (~/.claude/projects) are the evidence for an owner quote: any Bash that
# writes there (redirect, tee, cp, mv, sed -i, an interpreter, a cd into it) is refused, with or
# without `blocked[]` rules. Reading stays allowed. The command is normalised first (quotes and
# backslashes dropped, `//` and `/./` collapsed, `~` and $HOME expanded) so the cheap spellings of
# the path do not slip through; this is a speed bump for a careless agent, not a shell parser.
case "$payload" in
  *claude*projects*)
    if printf '%s' "$payload" | "$SDLC_PY" -c '
import json, os, re, sys
try:
    cmd = (json.load(sys.stdin).get("tool_input") or {}).get("command") or ""
except (ValueError, AttributeError):
    sys.exit(1)
home = os.path.expanduser("~")
cmd = re.sub(r"[\x27\"\\]", "", cmd)
cmd = re.sub(r"\$\{HOME\}|\$HOME|(?<![\w$])~", home, cmd)
cmd = re.sub(r"/(\./)+", "/", re.sub(r"/{2,}", "/", cmd))
HOME = r"\.claude/projects"
WRITES = (
    r">>?\s*\S*" + HOME,
    r"(^|[\s;&|(])(tee|cp|mv|dd|install|ln|truncate|rm|touch|chmod|rsync)\b",
    r"\bsed\b[^|;&]*\s-\w*i",
    r"\b(python3?|perl|ruby|node)\b",
    r"\bcd\b[^;&|]*" + HOME,
)
sys.exit(0 if re.search(HOME, cmd) and any(re.search(w, cmd) for w in WRITES) else 1)
'; then
      echo 'BLOCKED: ~/.claude/projects holds the session transcripts, the evidence of what the engineer said. They are never written from a shell; ask the engineer to say it in the session.' >&2
      exit 2
    fi
    ;;
esac

fields=()
while IFS= read -r -d '' f; do fields+=("$f"); done < <(
  printf '%s' "$payload" | "$SDLC_PY" -c '
import json, os, re, sys
def owner(cfg_path):
    """Who owns sdlc.json: the last CODEOWNERS line for it (or for `*`), else a plain description."""
    here = os.path.dirname(os.path.abspath(cfg_path))
    found = ""
    for rel in (".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS"):
        try:
            lines = open(os.path.join(here, rel), encoding="utf-8").read().splitlines()
        except OSError:
            continue
        for line in lines:
            parts = line.split("#")[0].split()
            if len(parts) > 1 and parts[0].lstrip("/") in ("sdlc.json", "*"):
                found = " ".join(parts[1:])
        break
    return found or "the owner of sdlc.json"
try:
    cmd = (json.load(sys.stdin).get("tool_input") or {}).get("command") or ""
    cmd = re.sub(r"\\\r?\n[ \t]*", " ", cmd)  # a backslash-newline continues the command: one line to match
    cfg = json.load(open(sys.argv[1], encoding="utf-8"))
    rules = cfg.get("blocked") or []
    out = [cmd, cfg.get("docs") or "docs/sdlc.md"]
    for i, r in enumerate(rules):
        # one bad rule is reported and skipped; the valid ones still apply
        if isinstance(r, dict) and isinstance(r.get("match"), str) and r["match"]:
            message = str(r.get("message", ""))
            if not message.strip():  # a refusal with no route: still a refusal, but it names who fixes the rule
                message = (
                    f"sdlc.json blocked[{i}] refuses this command but has no message, so it names no route. "
                    f"Config owner: {owner(sys.argv[1])}. Fix: give the rule a `message` saying who does what instead."
                )
            out += [r["match"], message]
        else:
            sys.stderr.write("sdlc.json blocked[%d] has no `match` string: skipped\n" % i)
except (OSError, ValueError, KeyError, AttributeError, TypeError):
    sys.exit(0)
if cmd and rules:
    sys.stdout.write("\0".join(out) + "\0")
' "$SDLC_JSON"
)
[ "${#fields[@]}" -ge 4 ] || exit 0
cmd=${fields[0]}
docs=${fields[1]}

# One rule per field pair: <regex>, <message>.
i=2
while [ "$i" -lt "${#fields[@]}" ]; do
  match=${fields[$i]}
  message=${fields[$((i + 1))]}
  i=$((i + 2))
  [ -n "$match" ] || continue
  if printf '%s' "$cmd" | grep -Eqi -- "$match"; then
    text=$(printf 'BLOCKED: %s\n(%s, "Hooks")' "$message" "$docs")
    # a repeat of this block says STOP (block_state.py); without the helper the text is plain
    out=$(printf '%s' "$payload" | python3 "$(dirname "$0")/block_state.py" gate-bash.sh "sdlc.json blocked[]" "$message" "$text" 2>/dev/null) && [ -n "$out" ] && text=$out
    printf '%s\n' "$text" >&2
    exit 2
  fi
done
exit 0
