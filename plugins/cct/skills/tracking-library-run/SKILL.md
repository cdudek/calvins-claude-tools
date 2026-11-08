---
name: tracking-library-run
description: Builds, repairs or migrates a project's central analytics tracking library - typed event registry, one track helper, consent-gated adapters, privacy guard, lint rule, tests and a generated tracking plan for PMs - for web, mobile or server-only apps, and moves old analytics calls onto it with a rename map. Use for "set up tracking", "tracking library", "event registry", "centralise our analytics", "fix our tracking setup", "migrate our events". Skip to add events to a working library (tracking-apply) or for a read-only check (tracking-audit).
allowed-tools: "Read Grep Glob Edit Write AskUserQuestion Bash(git *) Bash(gh *) Bash(pnpm *) Bash(npm *) Bash(npx *) Bash(yarn *) Bash(bun *) Bash(uv *) Bash(python3 *)"
user_invocable: true
metadata:
  version: 1.1.0
---

# Tracking setup

Events are never defined at the call site. A project gets one central tracking library, like an i18n catalogue: a typed registry of every event, one helper that call sites use, and the only code allowed to talk to an analytics tool. This skill builds that library, writes down the decisions the conventions leave open, and moves the existing calls onto it. It also repairs a library that `tracking-audit` found broken: run the steps whose check fails.

Read both references before the first step:

- `references/conventions.md`: naming, categories and routing, properties, identity, consent and privacy, lifecycle, limits, order of work. The rules.
- `references/library.md`: the registry, tracker, privacy guard, adapters, server half, tests, lint rule and plan generator, as TypeScript that compiles and passes its tests. The shape.

Run it once per app repo, or once per shared-packages repo when several apps share events. After that, every feature uses `cct:tracking-apply`, and `cct:tracking-audit` checks the result. Each step ends with its check; do not start the next step until it passes.

## 1. Find what exists

```bash
git grep -nE "posthog\.(capture|identify|group|alias|reset)|\bgtag\(|dataLayer\.push|\btrack(Event|Server)?\(|analytics\.(track|page|identify)|mixpanel\.|amplitude\.|sendGAEvent|usePostHog|logEvent\(|logScreenView|Analytics\.logEvent" -- ':!*.lock' ':!*.min.js'
git grep -nE "(posthog-js|posthog-node|posthog-react-native|posthog-ios|posthog-android|react-ga4|@next/third-parties/google|@segment/|mixpanel|@amplitude/|firebase/analytics|FirebaseAnalytics)" -- ':!*.lock'
```

Also read the package manifests, the root layout or app entry for tag scripts and `init` calls, the consent banner, and the auth provider. Write an inventory in the scratchpad: every event name, file:line, properties sent, destination, consent check (yes or no), whether it carries private data, and duplicate inits (two `posthog.init`, a tag manager next to a direct tag).

Check: every analytics SDK in the manifests has its init and its call sites in the inventory.

## 2. Pick the path

| The project has | Path |
| --- | --- |
| a browser app (web, extension, marketing site) | web: `library.md` as written |
| an iOS or Android app | mobile: step 5 |
| no user interface (an API, jobs, webhooks only) | server-only: step 6 |
| several of these | the registry as data shared by all (`library.md`, "Other stacks"), then each path |

Where the library lives follows `library.md`, "Where it lives": inside the app when one deployable fires the events, a shared package when two or more fire the same name. When that package belongs in another repo, ask its owner which repo, run this skill there first, then come back to wire each app.

Check: the path and the library's location are written down for step 3.

## 3. Record the decisions and the owners

Write `docs/tracking.md`. Infer what the code shows; ask the user, in one question round, only for the rest, offering the recommended default from `conventions.md` for each.

```markdown
# Tracking

The rules: <link to or copy of the conventions>. The events: docs/tracking-plan.md (generated).

## Owners
Registry owner: <person or team>. Library owner: <>. Product owner: <>. Conventions owner: <>. Marketing analytics owner: <>.

## Tools and routing
Product analytics: <tool, region, host>. Marketing analytics: <tool or none>. Routing: by category (conventions).
Marketing names: mapped in the library (default) | in the tool's admin UI.
Key events and ad-platform imports: set up by <marketing analytics owner>, for <events>.

## Where the library lives
<path or package>, and why (one app | shared by <apps>).

## Values
app: <list>. surface: <list>. page_type: <list>. account_type: <list>. plan_tier: <list or none>. Group type: <company | workspace | account | none>.

## Identity
identify at <session load, after login, on role/plan/company change in <file>>, reset at logout in <file>.

## Consent
Mechanism: <banner or framework>. Purposes to destinations: <map, with the Google consent types the marketing destination grants>.
Before consent: strict (no SDK before grant) | vendor mode (<which, and why>). Held or dropped: <hold | drop>.

## Server-side events
<which events, and why>. Idempotency: <the outbox table or column>.

## Data handling
Product analytics region: <>. "Discard client IP data": <on | off, why>. Marketing retention: <>. Product retention: <>. Google Signals: <on | off, why>. Erasure: <how a deletion reaches each tool>.

## Drift
Comparison: <population, unit, time zone>. Thresholds: <healthy, look>. Runs: monthly and after each release that changes tracking, by the registry owner.

## Decisions
- YYYY-MM-DD: <decision>, chosen over <alternative>, because <reason>.
```

Never put keys, secret project IDs or personal data in this file. The public product-analytics key (`phc_...`) belongs in the app's environment, not the doc.

Check: **the registry owner is named.** Without one, stop here and say so: nobody would gate new events and the lifecycle would not run (`conventions.md`, "Who owns what"). Add the registry file to `CODEOWNERS` with that owner.

## 4. Scaffold the library (web)

Copy the files in `library.md` "Layout" in this order, changing only the project's values:

1. `define.ts` (the surfaces, account types and plan tiers from step 3) and `registry.ts`, seeded with `page_view`, `consent_update`, `signup` if there is sign-up, `login_fail`, and the canonical form of every inventory event as `proposed`.
2. `privacy.ts`, `tracker.ts`, `adapters/` for the recorded tools plus `memory.ts`, `index.ts`. Move every SDK `init` into its adapter's `start` and delete the others, including the tag snippet in the HTML head.
3. `server.ts` if server events were recorded.
4. Wire once: the auth provider calls `identify` when the session loads, after login and when role, plan or company change; logout calls `reset`; the consent banner calls `consent.set` per destination; one router hook calls `track(events.pageView, ...)` after each navigation.

Keep the public key and host in the app's environment (`NEXT_PUBLIC_POSTHOG_KEY` or the framework's equivalent). Never a personal API key (`phx_...`) in the app.

Check: the project's typecheck passes and `git grep` from step 1 finds SDK calls only inside the library folder.

## 5. Mobile path (iOS, Android)

1. **Registry:** the shared `registry.json` (`library.md`, "Other stacks"), with Swift and Kotlin bindings generated from it in CI: an enum or sealed class per event, its properties typed.
2. **Tracker:** the same operations as `tracker.ts` (`track`, `identify`, `reset`, `consent.set`, the hold-or-drop queue, the privacy checks), with a real and a memory implementation.
3. **Nothing before consent:** set up PostHog only in `start` (`PostHogSDK.shared.setup(config)` on iOS, `PostHogAndroid.setup(context, config)` on Android) with automatic screen capture and autocapture off. Ship Firebase Analytics with collection off (`FIREBASE_ANALYTICS_COLLECTION_ENABLED` = `NO` in `Info.plist`; `firebase_analytics_collection_enabled` = `false` in the manifest) and turn it on in `start` with `setAnalyticsCollectionEnabled(true)`; `stop` turns it off again. Store the consent choice in the app's own storage.
4. **Screens:** a screen is a page. One hook (SwiftUI: a root view modifier on appear; Android: the navigation controller's destination listener) fires `page_view` with `page_type`. Turn off Firebase's automatic screen reporting (`FirebaseAutomaticScreenReportingEnabled` = `NO`; `google_analytics_automatic_screen_reporting_enabled` = `false`); the marketing adapter sends the page view to Firebase as `screen_view` with `screen_name` set to the page type. App streams cap distinct event names at 500 per user: route only the categories that need marketing.
5. **Offline:** the SDKs queue and retry offline themselves; the tracker stamps each event's time when it is tracked, never when it is sent.
6. **Identity:** `identify` on session restore and after login, `reset` at logout, as on the web.

Check: a unit test with the memory tracker shows nothing captured before consent and one `page_view` per screen; a debug build shows the events in PostHog's live events and in Firebase DebugView.

## 6. Server-only path

1. **Registry and helper:** the server half only (`server.ts`, or its Python, Ruby or Go form from `library.md`). No `page_view`, no banner, no client adapters.
2. **Consent:** read from where the user gave it (the account record or the order), passed in the context on every call; for an API client with no person behind it, the project records the legal basis and sends no person-level data.
3. **Identity:** every event needs a distinct ID: the opaque user ID for a user's action. A system actor (a cron job, an integration) uses a fixed ID such as `system:<job>` and sends `$process_person_profile: false`, so it creates no person profile.
4. **Once only:** each event has an idempotency key recorded in the same transaction as the state change (an outbox row); send only when the row is new.
5. **GA4:** only with a stored `client_id` (or `app_instance_id`) from the user's browser or app; without one, the event goes to product analytics only.

Check: a test with memory server adapters sends each event once for two deliveries of the same webhook; `cct:posthog-manage` (`ph query`) shows the event within ten minutes of a staging run.

## 7. Guard rails

1. The lint rule from `library.md`, merged into the project's lint config, and a fixture file outside the library with one of each banned pattern (SDK import, dynamic import, `require`, `gtag`, `dataLayer.push`, `posthog.capture`, a string or a variable as the event) run in CI, asserting one error per pattern.
2. `tracker.test.ts`, `types.test.ts` and `registry.test.ts` from `library.md` in the project's test runner, and the typecheck over the test files (the type tests fail by compiling).
3. `scripts/tracking-plan.ts`, a `tracking:plan` script, and a CI step running it with `--check`.

Check: CI runs all three and is green.

## 8. Migrate the existing calls

Write the rename map into `docs/tracking.md` under `## Migration`, one row per inventory event:

| Old name | New name | Old properties | New properties | Dashboards, insights, models to repoint | Deprecated on | Sunset |
| --- | --- | --- | --- | --- | --- | --- |
| `Signup Completed` | `signup` | `method` | `signup_method` | <list> | YYYY-MM-DD | YYYY-MM-DD |

Then:

1. Add each old name to the registry as `deprecated`, with `replacedBy`, `deprecatedOn`, a `sunset` 30 or more days later and a `toLegacy` mapping. Every old event goes through this window, even one nobody seems to read (`conventions.md`, "Lifecycle"). The library re-sends the old name to product analytics only.
2. Rewrite each call site to `track(events.x, props)`, fixing names, properties and private data on the way. Delete direct SDK calls.
3. The marketing analytics owner moves key events and ad-platform imports to the new names on the day they ship.
4. Events that fired before consent now wait for it; say so in the PR, since counts will drop.
5. Fill the "to repoint" column from the tool when credentials exist: `cct:posthog-manage` lists insights and cohorts using an event.

Large repos: migrate one surface per commit, each commit green. Follow the order of work in `conventions.md`: each step lands in production before the next starts.

Check: no call site uses an old name; the registry test passes.

## 9. Verify

Run, and show the output:

1. The project's typecheck, lint (no restricted-syntax hit outside the library, every fixture pattern caught) and tests.
2. `tracking:plan --check`.
3. Web: run the app with consent unanswered and then denied: the network panel or the E2E network log shows no request to the analytics hosts, and the tag script is not loaded. Grant consent: `page_view` arrives once per navigation, not twice.
4. With credentials, `cct:posthog-manage` shows the events arriving in the product tool; GA4's DebugView shows the marketing ones.
5. `cct:tracking-audit` on the repo: no Critical or High finding left.

## Output

- The library, the lint rule and its fixture, the tests, the plan generator and its CI step.
- `docs/tracking.md` with the owners, the decisions and the migration map; `docs/tracking-plan.md` generated.
- A short report: the path taken, events registered, call sites migrated, decisions still open with the role that owns each.
