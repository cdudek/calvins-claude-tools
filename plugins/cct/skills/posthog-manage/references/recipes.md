# PostHog recipes

All calls go through `bash <skill>/scripts/ph`. `{project}` becomes `POSTHOG_PROJECT_ID`. Responses are JSON; a HogQL result has `.columns` and `.results` (rows as arrays).

## HogQL

```bash
bash <skill>/scripts/ph query "SELECT ..." | jq -c '.results[]'
```

HogQL is PostHog's SQL over `events` (and `persons`, `sessions`, `groups`). Event properties are `properties.<name>`, person properties `person.properties.<name>` (avoid in output: they can hold personal data). Times are UTC unless the project timezone is applied with `toTimeZone`.

Event volume, last 7 days:

```sql
SELECT event, count() AS n, uniq(distinct_id) AS users, max(timestamp) AS last_seen
FROM events
WHERE timestamp > now() - INTERVAL 7 DAY
GROUP BY event ORDER BY n DESC LIMIT 200
```

A daily trend:

```sql
SELECT toDate(timestamp) AS day, count() AS n
FROM events
WHERE event = 'checkout_start' AND timestamp > now() - INTERVAL 30 DAY
GROUP BY day ORDER BY day
```

A conversion rate between two events over the same window (a quick read; it does not check order):

```sql
SELECT uniqIf(person_id, event = 'checkout_start') AS started,
       uniqIf(person_id, event = 'purchase') AS bought,
       round(bought / nullIf(started, 0), 3) AS rate
FROM events
WHERE event IN ('checkout_start', 'purchase') AND timestamp > now() - INTERVAL 30 DAY
```

For an ordered funnel with a conversion window or breakdowns, create or read a funnel insight instead (see Insights); it handles order and windows exactly as the UI does.

A breakdown by a property:

```sql
SELECT properties.payment_method AS method, count() AS n
FROM events
WHERE event = 'purchase' AND timestamp > now() - INTERVAL 30 DAY
GROUP BY method ORDER BY n DESC
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

A name missing from the result did not arrive. Then check the properties of one event arrive and are filled:

```sql
SELECT count() AS n,
       countIf(properties.order_value_band IS NULL) AS missing_band,
       countIf(properties.payment_method IS NULL) AS missing_method,
       countIf(properties.surface IS NULL) AS missing_surface
FROM events
WHERE event = 'purchase' AND timestamp > now() - INTERVAL 7 DAY
```

Double firing shows as the same user sending the event twice in one second (approximate, good enough to spot a duplicate call site):

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

To test a fresh change: the user opens the app with PostHog's debug mode (`?__posthog_debug=true` or `posthog.debug()`), clicks through, and the events show in the activity view within seconds; the query above with `INTERVAL 10 MINUTE` confirms them.

## Event and property definitions

```bash
bash <skill>/scripts/ph GET "/api/projects/{project}/event_definitions/?search=checkout&limit=100" \
  | jq -c '.results[] | {id, name, last_seen_at, verified, tags, description}'
bash <skill>/scripts/ph GET "/api/projects/{project}/property_definitions/?type=event&event_names=%5B%22purchase%22%5D&filter_by_event_names=true&limit=100" \
  | jq -c '.results[] | {name, property_type}'
```

Sync the registry's metadata to a definition (asks first; descriptions, tags and the verified flag can need a paid plan):

```bash
bash <skill>/scripts/ph PATCH "/api/projects/{project}/event_definitions/ID/" '{"description":"How many checkouts become paid orders. Owner: checkout. Since 1.14.0.","tags":["meaningful_action"],"verified":true}'
```

## Insights and dashboards

```bash
bash <skill>/scripts/ph GET "/api/projects/{project}/insights/?search=checkout&limit=50" | jq -c '.results[] | {short_id, name, last_modified_at}'
bash <skill>/scripts/ph GET "/api/projects/{project}/dashboards/?limit=100" | jq -c '.results[] | {id, name}'
```

Insights that use an event (to repoint after a rename):

```bash
bash <skill>/scripts/ph GET "/api/projects/{project}/insights/?limit=500" \
  | jq -r --arg e "checkout_started" '.results[] | select(tostring | contains("\"" + $e + "\"")) | "\(.short_id)\t\(.name)"'
```

Page with `.next` when the result has one.

## Feature flags

```bash
bash <skill>/scripts/ph GET "/api/projects/{project}/feature_flags/?limit=100" | jq -c '.results[] | {id, key, active, rollout: .filters.groups}'
bash <skill>/scripts/ph GET "/api/projects/{project}/feature_flags/ID/" | jq '{key, active, filters}'
```

Writes (ask first, state who will see the change):

```bash
bash <skill>/scripts/ph POST "/api/projects/{project}/feature_flags/" '{"key":"new-checkout","name":"New checkout","active":true,"filters":{"groups":[{"properties":[],"rollout_percentage":10}]}}'
bash <skill>/scripts/ph PATCH "/api/projects/{project}/feature_flags/ID/" '{"active":false}'
```

A flag change is live for real users at once. Read the flag first and show the before and after.

## Annotations

```bash
bash <skill>/scripts/ph GET "/api/projects/{project}/annotations/?limit=50" | jq -c '.results[] | {id, content, date_marker}'
bash <skill>/scripts/ph POST "/api/projects/{project}/annotations/" '{"content":"Release 1.14.0: new checkout","date_marker":"2026-01-15T10:00:00Z","scope":"project"}'
```

Annotate each release that changes tracking, so a step in a chart has a visible cause.

## Cohorts

```bash
bash <skill>/scripts/ph GET "/api/projects/{project}/cohorts/?limit=100" | jq -c '.results[] | {id, name, count, is_static}'
bash <skill>/scripts/ph GET "/api/projects/{project}/cohorts/ID/" | jq '{name, filters}'
```

Never list a cohort's persons into the chat; use counts.
