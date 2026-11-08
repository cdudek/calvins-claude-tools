---
name: tracking-audit
description: Read-only check of a repo or diff against the tracking conventions - SDK calls outside the central library, events not passed as registry keys, bad names, missing registry fields, private data, events before consent, GA4 name and limit breaches, renames that double-count, dead or unregistered events, missing guard rails and owners. Optionally compares the registry with events arriving in PostHog. Ranked findings with file:line and the fix. Use for "audit tracking", "check our events", "tracking review". Skip to add events (tracking-apply) or build or repair the library (tracking-library-run).
allowed-tools: "Read Grep Glob Bash(git *) Bash(gh *) Bash(bash */posthog-manage/scripts/*) Bash(jq *)"
user_invocable: true
metadata:
  version: 1.1.0
---

# Tracking audit

A read-only check of tracking against `../tracking-library-run/references/conventions.md` and the library shape in `../tracking-library-run/references/library.md`. It changes nothing. Fixes go through `cct:tracking-apply` (events) or `cct:tracking-library-run` (the library itself).

## Scope

- **Repo** (default): the whole tree, generated, vendored and lock files excluded.
- **Diff**: a branch (`git diff origin/<default>...HEAD`) or a PR (`gh pr diff <n>`). Check the changed lines, and read the registry and the files they call into.
- **Live** (optional): add the PostHog comparison in step 4 when `cct:posthog-manage` credentials are set.

Find the library first: the registry (`defineEvents`, `events = {`, a `registry.*` under a `tracking` folder or package) and the tracking doc (`docs/tracking.md`). No library at all is itself the first finding (High: "no central tracking library"), and the audit continues on the raw calls.

## 1. Inventory

```bash
git grep -nE "posthog\.(capture|identify|group|alias|reset|init)|\bgtag\(|dataLayer\.push|sendGAEvent|analytics\.(track|page)|mixpanel\.track|amplitude\.track|logEvent\(" -- ':!*.lock' ':!*.min.js'
git grep -nE "(from|import\(|require\() *['\"](posthog-js|posthog-node|posthog-react-native|@posthog/|react-ga4|@next/third-parties/google|firebase/analytics)" -- ':!*.lock'
git grep -nE "\btrack(Server)?\(" -- ':!*.lock'
```

Build three lists: registry entries (name, fields, status), helper calls (file:line, event, properties), and direct SDK calls outside the library folder.

## 2. Checks

Run every check. Each one names its source rule.

| # | Check | How |
| --- | --- | --- |
| 1 | Call sites outside the library | direct SDK imports or calls outside the library folder |
| 2 | Events not passed as registry keys | `track("...")`, `` track(`...`) ``, `track(name)`, `trackServer(ctx, "...")`; a helper that accepts a definition object instead of a key (forgeable) |
| 3 | Names breaking the convention | registry names and literal names against `^[a-z][a-z0-9]*(_[a-z0-9]+)*$`, 40 characters, present tense (no `-ed` verbs), `object_verb`, no values or versions, no reserved prefix or name |
| 4 | Property names | `snake_case`, `is_`/`has_` booleans, units on durations and amounts, canonical names from the conventions |
| 5 | Missing registry fields | each entry has name, category, capture, owner, status, question, `firedWhen`, since; deprecated ones have `replacedBy`, `deprecatedOn`, `sunset` (30 or more days later) and `toLegacy` |
| 6 | Private data | property kinds or values that can carry email, names, phone, free text (`message`, `query`, `body`, `text`, `comment`, `email`, `name`), tokens, or URLs with query strings; the privacy guard present, called on event, identity and context values, and rejecting nested objects; PostHog's IP setting recorded |
| 7 | Events before consent | sends not gated by the library's consent check; an SDK `init` or tag script outside the adapter's `start` (strict mode) or a looser vendor mode not recorded in the tracking doc; held events kept after `reset`; events fired at module load or on the landing route before the banner |
| 8 | Marketing names and limits | two events mapping to one marketing name; a name, parameter or user property breaking GA4's rules (`conventions.md`, Hard limits); over 25 parameters as sent; more custom parameters than dimensions; a `purchase` meant for revenue without `transaction_id`, numeric `value`, `currency` and `items`; a renamed event whose old name still reaches marketing (double-counted conversions) |
| 9 | Dead events | registry entries (not `removed`) with no call site |
| 10 | Unregistered calls | helper or SDK calls whose name is not in the registry |
| 11 | Deprecated still fired | call sites using a `deprecated` entry directly; a sunset in the past with the entry still `deprecated` |
| 12 | Duplicates | the same event fired from client and server, or from two places for one action; two SDK inits; automatic pageview left on next to the library's `page_view` |
| 13 | Per-variant events | names that differ only by a value (`share_twitter`, `share_linkedin`), detail-page events instead of `page_view` + `page_type` |
| 14 | Guard rails | in CI: the lint rule with its fixture of banned patterns, the tracker, type and registry tests, and the plan generator with `--check`; the generated plan matches the registry |
| 15 | Identity | identify outside the auth provider, no `reset` on logout, no reset on an account switch, identity properties passed on event calls, `alias` at ordinary login, emails or names as IDs |
| 16 | Owners | no registry owner named in the tracking doc; the registry file without a code owner |
| 17 | Server events | `trackServer` without stored consent, without an idempotency key, or sending to GA4 without a stored `client_id` |

## 3. Severity

- **Critical:** private data in a property value; events sent before consent.
- **High:** SDK calls outside the library; no library; no registry owner; a deprecated event past its sunset still fired; a marketing-name collision or limit breach (data silently lost); duplicate firing or double-counting of a KPI or conversion event; server events without idempotency.
- **Medium:** naming and property-naming breaks; missing registry fields; events not passed as registry keys; unregistered calls; per-variant events; missing guard rails; identity gaps.
- **Low:** dead registry entries; a stale generated plan; tracking doc gaps.

## 4. Live comparison (optional)

With `cct:posthog-manage` (credentials from the environment, never printed), against the production project. `ph query` prints one JSON object per row. Scope to the audited app when the registry is shared (`AND properties.app = '<app>'`), and look back 90 days so rare events can be judged:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/posthog-manage/scripts/ph query "SELECT event, countIf(timestamp > now() - INTERVAL 30 DAY) AS n30, count() AS n90, max(timestamp) AS last_seen FROM events WHERE timestamp > now() - INTERVAL 90 DAY GROUP BY event ORDER BY n90 DESC LIMIT 10000" | jq -r '[.event, .n30, .n90, .last_seen] | @tsv'
```

If `ph` prints `posthog-manage: partial`, the list is cut: narrow it (a single app, `event IN (...)` with the registry's names) before comparing. Ignore PostHog's own `$` events except `$pageview` (which should be zero when the library owns `page_view`). Then:

- **Registry `live`, nothing in 30 days:** if it fired in the 90 days at a rate that predicts five or more in 30 (`n90 / 3 >= 5`), High: a broken or removed call site, or a release that dropped it. Rarer than that, or an app not yet deployed: Low, "too rare to judge; check the trigger".
- **Registry `proposed`:** expected; no finding. **`proposed` but arriving:** Low; move it to `live`.
- **Arriving, not in the registry:** a legacy event (add it as `deprecated` with a replacement) or a stray direct call. Medium; High if it fires more than the registered event it duplicates.
- **`deprecated` past sunset, still arriving:** High.

The marketing tool has no equivalent API here; check its event list by hand in the property's admin if the audit needs it.

## 5. Report

Findings ranked by severity, then by count. One block per finding:

```markdown
### High: direct PostHog call outside the tracking library (3 places)

- src/app/checkout/page.tsx:42 `posthog.capture("checkout_started", { email })`
- src/components/share.tsx:17 `posthog.capture("share_twitter")`
- src/lib/billing/webhook.ts:88 `client.capture({ event: "purchase" })`

Rule: conventions, "The whole idea" point 1; library lint rule.
Fix: `track(events.checkoutStart, {...})` (drop `email`, Critical below), `track(events.share, { surface: "editor", share_channel: "twitter" })`, `trackServer(ctx, events.purchase, {...})`. Add the lint rule so it cannot return.
```

End with a summary line per severity, the live comparison counts if run, and the next step (`cct:tracking-apply` for event fixes, `cct:tracking-library-run` when the library or guard rails are missing).
