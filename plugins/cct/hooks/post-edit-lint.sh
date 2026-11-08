#!/usr/bin/env bash
# hook-event: PostToolUse
# hook-matcher: Edit|Write
# hook-timeout: 30
#
# Runs the repo's own ESLint / Stylelint on the single file that was just
# written and reports the violations back to the agent as context.
#
# NON-BLOCKING BY CONTRACT: always exits 0, and never emits a `decision` or
# `permissionDecision` field. The lint rules gate in CI; this hook only shortens
# the feedback loop so violations get fixed in the same turn instead of on the
# next PR push.
#
# Exit codes: 0 = continue (always). It never returns 2, which would block.
#
# Silent no-op — no stdout at all — when any of these hold:
#   * the tool input carries no file path, or the extension isn't lintable
#   * the path is inside node_modules / dist / .nuxt / .output / coverage / build
#   * no ancestor directory holds a config for that linter
#   * the linter isn't installed in that project's node_modules
#   * the file is clean, or the linter itself failed (config error, bad glob)
#
# Pure-local: no network, no LLM, no writes. Only ever reads the edited file.

# `-e` is deliberately omitted: a linter exiting non-zero is the *normal* path
# here, not an error. Every command that may fail is handled explicitly.
set -uo pipefail

MAX_LINES=40

INPUT=$(cat)

FILE=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
[ -n "$FILE" ] || exit 0

# On Windows (Git Bash / MSYS) the tool input carries a `C:\...` path. bash's
# `dirname` never reduces those to `/`, so the ancestor walks below would spin
# on the `.` fixed point until the hook timeout kills them. Normalize to a
# POSIX path first; on macOS/Linux `cygpath` does not exist and this is a no-op.
if command -v cygpath > /dev/null 2>&1; then
    case "$FILE" in
        [A-Za-z]:*) FILE=$(cygpath -u "$FILE") ;;
    esac
fi

[ -f "$FILE" ] || exit 0

case "$FILE" in
    */node_modules/* | */dist/* | */.nuxt/* | */.output/* | */coverage/* | */build/*) exit 0 ;;
esac

case "${FILE##*.}" in
    js | jsx | mjs | cjs | ts | tsx) LINTERS="eslint" ;;
    vue) LINTERS="eslint stylelint" ;;
    css | scss | less) LINTERS="stylelint" ;;
    *) exit 0 ;;
esac

# Nearest ancestor of $1 holding any of the remaining arguments. Stops at any
# `dirname` fixed point (`/`, but also `.` for relative and un-normalized
# Windows paths), so a degenerate input can never loop forever.
find_root() {
    local dir="$1" parent
    shift
    while [ -n "$dir" ] && [ "$dir" != "/" ]; do
        local name
        for name in "$@"; do
            [ -e "$dir/$name" ] && {
                printf '%s' "$dir"
                return 0
            }
        done
        parent=$(dirname "$dir")
        [ "$parent" = "$dir" ] && return 1
        dir=$parent
    done
    return 1
}

# Nearest ancestor of $1 with $2 installed in node_modules/.bin. Always call this
# with the *file's* directory, never with the config root: in a non-hoisted
# workspace the install sits below the config (`packages/web/node_modules/.bin`
# under a root `eslint.config.js`), and starting at the root would walk straight
# past it.
find_bin() {
    local dir="$1" bin="$2" parent
    while [ -n "$dir" ] && [ "$dir" != "/" ]; do
        [ -x "$dir/node_modules/.bin/$bin" ] && {
            printf '%s' "$dir/node_modules/.bin/$bin"
            return 0
        }
        parent=$(dirname "$dir")
        [ "$parent" = "$dir" ] && return 1
        dir=$parent
    done
    return 1
}

# Split the budget across the linters this file needs, so the internal cap stays
# under the hook timeout in hooks.json (30s). Otherwise a slow second linter can
# get the whole hook killed, discarding the first linter's collected output too.
case "$LINTERS" in
    *" "*) BUDGET=12 ;;
    *) BUDGET=24 ;;
esac

TIMEOUT=()
if command -v timeout > /dev/null 2>&1; then
    TIMEOUT=(timeout "$BUDGET")
elif command -v gtimeout > /dev/null 2>&1; then
    TIMEOUT=(gtimeout "$BUDGET")
fi

FILE_DIR=$(dirname "$FILE")
REPORT=""

for linter in $LINTERS; do
    case "$linter" in
        eslint)
            ROOT=$(find_root "$FILE_DIR" \
                eslint.config.js eslint.config.mjs eslint.config.cjs eslint.config.ts \
                .eslintrc .eslintrc.js .eslintrc.cjs .eslintrc.json .eslintrc.yml .eslintrc.yaml) || continue
            # Default `stylish` formatter — it is the only one still bundled with
            # ESLint 9 core (`compact`, `unix` and friends moved to packages).
            ARGS=(--no-color)
            # 0 = clean or warnings-only, 1 = lint errors. 2 = fatal config error.
            OK_CODES="0 1"
            LABEL="ESLint"
            ;;
        stylelint)
            ROOT=$(find_root "$FILE_DIR" \
                stylelint.config.js stylelint.config.mjs stylelint.config.cjs \
                .stylelintrc .stylelintrc.js .stylelintrc.cjs .stylelintrc.json .stylelintrc.yml .stylelintrc.yaml) || continue
            ARGS=(--no-color --formatter compact)
            # 0 = clean, 2 = lint problems. 1/78/80 = internal, config or glob error.
            OK_CODES="0 2"
            LABEL="Stylelint"
            ;;
    esac

    BIN=$(find_bin "$FILE_DIR" "$linter") || continue

    OUTPUT=$(cd "$ROOT" && ${TIMEOUT[@]+"${TIMEOUT[@]}"} "$BIN" "${ARGS[@]}" "$FILE" 2>&1)
    CODE=$?

    [[ " $OK_CODES " == *" $CODE "* ]] || continue
    [ -n "$OUTPUT" ] || continue

    TRIMMED=$(printf '%s\n' "$OUTPUT" | head -n "$MAX_LINES")
    [ "$(printf '%s\n' "$OUTPUT" | wc -l)" -gt "$MAX_LINES" ] &&
        TRIMMED="$TRIMMED
… truncated at $MAX_LINES lines — run $linter yourself for the full list."

    REPORT="$REPORT
$LABEL:
$TRIMMED"
done

[ -n "$REPORT" ] || exit 0

printf '%s' "post-edit-lint (non-blocking): the repo linter flagged ${FILE##*/}, which you just wrote. Fix these now — the same rules gate in CI.
$REPORT" |
    jq -Rs '{hookSpecificOutput: {hookEventName: "PostToolUse", additionalContext: .}}'

exit 0
