#!/usr/bin/env bash
# Offline test of ph's safety guards: no network, curl is a stub on PATH that records every call.
# Run: bash test_ph.sh   (exit 0 = all pass)
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd)
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
mkdir "$tmp/bin"
cat >"$tmp/bin/curl" <<'STUB'
#!/usr/bin/env bash
printf '%s\n' "$*" >>"$CURL_LOG"
cat >>"$CURL_LOG.stdin"
printf '{"id":1,"leak":"phx_abcdefghijklmnop","results":[]}\n200'
STUB
chmod +x "$tmp/bin/curl"
export PATH="$tmp/bin:$PATH" CURL_LOG="$tmp/curl.log"
export POSTHOG_API_KEY=phx_testkey0123456789 POSTHOG_HOST=https://eu.posthog.com POSTHOG_PROJECT_ID=1

fails=0
ph() { : >"$CURL_LOG"; : >"$CURL_LOG.stdin"; out=$(bash "$here/ph" "$@" 2>&1); rc=$?; calls=$(grep -c . "$CURL_LOG" || true); }
expect() { # name condition
  if eval "$2"; then echo "ok   $1"; else echo "FAIL $1 (rc=$rc calls=$calls out=${out:0:200})"; fails=$((fails + 1)); fi
}

ph GET api/projects/;                 expect "path without leading / refused" '[[ $rc == 2 && $calls == 0 ]]'
ph GET @evil.com/x;                   expect "path @host refused" '[[ $rc == 2 && $calls == 0 ]]'
ph GET .evil.com/x;                   expect "path .host refused" '[[ $rc == 2 && $calls == 0 ]]'
ph GET //evil.com/x;                  expect "path // refused" '[[ $rc == 2 && $calls == 0 ]]'
ph GET /api/users/@me/;               expect "@ later in the path allowed" '[[ $rc == 0 && $calls == 1 ]]'
ph TRACE /api/users/@me/;             expect "bad method refused" '[[ $rc != 0 && $calls == 0 ]]'
POSTHOG_HOST=http://eu.posthog.com ph GET /api/users/@me/;        expect "http host refused" '[[ $rc == 1 && $calls == 0 ]]'
POSTHOG_HOST=https://eu.posthog.com/x ph GET /api/users/@me/;     expect "host with a path refused" '[[ $rc == 1 && $calls == 0 ]]'
POSTHOG_HOST=https://eu.i.posthog.com ph GET /api/users/@me/;     expect "ingestion host refused" '[[ $rc == 1 && $calls == 0 ]]'

ph flags create cct-test;             expect "flags create without --yes is a dry run" '[[ $rc == 0 && $calls == 0 && $out == *"DRY RUN"* ]]'
ph experiments create x --flag f;     expect "experiments create without --yes is a dry run" '[[ $rc == 0 && $calls == 0 && $out == *"DRY RUN"* ]]'
ph dashboards create x;               expect "dashboards create without --yes is a dry run" '[[ $rc == 0 && $calls == 0 && $out == *"DRY RUN"* ]]'
ph annotations create deploy;         expect "annotations create without --yes is a dry run" '[[ $rc == 0 && $calls == 0 && $out == *"DRY RUN"* ]]'
ph dashboards add 1 2;                expect "dashboards add without --yes is a dry run" '[[ $rc == 0 && $calls == 0 && $out == *"DRY RUN"* ]]'
ph PATCH '/api/projects/{project}/feature_flags/1/' '{"active":true}'; expect "raw PATCH without --yes is a dry run" '[[ $rc == 0 && $calls == 0 && $out == *"DRY RUN"* ]]'
ph DELETE '/api/projects/{project}/x/1/';                            expect "raw DELETE without --yes is a dry run" '[[ $rc == 0 && $calls == 0 ]]'
ph POST '/api/projects/{project}/query/' '{"query":{}}';             expect "raw POST to /query/ is a read" '[[ $rc == 0 && $calls == 1 ]]'
ph dashboards create x --yes;         expect "--yes sends the write" '[[ $rc == 0 && $calls == 1 ]]'

ph GET /api/users/@me/
expect "key never on the curl command line" '! grep -q phx_testkey "$CURL_LOG"'
expect "key goes to curl on stdin" 'grep -q "Authorization: Bearer phx_testkey" "$CURL_LOG.stdin"'
expect "https only, no redirects" 'grep -q -- "--proto =https --max-redirs 0" "$CURL_LOG"'
expect "keys in responses redacted" '[[ $out == *"ph_[redacted]"* && $out != *phx_abc* ]]'
ph flags rollout 1 150;               expect "rollout over 100 refused" '[[ $rc == 2 && $calls == 0 ]]'
ph recordings get '../../users';      expect "session id with a path refused" '[[ $rc == 2 && $calls == 0 ]]'

git init -q "$tmp/repo"
ph recordings export abc-123 "$tmp/repo/out.jsonl"; expect "recording export inside a git repo refused" '[[ $rc == 1 && $calls == 0 && ! -e "$tmp/repo/out.jsonl" ]]'
: >"$tmp/exists.jsonl"
ph recordings export abc-123 "$tmp/exists.jsonl"; expect "recording export never overwrites" '[[ $rc == 1 && $calls == 0 ]]'

((fails == 0)) && echo "all passed" || { echo "$fails failed"; exit 1; }
