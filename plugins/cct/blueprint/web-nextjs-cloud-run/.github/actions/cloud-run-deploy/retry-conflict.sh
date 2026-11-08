#!/usr/bin/env bash
# Source this file before a Cloud Run service write. Each attempt invokes a fresh command.
retry_conflict() {
  local attempt output status
  for ((attempt = 1; attempt <= 5; attempt++)); do
    if output=$("$@" 2>&1); then
      [ -z "$output" ] || printf '%s\n' "$output"
      return 0
    else
      status=$?
    fi
    printf '%s\n' "$output" >&2
    if [[ "$output" != *ABORTED* && "$output" != *Conflict* ]]; then
      return "$status"
    fi
    [ "$attempt" -lt 5 ] || return "$status"
    sleep $((attempt * ${RETRY_BACKOFF_SECONDS:-3}))
  done
}
