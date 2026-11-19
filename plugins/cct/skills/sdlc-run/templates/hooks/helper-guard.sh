#!/usr/bin/env bash
# PreToolUse hook on Bash: a helper (a subagent) never starts a heavy command outside the heavy-job
# queue. Exit 2 refuses it and tells the helper to run it as `heavy.py run -- <command>`. The owner's
# own session is never touched: the payload fields `agent_id` and `agent_type` name a subagent, and
# heavy.py reads them defensively (absent, empty or unreadable is allowed).
#
# A repo adopted before the queue has no scripts/heavy.py: no opinion. The logic is
# `heavy.py guard-main --hook`; this wrapper only names it for settings.json and the audit.
set -uo pipefail
export PYTHONDONTWRITEBYTECODE=1 # a hook must not leave __pycache__ in a clean checkout
heavy="$(dirname "$0")/../../scripts/heavy.py"
[ -f "$heavy" ] || exit 0
exec python3 "$heavy" guard-main --hook
