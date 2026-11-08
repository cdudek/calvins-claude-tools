#!/usr/bin/env bash
# Runs the tests that ship inside plugins/cct (skills and hooks). Each test runs in its own folder.
set -u
root="$(cd "$(dirname "$0")/.." && pwd)/plugins/cct"
fail=0
suite_log="$(mktemp)" || exit 1
trap 'rm -f "$suite_log"' EXIT
while IFS= read -r f; do
  d="$(dirname "$f")"; b="$(basename "$f")"
  if [[ "$b" == *.py ]]; then (cd "$d" && python3 -m pytest -q -p no:cacheprovider "$b" >"$suite_log" 2>&1)
  else (cd "$d" && bash "$b" >"$suite_log" 2>&1); fi
  if [ $? -eq 0 ]; then echo "ok   ${f#"$root"/}"; else echo "FAIL ${f#"$root"/}"; cat "$suite_log"; fail=1; fi
done < <(find "$root/hooks" "$root/skills" -type f \( -name 'test_*.py' -o -name 'test_*.sh' \) -not -path '*/templates/*' | sort)
exit $fail
