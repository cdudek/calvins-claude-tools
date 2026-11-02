---
name: tracking-apply
description: Implement or audit OMR analytics tracking across any team's frontend, per the OMR Event Tracking Conventions (GA4 + PostHog, category-based routing through the typed @ramp106/omrjs-tracking wrapper). Use when the user says "add tracking", "implement tracking", "track this", "instrument", "new tracking event", "how do I fire an event", "use the tracking wrapper", "tracking audit", "audit tracking", "review tracking", "event naming", "GA4 event", "PostHog event", or when a PR/spec adds or changes analytics events.
allowed-tools: "Read Grep Glob Edit Write Bash(gh *) Bash(git *)"
user_invocable: true
metadata:
  version: 1.0.0
  author: Calvin Dudek
---

# Use Tracking

Instrument analytics on any OMR frontend, or audit existing tracking, so every event
follows the OMR Event Tracking Conventions. Two tools on purpose: **GA4** for ad
attribution, **PostHog** for product behaviour. Events route by **category**, decided once
in the typed registry — never by a per-callsite tool choice, and never by calling GA4 or
PostHog directly.

This skill is org-wide. It applies to every team's tracking (reviews, eventmanager,
festival, platform, …), not one product.

## Reference files — read before doing anything

- **`references/tracking-conventions.md`** — the full conventions: the four-point idea,
  naming, the six categories + routing, properties, identity, consent/PII, event lifecycle,
  ownership, anti-patterns, hard limits, worked examples, and end-to-end journeys. The
  authority for *what to name things and where they route*.
- **`references/using-the-wrapper.md`** — how to actually fire events in code with the
  shipped `@ramp106/omrjs-tracking` wrapper: the two-layer package architecture,
  `initTracking` / `track` / `identify`, adding a new event, building a team package,
  renames/migrations (`legacyAlias`, `dataLayerName`, …), and what the wrapper enforces.
  The authority for *how to implement*.

Read `using-the-wrapper.md` for Implement work, `tracking-conventions.md` for Audit work —
in practice both, since implementing correctly means obeying the conventions.

## Source of truth, in order

1. **The typed registry in code** — `@ramp106/omrjs-tracking`'s `CORE_EVENTS` plus each
   team's `defineTeamEvents({ ... })` registry (e.g. `packages/tracking-reviews/src/registry.ts`
   in the omr-js monorepo). This is what actually exists and fires.
2. **The event catalogue** — the canonical list of proposed names/categories/props per
   product. A living proposal; diverging is fine when the alternative follows the rules —
   but then the catalogue is updated in the same change.
3. **The conventions** (`references/tracking-conventions.md`) — the rules everything must
   satisfy. Fixed; changes need sign-off (Calvin).

The hard requirement is **self-consistency**: registry, catalogue, and spec must always
agree on names, categories, and lifecycle states. Divergence without updating the others is
a violation; divergence *with* the update is a normal decision.

## Mode selection

- User wants to instrument something new, wire up an app, or add/fire an event → **Implement mode**.
- User has a PR, spec, diff, or codebase with tracking calls to check → **Audit mode**.
- Ambiguous → ask which. Usually audit first (design/implement follows).

## Hard rules (non-negotiable — enforceable violations, not style)

| Rule | Wrong | Right |
|---|---|---|
| Lowercase `snake_case` | `ReviewSubmit`, `submit-review` | `review_submit` |
| Present tense verb | `review_submitted`, `ai_message_sent` | `review_submit`, `assistant_message_send` |
| Object first (`object_verb`) | `submit_review`, `apply_filter` | `review_submit`, `filter_apply` |
| **One event, never one per variant** | `share_twitter`/`share_linkedin`, `signup_google` | `share` + `share_channel`, `signup` + `signup_method` |
| No values in the name | `reengage_after_30d`, any `*_v2` name | `session_reengage` + property; carrier names live in the registry, not the event name |
| No PII in a property value | raw email, person name, phone, free text | opaque IDs, `email_hash`, derived numbers (`review_length_chars`) |
| A fixed string, never a variable | `track(name)` | `track('review_submit')` |
| No reserved prefixes/names | `ga_*`, `google_*`, `firebase_*`, `$*`; GA4 reserved names `user_engagement`, `session_start`, `first_open`, `first_visit`, `app_remove`, `app_update` | plain names |
| Route through the wrapper only | `dataLayer.push(...)`, `gtag(...)`, `posthog.capture(...)` in an app | `track(...)` from the team package |

Naming is never compromised — not for migration convenience, not for GA4 report continuity.
Renames go through the 30-day dual-fire / deprecation window instead (see the wrapper guide).

## Categories and routing (the one decision that matters)

Category answers "what business question does this serve" and mechanically decides the tool.
Work down the list, stop at the first match:

| Category | Test | Routes to |
|---|---|---|
| `lifecycle` | session / page-frame (`page_view`, `consent_update`) | Both |
| `acquisition` | anonymous becomes known, ad-attributable (`signup`, `lead_generate`) | Both |
| `meaningful_action` | a leadership dashboard reports it **OR** marketing bids on it | Both |
| `engagement` | a smaller step toward a meaningful action (`filter_apply`) | PostHog |
| `retention` | users returning / adopting (`session_reengage`, `notification_click`) | PostHog |
| `friction` | where users get stuck (`login_fail`) | PostHog |

`cta_click` is the single per-call exception (`meaningful_action` for high-intent,
`engagement` otherwise). Category labels are internal routing attributes — never sent as
event names or payload fields, so `engagement` does not collide with GA4's reserved
`user_engagement`.

## New event, or a property on an existing one?

Same action, only the kind differs (rating, method, channel) → **property**. A genuinely
different action, or a distinct funnel step with its own drop-off → **new event**. Funnel
steps (`review_start` → `review_submit`) are separate events, not variants. Detail-page
views are `page_view` + `page_type` + entity id, never `article_view` / `item_view`.

## Implement mode

1. Read `references/using-the-wrapper.md` (and consult `tracking-conventions.md` for
   naming/category calls).
2. **Locate the team package.** Apps import `track` / `identify` from their team package
   (e.g. `@ramp106/omrjs-tracking-reviews`), never from `@ramp106/omrjs-tracking`. Confirm
   the app is initialised once with `initTracking({ app, posthog, debug })`.
3. **Reuse before inventing.** Grep the registry + catalogue for an existing event first.
4. **Design the event** with the conventions' checklist: category (→ routing), new-event-
   vs-property, `object_verb` name, typed props (`object_adjective`, `is_`/`has_` booleans,
   unit suffixes, fixed value sets), a `surface` from the list, PII check on every value.
5. **Add it to the team registry** via `defineTeamEvents({ ... })` — canonical name,
   `category`, `state: 'proposed'`, typed props. New page type → augment `PageTypeExtensions`;
   new prop on a core event → augment the extension interface. A rename gets a `legacyAlias`
   (+ `sunsetDate`, and a `legacyPayload` if the legacy GTM fields differ) — never a `live`→
   `removed` jump.
6. **Fire it** at the call site: `track('name', { surface, ...props })`. Never pass `app`,
   `experiment_variant`, or identity fields — the wrapper adds them. Identity is set once at
   login via `identify(...)`, reset on logout via `resetIdentity()`.
7. **Update the catalogue in the same change** if the registry now diverges from it.
8. Verify: `tsc` compiles (the typed registry accepts the event + props), and in `debug`
   mode the dev-validate warnings are clean.

## Audit mode

1. Read both reference files.
2. **Collect the events under review** — from a PR (`gh pr diff` / `gh pr view`), a spec, or
   by grepping the code for `track(`, and for leaks: `dataLayer.push`, `gtag(`, `capture(`.
3. **Check each event**, in order:
   hard rules → category/routing (apply the category test yourself; don't trust the label) →
   catalogue/registry conformance (name + category match a row; flag drift) → properties
   (`snake_case`, `object_adjective`, `is_`/`has_`, unit suffixes, **no PII**) → lifecycle
   (new = `proposed`; renames have a deprecation path, never `live`→`removed`) → identity
   (set once at login, never repeated per-event; the contract fields only) → **wrapper
   discipline** (no direct GA4/PostHog calls in app code).
4. **Report findings by severity:**
   - **Violation** — breaks a hard rule (naming, PII, one-per-variant, lifecycle, direct
     tool call). Must fix.
   - **Inconsistency** — diverges from catalogue/registry without updating it, or uses
     states/categories inconsistently. Fix by picking one and updating every source in the
     same change.
   - **Suggestion** — compliant but improvable.
   Each finding: event name, what's wrong, the compliant alternative, and which convention
   section (or wrapper rule) it violates.

## Ownership guard

Per-event category calls belong to the team — apply the category test, record the decision
once (registry + catalogue, same change). Only two things escalate: changes to the
conventions themselves (naming rules, routing table, identity model — sign-off: Calvin), and
new events entering the catalogue (gated by the catalogue owner once assigned). An audit
checks that the decision rule was applied and recorded consistently, not who made it.

## Sources

Written from scratch by OMR. The bundled `references/tracking-conventions.md` is a snapshot
of the OMR Event Tracking Conventions (Knowledge Hub topic "Tracking Architecture Reset");
`references/using-the-wrapper.md` documents the `@ramp106/omrjs-tracking` package in the
[ramp106/omr-js](https://github.com/ramp106/omr-js) monorepo.
