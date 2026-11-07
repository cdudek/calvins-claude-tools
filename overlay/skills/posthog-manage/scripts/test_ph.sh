#!/usr/bin/env bash
# Offline tests of ph: its safety guards and its command contracts. No network: curl is a stub on PATH that records
# every call and answers from a route table (METHOD, path regex, HTTP status, body or @fixture-file).
# Run: bash test_ph.sh   (exit 0 = all pass). PH_BASH=/bin/bash runs ph under another bash, such as macOS's 3.2.
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd)
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
chmod 700 "$tmp"
mkdir "$tmp/bin" "$tmp/fx"
cat >"$tmp/bin/curl" <<'STUB'
#!/usr/bin/env bash
printf '%s\n' "$*" >>"$CURL_LOG"
cat >>"$CURL_LOG.stdin"
env | grep -c '^POSTHOG_API_KEY=' >>"$CURL_LOG.env" || true
method=GET url="" prev=""
for a in "$@"; do
  [[ "$prev" == -X ]] && method=$a
  [[ "$a" == https://* ]] && url=$a
  prev=$a
done
path="/${url#https://*/}"
if [[ -n "${CURL_STDERR:-}" ]]; then echo "$CURL_STDERR" >&2; fi
while read -r m re st body; do
  [[ -z "$m" || "$m" == "#"* ]] && continue
  if [[ "$method" == "$m" && "$path" =~ $re ]]; then
    if [[ "$st" == 429once ]]; then
      if [[ ! -e "$CURL_LOG.429" ]]; then : >"$CURL_LOG.429"; printf '{}\n429'; exit 0; fi
      st=200
    fi
    if [[ "$body" == @* ]]; then cat "${body#@}"; else printf '%s' "$body"; fi
    printf '\n%s' "$st"
    exit 0
  fi
done <"$ROUTES"
printf '{"id":1,"leak":"phx_abcdefghijklmnop","results":[]}\n200'
STUB
chmod +x "$tmp/bin/curl"
export PATH="$tmp/bin:$PATH" CURL_LOG="$tmp/curl.log" ROUTES="$tmp/routes" HOME="$tmp" ZDOTDIR="$tmp"
export POSTHOG_API_KEY=phx_testkey0123456789 POSTHOG_HOST=https://eu.posthog.com POSTHOG_PROJECT_ID=1
: >"$ROUTES"

fails=0
ph() {
  : >"$CURL_LOG"; : >"$CURL_LOG.stdin"; : >"$CURL_LOG.env"; rm -f "$CURL_LOG.429"
  out=$("${PH_BASH:-bash}" "$here/ph" "$@" 2>"$tmp/err"); rc=$?; err=$(cat "$tmp/err")
  calls=$(grep -c . "$CURL_LOG" || true)
}
expect() { # name condition
  if eval "$2"; then echo "ok   $1"; else echo "FAIL $1 (rc=$rc calls=$calls out=${out:0:300} err=${err:0:300})"; fails=$((fails + 1)); fi
}
routes() { printf '%s\n' "$@" >"$ROUTES"; }
code_of() { sed -n 's/^Approval code: \([0-9a-f]\{12\}\)\..*/\1/p' <<<"$out"; }

# ── Help and credentials ──────────────────────────────────────────────────────
POSTHOG_API_KEY= POSTHOG_HOST= ph help;           expect "help needs no credentials" '[[ $rc == 0 && $calls == 0 && $out == *"ph flags rollout"* ]]'
POSTHOG_API_KEY= ph flags --help;                   expect "area help, no credentials" '[[ $rc == 0 && $calls == 0 && $out == *"ph flags create"* && $out != *"ph recordings"* ]]'

# ── Transport guards ──────────────────────────────────────────────────────────
ph GET api/projects/;                 expect "path without leading / refused" '[[ $rc == 2 && $calls == 0 ]]'
ph GET @evil.com/x;                   expect "path @host refused" '[[ $rc == 2 && $calls == 0 ]]'
ph GET .evil.com/x;                   expect "path .host refused" '[[ $rc == 2 && $calls == 0 ]]'
ph GET //evil.com/x;                  expect "path // refused" '[[ $rc == 2 && $calls == 0 ]]'
ph GET /api/users/@me/;               expect "@ later in the path allowed" '[[ $rc == 0 && $calls == 1 ]]'
ph TRACE /api/users/@me/;             expect "bad method refused" '[[ $rc != 0 && $calls == 0 ]]'
POSTHOG_HOST=http://eu.posthog.com ph GET /api/users/@me/;        expect "http host refused" '[[ $rc == 1 && $calls == 0 ]]'
POSTHOG_HOST=https://eu.posthog.com/x ph GET /api/users/@me/;     expect "host with a path refused" '[[ $rc == 1 && $calls == 0 ]]'
POSTHOG_HOST=https://eu.i.posthog.com ph GET /api/users/@me/;     expect "ingestion host refused" '[[ $rc == 1 && $calls == 0 ]]'
POSTHOG_HOST=https://eu.i.posthog.com:443 ph GET /api/users/@me/; expect "ingestion host with a port refused" '[[ $rc == 1 && $calls == 0 ]]'

ph GET /api/users/@me/
expect "key never on the curl command line" '! grep -q phx_testkey "$CURL_LOG"'
expect "key goes to curl on stdin" 'grep -q "Authorization: Bearer phx_testkey" "$CURL_LOG.stdin"'
expect "curl ignores ~/.curlrc (-q first), no globbing, https only, no redirects, time limits" \
  'grep -q -- "^-q -sS -g --proto =https --proto-redir =https --max-redirs 0 --connect-timeout 10 --max-time 120" "$CURL_LOG"'
expect "the key is not inherited by child processes" '! grep -q "^[1-9]" "$CURL_LOG.env"'
expect "keys in responses redacted" '[[ $out == *"ph_[redacted]"* && $out != *phx_abc* ]]'
CURL_STDERR="curl: (35) handshake failed for phx_secretsecretsecret" ph GET /api/users/@me/
expect "keys in curl's stderr redacted" '[[ $err == *"ph_[redacted]"* && $err != *phx_secret* ]]'

# ── Writes: dry run, approval code bound to the request and the object ──────
ph flags create cct-test;             expect "flags create without --yes is a dry run" '[[ $rc == 0 && $calls == 0 && $out == *"DRY RUN"* && -n $(code_of) ]]'
ph dashboards create x;               expect "dashboards create without --yes is a dry run" '[[ $rc == 0 && $calls == 0 && $out == *"DRY RUN"* ]]'
c=$(code_of)
ph dashboards create x --yes "$c";    expect "--yes CODE sends the write it showed" '[[ $rc == 0 && $calls == 1 && $out == "{\"id\":1}" ]]'
ph dashboards create y --yes "$c";    expect "--yes CODE refuses a different request" '[[ $rc == 3 && $calls == 0 ]]'
ph dashboards create x --yes;         expect "--yes without a code refused" '[[ $rc == 2 && $calls == 0 ]]'
ph annotations create deploy;         expect "annotations create is a dry run" '[[ $rc == 0 && $calls == 0 && $out == *"DRY RUN"* ]]'
ph annotations create -- --yes;       expect "-- makes --yes a literal argument" '[[ $rc == 0 && $calls == 0 && $out == *"annotation \"--yes\""* ]]'
ph dashboards add 1 2;                expect "dashboards add is a dry run" '[[ $rc == 0 && $calls == 0 && $out == *"DRY RUN"* ]]'
ph PATCH '/api/projects/{project}/feature_flags/1/' '{"active":true}'; expect "raw PATCH is a dry run" '[[ $rc == 0 && $calls == 0 && $out == *"DRY RUN"* ]]'
ph DELETE '/api/projects/{project}/x/1/';                            expect "raw DELETE is a dry run" '[[ $rc == 0 && $calls == 0 ]]'
ph POST '/api/projects/{project}/x/' '{"token":"phx_abcdefghijk123"}'; expect "dry-run bodies are redacted" '[[ $out == *"ph_[redacted]"* && $out != *phx_abcdefghijk123* ]]'
ph POST '/api/projects/{project}/x/' 'not json';                     expect "raw bodies must be JSON" '[[ $rc == 2 && $calls == 0 ]]'
printf '{"name":"a"}' >"$tmp/body.json"
ph PATCH '/api/projects/{project}/dashboards/1/' "@$tmp/body.json"; c=$(code_of)
expect "an @file dry run shows the file's bytes" '[[ $out == *"Body: {\"name\":\"a\"}"* ]]'
printf '{"name":"b"}' >"$tmp/body.json"
ph PATCH '/api/projects/{project}/dashboards/1/' "@$tmp/body.json" --yes "$c"; expect "a changed @file refuses the old code" '[[ $rc == 3 && $calls == 0 ]]'

printf '{"results":[{"id":7,"key":"new-checkout","active":true,"version":1,"filters":{"groups":[{"properties":[{"key":"email","operator":"icontains","value":"@acme.com"}],"rollout_percentage":5}]}}]}' >"$tmp/fx/flag1.json"
sed 's/"version":1/"version":2/; s/"rollout_percentage":5/"rollout_percentage":50/' "$tmp/fx/flag1.json" >"$tmp/fx/flag2.json"
routes "GET feature_flags/\?key= 200 @$tmp/fx/flag1.json" "POST set_release_condition_rollout 200 {\"id\":7,\"key\":\"new-checkout\",\"version\":2,\"created_by\":{\"email\":\"ana@example.com\"}}"
ph flags rollout new-checkout 20; c=$(code_of)
expect "rollout preview names the condition and the change" '[[ $rc == 0 && $calls == 1 && $out == *"5% -> 20%"* && $out == *"email icontains"* ]]'
ph flags rollout new-checkout 20 --yes "$c"
expect "rollout sends with the version it previewed, and summarises the answer" '[[ $rc == 0 && $calls == 2 && $out == *"\"version\":2"* && $out != *ana@example.com* ]]'
expect "rollout body carries the version" 'grep -q "\"version\":1" "$CURL_LOG"'
routes "GET feature_flags/\?key= 200 @$tmp/fx/flag2.json" "POST set_release_condition_rollout 200 {}"
ph flags rollout new-checkout 20 --yes "$c"
expect "a flag changed since the dry run refuses the approval, nothing sent" '[[ $rc == 3 && $calls == 1 && $err == *"changed since the dry run"* ]]'
ph flags rollout 1 150;               expect "rollout over 100 refused" '[[ $rc == 2 && $calls == 0 ]]'
ph flags create x --variants a:50,b:40; expect "variants must add up to 100" '[[ $rc == 2 && $calls == 0 ]]'

# ── HTTP errors and retries ───────────────────────────────────────────────────
routes "GET /api/users 401 {\"detail\":\"bad key\"}"
ph GET /api/users/@me/;               expect "401 names the scope problem" '[[ $rc == 1 && $err == *"lacks the scope"* ]]'
routes "POST set_release_condition_rollout 409 {}" "GET feature_flags/\?key= 200 @$tmp/fx/flag1.json"
ph flags rollout new-checkout 20; c=$(code_of); ph flags rollout new-checkout 20 --yes "$c"
expect "409 says someone changed it" '[[ $rc == 1 && $err == *"409"* && $err == *"re-decide"* ]]'
routes "GET /api/users 429once {\"ok\":1}"
ph GET /api/users/@me/;               expect "a read meeting 429 is retried once" '[[ $rc == 0 && $calls == 2 && $out == *"\"ok\":1"* ]]'
routes "POST /x/ 503 {}"
ph POST '/api/projects/{project}/x/' '{}'; c=$(code_of); ph POST '/api/projects/{project}/x/' '{}' --yes "$c"
expect "a write is never retried" '[[ $rc == 1 && $calls == 1 ]]'

# ── Lists, queries, partial results ───────────────────────────────────────────
routes "GET feature_flags/\?limit 200 {\"next\":\"https://eu.posthog.com/next\",\"results\":[{\"id\":1,\"key\":\"a\",\"active\":true,\"filters\":{\"groups\":[]}}]}"
ph flags list;                        expect "a list with more pages says it is partial" '[[ $rc == 0 && $err == *"partial"* && $out == *"\"key\":\"a\""* ]]'
printf '{"columns":["event","n30","n90","last_seen"],"results":[["page_view",10,30,"2026-11-06"],["signup",2,5,"2026-11-05"]],"hasMore":true,"limit":100}' >"$tmp/fx/q.json"
routes "POST /query/ 200 @$tmp/fx/q.json"
ph query "SELECT event, countIf(timestamp > now() - INTERVAL 30 DAY) AS n30, count() AS n90, max(timestamp) AS last_seen FROM events GROUP BY event"
expect "query prints one object per row" '[[ $rc == 0 && $(wc -l <<<"$out") -eq 2 && $out == *"{\"event\":\"page_view\",\"n30\":10,\"n90\":30,\"last_seen\":\"2026-11-06\"}"* ]]'
expect "a truncated query says so" '[[ $err == *"partial"* ]]'
# the jq filter tracking-audit documents, read from its SKILL.md so the two cannot drift apart
filter=$(grep -E 'scripts/ph query .*\| jq -r' "$here/../../tracking-audit/SKILL.md" | sed -E "s/.*\| jq -r '(.*)'\$/\1/")
audit=$(printf '%s\n' "$out" | jq -r "${filter:-.missing}")
expect "the tracking-audit pipeline reads ph query output" '[[ $audit == "page_view	10	30	2026-11-06"* ]]'
routes "POST /query/ 200 {\"error\":\"Unknown table\",\"results\":[]}"
ph query "SELECT 1 FROM nope";        expect "a query error stops" '[[ $rc == 1 && $err == *"Unknown table"* ]]'
routes "POST /query/ 200 {\"query_status\":{\"complete\":false},\"results\":[]}"
ph query "SELECT 1";                  expect "an unfinished query stops" '[[ $rc == 1 && $err == *"still running"* ]]'

# ── Experiments ───────────────────────────────────────────────────────────────
printf '{"results":[{"id":9,"key":"exp-flag","active":true,"version":3,"filters":{"groups":[{"rollout_percentage":100}],"multivariate":{"variants":[{"key":"control","rollout_percentage":50},{"key":"test","rollout_percentage":50}]}}}]}' >"$tmp/fx/expflag.json"
routes "GET feature_flags/\?key= 200 @$tmp/fx/expflag.json"
ph experiments create "Copy test" --flag exp-flag --event purchase
expect "experiment on an existing flag reuses it and sends no flag settings" '[[ $rc == 0 && $out == *"EXISTING flag exp-flag (active=true"* && $out != *"\"feature_flag\":"* ]]'
ph experiments create "Copy test" --flag exp-flag --variants control:50,b:50
expect "variants on an existing flag are refused" '[[ $rc == 2 ]]'
routes "GET feature_flags/\?key= 200 {\"results\":[]}"
ph experiments create "Copy test" --flag new-flag --event purchase
expect "experiment on a new flag sends the flag settings" '[[ $rc == 0 && $out == *"NEW flag"* && $out == *"\"feature_flag\":{\"filters\""* ]]'
printf '{"id":5,"name":"Rev","metrics":[{"kind":"ExperimentMetric","metric_type":"ratio","name":"revenue per order"}]}' >"$tmp/fx/exp.json"
printf '{"baseline":{"key":"control","number_of_samples":100,"sum":50,"sum_squares":1,"denominator_sum":200},"variant_results":[{"key":"test","method":"bayesian","number_of_samples":100,"sum":60,"sum_squares":1,"denominator_sum":200,"chance_to_win":0.8,"significant":false,"credible_interval":[0.1,0.4],"validation_failures":["not-enough-exposures"]}]}' >"$tmp/fx/expres.json"
routes "GET experiments/5/ 200 @$tmp/fx/exp.json" "POST /query/ 200 @$tmp/fx/expres.json"
ph experiments results 5
expect "a ratio metric is sum / denominator_sum" '[[ $rc == 0 && $out == *"\"variant\":\"control\""*"\"estimate\":0.25"* && $out == *"\"estimate\":0.3,"* && $out == *"\"estimate_is\":\"ratio\""* ]]'
expect "validation failures are kept" '[[ $out == *"not-enough-exposures"* ]]'

# ── Personal data stays out by default ────────────────────────────────────────
routes "GET /api/users/@me 200 {\"email\":\"ana@example.com\",\"organizations\":[{\"id\":\"o1\",\"name\":\"Acme\"}]}" \
       "GET /api/organizations/o1/projects 200 {\"results\":[{\"id\":1,\"name\":\"Web\"}]}"
ph whoami;                            expect "whoami hides the email" '[[ $rc == 0 && $out != *ana@example.com* && $out == *"\"projects\":[{\"id\":1"* ]]'
ph whoami --personal;                 expect "--personal shows it" '[[ $out == *ana@example.com* ]]'
routes "GET session_recordings/\? 200 {\"has_next\":true,\"results\":[{\"id\":\"s1\",\"distinct_id\":\"ana@example.com\",\"start_url\":\"https://shop.example.com/reset?token=abc#x\",\"console_error_count\":2}]}"
ph recordings list
expect "recordings hide distinct ids and URL queries, and say when partial" '[[ $rc == 0 && $out != *ana@example.com* && $out != *token=abc* && $out == *"https://shop.example.com/reset"* && $err == *partial* ]]'
routes "GET console_logs 200 {\"results\":[{\"timestamp\":\"t\",\"level\":\"error\",\"message\":\"login failed for ana@example.com at https://x.example.com/a?code=1\",\"truncated\":false}],\"has_more\":false,\"console_log_capture_enabled\":false,\"logs_expired\":false}"
ph recordings console s1
expect "console text is cleaned and capture-off is said" '[[ $rc == 0 && $out == *"[email]"* && $out != *code=1* && $err == *"capture is off"* ]]'
routes "GET persons/\? 200 {\"results\":[{\"uuid\":\"p1\",\"distinct_ids\":[\"ana@example.com\",\"x\"],\"is_identified\":true}]}"
ph persons find x;                    expect "persons find hides distinct ids" '[[ $rc == 0 && $out != *ana@example.com* && $out == *"\"distinct_id_count\":2"* ]]'
printf '{"results":[{"id":7,"key":"f","active":true,"version":1,"filters":{"groups":[]}}]}' >"$tmp/fx/f.json"
routes "GET feature_flags/\?key= 200 @$tmp/fx/f.json" "POST test_evaluation 200 {\"result\":true,\"reason\":\"condition_match\",\"condition_index\":0,\"person_properties\":{\"email\":\"ana@example.com\"}}"
ph flags evaluate f x;                expect "flag evaluation hides person properties" '[[ $rc == 0 && $out == *"\"result\":true"* && $out != *ana@example.com* ]]'

# ── Project selection ─────────────────────────────────────────────────────────
routes "GET /api/users/@me 200 {\"organizations\":[{\"id\":\"o1\",\"name\":\"A\"},{\"id\":\"o2\",\"name\":\"B\"}]}" \
       "GET /api/organizations/o1/projects 200 {\"results\":[{\"id\":1,\"name\":\"Web\"}]}" \
       "GET /api/organizations/o2/projects 403 {}"
POSTHOG_PROJECT_ID= ph flags list
expect "no automatic project when an organization could not be listed" '[[ $rc == 1 && $err == *"could not be listed"* ]]'

# ── Recording export ──────────────────────────────────────────────────────────
: >"$ROUTES"
ph recordings get '../../users';      expect "session id with a path refused" '[[ $rc == 2 && $calls == 0 ]]'
mkdir -p "$tmp/repo/.git" "$tmp/out"; chmod 700 "$tmp/out"
ph recordings export abc-123 "$tmp/repo/out.jsonl"; expect "export inside a git repo refused, even without git" '[[ $rc == 1 && $calls == 0 && ! -e "$tmp/repo/out.jsonl" ]]'
: >"$tmp/out/exists.jsonl"
ph recordings export abc-123 "$tmp/out/exists.jsonl"; expect "export never overwrites" '[[ $rc == 1 && $calls == 0 ]]'
ln -s "$tmp/out/target" "$tmp/out/link.jsonl"
ph recordings export abc-123 "$tmp/out/link.jsonl"; expect "export never follows a symlink, even a dangling one" '[[ $rc == 1 && $calls == 0 && ! -e "$tmp/out/target" ]]'
mkdir "$tmp/shared"; chmod 777 "$tmp/shared"
ph recordings export abc-123 "$tmp/shared/x.jsonl"; expect "export refuses a folder others can write" '[[ $rc == 1 && $calls == 0 ]]'
routes "GET snapshots/\$ 200 {\"sources\":[{\"source\":\"blob_v2\",\"blob_key\":\"0\"}]}" "GET snapshots/\?source 200 [1,{\"type\":2}]"
ph recordings export abc-123 "$tmp/out/s.jsonl"
expect "export writes a new file readable by the user only" '[[ $rc == 0 && $(ls -l "$tmp/out/s.jsonl" | cut -c1-10) == "-rw-------" && $out == *"\"blocks\":1"* ]]'
routes "GET snapshots/\$ 200 {\"sources\":[{\"source\":\"blob_v2\",\"blob_key\":\"0\"}]}" "GET snapshots/\?source 500 {}"
ph recordings export abc-123 "$tmp/out/f.jsonl"
expect "a failed export leaves no partial file" '[[ $rc == 1 && ! -e "$tmp/out/f.jsonl" && $err == *"partial file was removed"* ]]'

((fails == 0)) && echo "all passed" || { echo "$fails failed"; exit 1; }
