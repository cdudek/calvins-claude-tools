---
status: current
last_updated: 2026-08-05
audience: engineers instrumenting any OMR frontend app
covers: "@ramp106/omrjs-tracking (core engine) + per-team packages (e.g. @ramp106/omrjs-tracking-reviews)"
---

# Using the tracking wrapper

How to actually fire events in code. The rules for *what* to name things and *which*
category they belong to live in `tracking-conventions.md` — this file is the *how*.

**Golden rule: no app talks to GA4 (`window.dataLayer` / GTM) or PostHog directly.**
Every event goes through the wrapper. The wrapper adds standard context, routes by
category, gates on consent, and manages identity. If you find yourself writing
`dataLayer.push(...)`, `gtag(...)`, `posthog.capture(...)`, or `window.dataLayer` in an
app, that is the bug — route it through `track()` instead.

## The two-layer architecture

```
@ramp106/omrjs-tracking            ← CORE ENGINE (registry-agnostic)
  createTracker, initTracking, track routing, identify/resetIdentity,
  the GA4 + PostHog sinks, CORE_EVENTS (cross-team canonical events),
  the primitives (Category, Surface, EventState, defineEvents, defineTeamEvents),
  validateEventName + the naming/limit guardrails.
        │  imported by
        ▼
@ramp106/omrjs-tracking-<team>     ← TEAM PACKAGE (one per team)
  createTracker(defineEvents({ ...CORE_EVENTS, ...TEAM_EVENTS }))
  e.g. @ramp106/omrjs-tracking-reviews (reviews-frontend + eventmanager)
        │  imported by
        ▼
the app                            ← imports track / identify FROM ITS TEAM PACKAGE
```

Core knows about **no team's events**. Each team binds its own registry to the engine and
ships the result as a domain package. Apps import `track` / `identify` from **their team
package**, never from `@ramp106/omrjs-tracking` directly — the same rule as consuming
`@ramp106/omrjs-reviews-ui` rather than `@ramp106/omrjs-core-ui`.

New team (Festival, Platform, …)? Create a sibling package the same way. Do **not** extend
another team's package.

## Everyday use (in an app)

### 1. Initialise once, per app

Call `initTracking` once, after you have created the PostHog client (core-ui's
`createPosthogClient`):

```ts
import { initTracking } from '@ramp106/omrjs-tracking-reviews'

initTracking({ app: 'reviews', posthog: ph, debug: import.meta.env.DEV })
```

- `app` is core-ui's `AppCode` — injected on every event, both sinks. You never pass it on
  a `track()` call.
- Events fired *before* `initTracking` are queued and flushed on init, so you don't have to
  race the bootstrap.
- On init the wrapper also, on its own: subscribes to the CMP and fires `consent_update`,
  and fires `session_reengage` when the persisted last-seen timestamp is ≥ 1 day old. Apps
  never write their own consent check or re-engagement timer.
- SSR-safe: `track` / `initTracking` no-op when `window` is undefined.

### 2. Track events

```ts
import { track } from '@ramp106/omrjs-tracking-reviews'

track('review_submit', { surface: 'editor', tool_id, rating: 4 })
track('page_view', { page_type: 'tool', tool_id })
track('cta_click', { category: 'meaningful_action', surface: 'cta', cta_id })
```

- The event **name is a fixed string literal**, checked against the merged registry —
  a name that isn't in the registry (or is `state: 'removed'`) is a **compile error**.
  Never `track(someVariable)`.
- **Props are fully typed** per event. TypeScript tells you which props an event needs.
- `surface` is required on every event **except** `page_view` (which takes `page_type` +
  entity IDs instead) and the wrapper-fired system events. This is enforced by a
  type-level registry test.
- You never pass `app`, `experiment_variant`, or identity fields — the wrapper adds them.
  On PostHog captures it sets `experiment_variant` from active `exp`-type feature flags.

### 3. Identify at login, reset at logout

```ts
import { identify, resetIdentity } from '@ramp106/omrjs-tracking-reviews'

identify({ user_id, account_type, company_id, company_name, company_slug, plan_tier })
resetIdentity() // on logout
```

One `identify` call runs, in order: `posthog.identify` → `posthog.group('account', …)` →
`posthog.alias` (first-time-only, consent-gated) → one `identity_update` dataLayer push (a
technical carrier for GTM's GA4 User-ID / user-property mappings — **not** an analytics
event). After that, **both tools carry identity on every authenticated event
automatically** — you never repeat `user_id` / `account_type` / `plan_tier` on a `track()`
call.

The identity contract (`IdentifyPayload`):

| Field | Notes |
|---|---|
| `user_id` | Opaque UUID. Becomes GA4's User-ID. **Never a raw email or person name.** |
| `account_type` | Role: `vendor`, `reviewer`, `agency`, … (catalogue-owned; teams narrow the type). |
| `company_id` | B2B account id. |
| `company_name` | Firmographic, **PostHog only** — too long for GA4's 36-char cap. |
| `company_slug` | GA4-safe readable company id — rides the GA4 leg where `company_name` can't. |
| `plan_tier` | The reviews-api plan **name** (server-resolved, immutable natural key). Joined in the warehouse by `account_type`. Omit where the product has no plan. |
| `set_once` | Write-once person properties → PostHog `$set_once` (e.g. `signup_date`, `initial_referrer`). |

Repeat identical payloads dedup; a changed payload re-fires. `posthog.identify`/`group`
errors deliberately **propagate** so the login flow can retry — catch them at the call
site if an uncaught throw would break login.

Login itself is **not** an event (identity rides every event after it). A **failed** login
*is* — it's the `login_fail` friction event, no identity to attach yet.

## Adding a new event

Events are defined **in code, in the team registry** — one typed source of truth, not a
wiki or a slide. To add one, edit your team package (e.g.
`packages/tracking-reviews/src/registry.ts`), never the app:

```ts
import { defineTeamEvents } from '@ramp106/omrjs-tracking'
import type { SurfaceProps } from '@ramp106/omrjs-tracking'

export interface ReviewSubmitProps extends SurfaceProps {
  tool_id: string
  rating?: number
  is_first_review?: boolean
}

export const REVIEWS_EVENTS = defineTeamEvents({
  review_submit: {
    category: 'meaningful_action', // decides routing — set once, here
    state: 'proposed',             // new events always enter as 'proposed'
    props: {} as ReviewSubmitProps,
  },
  // …
})
```

Steps:

1. **Add the row** via `defineTeamEvents({ ... })`: canonical `object_verb` name, `category`
   (this alone decides GA4/PostHog routing), `state: 'proposed'`, typed `props` extending
   `SurfaceProps` (or a page-view/system shape). `defineTeamEvents` **rejects at compile
   time *and* runtime** any name that collides with a `CORE_EVENTS` key — cross-team
   canonical events live in core, not in a team package.
2. **New page type?** Declare it in the team's `pageTypes.ts` by augmenting core's
   `PageTypeExtensions` interface (don't add a new event — detail pages are
   `page_view` + `page_type` + entity id).
3. **New typed prop on a core event** (e.g. `lead_generate`)? Augment the extension
   interface (`LeadGenerateExtensions`) via `declare module '@ramp106/omrjs-tracking'` —
   core stays free of team vocabulary.
4. **Catalogue-sync rule:** any registry change that diverges from the event catalogue
   updates the catalogue in the same PR. Registry, catalogue, and spec must always agree.
5. First verified production fire flips `state` to `live`.

## Building a new team package

For a team that doesn't have one yet:

```ts
// packages/omrjs-tracking-<team>/src/index.ts
import { CORE_EVENTS, createTracker, defineEvents } from '@ramp106/omrjs-tracking'
import type { TrackableEventNames } from '@ramp106/omrjs-tracking'
import './pageTypes'
import { TEAM_EVENTS } from './registry' // defineTeamEvents({ ... })

export const REGISTRY = defineEvents({ ...CORE_EVENTS, ...TEAM_EVENTS })
export type TrackingEventName = TrackableEventNames<typeof REGISTRY>

export const { track, identify, resetIdentity, initTracking } = createTracker(REGISTRY)
```

`createTracker(registry)` returns one tracker `{ initTracking, track, identify,
resetIdentity }` bound to that registry. Engine state (config, the pre-init queue, identity
dedup, the consent listener) is a module-level singleton in core — one tracker per app.
A team may re-export a narrower `identify` (Reviews narrows the open `account_type` to its
catalogue roles).

## Renames & migrations (never break running dashboards)

You **never** jump an event from `live` straight to a new name — that silently breaks saved
PostHog insights, running experiments, and dbt models. Renames go through a dual-fire /
deprecation window (≥ 30 days). The registry gives you the machinery:

| Field | What it does |
|---|---|
| `state: 'deprecated'` | Still fires; `console.warn`s in `debug` mode (with `sunsetDate` if set). |
| `state: 'removed'` | Drops out of the name union — every call site becomes a compile error. |
| `sunsetDate` | The date after which a deprecated event may go to `removed`. |
| `legacyAlias` | Dual-fires the **old** GTM name to the dataLayer alongside the canonical event, until sunset. A `string`, or a `(props) => string \| undefined` for per-value legacy names. |
| `legacyPayload` | `(props) => Record` — maps canonical props into the legacy GTM field shape when the legacy event expects different field names. |
| `legacyOnlyProps` | Props that feed **only** the legacy fire; stripped from the canonical payload on both sinks. **Requires** a `legacyAlias` *and* a `legacyPayload` (`defineEvents` throws otherwise — else they'd be stripped and never rebuilt). |
| `posthogOnlyProps` | Props stripped from the GA4 push but kept on the PostHog capture (e.g. a `target_url`). |
| `dataLayerName` | Carries the canonical GA4 push under a **different** dataLayer name *permanently* (GTM maps it back). Used only when the canonical name would collide with another container's native collection — `page_view` rides as `page_view_v2`, `search` as `search_perform`. This is a proven-non-colliding carrier, **not** a version suffix in your event name — never invent `*_v2` names. |

Example (a renamed event with a reshaped legacy payload):

```ts
review_respond: {
  category: 'meaningful_action',
  state: 'proposed',
  legacyAlias: 'review_reply_publish', // old GTM name, dual-fired until sunset
  props: {} as ReviewResponseProps,
},
```

Caveat: if a *functional* `legacyAlias` resolves to `undefined` for a call, that call's
`legacyOnlyProps` are stripped but never rebuilt — `debug` mode `console.warn`s; no
build-time check catches it (it's per-call).

## What the wrapper enforces for you

| Layer | When | What |
|---|---|---|
| **Build-time (hard CI fail)** | every registry | `validateEventName`: lowercase `snake_case`, `[a-z0-9_]`, ≤ 40 chars, no reserved prefix (`ga_`/`google_`/`firebase_`/`$`), not a GA4 reserved name. Core asserts over `CORE_EVENTS`; each team asserts over its own registry. |
| **Type-level** | compile | props typed per event; `surface` required except on `page_view` / system events; `state: 'removed'` names are un-callable; `set_once` bucket typed. |
| **Dev-mode runtime** (`debug: true`, never in prod) | each `track()` | `devValidate` `console.warn`s (never throws) on non-`snake_case` keys, likely-PII keys / email-shaped values, and — for GA4-routed events — GA4's 25-prop / 100-char caps. |
| **Review responsibility** | PR | `object_verb` order and present-tense verbs — a heuristic would misfire on names like `page_view`, so a human checks these. |

## Routing recap

Routing follows the registry `category`, mechanically:

| Category | GA4 | PostHog |
|---|---|---|
| `lifecycle`, `acquisition`, `meaningful_action` | ✓ | ✓ |
| `engagement`, `retention`, `friction` | ✗ | ✓ |

`cta_click` is the single per-call exception: its category (`meaningful_action` vs
`engagement`) comes from the props at the call site (`category: 'per_call'` in the
registry). Everything else has a fixed category in the registry.

## Gotchas

- **Import from your team package**, not from `@ramp106/omrjs-tracking`. Core has no
  `track` you'd want directly — team packages bind the registry.
- **`page_view` is not the tools' automatic pageview.** GA4 auto-pageview is disabled; you
  fire `page_view` yourself on every route change (incl. SPA navigations), with `page_type`
  + the IDs that page needs. Omit IDs that don't apply — don't set them to `null`.
- **Don't repeat identity on events.** `user_id`, `account_type`, `company_*`, `plan_tier`
  are set once at `identify` and auto-carried. Passing them per-event is noise.
- **`session_reengage` and `consent_update` are wrapper-fired.** Don't fire them from app
  code.
- **localStorage failures are silent** for `session_reengage` (private mode / quota) — the
  event is simply skipped, never throws.
