#!/usr/bin/env bash
# Runs the tests that ship inside plugins/cct (skills and hooks), then the agent-tracker mod's checks.
# Each cct test runs in its own folder.
set -u
repo="$(cd "$(dirname "$0")/.." && pwd)"
root="$repo/plugins/cct"
fail=0
suite_log="$(mktemp)" || exit 1
trap 'rm -f "$suite_log"' EXIT
while IFS= read -r f; do
  d="$(dirname "$f")"; b="$(basename "$f")"
  if [[ "$b" == *.py ]]; then (cd "$d" && python3 -m pytest -q -p no:cacheprovider "$b" >"$suite_log" 2>&1)
  else (cd "$d" && bash "$b" >"$suite_log" 2>&1); fi
  if [ $? -eq 0 ]; then echo "ok   ${f#"$root"/}"; else echo "FAIL ${f#"$root"/}"; cat "$suite_log"; fail=1; fi
done < <(find "$root/hooks" "$root/skills" -type f \( -name 'test_*.py' -o -name 'test_*.sh' \) -not -path '*/templates/*' | sort)

# The agent-tracker mod: validate the manifest and the marketplace, type-check the module, run its *.test.ts files.
# GitHub's runner has no `claude` CLI, so CI skips this block; a local run has it.
mod="$repo/plugins/agent-tracker"
run_mod() { # <label> <command...>
  local label="$1"; shift
  if "$@" >"$suite_log" 2>&1; then echo "ok   agent-tracker: $label"; else echo "FAIL agent-tracker: $label"; cat "$suite_log"; fail=1; fi
}
if [ -d "$mod" ]; then
  if command -v claude >/dev/null 2>&1; then
    run_mod validate bash -c 'claude plugin validate --strict "$1" && claude plugin validate "$2"' _ "$mod" "$repo/.claude-plugin/marketplace.json"
    run_mod test claude plugin test "$mod"
  elif [ -n "${CI:-}" ]; then echo "skip agent-tracker: claude CLI not found"
  else echo "FAIL agent-tracker: claude CLI not found"; fail=1; fi
fi
exit $fail
