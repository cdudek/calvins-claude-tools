#!/usr/bin/env bash
# Runs the tests that ship inside plugins/cct (skills and hooks), then the agent-tracker mod's and the factory plugin's checks.
# Each cct test runs in its own folder.
set -u
repo="$(cd "$(dirname "$0")/.." && pwd)"
root="$repo/plugins/cct"
fail=0
suite_log="$(mktemp)" || exit 1
logs="$(mktemp -d)" || exit 1
trap 'rm -rf "$suite_log" "$logs"' EXIT
# Test files run side by side (TEST_JOBS, default 4); each writes its own log, results print in file order.
# A file that runs past TEST_FILE_TIMEOUT seconds (default 420) is stopped and fails under its own name, so a hang
# never ends as a cancelled job with no output. Each file prints one progress line as it finishes.
run_one() { # <test file> <log folder>
  local f="$1" d b log rc start
  d="$(dirname "$f")"; b="$(basename "$f")"; log="$2/$(printf '%s' "$f" | tr '/' '_')"; start=$SECONDS
  if [[ "$b" == *.py ]]; then (cd "$d" && perl -e 'alarm shift; exec @ARGV' "${TEST_FILE_TIMEOUT:-420}" python3 -m pytest -q -p no:cacheprovider -o faulthandler_timeout=120 "$b" >"$log.out" 2>&1)
  else (cd "$d" && perl -e 'alarm shift; exec @ARGV' "${TEST_FILE_TIMEOUT:-420}" bash "$b" >"$log.out" 2>&1); fi
  rc=$?
  [ "$rc" = 142 ] && echo "timed out after ${TEST_FILE_TIMEOUT:-420}s" >>"$log.out"
  echo "$rc" >"$log.rc"
  echo "  done $((SECONDS - start))s rc=$rc ${b}"
  [ "$rc" = 0 ] || { echo "---- ${b} (failed, last 60 lines)"; tail -60 "$log.out"; }  # now, in case the job is cut off later
}
export -f run_one
files="$(find "$root/hooks" "$root/skills" -type f \( -name 'test_*.py' -o -name 'test_*.sh' \) -not -path '*/templates/*' | sort)"
[ -n "$files" ] && printf '%s\n' "$files" | xargs -P "${TEST_JOBS:-4}" -I{} bash -c 'run_one "$1" "$2"' _ {} "$logs"
while IFS= read -r f; do
  [ -n "$f" ] || continue
  log="$logs/$(printf '%s' "$f" | tr '/' '_')"
  if [ "$(cat "$log.rc" 2>/dev/null)" = 0 ]; then echo "ok   ${f#"$root"/}"; else echo "FAIL ${f#"$root"/}"; cat "$log.out"; fail=1; fi
done <<<"$files"

# The agent-tracker mod: validate the manifest and the marketplace, type-check the module, run its *.test.ts files.
# GitHub's runner has no `claude` CLI, so CI skips this block; a local run has it.
mod="$repo/plugins/agent-tracker"; modname=agent-tracker
run_mod() { # <label> <command...>
  local label="$1"; shift
  if "$@" >"$suite_log" 2>&1; then echo "ok   $modname: $label"; else echo "FAIL $modname: $label"; cat "$suite_log"; fail=1; fi
}
if [ -d "$mod" ]; then
  if command -v claude >/dev/null 2>&1; then
    run_mod validate bash -c 'claude plugin validate --strict "$1" && claude plugin validate "$2"' _ "$mod" "$repo/.claude-plugin/marketplace.json"
    run_mod test claude plugin test "$mod"
  elif [ -n "${CI:-}" ]; then echo "skip agent-tracker: claude CLI not found"
  else echo "FAIL agent-tracker: claude CLI not found"; fail=1; fi
fi
# The factory plugin: validate the manifest, then its own pytest suite (hooks and the run skill's scripts).
fac="$repo/plugins/factory"; modname=factory
if [ -d "$fac" ]; then
  if command -v claude >/dev/null 2>&1; then run_mod validate claude plugin validate --strict "$fac"
  elif [ -n "${CI:-}" ]; then echo "skip factory validate: claude CLI not found"
  else echo "FAIL factory validate: claude CLI not found"; fail=1; fi
  run_mod pytest python3 -m pytest -q -p no:cacheprovider "$fac"
fi
exit $fail
