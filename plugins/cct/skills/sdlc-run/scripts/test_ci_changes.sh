#!/usr/bin/env bash
# Usage: bash test_ci_changes.sh
# Runs the `changes` step of templates/ci/github-actions.yml (the lines between its
# changes-script markers) against fake changed-file lists and the shipped TypeScript ciPaths,
# with a stub `gh`. Prints one line per case; exits 1 if any case differs from what it expects.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
tpl="$here/../templates"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

sed -n '/# >>> changes-script/,/# <<< changes-script/p' "$tpl/ci/github-actions.yml" | sed 's/^          //' > "$tmp/changes.sh"
[ -s "$tmp/changes.sh" ] || { echo "FAIL: no changes-script markers in the template"; exit 1; }
jq '{ciPaths: .typescript}' "$tpl/ci-paths.json" > "$tmp/sdlc.json"
mkdir "$tmp/bin"
printf '#!/bin/sh\ncat "$FAKE_FILES"\n' > "$tmp/bin/gh"
chmod +x "$tmp/bin/gh"

fail=0
# case NAME BASE HEAD EXPECTED(lint unit build deploy matrix-kind) FILES...
# kind: none | shards | touched
run_case() {
  local name=$1 base=$2 head=$3 want=$4; shift 4
  printf '%s\n' "$@" > "$tmp/files"
  : > "$tmp/out"
  local pr=7
  [ "$base" = push ] && pr=""
  (cd "$tmp" && PATH="$tmp/bin:$PATH" FAKE_FILES="$tmp/files" GITHUB_OUTPUT="$tmp/out" GITHUB_STEP_SUMMARY=/dev/null \
    PR="$pr" BASE="$base" HEAD="$head" DEFAULT=main SHARDS=4 bash "$tmp/changes.sh") || { echo "FAIL  $name: script exited non-zero"; fail=1; return; }
  local m kind
  m=$(sed -n 's/^matrix=//p' "$tmp/out")
  case "$m" in '[]') kind=none ;; *'"files":""'*) kind=shards ;; *) kind=touched ;; esac
  local got
  got="$(sed -n 's/^lint=//p' "$tmp/out") $(sed -n 's/^unit=//p' "$tmp/out") $(sed -n 's/^build=//p' "$tmp/out") $(sed -n 's/^deploy=//p' "$tmp/out") $kind"
  if [ "$got" = "$want" ]; then echo "ok    $name: $got"; else echo "FAIL  $name: got [$got] want [$want]"; fail=1; fi
}

M=milestone/x # a feature PR into a milestone branch: no full run
run_case "docs only"                 $M f/a "false false false false none" docs/guide.md README.md changes/2026-x/plan.md
run_case "image and md only"         $M f/a "false false false false none" docs/img/diagram.png README.md
run_case "unknown non-code file"     $M f/a "false false false false none" notes.csv .claude/plans/a.json
run_case "src change"                $M f/a "true true true true none"     src/lib/a.ts
run_case "test change"               $M f/a "true true false false none"   test/a.test.ts
run_case "e2e spec change"           $M f/a "true false false false touched" e2e/login.spec.ts
run_case "e2e helper, no spec"       $M f/a "true false false false none"  e2e/helpers.ts
run_case "css change"                $M f/a "true false false true none"   src/app.css
run_case "lockfile"                  $M f/a "true true true true none"     pnpm-lock.yaml
run_case "config file no step knows" $M f/a "true true true true none"     tsconfig.json
run_case "migration"                 $M f/a "false true false true none"   drizzle/0001.sql
# the safety net
run_case "test only, PR into main"   main f/a "true true true true shards" test/a.test.ts
run_case "docs only, PR into main"   main f/a "false false false false none" README.md docs/a.png
run_case "milestone head into main"  main milestone/x "true true true true shards" src/a.ts
run_case "push to default branch"    push "" "true true true true shards" README.md
exit "$fail"
