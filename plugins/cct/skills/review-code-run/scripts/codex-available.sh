#!/usr/bin/env bash
# Usage: codex-available.sh
# Purpose: Preflight for the Codex co-review lane. Reports whether the Codex CLI is
#          installed and authenticated, so `codex-lane.md` can run the pass, degrade
#          to Claude-only, or stop with a fix instruction.
#
# It knows nothing about secrets. Withholding secret-shaped files is
# `codex-review.sh`'s job — it builds the sanitized mirror and so owns the scan
# (`codex-scan-secrets.sh`). Keeping the scan out of the preflight is what the
# withhold-instead-of-refuse design bought: nothing routes on secrets any more, so
# the preflight has one question to answer and answers it.
#
# Output sections:
#   -#-#- CODEX_PREFLIGHT -#-#-
#   - available: yes|no
#   - reason: <empty when available, else why not and how to fix it>
#   - version: <codex --version output, or empty — informational only, nothing routes on it>
#
# Exit status is always 0 — availability is data for the caller to route on, never an
# error. The caller reads `- available:`.

set -uo pipefail

emit() {
  printf -- '-#-#- CODEX_PREFLIGHT -#-#-\n'
  printf -- '- available: %s\n' "$1"
  printf -- '- reason: %s\n' "$2"
  printf -- '- version: %s\n' "$3"
}

if ! command -v codex >/dev/null 2>&1; then
  emit no "codex CLI not on PATH — install with: npm install -g @openai/codex" ""
  exit 0
fi

version=$(codex --version 2>/dev/null | head -1)

# `codex login status` covers the ChatGPT-account path; OPENAI_API_KEY covers the
# API-key path. Only presence is tested — the value is never read or printed.
if ! { codex login status >/dev/null 2>&1 || [ -n "${OPENAI_API_KEY:-}" ]; }; then
  emit no "codex CLI not authenticated — run: codex login (or export OPENAI_API_KEY)" "$version"
  exit 0
fi

emit yes "" "$version"
