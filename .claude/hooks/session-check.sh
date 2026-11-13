#!/usr/bin/env bash
# SessionStart hook: tell Claude when the plan gate cannot work on this machine. Stdout
# becomes session context, so Claude passes it on instead of silently skipping the gate.
# Never fails a session. docs/sdlc.md has the install; sdlc.json names the command.
set -uo pipefail
. "$(dirname "$0")/sdlc-config.sh"

missing=()
command -v plannotator >/dev/null 2>&1 || missing+=("the plannotator binary")
installed="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/plugins/installed_plugins.json"
{ [ -f "$installed" ] && grep -q '"plannotator@plannotator"' "$installed"; } || missing+=("the plannotator Claude Code plugin")

if [ "${#missing[@]}" -gt 0 ]; then
  tools=$(sdlc_get 'cfg["toolsCommand"]' || echo "the install in docs/sdlc.md")
  docs=$(sdlc_get 'cfg["docs"]' || echo "docs/sdlc.md")
  echo "SDLC setup incomplete on this machine: $(IFS=,; echo "${missing[*]}") missing." \
       "Plans will not be gated in a browser. Fix: \`$tools\`, then restart Claude Code. See $docs."
fi

# -#-#- STALE COPIES -#-#-
# WHY THIS IS AT SESSION START. The hooks, the workflows and the guardrail test that CI
# actually runs are COPIES inside this repo -- CI runs on a runner with no plugin installed.
# They do not update themselves. So a repo can sit for weeks passing its own stale checks
# while the kit has already changed the rule, and nothing says a word. `status.sh` knows,
# but only when something asks it, and chain step 0 asks only once a change is already
# starting -- by then the stale guardrail is what fails the PR.
#
# Best effort by design: the kit lives at a cache path that changes on every plugin update,
# and old versions are never swept, so a machine holds many copies at once. This asks EVERY
# copy and stays quiet when the repo matches ANY of them -- a repo that matches an installed
# kit is not stale, whichever copy a session happens to load. Picking one copy by mtime is
# what made this cry wolf: it landed on a kit OLDER than the repo and reported the repo
# behind. A SessionStart hook that guesses wrong must cost nothing.
#
# Only a copy that actually has the flag is ever run. An adopt.py predating it treats
# `--templates-hash` as an ordinary run and REWRITES THE REPO -- a full adopt, from a
# session hook, unasked. 20 of the 31 copies on the machine that found this were that old.
have=$(sdlc_get 'cfg.get("kitTemplates","")' 2>/dev/null || echo "")
asked=""
match=""
for adopt in "${CLAUDE_CONFIG_DIR:-$HOME/.claude}"/plugins/cache/*/cct/*/skills/sdlc-run/scripts/adopt.py; do
  [ -f "$adopt" ] || continue
  grep -q -- "--templates-hash" "$adopt" || continue
  want=$(python3 "$adopt" --templates-hash 2>/dev/null || echo "")
  # A hash and nothing else. Anything longer is a copy that ran instead of answering.
  case "$want" in [0-9a-f]*) [ "${#want}" -eq 12 ] || continue ;; *) continue ;; esac
  asked=1
  if [ "$have" = "$want" ]; then
    match=1
    break
  fi
done
if [ -n "$asked" ]; then
  if [ -z "$match" ]; then
    # Hashes carry no order, so this cannot say WHICH side is behind, and must not pretend
    # to. A repo adopted from a local kit checkout is AHEAD of every cached copy, and
    # adopting from a stale cache would then quietly roll the repo back.
    echo "This repo's SDLC copies match no kit installed on this machine." \
         "The hooks, the workflows and the guardrail test live IN the repo," \
         "because CI runs them where no plugin exists -- so they do not update themselves." \
         "Either the repo is behind the kit, or the plugin cache is behind the repo." \
         "Fix: run \`/reload-plugins\` first, and if this still shows, run" \
         "\`/cct:sdlc-run adopt\`, which rewrites them and opens a normal PR." \
         "Tell the user this, in one line, before starting any change."
  fi
fi
exit 0
