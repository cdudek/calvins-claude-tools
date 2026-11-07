---
name: tracking-audit
description: Read-only check of a repo or a diff against the tracking conventions - call sites outside the central library, string-literal events, bad names, missing registry fields, private data in properties, events before consent, marketing-name collisions and limits, dead registry events, unregistered calls, deprecated events still fired. Optionally compares the registry with events arriving in PostHog. Outputs ranked findings with file:line and the fix. Use for "audit tracking", "check our events", "tracking review". Skip to add events (tracking-apply) or build the library (tracking-setup).
allowed-tools: "Read Grep Glob Bash(git *) Bash(gh *) Bash(bash */posthog-manage/scripts/*) Bash(jq *)"
user_invocable: true
metadata:
  version: 1.0.0
---

# Tracking audit

A read-only check of tracking against `../tracking-setup/references/conventions.md` and the library shape in `../tracking-setup/references/library.md`. It changes nothing. Fixes go through `cct:tracking-apply` (events) or `cct:tracking-setup` (the library itself).

## Scope

- **Repo** (default): the whole tree, generated, vendored and lock files excluded.
- **Diff**: a branch (`git diff origin/<default>...HEAD`) or a PR (`gh pr diff <n>`). Check the changed lines, and read the registry and the files they call into.
- **Live** (optional): add the PostHog comparison in step 4 when `cct:posthog-manage` credentials are set.

Find the library first: the registry (`defineEvents`, `events = {`, a `registry.*` under a `tracking` folder or package) and the tracking doc (`docs/tracking.md`). No library at all is itself the first finding (High: "no central tracking library"), and the audit continues on the raw calls.

## 1. Inventory

```bash
git grep -nE "posthog\.(capture|identify|group|alias)|\bgtag\(|dataLayer\.push|sendGAEvent|analytics\.(track|page)|mixpanel\.track|amplitude\.track|logEvent\(" -- ':!*.lock' ':!*.min.js'
git grep -nE "from ['\"](posthog-js|posthog-node|react-ga4|@next/third-parties/google)" -- ':!*.lock'
git grep -nE "\btrack(Server)?\(" -- ':!*.lock'
```

Build three lists: registry entries (name, fields, status), helper calls (file:line, event, properties), and direct SDK calls outside the library folder.

## 2. Checks

Run every check. Each one names its source rule.

| # | Check | How |
| --- | --- | --- |
| 1 | Call sites outside the library | direct SDK imports or calls outside the library folder |
| 2 | String literals or variables as the event | `track("...")`, `` track(`...`) ``, `track(name)` |
| 3 | Names breaking the convention | registry names and literal names against `^[a-z][a-z0-9]*(_[a-z0-9]+)*$`, 40 characters, present tense (no `-ed` verbs), `object_verb`, no values or versions, no reserved prefix or name |
| 4 | Property names | `snake_case`, `is_`/`has_` booleans, units on durations and amounts, canonical names from the conventions |
| 5 | Missing registry fields | each entry has name, category, capture, owner, status, question, since; deprecated ones have `replacedBy` and `sunset` |
| 6 | Private data | property kinds or values that can carry email, names, phone, free text (`message`, `query`, `body`, `text`, `comment`, `email`, `name`), tokens, or URLs with query strings; the privacy guard present and called |
| 7 | Events before consent | sends not gated by the library's consent check; SDK inits without privacy mode (PostHog persistence not memory, GA4 consent defaults missing); events fired at module load or on the landing route before the banner |
| 8 | Marketing names | two events mapping to one marketing name, names over 40 characters, more than 25 properties on a marketing event, a reserved GA4 name |
| 9 | Dead events | registry entries (not `removed`) with no call site |
| 10 | Unregistered calls | helper or SDK calls whose name is not in the registry |
| 11 | Deprecated still fired | call sites using a `deprecated` entry directly; a sunset in the past with the entry still `deprecated` |
| 12 | Duplicates | the same event fired from client and server, or from two places for one action; two SDK inits; automatic pageview left on next to the library's `page_view` |
| 13 | Per-variant events | names that differ only by a value (`share_twitter`, `share_linkedin`), detail-page events instead of `page_view` + `page_type` |
| 14 | Guard rails | the lint rule, the registry test, the consent test and the plan generator exist and run in CI; the generated plan matches the registry |
| 15 | Identity | identify outside the auth provider, no `reset` on logout, identity properties passed on event calls |

## 3. Severity

- **Critical:** private data in a property value; events sent before consent.
- **High:** SDK calls outside the library; no library; a deprecated event past its sunset still fired; a marketing-name collision or limit breach (data silently lost); duplicate firing of a KPI event.
- **Medium:** naming and property-naming breaks; missing registry fields; string literals or variables at call sites; unregistered calls; per-variant events; missing guard rails.
- **Low:** dead registry entries; a stale generated plan; tracking doc gaps.

## 4. Live comparison (optional)

With `cct:posthog-manage` (credentials from the environment, never printed), pull what actually arrived in the last 30 days:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/posthog-manage/scripts/ph query "SELECT event, count() AS n, max(timestamp) AS last_seen FROM events WHERE timestamp > now() - INTERVAL 30 DAY GROUP BY event ORDER BY n DESC LIMIT 1000" | jq -c '.results[]'
```

Compare with the registry, ignoring PostHog's own `$` events except `$pageview` (which should be zero if the library owns `page_view`):

- **Registry only, status `live`:** declared live but not arriving. High: broken or removed call site.
- **Registry only, status `proposed`:** expected; no finding.
- **Live only:** arriving but not in the registry. A legacy event (add it as `deprecated` with a replacement) or a stray direct call. Medium; High if it fires more than the registered event it duplicates.
- **`deprecated` past sunset, still arriving:** High.
- **`proposed` but arriving:** Low; move it to `live`.

The marketing tool has no equivalent API here; check its event list by hand in the property's admin if the audit needs it.

## 5. Report

Findings ranked by severity, then by count. One block per finding:

```markdown
### High: direct PostHog call outside the tracking library (3 places)

- src/app/checkout/page.tsx:42 `posthog.capture("checkout_started", { email })`
- src/components/share.tsx:17 `posthog.capture("share_twitter")`
- src/lib/billing/webhook.ts:88 `client.capture({ event: "purchase" })`

Rule: conventions, "The whole idea" point 1; library lint rule.
Fix: `track(events.checkoutStart, {...})` (drop `email`, Critical below), `track(events.share, { share_channel: "twitter" })`, `trackServer(events.purchase, {...})`. Add the lint rule so it cannot return.
```

End with a summary line per severity, the live comparison counts if run, and the next step (`cct:tracking-apply` for event fixes, `cct:tracking-setup` when the library or guard rails are missing).
