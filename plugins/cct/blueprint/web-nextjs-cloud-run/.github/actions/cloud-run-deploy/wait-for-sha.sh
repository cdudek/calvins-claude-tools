#!/usr/bin/env bash
# Polls $URL until it returns {"sha": "$EXPECT_SHA"} on $1 consecutive reads, or fails after
# $TIMEOUT_SECONDS. Sends $TOKEN as a bearer token when it is set (private services).
# Consecutive reads, because one hit can come from an instance that is still switching over.
set -uo pipefail
need="${1:-1}"
poll=10
deadline=$(($(date +%s) + ${TIMEOUT_SECONDS:-600}))
auth=()
[ -n "${TOKEN:-}" ] && auth=(-H "Authorization: Bearer ${TOKEN}")
hits=0
live=none
echo "Waiting for ${URL} to serve ${EXPECT_SHA} (${need} in a row)…"
while [ "$(date +%s)" -lt "$deadline" ]; do
  live="$(curl -fsS --max-time 10 "${auth[@]}" "$URL" | jq -r '.sha // "none"' 2>/dev/null || echo unreachable)"
  if [ "$live" = "$EXPECT_SHA" ]; then
    hits=$((hits + 1))
    echo "  match ${hits}/${need}"
    [ "$hits" -ge "$need" ] && exit 0
  else
    hits=0
    echo "  live=${live}"
  fi
  sleep "$poll"
done
echo "::error::${URL} serves '${live}', expected '${EXPECT_SHA}' after ${TIMEOUT_SECONDS:-600}s."
exit 1
