# Event tracking conventions

The rules every analytics event follows: what it is called, what it carries, where it goes and who may change it. A number should mean the same thing in every tool, and an event name should still make sense to someone a year from now.

This is a reference. Find the rule you need, apply it, move on. The events that exist live in the project's registry (see `library.md`), and the generated tracking plan is the readable copy of it.

Shared by `tracking-setup`, `tracking-apply` and `tracking-audit`. Where a rule says "the project records", the answer goes in the project's tracking doc (`docs/tracking.md` or the stack's equivalent), written by `tracking-setup`.

## The whole idea in five points

1. **Events live in one central library, like an i18n catalogue.** One typed registry holds every event. Call sites use a typed helper and never name a tool, never pass a raw string, never call an analytics SDK.
2. **Two kinds of tool, on purpose.** Marketing analytics (GA4 in the examples) does ad attribution: it tells the ad platforms what to bid on. Product analytics (PostHog in the examples) does product behaviour: funnels, retention, experiments, session replay. Neither does the other's job well.
3. **Route by category, not by event.** Nobody picks a tool at the call site. The event's category in the registry decides where it goes.
4. **Name things the same way every time.** Lowercase `snake_case`, object then verb (`review_submit`), one name everywhere.
5. **Keep private data out.** No personal names, emails, free text or tokens. Only IDs, bands and fixed labels.

## Words

| Term | Meaning |
| --- | --- |
| **Event** | A thing a user or the system did: `signup`, `checkout_complete`. |
| **Property** | A detail on an event: `rating: 4`, `signup_method: "google"`. |
| **Category** | One of six buckets saying which question an event answers. It decides the destinations. |
| **Destination** | Where an event is sent: `product` (product analytics), `marketing` (marketing analytics). |
| **Surface** | Which functional zone of the UI fired the event (`auth`, `search`, `checkout`). |
| **Registry** | The typed module that defines every event. The single source of truth. |
| **Tracking library** | The registry plus the helper, adapters, consent, privacy guard and identity code around it. The only code that talks to analytics tools. |
| **Tracking plan** | The human-readable list of events, generated from the registry. |
| **Identity stitching** | Linking anonymous activity to an account once the user logs in. |
| **Drift** | The gap between two tools' counts for the same event. |

## The two decisions you actually make

### Decision 1: which tool does the event go to?

You do not pick the tool. You pick the category, and the category picks the tools. Work down the list and stop at the first match.

| Ask | Answer |
| --- | --- |
| Is it a session or page-frame event (`page_view`, `consent_update`)? | **Lifecycle.** Both. |
| Is it the moment an anonymous visitor becomes known, and could marketing tie it to an ad (signup, lead)? | **Acquisition.** Both. |
| Would a leadership dashboard report it, or would marketing bid on it? | **Yes:** meaningful action, both. **No:** engagement, retention or friction, product analytics only. |

### Decision 2: new event, or a property on an existing one?

Is the action genuinely different, or the same action with a different detail?

| Situation | Do this |
| --- | --- |
| A different action, or a funnel step with its own drop-off, dashboard or experiment | **New event** |
| The same action, only the kind differs (rating, method, channel, threshold, plan) | **Property** |

Gut check: you want to count it separately. Is that because it is a different action, or the same action with a filter? Filter means property.

Funnel steps are not variants. `checkout_start`, `payment_info_add` and `purchase` each have their own drop-off, so they are separate events. A detail-page view is never its own event: it is `page_view` with a `page_type`.

## Naming

### Events

| Rule | Example |
| --- | --- |
| Lowercase `snake_case` | `review_submit` |
| Present-tense verb | `submit`, not `submitted` |
| Object first, then verb (`object_verb`) | `note_create`, not `create_note` |
| Three parts when two things are involved | `cart_item_add`, `workspace_member_invite` |
| One word when the verb stands alone | `signup`, `search`, `subscribe`, `share`, `purchase` |
| No values in the name | `session_reengage` + `days_since_last_session`, not `reengage_after_30d` |
| No versions in the name | `note_export`, never `note_export_v2`. A replacement event gets a new honest name and the old one is deprecated |
| One name in code and in every tool | The registry is the only place a name is written. A destination-specific alias (see Marketing names) is mapped in the library, never at a call site |
| A fixed registry entry, never a variable | `track(events.reviewSubmit, ...)`, never `track(name, ...)` |

Why object first: sorting groups related events (`cart_*`, `note_*`), it matches what PostHog (`survey_shown`) and GA4 (`page_view`, `session_start`) already do, and it mirrors the property rule. The cost is that a few recommended marketing names are verb first (`sign_up`); the library maps those once.

Never use the reserved prefixes `ga_`, `google_`, `firebase_` (GA4) or `$` (PostHog). Avoid GA4's reserved event names, among them `app_remove`, `app_update`, `error`, `first_open`, `first_visit`, `screen_view`, `session_start`, `user_engagement`. No `category:name` prefixes: the colon breaks GA4. `page_view` is the one Google name kept as is, because it already fits `object_verb`.

**Good:** `signup`, `review_submit`, `filter_apply`, `email_verify`, `cta_click`, `demo_book`, `share`, `search`, `page_view`, `cart_item_add`, `note_create`, `checkout_complete`

| Wrong | Problem | Right |
| --- | --- | --- |
| `submitReview`, `Submit Review`, `submit-review` | Case | `review_submit` |
| `review_submitted`, `checkout_completed` | Past tense | `review_submit`, `checkout_complete` |
| `submit_review` | Verb first | `review_submit` |
| `ga_signup` | Reserved prefix | `signup` |
| `reengage_after_30d`, `subscribe_monthly`, `share_twitter` | Value in the name | event + property |
| `cart_add` | Unclear which thing | `cart_item_add` |

### Properties

| Rule | Example |
| --- | --- |
| Lowercase `snake_case` | `signup_method` |
| Noun first, then adjective (`object_adjective`) | `user_id`, `plan_tier` |
| Booleans start with `is_` or `has_` | `is_first_order` |
| Timestamps end in `_at`, UTC | `created_at` |
| Dates end in `_date` | `signup_date` |
| Durations and amounts name the unit | `time_on_step_seconds`, `value_eur` |
| A fixed set of values wherever possible | `signup_method`: `email`, `google`, `magic_link` |
| IDs, never names or full values | `product_id`, then join the name in the warehouse |

## The six categories and routing

Every event is in exactly one category. The category answers "which question does this serve". That is different from `surface`, which answers "where in the product".

| # | Category | What is in it | Goes to |
| --- | --- | --- | --- |
| 1 | `lifecycle` | Session and page-frame events: `page_view` (fired by the library with `page_type` and entity IDs), `consent_update` | Both |
| 2 | `acquisition` | Anonymous becomes known. Top of funnel, ad-attributable: `signup`, `lead_generate` | Both |
| 3 | `meaningful_action` | Business KPIs: reported to leadership or bid on by marketing. Money, sales pipeline, first value, high-intent behaviour | Both |
| 4 | `engagement` | Smaller steps toward a meaningful action, not a KPI on their own: `filter_apply`, `cart_item_add` | Product |
| 5 | `retention` | Users returning or adopting features: `session_reengage`, `notification_click` | Product |
| 6 | `friction` | Where users get stuck: `login_fail`, `form_submit_fail` | Product |

| Category | Marketing | Product |
| --- | --- | --- |
| `lifecycle` | yes | yes |
| `acquisition` | yes | yes |
| `meaningful_action` | yes | yes |
| `engagement` | no | yes |
| `retention` | no | yes |
| `friction` | no | yes |

Lifecycle reaches both tools, identity and consent included, with no carve-out.

**The category lives in the registry, not at the call site.** The library reads it and routes. A call site never says which tool.

**One allowed exception: a per-call category.** An event like `cta_click` is a meaningful action for a high-intent button and engagement for the rest. Its registry entry lists both categories, and the helper's type then requires the call site to pass one of them. Keep this to the one or two events that need it; the registry test counts them.

**Sanity check:** for any key KPI you can point at one event, or a small set, that produces it.

Meaningful actions group by business area for navigation only. Every row is still `meaningful_action`.

| Area | Example events |
| --- | --- |
| Money | `subscribe`, `plan_upgrade`, `purchase` |
| Sales pipeline | `demo_book`, `lead_generate` |
| Core value | `note_create`, `review_submit`, `order_reorder` |
| Discovery | `search`, `content_select` |
| Onboarding | `email_verify`, `onboarding_complete` |

## Properties you will reuse

### Context properties

| Property | Set by | Values |
| --- | --- | --- |
| `app` | the library | the deployed app that fired it (`shop-web`, `notes-ios`). The list is in the tracking doc |
| `surface` | the call site | a fixed list the project records, for example `auth`, `onboarding`, `search`, `filter`, `nav`, `cta`, `billing`, `checkout`, `editor`, `widget`, `assistant`, `profile`, `dashboard` |
| `experiment_variant` | the library | set while the user is in a product-analytics experiment |
| `release` | the library, optional | the app version, for spotting broken releases |

`surface` is the functional zone of the UI and nothing else. Three properties answer three separate questions and never overlap:

- `app`: which deployed app fired it.
- `surface`: which kind of zone fired it.
- `account_type`: who the user is (from identity).

"A seller edited a listing in the editor of the shop's web app" is `app: shop-web`, `account_type: seller`, `surface: editor`, never one packed field.

### What is on every event, and from where

| What | Examples | Set by | Reaches |
| --- | --- | --- | --- |
| Context | `app`, `release` | the library | both |
| Context | `surface` | the call site | both |
| Context | `experiment_variant` | the library, during an experiment | product |
| Identity | `user_id`, `account_type`, `company_id`, `plan_tier` | once at login, by the library | both, carried automatically |
| Event properties | `rating`, `signup_method` | the call site, typed by the registry | both, on the events that define them |

Identity is set once at login and carried by both tools after that. You never pass it on a call.

### Common property names

Use the canonical name; do not invent variants. The exact values per product (plans, roles, lead types) live in the registry, so this list does not go stale when a plan is renamed.

| Property | Used on | Values |
| --- | --- | --- |
| `user_id` | identity | opaque internal ID, never an email |
| `company_id`, `company_domain` | B2B identity and events | IDs, `example.com` |
| `product_id`, `order_id`, `note_id` | per-entity events | IDs |
| `account_type` | identity (person) | the roles, for example `buyer`, `seller`, `admin` |
| `plan_tier` | identity (group), where there are plans | for example `free`, `pro`, `team` |
| `signup_method` | `signup` | `email`, `google`, `magic_link` |
| `lead_type` | `lead_generate` | `demo`, `contact`, `waitlist` |
| `billing_period` | `subscribe`, `plan_upgrade` | `monthly`, `annual` |
| `share_channel` | `share` | `email`, `copy_link`, `linkedin` |
| `days_since_last_session` | `session_reengage` | integer |
| `is_first_*`, `is_authenticated` | many | boolean |
| `time_to_*_seconds` | funnel and friction events | integer, one unit |
| `error_type`, `step_name`, `field_name` | friction events | fixed values |
| `entity_type`, `entity_id` | `share`, `content_select` | fixed values, ID |

**Role, plan and purchases are three different things.** Role (`account_type`): who the person is, set at identify. Standing plan (`plan_tier`): what the account subscribes to, a group property, only where plans exist. One-time purchase: a `purchase` event with an `item_type` property and value bands, never a standing property. Leave `plan_tier` off where a product has no plans.

## page_view and page types

`page_view` is one event for every page. The library fires it on every route change, including client-side navigations, and the tools' automatic pageview is turned off so it does not double-count. Each fire carries `page_type` plus the IDs that page needs. Leave out properties that do not apply; never set them to null.

| `page_type` | Needs |
| --- | --- |
| `home`, `auth`, `dashboard`, `settings` | nothing |
| `product` | `product_id` |
| `category` | `category_id` |
| `article` | `article_id` |
| `checkout` | nothing (steps are events) |
| `landing` | `campaign_id`, optional |
| `other` | nothing; the catch-all |

The project's own page types live in the registry. Adding one is a one-line change there, never a new event like `product_view` or `article_view`.

## Identity

At login, before any other event, the library runs, in this order:

```ts
posthog.identify(user_id, personProperties)
posthog.group("company", company_id, groupProperties) // B2B only
posthog.alias(anonymous_id, user_id)                  // first login only, where the SDK needs it
```

| Call | What it does |
| --- | --- |
| `identify` | "This anonymous session is now user X." Links every later event to the person. |
| `group` | "User X belongs to company Y." Needed for B2B funnels and group experiments. |
| `alias` | Connects pre-login activity to the known user. |

Order matters. Identify after an event and the event sticks to the anonymous user. Group after an experiment exposure and the result cannot be grouped. Alias before identify and there is nobody to link to. The library owns this; call sites never do.

**The marketing tool gets the same identity.** At the same login the library sets GA4's User-ID to the same opaque `user_id` and sets user properties (`account_type`, `company_id`, `plan_tier`). Under consent, never an email or a person's name.

**Logout** calls the library's `reset`, which clears the identity in every tool, so the next person on the device starts anonymous.

**Login is not an event; a failed login is.** A successful login is already recorded by identify, and identity rides every event after it; count logins as identified sessions. A failed login has no identity to attach and diagnoses drop-off, so `login_fail` is a friction event.

| Scope | Describes | Set with |
| --- | --- | --- |
| Event | the event | `capture("name", { ... })` |
| Person | the user, across events | `identify(id, { ... })`, `$set`, `$set_once` |
| Group | the company | `group("company", id, { ... })` |

`$set` overwrites: use it for things that change (`plan_tier`). `$set_once` writes only the first time: use it for things that never change (`signup_date`, `initial_referrer`). Watch out: `$set_once` is claimed by the first event the tool receives, which may not be the earliest by timestamp, so a backfill can overwrite the original.

## Marketing names

GA4 has recommended event names. Sending Google's exact name builds standard reports and offers the event as an ads conversion. Keep the `object_verb` name in the registry and give the entry a `marketingName`; the library sends that name to the marketing tool and the canonical name everywhere else. The project records whether it maps in the library (default, versioned and reviewable) or in the GA4 admin UI.

| Registry name | GA4 name | What it turns on |
| --- | --- | --- |
| `signup` | `sign_up` | conversions, ads suggested conversion |
| `lead_generate` | `generate_lead` | lead generation report |
| `subscribe` | `subscribe` | conversions |
| `search` | `search` | site search report |
| `content_select` | `select_content` | content reports |
| `share` | `share` | engagement reports |
| `page_view` | `page_view` | engagement reports |
| `checkout_start` | `begin_checkout` | ecommerce funnel, when it goes to marketing |
| `purchase` | `purchase` | conversions, ads purchase conversion |

Events with no Google equivalent go under their own name. Two registry events must never map to the same marketing name.

Ecommerce follows the standard shape: `cart_item_add`, `cart_item_remove`, `cart_item_update`, `checkout_start`, `payment_info_add` (engagement, product only), then `purchase` (meaningful action, both). Use `page_view` with `page_type: "product"` for product pages unless the marketing tool's ecommerce reports are needed, then the project records the exception.

## Hard limits

| | GA4 | PostHog |
| --- | --- | --- |
| Event name length | 40 characters | keep to 40 for parity |
| Characters | `[a-zA-Z0-9_]`, starts with a letter | same |
| Distinct event names | 500 per app stream; treat it as the budget on web too | no hard cap |
| Properties per event | 25 | no hard cap |
| Property name length | 40 characters | no hard cap |
| Property value length | 100 characters | no hard cap |
| User property name / value | 24 / 36 characters, 25 user properties | no hard cap |
| Custom dimensions | 50 event-scoped, 25 user-scoped (standard); a property not registered as one does not show in reports | not needed |
| Reserved | `ga_`, `google_`, `firebase_` prefixes, the reserved event names | `$` prefix |

The name cap is the main reason never to make one event per variant. Events routed to marketing are checked against these limits in the registry test, not in production.

## Client side or server side

Default: the browser, through the library. Move an event to the server when:

- it is revenue or a state change the database already knows (`purchase`, `subscribe`, `subscription_cancel`): the server is the truth and ad blockers cannot drop it;
- it happens without a browser (webhooks, jobs, emails, an API client);
- measured ad-blocker loss on a key event passes about 10% against billing or auth records.

A server event uses the same registry entry with `capture: "server"` and the server half of the library (PostHog's server SDK, the GA4 Measurement Protocol). It carries the same `user_id` so identity stitches, and it must respect the consent the user gave in the browser: store the consent state with the user or the session and check it before sending. Never fire the same event from both sides.

## Consent and privacy

### Never put private data in a property value

| Use | Example |
| --- | --- |
| Internal ID | `user_id: "a7b3f1..."` |
| Hashed email (SHA-256 with a project salt), only when a join truly needs it | `email_hash: "e3b0..."` |
| Company domain or name (firmographic, not personal) | `company_domain: "example.com"` |
| Bands and labels | `order_value_band: "25-100"`, `country_code: "DE"` |

| Never send | Instead |
| --- | --- |
| Email | an ID; `email_hash` only if a join needs it |
| A person's name, phone number | leave out |
| Full IP address | let the tools anonymise; never add it |
| Postal address, precise location | country only |
| Card or bank details | leave to the payment provider |
| Free text (a note body, a search query that might hold personal data, an error message from user input) | a derived number (`note_length_chars`) or a fixed value (`error_type`) |
| Tokens, session IDs, magic-link codes, URLs with query strings that carry them | leave out; strip query strings from URLs |

The library enforces this: each event allowlists its properties in the registry, and the privacy guard rejects anything not allowlisted, anything that looks like an email or a token, and any string over 100 characters.

### No event before consent

The library asks the consent state before every send. Before consent, nothing leaves the browser: events are dropped, or held in memory and sent only once consent is granted, per the project's recorded choice. Product analytics starts with no persistence (memory only) and the marketing tool runs with consent mode set to denied. When consent changes, the library upgrades or stops each tool and fires `consent_update`. No app writes its own consent check.

### Decisions the project records

| Setting | Recommended default |
| --- | --- |
| Product analytics region | the region the users' law expects (EU cloud for EU users) |
| Marketing analytics retention | the longest the plan allows (14 months on standard GA4), never the 2-month default |
| Product analytics retention | the plan's actual window, written down |
| Google Signals (cross-device ad data) | off unless a stated need justifies it |
| Consent mechanism | which banner or framework, and which consent purposes map to which destination |
| Before-consent behaviour | drop, or hold in memory until granted |
| Right to erasure | how a deletion request reaches each tool; keeping only IDs and bands makes it one mapping |

## Who owns what

Roles, not people. The project's tracking doc names the person for each role.

| Role | Owns | Does not own |
| --- | --- | --- |
| **Product owner** | what to track: the question in plain language, the success measure | names, properties, category |
| **Engineer** | how to track: turns the question into events per this doc, picks category and surface, reuses existing events, proposes tracking when a spec forgets it | approving cross-feature registry changes |
| **Registry owner** | the registry: approves new events, runs the lifecycle and the deprecation window, runs the audit | per-feature event design |
| **Library owner** | the library: routing, consent, identity order, privacy guard, adapters | the business meaning of an event |
| **Conventions owner** | changes to this document and to routing | day-to-day registry work |

On a small team one person holds several roles. Write that down anyway, so the decisions have somewhere to go. Talk tracking through when the spec is written, not at review time.

## Lifecycle of an event

The state lives in the registry and is mirrored in the product-analytics tool (event definitions, verified flag), so analysts see it where they work.

| State | Meaning |
| --- | --- |
| `proposed` | in the registry, not firing in production yet |
| `live` | firing in production, safe for dashboards |
| `deprecated` | still firing, has a sunset date and a named replacement |
| `removed` | no longer fired; the entry stays as a tombstone so the name is never reused for something else |

Renaming or deleting an event silently breaks saved insights, running experiments and warehouse models. Never jump from `live` to `removed`.

| Move | When |
| --- | --- |
| `proposed` to `live` | the first time it is seen in production |
| `live` to `deprecated` | the replacement is firing; sunset date and replacement written in the registry |
| `deprecated` to `removed` | 30 days or more later, and nothing references it |

A rename is a new entry plus the old one marked `deprecated` with `replacedBy`. During the window the library dual-fires: the call site calls the new event and the library also sends the old name, so dashboards keep working while they are repointed.

## Checks

### While designing (in the spec or tech plan)

1. Which question does it answer? No question, no event.
2. Category? If none of the six fit, the event is not well defined.
3. New event or a variant? A variant is a property.
4. Which surface? Propose a new value in the same change if none fits.
5. A detail-page view? That is `page_view` + `page_type`.
6. Name follows the rules? `snake_case`, present tense, `object_verb`, no values.
7. Properties follow the rules? `object_adjective`, `is_`/`has_`, units, fixed values.
8. Any private data in a value? Use an ID, a band or a derived number.

### In the change

- The type check passes: the registry accepts the event and its properties.
- The event is in the registry with owner, category, question, since and status `proposed`.
- The call site goes through the helper. No SDK call, no string literal.
- No private data in any value. No event before consent (a test proves it).
- The generated tracking plan is up to date.

### After deploy

- Confirm it fires once, not twice. Product analytics: debug mode and the live events view. GA4: DebugView and the realtime report. Check that login stitching works.
- The first production fire moves the state to `live`.
- For events in both tools, compare counts within a day.

## Drift

Product metrics: product analytics is the source of truth. Paid-ad metrics: marketing analytics is. No metric has two sources of truth. On shared events, within 5% is healthy, 5 to 10% is worth a glance (high-volume events run higher), over 10% is a bug. The tools sample and filter differently, so they never match exactly.

## Examples to copy

Registry entries first, then the call. Call sites never pass `app`, `experiment_variant`, the category or identity.

### signup (acquisition)

```ts
signup: {
  name: "signup", category: "acquisition", capture: "client", marketingName: "sign_up",
  owner: "growth", status: "proposed", since: "1.4.0",
  question: "How many visitors create an account, by method?",
  props: { signup_method: ["email", "google", "magic_link"], is_invited: "bool" },
},
```

```ts
track(events.signup, { surface: "auth", signup_method: "google", is_invited: false });
```

### page_view (lifecycle)

```ts
track(events.pageView, { page_type: "product", product_id });
```

Fired by the library's router hook, not by each page. IDs that do not apply are left out.

### note_create (meaningful action, a notes app)

```ts
track(events.noteCreate, { surface: "editor", note_id, template: "blank", is_first_note: true, note_length_chars: 412 });
```

`note_length_chars` is derived. The note's text never leaves the app.

### purchase (meaningful action, a shop, captured on the server)

```ts
trackServer(events.purchase, { user_id, order_id, order_value_band: "25-100", item_count: 2, payment_method: "card", is_first_order: true });
```

Fired from the payment webhook, so ad blockers cannot drop it and the count matches billing.

### cta_click (the per-call category)

```ts
track(events.ctaClick, { surface: "cta", cta_id: "pricing_hero", cta_position: "hero" }, { category: "meaningful_action" });
```

A low-intent CTA passes `{ category: "engagement" }` and goes to product analytics only. `cta_position` stays a property, never part of the name.

### session_reengage (retention)

```ts
track(events.sessionReengage, { surface: "nav", days_since_last_session: 30, entry_page_type: "home" });
```

Fired by the library on the first event after an N-day gap. The gap is a property, never `reengage_after_30d`.

### login_fail (friction)

```ts
track(events.loginFail, { surface: "auth", error_type: "wrong_password" });
```

`error_type` is a fixed set (`wrong_password`, `no_account`, `locked`), never the raw error message.

## Journeys

There is no "abort" or "bored" event. Abandonment is the absence of the next step, measured as the drop between two events in a funnel.

### A shop: buying

```
page_view          { page_type: "product", product_id }                 lifecycle, both
cart_item_add      { product_id, quantity: 1, item_value_band }          engagement, product
cart_item_update   { product_id, quantity: 2 }                           engagement, product
checkout_start     { item_count: 2, cart_value_band }                    engagement, product
payment_info_add   { payment_method }                                    engagement, product
purchase           { order_id, order_value_band, item_count }            meaningful action, both (server)
```

The drop from `checkout_start` to `purchase` is checkout abandonment. Changing the quantity is `cart_item_update`, not a new event. "How many people had something in the cart?" is unique users with `cart_item_add` in the period; the funnel is `cart_item_add`, `checkout_start`, `purchase`, broken down by any property; session replay shows why people stall.

### A notes app: first value

```
signup             { signup_method }                                     acquisition, both
onboarding_complete{ onboarding_flow, time_to_complete_seconds }         meaningful action, both
note_create        { note_id, template, is_first_note }                  meaningful action, both
note_share         { note_id, share_channel }                            engagement, product
session_reengage   { days_since_last_session }                           retention, product
```

`signup` to the first `note_create` is activation. Everything between is product-only context about the path.

## Anti-patterns

| Wrong | Right |
| --- | --- |
| `review_submit_5_star`, `review_submit_4_star` | `review_submit` + `rating` |
| `signup_email`, `signup_google` | `signup` + `signup_method` |
| `cta_click_header`, `cta_click_hero` | `cta_click` + `cta_position` |
| `subscribe_monthly`, `subscribe_yearly` | `subscribe` + `billing_period` |
| `share_twitter`, `share_linkedin` | `share` + `share_channel` |
| one event per page type | `page_view` + `page_type` |
| `posthog.capture("Signup")` in a component | `track(events.signup, ...)` |
| `gtag("event", "purchase", ...)` in a page | `trackServer(events.purchase, ...)` |
| the same event fired from client and server | one side, recorded in the registry |
| a `login` event | identify; count identified sessions |

## Why two tools

Marketing analytics owns ad attribution: the ad platforms bid well only on conversions they receive, and their bidding integrations exist for their own analytics. Product analytics owns product behaviour: funnels, retention, B2B groups, session replay, feature flags, experiments. Marketing analytics does those poorly: it samples, has no account concept and no experiment exposure.

Not everything goes to both, because the marketing tool's name and property caps fill up, mirrored events lose detail at 25 properties, every shared event doubles setup, consent and tests, and every erasure request hits two tools.

A project that runs only one tool still uses the categories: they keep the routing decision cheap when a second tool arrives.
