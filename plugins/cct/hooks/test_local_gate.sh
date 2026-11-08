#!/usr/bin/env bash
# Usage: bash test_local_gate.sh — local repository fixtures; no publication.
set -euo pipefail
python3 "$(dirname "$0")/test_local_gate.py"
