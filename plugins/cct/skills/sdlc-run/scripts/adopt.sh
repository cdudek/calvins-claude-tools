#!/usr/bin/env bash
# Install or refresh the SDLC chain in the current repo. See adopt.py for what is
# generated and what is kept. Usage: adopt.sh [--dry-run] [--preset node|python]
set -euo pipefail
exec python3 "$(dirname "$0")/adopt.py" "$@"
