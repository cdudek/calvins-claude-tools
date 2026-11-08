#!/usr/bin/env bash
# Usage: probe-pattern.sh <kind-file> <pattern-file> <input-file>
# Purpose: Decides whether a PATTERN matches an INPUT, in isolation, so a review finding
#          that claims a matcher's runtime behaviour can be settled by observation
#          instead of by reading. Emits the observed result for a validator to weigh.
#
#   <kind-file>     file holding one of: case | glob | grep-basic | grep-extended | python-re
#   <pattern-file>  file holding the pattern, verbatim, no surrounding quotes
#   <input-file>    file holding the input string, verbatim (trailing newline stripped)
#
# All three are FILES on purpose, the kind included. A value passed as an argument has
# to survive a shell round-trip first, and these values come from a reviewer that read
# untrusted code: a quote, a backtick or a `$(` in any of them breaks out while the
# caller's shell is still building the command line. Validating the kind *inside* this
# script does not help — by then the caller's shell has already parsed it. Keeping every
# input on the same footing leaves no exception for a future edit to forget.
#
# What this deliberately does NOT do: run the artifact under review. A finding about a
# repo script's behaviour would mean executing code a reviewer just read as untrusted
# data, which is not a probe, it is arbitrary execution. This script evaluates only
# self-contained matchers — a `case` pattern, a glob, a regex — where the claim can be
# reproduced without the surrounding program. Claims that need the program stay
# `unverifiable`, which is honest; see references/pipeline-tail.md.
#
# Output sections:
#   -#-#- PROBE -#-#-
#   - status: ok|failed
#   - kind: <the validated kind, or the placeholder <invalid> / <unreadable>>
#
# The placeholders are deliberate: an unvalidated kind is never echoed, because a value
# carrying newlines could forge extra `- status:` / `- matched:` lines in this block and
# the caller parses those as a genuine observed result.
#   - matched: yes|no        (only when status is ok)
#   - reason: <why it failed — only when status is failed>
#
# Exit status is always 0. A probe that could not run is data for the validator to
# weigh, not a reason to abort the review.

set -uo pipefail

emit_failed() {
  printf -- '-#-#- PROBE -#-#-\n'
  printf -- '- status: failed\n'
  printf -- '- kind: %s\n' "${KIND:-}"
  printf -- '- reason: %s\n' "$1"
  exit 0
}

KIND_FILE="${1:-}"
PATTERN_FILE="${2:-}"
INPUT_FILE="${3:-}"
KIND=""

[ -r "${KIND_FILE:-/nonexistent}" ] || emit_failed "kind file not readable: ${KIND_FILE:-<none>}"
# On a partial read (I/O fault, or a race after the -r check) the assignment still
# captures whatever bytes arrived, so the unvalidated — possibly multi-line — value
# would reach emit_failed and be echoed raw. Mask it first, like the invalid branch.
#
# This branch has NO behavioural test, deliberately. Reaching it needs a read that
# starts and then fails; `chmod 000` is caught by the `-r` check above, so the test that
# looks like it covers this actually exercises that earlier branch. Rather than assert
# the line is present — a check that survives any rewrite of what it guards — the guard
# pins the property both branches share: the `- kind:` row is masked or blank, never the
# value. Injecting an I/O fault to reach this line is not worth the fixture.
if ! KIND=$(cat "$KIND_FILE"); then
  KIND="<unreadable>"
  emit_failed "could not read the kind file"
fi
# Strip surrounding whitespace, then require an exact enum member. A newline inside the
# value would otherwise forge extra `- status:` / `- matched:` lines in this script's own
# output, which the caller parses as a genuine observed result.
KIND="${KIND#"${KIND%%[![:space:]]*}"}"
KIND="${KIND%"${KIND##*[![:space:]]}"}"
case "$KIND" in
  case|glob|grep-basic|grep-extended|python-re) ;;
  *) KIND="<invalid>"
     emit_failed "kind is not one of case|glob|grep-basic|grep-extended|python-re" ;;
esac
# `-r`, not `-f`: an existing-but-unreadable file passes `-f`, and with no `set -e` the
# unchecked `cat` below would then yield an empty string. An empty pattern matches
# EVERYTHING for the grep and regex kinds, so the probe would confidently report
# `matched: yes` for a pattern it never actually read.
[ -r "${PATTERN_FILE:-/nonexistent}" ] || emit_failed "pattern file not readable: ${PATTERN_FILE:-<none>}"
[ -r "${INPUT_FILE:-/nonexistent}" ] || emit_failed "input file not readable: ${INPUT_FILE:-<none>}"

pattern=$(cat "$PATTERN_FILE") || emit_failed "could not read the pattern file"
input=$(cat "$INPUT_FILE") || emit_failed "could not read the input file"

# A readable but EMPTY pattern is the same hazard as an unreadable one for the grep and
# regex kinds: `grep -E ''` and `re.search('')` match every input, so the probe would
# report `matched: yes` for a pattern that says nothing. `case`/`glob` are not gated —
# an empty pattern there matches only an empty input, which is a real answer.
case "$KIND" in
  grep-basic|grep-extended|python-re)
    [ -n "$pattern" ] || emit_failed "pattern is empty — an empty $KIND pattern matches everything" ;;
esac

# A catastrophic-backtracking pattern can hang grep or python indefinitely, and
# `probe_pattern` comes straight from diff text a reviewer read as untrusted data. Bound
# every matcher run. Pure bash on purpose: neither `timeout` nor `gtimeout` ships on
# macOS, so a hard dependency would make the probe unavailable rather than bounded.
PROBE_TIMEOUT="${PROBE_TIMEOUT:-5}"
PROBE_POLL="0.05"
run_bounded() {   # run_bounded <outfile> <cmd...>; returns 124 on timeout
  local out="$1"; shift
  # Sub-second polling: a `sleep 1` granularity charged every non-instant matcher a
  # full second even though grep and python finish in milliseconds, and the "probe
  # twice" rule doubles that per finding. Measured: 1.00s -> 0.09s for one grep.
  local ticks
  ticks=$(awk -v t="$PROBE_TIMEOUT" -v p="$PROBE_POLL" 'BEGIN{printf "%d", (t/p)+0.5}')
  [ "$ticks" -gt 0 ] 2>/dev/null || ticks=100

  # `set -m` puts the job in its own process group so the timeout can signal the whole
  # subtree, and both a group kill and a direct kill are attempted.
  #
  # This is DEFENSIVE, not a fix for an observed bug. A reviewer reasoned that the
  # inherited EXIT trap blocks bash's exec optimization, leaving the real matcher
  # orphaned when only the wrapper is killed. Tested here against a child that writes
  # its own pid to a file: on this bash the leaf died with every form, including the
  # plain subshell — so the leak did not reproduce. The reasoning is still sound for
  # shells that behave differently, and the hardening costs two lines, so it stays.
  # Do not "simplify" it back on the grounds that the simpler form also passed.
  set -m
  "$@" > "$out" 2>/dev/null &
  local pid=$! waited=0
  set +m

  while kill -0 "$pid" 2>/dev/null; do
    if [ "$waited" -ge "$ticks" ]; then
      kill -9 -- "-$pid" 2>/dev/null
      kill -9 "$pid" 2>/dev/null
      wait "$pid" 2>/dev/null
      return 124
    fi
    sleep "$PROBE_POLL"
    waited=$((waited + 1))
  done
  wait "$pid"
}

matched=""

WORKDIR="$(mktemp -d)" || emit_failed "could not create a scratch dir"
trap 'rm -rf "$WORKDIR"' EXIT

case "$KIND" in
  case|glob)
    # `case` and shell globbing are the same matcher. The pattern must stay unquoted
    # for it to be a pattern at all — that is the behaviour under test — so this branch
    # is the one place a value from the finding is interpreted. It is bounded: a `case`
    # pattern has no command-substitution syntax, and the value never reaches `eval` or
    # a command position (verified: a pattern of `$(touch …)` matches nothing and runs
    # nothing).
    #
    # `|` is split here rather than left in the pattern. In a real `case` arm the bar
    # separates alternatives, but it only does so when written literally in the source
    # — arriving via a variable it degrades to an ordinary glob character. Probing
    # `develop|main` unsplit would answer "no match" for the input `main`, which is
    # true of this script and false of the code under review: exactly the misleading
    # result a probe exists to prevent.
    matched=no
    rest="$pattern"
    # Bounded on purpose. An unbounded `while :` here spins forever if the advance below
    # is ever broken, and this runs inside a review pipeline — a hang is worse than a
    # wrong answer, because nothing times it out. 64 alternatives is far past any real
    # `case` arm; exceeding it means the loop is not advancing.
    guard=0
    exhausted=no
    while [ "$guard" -lt 64 ]; do
      guard=$((guard + 1))
      alt="${rest%%|*}"
      case "$input" in
        $alt) matched=yes; exhausted=yes; break ;;
      esac
      if [ "$rest" = "${rest#*|}" ]; then exhausted=yes; break; fi
      rest="${rest#*|}"
    done
    # Fail only when the budget ran out with alternatives still unchecked. A pattern with
    # exactly 64 of them resolves on the 64th pass and is a correct answer, not an
    # overflow — the earlier form discarded that result and reported a spurious failure
    # at exactly the documented boundary.
    [ "$exhausted" = "yes" ] \
      || emit_failed "pattern has more than 64 alternatives, or the split is not advancing"
    ;;
  grep-basic|grep-extended)
    grep_flags=(-q --)
    [ "$KIND" = "grep-extended" ] && grep_flags=(-Eq --)
    printf '%s' "$input" > "$WORKDIR/gi"
    run_bounded "$WORKDIR/go" grep "${grep_flags[@]}" "$pattern" "$WORKDIR/gi"
    rc=$?
    # grep: 0 = match, 1 = no match, 2 = malformed pattern or read error. Folding 2 into
    # the no-match branch would report a confident `matched: no` for a pattern that never
    # compiled — the same false answer the python-re branch already avoids.
    case "$rc" in
      0)   matched=yes ;;
      1)   matched=no ;;
      124) emit_failed "grep probe exceeded ${PROBE_TIMEOUT}s — the pattern may backtrack catastrophically" ;;
      *)   emit_failed "not a valid $KIND pattern (grep exit $rc)" ;;
    esac
    ;;
  python-re)
    command -v python3 >/dev/null 2>&1 || emit_failed "python3 not on PATH"
    # Pattern and input reach python as argv, never as source text, so nothing here is
    # eval'd. `re.search`, not `match`: the claim is "does this pattern occur".
    # The filename must NOT shadow a stdlib module. Python puts the script's own
    # directory first on sys.path, so a helper called `re.py` makes `import re` import
    # itself — `re.search` then does not exist and the probe dies with exit 1 instead of
    # answering. It was named `re.py` at first and one interpreter happened to hide it;
    # a behavioural test under a different interpreter surfaced it immediately.
    cat > "$WORKDIR/probe_regex_check.py" <<'PYSRC'
import re, sys
try:
    print("yes" if re.search(sys.argv[1], sys.argv[2]) else "no")
except re.error:
    print("badpattern")
PYSRC
    run_bounded "$WORKDIR/po" python3 "$WORKDIR/probe_regex_check.py" "$pattern" "$input"
    rc=$?
    [ "$rc" = "124" ] && emit_failed "python-re probe exceeded ${PROBE_TIMEOUT}s — the pattern may backtrack catastrophically"
    [ "$rc" = "0" ] || emit_failed "python3 probe failed to run (exit $rc)"
    matched=$(cat "$WORKDIR/po")
    [ "$matched" = "badpattern" ] && emit_failed "not a valid python regex"
    ;;
  *)
    # Unreachable: the enum was validated above. Kept so a future kind added to the
    # validation list but not to this dispatch fails loudly instead of silently.
    emit_failed "kind passed validation but has no matcher branch"
    ;;
esac

[ -n "$matched" ] || emit_failed "probe produced no result"

printf -- '-#-#- PROBE -#-#-\n'
printf -- '- status: ok\n'
printf -- '- kind: %s\n' "$KIND"
printf -- '- matched: %s\n' "$matched"
