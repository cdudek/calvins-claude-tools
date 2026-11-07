# PostHog recipes

All calls go through `bash <skill>/scripts/ph` (written `ph` below). Lists print one JSON object per line; `--table` aligns them with a header, `--csv` gives CSV. Single objects print as one JSON line. Writes print `DRY RUN` and the request until `--yes`.

## Setup

```bash
ph check                       # POSTHOG_API_KEY / POSTHOG_HOST / POSTHOG_PROJECT_ID: set or missing
ph whoami                      # {email, host, organizations, projects: [{id, name, organization}], project}
ph projects --table
ph use <id>                    # checks the project, prints: export POSTHOG_PROJECT_ID=<id>
```

## Feature flags

```bash
ph flags list --table          # id, key, name, active, rollout (per condition), conditions, variants
ph flags get new-checkout      # + filters, version, url
ph flags evaluate new-checkout <distinct-id>   # + evaluation: {result, reason, condition_index, payload}
```

`evaluate` asks PostHog how the flag resolves for that person now (`test_evaluation`, a read). It needs the person to exist in PostHog; an inactive flag answers `flag_not_found`, a person outside the rollout `out_of_rollout_bound`. The public `/flags` endpoint takes the project key and is for apps, not for this skill.

Writes (dry run first, ask the user, then `--yes`):

```bash
ph flags create new-checkout --name "New checkout" --rollout 10 --prop plan=pro --prop email~@acme.com
ph flags create pricing-test --variants control:50,test:50          # multivariate
ph flags rollout new-checkout 20 [--condition 0]                    # one release condition's percentage
ph flags enable new-checkout ; ph flags disable new-checkout
ph flags delete new-checkout                                        # soft delete
```

- `create` makes the flag **inactive at 0 %** unless `--active` and `--rollout` say otherwise. `--prop k=v` is an exact match, `k~v` contains; both on person properties, all ANDed in one condition. For several conditions, cohorts or group flags, create it in the app or send the full `filters` with the raw call.
- `rollout`, `enable` and `disable` send the `version` from the read just before; if someone changed the flag in between, PostHog answers 409. Read again and re-decide.
- On a multivariate flag, `rollout` sets how many matching users get any variant, not the split between variants.

## Experiments

```bash
ph experiments list --table                     # id, name, status (draft|running|paused|stopped), flag, dates, variants
ph experiments get <id>                         # + metrics, description, conclusion, url
ph experiments results <id>                     # one row per metric and variant
```

A results row: `{metric, primary, variant, exposures, value, rate, chance_to_win, p_value, significant, interval}`. `exposures` is the number of people in the variant, `value` the metric sum (conversions for a funnel metric), `rate` = value / exposures. Bayesian projects fill `chance_to_win` and a credible interval, frequentist ones `p_value` and a confidence interval. No rows or zero exposures: not launched yet, or nobody saw it.

Writes:

```bash
ph experiments create "Checkout copy" --flag checkout-copy --event purchase                    # mean metric on one event
ph experiments create "Signup flow" --flag signup-flow --funnel signup_start,signup_complete --variants control:34,a:33,b:33
ph experiments launch <id>                      # activates the flag, start_date = now: real users enrol
ph experiments stop <id> --conclusion won --comment "B +4 %"   # end_date = now; the flag is not changed
ph experiments archive <id> [--disable-flag]    # only after stop
ph experiments delete <id>                      # soft delete; the flag stays (ph flags delete)
```

`create` makes a draft and the flag if its key is free. PostHog rejects a metric on an event the project never received; `--allow-unknown-events` overrides that only after the user confirms the event is coming. Shipping a variant (rolling the winner to everyone) is a flag change: `ph flags ...` or the app.

## Dashboards and insights

```bash
ph dashboards list --table
ph dashboards get <id>                          # {id, name, description, url, tiles: [{tile, insight, short_id, name, kind} | {tile, text}]}
ph dashboards url <id>                          # the app link to share; viewers need PostHog access
ph insights list --search checkout --table      # id, short_id, name, kind, last_modified_at
ph insights get <id|short_id>                   # {.., url, query, result}: computed fresh (refresh=blocking)
```

Writes:

```bash
ph dashboards create "Weekly growth"
ph insights create trend signup --name "Signups per week" --days 90 --interval week --dashboard <id>
ph insights create funnel visit signup purchase --name "Checkout funnel" --days 30
ph insights create hogql "SELECT toStartOfWeek(timestamp) AS week, count() FROM events WHERE event = 'purchase' GROUP BY week ORDER BY week" --name "Purchases"
ph dashboards add <dashboard-id> <insight-id>
ph insights delete <id> ; ph dashboards delete <id>          # soft deletes
```

A public share link (no login) is a sharing setting on the dashboard; turning it on publishes data, so leave it to the user in the app.

## Reports

```bash
ph trend purchase --days 30 --interval day                   # {series, date, value}
ph trend '$pageview' --days 7 --breakdown '$browser' --table # one series per value; "(none)" = property not set
ph trend '$pageview' --days 28 --interval week --math dau
ph funnel visit signup purchase --days 30 --window 14        # {step, event, count, of_first, median_seconds}
ph retention signup --return-event '$pageview' --period Week --intervals 8   # {cohort, size, retained: [per period]}
ph events top --days 7 --table                               # {event, count, users, last_seen}
ph query "SELECT ..." --csv
```

Quote event names that start with `$` in single quotes. Event names come from `ph events top` or `ph events list`.

## HogQL

`ph query` runs PostHog's SQL over `events` (and `persons`, `sessions`, `session_replay_events`). Event properties are `properties.<name>`, person properties `person.properties.<name>` (keep them out of output: personal data). Times are UTC.

A conversion rate between two events (quick, ignores order):

```sql
SELECT uniqIf(person_id, event = 'checkout_start') AS started,
       uniqIf(person_id, event = 'purchase') AS bought,
       round(bought / nullIf(started, 0), 3) AS rate
FROM events
WHERE event IN ('checkout_start', 'purchase') AND timestamp > now() - INTERVAL 30 DAY
```

Errors per day from exception events:

```sql
SELECT toDate(timestamp) AS day, count() AS exceptions, uniq($session_id) AS sessions
FROM events WHERE event = '$exception' AND timestamp > now() - INTERVAL 14 DAY
GROUP BY day ORDER BY day
```

Recordings by activity, without the recordings API:

```sql
SELECT session_id, min(start_time) AS start, sum(click_count) AS clicks, sum(console_error_count) AS errors,
       sum(active_milliseconds) / 1000 AS active_seconds, any(first_url) AS first_url
FROM session_replay_events
WHERE start_time > now() - INTERVAL 1 DAY
GROUP BY session_id HAVING errors > 0 ORDER BY errors DESC LIMIT 50
```

## Does the tracking plan arrive?

Feed the registry's names into one query:

```sql
SELECT event, count() AS n, max(timestamp) AS last_seen
FROM events
WHERE timestamp > now() - INTERVAL 7 DAY
  AND event IN ('page_view', 'signup', 'checkout_start', 'purchase')
GROUP BY event
```

A name missing from the result did not arrive. Then check one event's properties are filled:

```sql
SELECT count() AS n,
       countIf(properties.order_value_band IS NULL) AS missing_band,
       countIf(properties.payment_method IS NULL) AS missing_method
FROM events
WHERE event = 'purchase' AND timestamp > now() - INTERVAL 7 DAY
```

Double firing shows as one user sending the event twice in one second:

```sql
SELECT count() AS duplicated_seconds
FROM (
  SELECT distinct_id, toStartOfInterval(timestamp, INTERVAL 1 SECOND) AS s, count() AS c
  FROM events
  WHERE event = 'checkout_start' AND timestamp > now() - INTERVAL 1 DAY
  GROUP BY distinct_id, s
  HAVING c > 1
)
```

To test a fresh change: the user opens the app with PostHog's debug mode (`?__posthog_debug=true` or `posthog.debug()`), clicks through, and the query above with `INTERVAL 10 MINUTE` confirms the events.

## Event and property definitions, actions

```bash
ph events list --search checkout --table        # id, name, last_seen_at, verified, tags, description
ph events describe purchase                     # + properties seen on it, with types
ph properties list --event purchase --table     # name, property_type, is_numerical, verified
ph actions list --table
ph events verify purchase                       # write; verified, descriptions and tags need a paid plan
```

Description and tags sync from a registry: the raw call, `ph PATCH '/api/projects/{project}/event_definitions/<id>/' '{"description":"...","tags":["meaningful_action"]}'` (dry run, then `--yes`).

## Session recordings

```bash
ph recordings list --days 1 --errors --table                 # id, start_time, duration, active_seconds, clicks, keys, console_errors, start_url, distinct_id, url
ph recordings list --days 7 --person ana@example.com --min-duration 60 --url /checkout
ph recordings get <session-id>                               # + inactive_seconds, mouse, console counts, person_uuid, event_count, url
ph recordings console <session-id> --level error             # the browser console, oldest first
ph recordings events <session-id> --table                    # timestamp, event, url, dom_event, exception types and values
ph playlists list --table ; ph playlists add <short-id> <session-id>   # add is a write
```

- `--person` takes a distinct id or an email (looked up through persons). `--errors` means at least one console error; `--url` matches the first URL, case-insensitive; `--min-duration` is in seconds.
- The replay link is `<host>/project/<project-id>/replay/<session-id>`; give it to the user, who watches it.
- Recordings expire after the plan's retention; `get` on an expired one answers 404.

**Export** (personal data):

```bash
ph recordings export <session-id> ~/Downloads/session-<id>.jsonl
```

It refuses an existing file and any folder inside a git repository, creates the file readable by the user only, and prints `{file, blocks, lines, format}`. Under the hood: `GET .../session_recordings/<id>/snapshots/` lists the blocks (`sources: [{source: "blob_v2", blob_key, start_timestamp, end_timestamp}]`), then `?source=blob_v2&start_blob_key=A&end_blob_key=B` returns them as JSON lines, at most 21 blocks per call for a personal key. Each line is `[window_id, rrweb_event]`: full DOM snapshots, incremental mutations, mouse moves and clicks, scrolls, inputs (masked as the project's replay settings say), console and network plugin events. An rrweb player or a script can replay or search it.

## Persons and cohorts

```bash
ph persons find <distinct-id|email>             # {uuid, distinct_ids (first 5), distinct_id_count, is_identified, created_at, last_seen_at}
ph persons events <distinct-id|email> --days 7 --table   # timestamp, event, url, session_id
ph cohorts list --table                          # id, name, count, is_static, created_at
ph cohorts create-static "Beta testers" user-1 user-2 user-3     # write
ph cohorts create-static "Beta testers" @ids.txt                 # one distinct id per line
```

`create-static` resolves the distinct ids to persons first and says how many it found; unknown ids are left out. Never list a cohort's persons into the chat; use counts.

## Annotations

```bash
ph annotations list --table
ph annotations create "Release 1.14.0: new checkout"             # now; --date 2026-01-15T10:00:00Z for another time
ph annotations delete <id>
```

Annotate each release that changes tracking or the product, so a step in a chart has a visible cause.

## Surveys and error tracking

```bash
ph surveys list --table                          # id, name, type, start_date, end_date, archived
ph surveys get <id>                              # questions, linked flag, url
ph surveys results <id> --days 30                # response stats, per question
ph errors list --status active --table           # id, status, name, description, first_seen, url
```

Occurrence counts and trends per issue come from HogQL over `$exception` events (above).

## Raw calls

```bash
ph GET '/api/projects/{project}/feature_flags/?limit=500' | jq ...
ph PATCH '/api/projects/{project}/feature_flags/<id>/' @flag.json      # dry run; --yes sends
```

Anything but `GET` and a `POST` to `/query/` is a write and needs `--yes`. Paths start with one `/`. The API reference is at posthog.com/docs/api; the live schema at `<host>/api/schema/`.
