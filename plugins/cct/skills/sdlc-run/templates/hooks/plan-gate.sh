#!/usr/bin/env bash
# PermissionRequest hook on ExitPlanMode: open the plan in plannotator so it is approved
# or annotated in a browser, not skimmed in chat. docs/sdlc.md.
#
# Exit 0 with no output = fall through to Claude Code's normal approval prompt. That is
# the right answer on a machine without plannotator, AND on one with the plannotator
# plugin installed -- the plugin registers this same hook, and two of them open two
# browser sessions for one plan.
set -euo pipefail

installed="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/plugins/installed_plugins.json"
if [ -f "$installed" ] && grep -q '"plannotator@plannotator"' "$installed"; then
  exit 0 # the plugin's hook handles it
fi
if ! command -v plannotator >/dev/null 2>&1; then
  exit 0 # nothing to gate with; normal prompt
fi
exec plannotator
