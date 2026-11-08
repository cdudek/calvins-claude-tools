#!/usr/bin/env bash
# Falsifiable test for the PostToolUse post-edit-lint hook. Exit non-zero on failure.
#
# Self-contained: builds a throwaway project fixture with a stub `eslint` in
# node_modules/.bin, so it needs no network and no real linter install.

set -uo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
HOOK="$DIR/post-edit-lint.sh"
fail=0

FIXTURE=$(mktemp -d)
trap 'rm -rf "$FIXTURE"' EXIT
mkdir -p "$FIXTURE/node_modules/.bin"
echo 'export default []' > "$FIXTURE/eslint.config.js"
echo 'const a = 1' > "$FIXTURE/app.ts"

stub_eslint() { # $1 = stdout, $2 = exit code
    cat > "$FIXTURE/node_modules/.bin/eslint" <<EOF
#!/usr/bin/env bash
printf '%s' "$1"
exit $2
EOF
    chmod +x "$FIXTURE/node_modules/.bin/eslint"
}

# Asserts the emitted context contains every given substring.
check_contains() { # $1 = label, $2 = hook exit code, $3 = hook stdout, $4… = substrings
    local label="$1" code="$2" out="$3"
    shift 3
    if [ "$code" != "0" ]; then
        echo "FAIL: $label — hook exited $code, must always be 0 (non-blocking)"
        fail=1
        return
    fi
    local needle
    for needle in "$@"; do
        case "$out" in
            *"$needle"*) ;;
            *)
                echo "FAIL: $label — context missing '$needle'; got: $out"
                fail=1
                return
                ;;
        esac
    done
    echo "PASS: $label"
}

check() { # $1 = label, $2 = expected-empty|expected-report, $3 = hook stdout, $4 = hook exit code
    local label="$1" expect="$2" out="$3" code="$4"
    if [ "$code" != "0" ]; then
        echo "FAIL: $label — hook exited $code, must always be 0 (non-blocking)"
        fail=1
        return
    fi
    case "$expect" in
        empty)
            if [ -n "$out" ]; then
                echo "FAIL: $label — expected silence, got: $out"
                fail=1
            else
                echo "PASS: $label — silent no-op"
            fi
            ;;
        report)
            printf '%s' "$out" | python3 -c '
import json,sys
d=json.load(sys.stdin)["hookSpecificOutput"]
assert d["hookEventName"]=="PostToolUse", "wrong hookEventName"
assert "no-unused-vars" in d["additionalContext"], "linter output missing from context"
assert "non-blocking" in d["additionalContext"], "non-blocking framing missing"
print("PASS: '"$label"' — emits non-blocking PostToolUse context")
' || fail=1
            ;;
    esac
}

run() { printf '%s' "$1" | bash "$HOOK"; }

# 1. Non-lintable extension — must not even look for a linter.
OUT=$(run "{\"hook_event_name\":\"PostToolUse\",\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":\"$FIXTURE/README.md\"}}")
check "non-lintable extension" empty "$OUT" $?

# 2. No file path in the tool input (e.g. a tool the matcher over-matched).
OUT=$(run '{"hook_event_name":"PostToolUse","tool_name":"Edit","tool_input":{}}')
check "missing file_path" empty "$OUT" $?

# 3. Vendored path — never lint what we do not own.
mkdir -p "$FIXTURE/node_modules/pkg"
echo 'const a = 1' > "$FIXTURE/node_modules/pkg/index.ts"
OUT=$(run "{\"hook_event_name\":\"PostToolUse\",\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"$FIXTURE/node_modules/pkg/index.ts\"}}")
check "node_modules path" empty "$OUT" $?

# 4. Clean file — linter exits 0 with no output, so the agent hears nothing.
stub_eslint "" 0
OUT=$(run "{\"hook_event_name\":\"PostToolUse\",\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"$FIXTURE/app.ts\"}}")
check "clean file" empty "$OUT" $?

# 5. Fatal linter error (exit 2) — tooling noise is swallowed, not reported.
stub_eslint "Error: Could not find config file." 2
OUT=$(run "{\"hook_event_name\":\"PostToolUse\",\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"$FIXTURE/app.ts\"}}")
check "linter config error" empty "$OUT" $?

# 6. Real violations (exit 1) — reported back as PostToolUse context.
stub_eslint "app.ts: line 1, col 7, Error - 'a' is assigned a value but never used. (no-unused-vars)" 1
OUT=$(run "{\"hook_event_name\":\"PostToolUse\",\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"$FIXTURE/app.ts\"}}")
check "violations reported" report "$OUT" $?

# Prove the negative: a blocking verdict would be a bug — the hook must never
# emit one, on the very payload that produced findings.
for forbidden in '"decision"' '"permissionDecision"' '"block"'; do
    if printf '%s' "$OUT" | grep -q "$forbidden"; then
        echo "FAIL: hook emitted $forbidden — it must never block"
        fail=1
    fi
done
[ $fail -eq 0 ] && echo "PASS: no blocking verdict emitted"

# 7. Non-hoisted workspace: the install sits BETWEEN the edited file and the
# config. Walking up from the config root instead of the file skips it, and the
# hook goes silent on an installed linter — the regression this locks in.
NESTED=$(mktemp -d)
trap 'rm -rf "$FIXTURE" "$NESTED"' EXIT
mkdir -p "$NESTED/packages/web/node_modules/.bin" "$NESTED/packages/web/src"
echo 'export default []' > "$NESTED/eslint.config.js"
echo 'const a = 1' > "$NESTED/packages/web/src/app.ts"
cat > "$NESTED/packages/web/node_modules/.bin/eslint" <<'EOF'
#!/usr/bin/env bash
printf '%s' "app.ts: line 1, col 7, Error - 'a' is assigned a value but never used. (no-unused-vars)"
exit 1
EOF
chmod +x "$NESTED/packages/web/node_modules/.bin/eslint"
OUT=$(run "{\"hook_event_name\":\"PostToolUse\",\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"$NESTED/packages/web/src/app.ts\"}}")
check "bin installed below the config root" report "$OUT" $?

# 8. `.vue` runs both linters — both reports must reach the agent in one payload.
cat > "$FIXTURE/node_modules/.bin/stylelint" <<'EOF'
#!/usr/bin/env bash
printf '%s' "app.vue: line 9, col 3, error - Hex colors are banned (color-no-hex)"
exit 2
EOF
chmod +x "$FIXTURE/node_modules/.bin/stylelint"
echo '{}' > "$FIXTURE/.stylelintrc.json"
echo '<template><i /></template>' > "$FIXTURE/app.vue"
stub_eslint "app.vue: line 1, col 1, Error - bad (no-unused-vars)" 1
OUT=$(run "{\"hook_event_name\":\"PostToolUse\",\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":\"$FIXTURE/app.vue\"}}")
check_contains "vue reports both linters" $? "$OUT" "ESLint:" "Stylelint:" "no-unused-vars" "color-no-hex"

# 9. Long output is truncated, and says so rather than dropping lines silently.
stub_eslint "$(for i in $(seq 1 60); do echo "line $i no-unused-vars"; done)" 1
OUT=$(run "{\"hook_event_name\":\"PostToolUse\",\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"$FIXTURE/app.ts\"}}")
check_contains "long output truncated" $? "$OUT" "truncated at 40 lines"

# 10. Relative path with no config anywhere above: `dirname` bottoms out at `.`,
# which is its own parent — pre-guard, the ancestor walks spun on it forever
# (same failure as un-normalized `C:\` paths on Windows). Must exit promptly.
LOOPDIR=$(mktemp -d)
trap 'rm -rf "$FIXTURE" "$NESTED" "$LOOPDIR"' EXIT
mkdir -p "$LOOPDIR/src"
echo 'const a = 1' > "$LOOPDIR/src/app.ts"
OUT=$(cd "$LOOPDIR" && printf '%s' '{"hook_event_name":"PostToolUse","tool_name":"Edit","tool_input":{"file_path":"src/app.ts"}}' | timeout 10 bash "$HOOK")
CODE=$?
if [ "$CODE" = "124" ]; then
    echo "FAIL: relative path without config — hook hung until timeout (dirname fixed-point loop)"
    fail=1
else
    check "relative path without config terminates" empty "$OUT" "$CODE"
fi

# 11. Windows-style path (Git Bash / MSYS only): must be normalized via cygpath
# and then lint like any POSIX path. Elsewhere cygpath does not exist and the
# normalization is a no-op, so this case is skipped.
if command -v cygpath > /dev/null 2>&1; then
    stub_eslint "app.ts: line 1, col 7, Error - 'a' is assigned a value but never used. (no-unused-vars)" 1
    WINFILE=$(cygpath -m "$FIXTURE/app.ts")
    OUT=$(printf '%s' "{\"hook_event_name\":\"PostToolUse\",\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"$WINFILE\"}}" | timeout 30 bash "$HOOK")
    CODE=$?
    if [ "$CODE" = "124" ]; then
        echo "FAIL: windows path — hook hung until timeout"
        fail=1
    else
        check_contains "windows path normalized and linted" "$CODE" "$OUT" "no-unused-vars"
    fi
else
    echo "SKIP: windows path normalization (no cygpath on this platform)"
fi

# 12. No `timeout`/`gtimeout` on PATH: the linter must still run. Expanding an
# empty array under `set -u` aborts the subshell on bash < 4.4 (macOS 3.2).
BARE=$(mktemp -d)
mkdir -p "$BARE/bin"
for t in jq dirname cat head wc printf bash sh env seq; do
    tp=$(command -v "$t") || continue
    # A bare name means shell builtin — available inside the hook's bash without
    # a binary on PATH, so nothing to link.
    [ -f "$tp" ] && ln -sf "$tp" "$BARE/bin/$t" 2> /dev/null
done
# Capability probe instead of platform assumptions: on MSYS the linked copies
# are not reliably executable (.exe suffix semantics), so only run the sandbox
# test where the sandbox itself demonstrably works.
if PATH="$BARE/bin" bash -c 'cat /dev/null && jq --version' > /dev/null 2>&1; then
    stub_eslint "app.ts: line 1, col 7, Error - 'a' is assigned a value but never used. (no-unused-vars)" 1
    OUT=$(printf '%s' "{\"hook_event_name\":\"PostToolUse\",\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"$FIXTURE/app.ts\"}}" | PATH="$BARE/bin" bash "$HOOK" 2>&1)
    check_contains "runs with no timeout binary on PATH" $? "$OUT" "no-unused-vars"
else
    echo "SKIP: no-timeout-binary sandbox (sandbox PATH not executable on this platform)"
fi
rm -rf "$BARE"

exit $fail
