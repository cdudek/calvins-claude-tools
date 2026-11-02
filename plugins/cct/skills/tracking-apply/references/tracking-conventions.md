---
status: current
version: 2
last_updated: 2026-06-10
audience: PMs, engineers, designers, analysts, anyone who touches product data
note: Bundled snapshot for the tracking-apply skill. Canonical source is the OMR Knowledge Hub topic "Tracking Architecture Reset". Once the typed registry in @ramp106/omrjs-tracking (omr-js) is live it is the authority for what exists; this file stays the authority for the rules.
---

# OMR Event Tracking Conventions

## Start here

Every analytics event at OMR follows this document: what it's called, what details it carries, and which of our two tools it goes to. The goal is simple. A number should mean the same thing whether you read it in GA4 or PostHog, and an event name should still make sense to someone a year from now.

This is a reference. You don't read it cover to cover. Find the rule you need, apply it, move on. The list of events that exist today lives in a separate file, the OMR Event Catalogue.

PMs and designers need only this section and the next one. Engineers and analysts use the rest as a reference.

> **One open item.** The Catalogue owner role is not assigned yet (see "Who owns what"). Until someone holds it, no one gates new events against this doc and the lifecycle rules are not enforced. This is the first thing to fix.

### The whole idea in four points

1. **Two tools, on purpose.** GA4 handles ad attribution: it tells Google Ads what to bid on. PostHog handles product behaviour: funnels, retention, experiments, session replay. Neither can do the other's job.
2. **Route by category, not by event.** You never choose GA4 or PostHog in the code. You set the event's category, and the shared tracking code sends it to the right place.
3. **Name things the same way every time.** Lowercase `snake_case`, object then verb (`review_submit`), the same name in both tools.
4. **Keep private data out.** No personal names, emails, or raw text in events. Only IDs and safe labels.

If you remember nothing else, remember these four.

### Words used in this doc

Read once and the rest reads cleanly.

| Term | Plain meaning |
|---|---|
| **GA4** | Google Analytics 4. We use it for ad attribution and Google Ads. |
| **PostHog** | Our product analytics tool. Funnels, retention, experiments, session replay. |
| **Event** | A thing a user did, like `signup` or `review_submit`. |
| **Property** | A detail on an event, like `rating: 4` or `signup_method: 'google'`. |
| **Category** | One of six buckets that says what business question an event answers. The category decides which tool it goes to. |
| **Surface** | Which part of the product fired the event (auth, reviews, search). |
| **Tracking wrapper** | The shared code every OMR app calls to send events. It adds standard details, routes to the right tool, and checks consent. No app talks to GA4 or PostHog directly. |
| **Catalogue** | The official list of every event that exists. A separate file. |
| **Identity stitching** | Linking a user's anonymous activity to their account once they log in. |
| **Drift** | The gap between the counts GA4 and PostHog report for the same event. |

## The two decisions you will actually make

Most of the work comes down to two questions.

### Decision 1: which tool does my event go to?

You don't pick the tool. You pick the category, and the category picks the tool. Work down this list, stop at the first match.

| Ask                                                                                                      | Answer                                                                                            |
| -------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| Is it a session or page-frame event (`page_view`, session start)?                                        | **Lifecycle.** Both tools.                                                                        |
| Is it the moment an anonymous visitor becomes known, and marketing could tie it to an ad (signup, lead)? | **Acquisition.** Both tools.                                                                      |
| Would a leadership dashboard report it, or would marketing bid on it?                                    | **Yes:** Meaningful action, both tools. **No:** Engagement, Retention, or Friction, PostHog only. |

Full category definitions are in "The six categories". Why we don't just send everything to both tools is in "Why two tools".

### Decision 2: new event, or a property on an existing one?

One question: is the action genuinely different, or is it the same action with a different detail?

| Situation | Do this |
|---|---|
| A different action, or a distinct funnel step with its own drop-off rate, dashboard, or experiment | Create a **new event** |
| The same action, only the kind differs (rating, method, channel, threshold) | Add a **property** |

Gut check: if you want to count it separately on a dashboard, is that because it's a different action, or the same action with a filter? Filter means property. Different action means event.

Funnel steps are not variants. `review_start`, `review_draft_save`, and `review_submit` each have their own drop-off, so they are separate events. That is correct.

---

## Naming

### Events

| Rule | Example |
|---|---|
| Lowercase `snake_case` | `review_submit` |
| Present-tense verb | `submit`, not `submitted` |
| Object first, then verb (`object_verb`) | `review_submit`, not `submit_review` |
| Three parts when two things are involved | `cart_item_add`, `vendor_profile_claim` |
| One word when the verb stands alone | `signup`, `search`, `subscribe`, `share` |
| No values in the name (they go in properties) | `session_reengage` + `days_since_last_session`, not `reengage_after_30d` |
| Same name in code, both tools | `review_submit`. A few events also map to a Google name in the GA4 UI only (see GA4 names); the name in code stays identical |
| A fixed string, never a variable | `track('review_submit')`, never `track(name)` |

Why object first: it groups related events together when sorted (`review_*`, `cart_*`), it matches what PostHog and GA4 already do, and it mirrors how we name properties. Full reasoning in "Why object first".

Do not use the reserved prefixes `ga_`, `google_`, `firebase_` (GA4) or `$` (PostHog), and avoid the GA4 reserved names `app_remove`, `app_update`, `first_open`, `session_start`, `user_engagement`. No `category:name` prefixes either, the colon breaks GA4. Name length and other hard limits are in "Hard limits".

**Good:** `signup`, `review_submit`, `filter_apply`, `email_verify`, `cta_click`, `demo_book`, `share`, `search`, `page_view`, `cart_item_add`, `vendor_profile_claim`

`page_view` is the one Google name we keep as is, because it already fits `object_verb`.

**Bad, and why:**

| Wrong | Problem | Right |
|---|---|---|
| `submitReview`, `Submit Review`, `submit-review` | Case style | `review_submit` |
| `review_submitted` | Past tense | `review_submit` |
| `submit_review` | Verb first | `review_submit` |
| `ga_signup` | Reserved prefix | `signup` |
| `reengage_after_30d`, `subscribe_monthly`, `share_twitter` | Value baked into the name | event + property |
| `cart_add` | Unclear which thing | `cart_item_add` |

### Properties

| Rule | Example |
|---|---|
| Lowercase `snake_case` | `signup_method` |
| Noun first, then adjective (`object_adjective`) | `user_id`, `plan_tier` |
| Booleans start with `is_` or `has_` | `is_first_review` |
| Timestamps end in `_at` (UTC) | `created_at` |
| Dates end in `_date` | `signup_date` |
| Durations name the unit | `time_on_step_seconds` |
| Use a fixed set of values where you can | `signup_method`: `email`, `google`, `magic_link` |

---

## The six categories and routing

Every event is in exactly one category. The category answers "what business question does this serve", which is different from `surface`, which says "where in the product".

| # | Category | What's in it | Goes to |
|---|---|---|---|
| 1 | **Lifecycle** | Session and page-frame events. `session_start` is platform-fired; `page_view` we fire ourselves with `page_type` and entity IDs | Both |
| 2 | **Acquisition** | Anonymous becomes known. Top of funnel, ad-attributable | Both |
| 3 | **Meaningful action** | Business KPIs: leadership reports them or marketing bids on them. Monetisation, sales pipeline, first-time value, high-intent behaviour | Both |
| 4 | **Engagement** | Smaller steps toward a meaningful action, not a KPI on their own (`filter_apply`) | PostHog |
| 5 | **Retention** | Users returning or adopting features (`session_reengage`) | PostHog |
| 6 | **Friction** | Where users get stuck (`form_submit_fail`) | PostHog |

Routing follows straight from the category:

| Category | GA4 | PostHog |
|---|---|---|
| Lifecycle | ✓ | ✓ |
| Acquisition | ✓ | ✓ |
| Meaningful action | ✓ | ✓ |
| Engagement | ✗ | ✓ |
| Retention | ✗ | ✓ |
| Friction | ✗ | ✓ |

**Lifecycle events go to both tools, including identity and consent.** Identity (set at login) and `consent_update` reach GA4 and PostHog alike, so the rule holds with no carve-out. The how is under Identity, below.

**One real exception: `cta_click`.** It carries `meaningful_action` for high-intent CTAs and `engagement` for the rest, so the engineer sets its category per call site. It is the only content event whose category depends on significance rather than being fixed. See the catalogue note on `cta_click`.

**What an engineer writes:** the event name plus its category. The wrapper does the routing.

```typescript
track('review_submit', { category: 'meaningful_action', surface: 'editor', /* ... */ })
```

Sanity check: for any key KPI, you should be able to point at one event, or a small set, that produces it.

Meaningful action is the biggest category. For navigation, here is how those events group by business area. This is just a grouping, every row is still `meaningful_action`.

| Business area   | Example events                                         |
| --------------- | ------------------------------------------------------ |
| Monetisation    | `subscribe`, `plan_upgrade`, `purchase` |
| Sales pipeline  | `demo_book`                           |
| Vendor / agency | `vendor_profile_claim`, `review_respond`               |
| Reviewer        | `review_submit`, `review_start`                        |
| Discovery       | `search`, `content_select`                             |
| Onboarding      | `email_verify`, `onboarding_complete`                  |

---

## Properties you will reuse

### Context properties

`surface` is the one context value you pass on each `track()` call (the wrapper can't know which UI zone fired). `app` and `experiment_variant` the wrapper adds for you.

| Property             | Set by | Values                                                                                                                                         |
| -------------------- | ------ | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| `surface`            | caller | `auth`, `onboarding`, `search`, `filter`, `nav`, `cta`, `billing`, `checkout`, `editor`, `widget`, `assistant`, `profile`, `dashboard`                     |
| `app`                | wrapper | `reviews`, `eventmanager`, `hub-frontend`, `festival-pages`, `festival-mobile`, `omj`, `daily`, `omr-content-editor`, `omr-com`, `lead-portal` |
| `experiment_variant` | wrapper | set when the user is in a PostHog experiment                                                                                                   |

We use `surface`, not `category`, because "category" already means software-product category at OMR.

`surface` is the functional zone of the UI, nothing else. Three properties answer three separate questions and never overlap:

- `app`: which deployed app fired it (`reviews`, `eventmanager`, ...).
- `surface`: which kind of zone fired it (the list above).
- `account_type`: who the user is (the role, see below).

So "a vendor claimed their profile from the editor in the reviews app" is `app: reviews`, `account_type: vendor`, `surface: editor`, not all three packed into one field.

### What is on every event, and from where

Three different things end up on an event. Only `experiment_variant` is PostHog-only; identity and the rest reach both tools. This is the part that trips people up.

| What | Examples | Set by | Reaches |
|---|---|---|---|
| Context | `app` | the wrapper | both tools |
| Context | `surface` | you, on each call | both tools |
| Context | `experiment_variant` | the wrapper, during a PostHog experiment | PostHog |
| Identity | `user_id`, `account_type`, `company_id`, `company_name`, `plan_tier` | once at login | both tools (auto-carried) |
| Event properties | `rating`, `signup_method`, ... | you, on each call | both tools, on the events that carry them |

**Identity is set once at login and carried by both tools.** On the PostHog side the wrapper calls `identify` and `group`; on the GA4 side it sets the User-ID and user properties (see Identity, below). After that, every authenticated event in both tools carries `user_id`, `account_type`, `company_id`, `company_name`, and `plan_tier` automatically. You set this once, you never pass it on a `track()` call.

**What never reaches either tool: raw personal PII.** No email, no person's name, no phone number, in GA4 or PostHog. We do send the opaque internal `user_id` (GA4 uses it as the User-ID) plus firmographic and account labels (`account_type`, `company_id`, `company_name`, `plan_tier`). A company name is firmographic, not personal data, so it is fine; a person's name is not. All of it is gated on consent. Same PII line as Consent and privacy.

### Common property names

Send IDs, not names or full values. The warehouse looks up the rest at query time.

| Property                                               | Used on                                     | Values                                                            |
| ------------------------------------------------------ | ------------------------------------------- | ----------------------------------------------------------------- |
| `user_id` (UUID)                                       | identity                                    | never a raw email (see PII)                                       |
| `company_id`, `company_domain`                         | B2B only                                    | `siemens.com`                                                     |
| `product_id`, `category_id`, `article_id`, `agency_id` | per-entity events                           | UUIDs                                                             |
| `account_type` (role)                                  | identity (person)                           | `vendor`, `reviewer`, `agency`, `admin` (full list in the catalogue) |
| `plan_tier` (subscription)                             | identity (group), where the product has one | `free`, `essential`, `professional`, `ultimate`                            |
| `signup_method`                                        | `signup`                                    | `email`, `google`, `magic_link` (catalogue is the authority)         |
| `lead_type`                                            | `lead_generate`                             | `demo`, `contact`, `waitlist`, `enterprise`                       |
| `rating`                                               | `review_submit`                             | 1 to 5                                                            |
| `is_first_*`, `is_authenticated`                       | many                                        | booleans                                                          |
| `days_since_last_session`                              | `session_reengage`                          | integer                                                           |
| `billing_period`                                       | `subscribe`, `plan_upgrade`                 | `monthly`, `annual`                                               |
| `share_channel`                                        | `share`                                     | e.g. `linkedin`, `email`, `copy_link` (per the catalogue)         |

The exact enum values per product (plan tiers, roles, lead types) are owned by the catalogue, not pinned here, so this doc does not go stale when a plan is renamed. The values above are the canonical OMR set as of writing.

**Role, plan, and purchases are three different things.** Don't merge them into one field.

- **Role** (`account_type`): who the person is. Set once at `identify`, always present.
- **Standing plan** (`plan_tier`): what the account subscribes to. A group property on the company, present only where the product has subscriptions (Reviews, paid Jobs postings).
- **One-time purchase**: a festival ticket or an academy course fires `purchase` (an `item_type` property tells them apart), a Meaningful action with amount bands, never a standing property.

Where a product has no plan (a festival attendee, a content reader), leave `plan_tier` off, the same way `page_view` omits IDs that don't apply. The roles and plan names per product live in the catalogue, not here.

### page_view and page types

`page_view` is one event used for many page types. Each fire carries `page_type` plus the IDs that page needs. Leave out properties that don't apply, don't set them to null.

| `page_type` | Route | Needs |
|---|---|---|
| `product` | `/product/[slug]` | `product_id`, `category_id` |
| `product_pricing` | `/product/[slug]/pricing` | `product_id` |
| `product_alternatives` | `/product/[slug]/alternatives` | `product_id` |
| `category` | `/category/[slug]` | `category_id` |
| `article` | `/contenthub/[slug]` | `article_id` |
| `agency` | `/service/[slug]` | `agency_id` |
| `compare` | `/compare/...` | `product_id_a`, `product_id_b` |
| `home`, `auth`, `dashboard` | various | none |
| `other` | catch-all, no dedicated type | none |
| `landing` | promo pages | `campaign_id` (optional) |

This table holds the shared, cross-app page types. App-specific ones (for example eventmanager's vendor and agency pages, or the festival pages used in the Journeys) are defined in that app's catalogue section, not here. Adding a shared value is a one-line change to this table; adding an app-specific value is a change to that app's catalogue list.

---

## Identity

When a user logs in, call these three, in this order, before any other event:

```typescript
posthog.identify(user_id, personProperties)
posthog.group('account', company_id, groupProperties)   // B2B only
posthog.alias(anonymous_id, user_id)                     // first time only
```

| Call | What it does |
|---|---|
| `identify` | Says "this anonymous session is now user X". Links every later event to the right person. |
| `group` | Says "user X belongs to company Y". Needed for B2B funnels and group experiments. |
| `alias` | Connects the pre-login activity to the now-known user. |

Order matters. `identify` after an event, and the event sticks to the anonymous user. `group` after an experiment, and you can't group the result. `alias` before `identify`, and there is no user to link to. The wrapper handles all of this at login. You don't call it yourself at every event.

**GA4 gets the same identity.** At the same login, the wrapper sets GA4's **User-ID** to that opaque `user_id` and sets GA4 user properties (`account_type`, `company_id`, `company_name`, `plan_tier`). The User-ID stitches a user's sessions and cross-app journeys in GA4, the same job `identify` does in PostHog. So identity lands in both tools at login, under consent. Never a raw email or person name in either.

**Login itself is not an event, but a failed login is.** A successful login is already recorded: the `identify` call fires and identity rides every event after it, so a `login` event would add nothing. To count logins, count identified sessions in PostHog. A failed login is the opposite case, it is a Friction event, because it diagnoses a drop-off and there is no identity to attach yet. See `login_fail` in the examples.

**Where a property lives:**

| Scope | Describes | Set with |
|---|---|---|
| Event | the event | `capture('name', { ... })` |
| Person | the user, across all events | `identify(id, { ... })`, `$set`, `$set_once` |
| Group | the company | `group('account', id, { ... })` |

**`$set` vs `$set_once`:** `$set` overwrites, use it for things that change (`current_plan`). `$set_once` writes only the first time, use it for things that never change (`signup_date`, `initial_referrer`). Watch out: `$set_once` is claimed by the first event PostHog receives, which may not be the earliest by timestamp, so a backfill can overwrite the original.

---

## GA4 names

GA4 has a list of recommended event names. Firing under Google's exact name auto-builds a couple of standard reports and turns on the Google Ads suggested-conversion option. It's convenient, not required. We keep our `object_verb` names and map them to Google's names once, in the GA4 admin UI.

| Our event | GA4 name | What the mapping turns on |
|---|---|---|
| `signup` | `sign_up` | Conversions tab, Google Ads suggested conversion |
| `lead_generate` | `generate_lead` | Lead Generation report |
| `subscribe` | `subscribe` | Conversions tab |
| `search` | `search` | Site Search report |
| `content_select` | `select_content` | Content reports |
| `share` | `share` | Engagement reports |
| `page_view` | `page_view` | Engagement reports |
| `purchase` | `purchase` | Conversions tab, Google Ads purchase conversion |

Events with no Google equivalent just fire under our own name. No mapping needed.

**Identity in GA4.** Separately from event names, the wrapper sets GA4's User-ID to the same opaque `user_id` used in PostHog, plus user properties (`account_type`, `company_id`, `company_name`, `plan_tier`), once at login under consent. That is what links a user's sessions and cross-app journeys in GA4. Never a raw email or person name.

**Transactional events.** Reviews and eventmanager have no checkout today, so they don't fire these. Festival ticketing and the sponsor shopping system are transactional and use the standard pattern: `cart_item_add`, `cart_item_remove`, `cart_item_update`, `checkout_start`, and `payment_info_add` (Engagement, PostHog), then `purchase` (Meaningful action, both tools). See the Journeys section. `item_view` stays reserved: Reviews has no SKU product pages, those are `page_view` + `page_type: 'product'`.

---

## Client-side or server-side

**Decision: everything fires from the browser through the wrapper, for now.**

We're deferring server-side because the first scope (Reviews and eventmanager) has no checkout flow, and its revenue events (`subscribe`, `plan_upgrade`, `plan_downgrade`, `subscription_cancel`) are low-volume and checkable against billing, because server-side would add the PostHog server SDK, the GA4 Measurement Protocol, identity propagation, and separate test setup, and because losing the odd `signup` to an ad-blocker is fine (it comes back on the next page load).

**Revisit when:** ad-blocker loss on `subscribe` or `signup` passes 10% against billing or auth records, or the transactional apps (festival ticketing, sponsor shopping) are instrumented, in which case `purchase` goes server-side from day one for revenue accuracy.

---

## Consent and privacy

For a German company this part is not optional. It applies to every event.

### Never put private data in a property value

| Use this | Example |
|---|---|
| Internal UUID | `user_id: 'a7b3f1...'` |
| Hashed email (SHA-256, can't be reversed) | `email_hash: 'e3b0...'` |
| Company domain | `company_domain: 'siemens.com'` |
| Company name (firmographic, not personal) | `company_name: 'Siemens'` |
| Bands and labels | `mrr_band: '10k-25k'`, `country_code: 'DE'` |

| Never send | Instead |
|---|---|
| Raw email | hash it to `email_hash` |
| A person's name, phone number | leave out. A company name is fine (firmographic); a person's name is not |
| Full IP address | both tools anonymise it, don't add it |
| Postal address, precise location | country only |
| Card details | Stripe handles it, never copy to analytics |
| Free text (review body, a search that might hold PII) | a derived number (`review_length_chars`) |

### No event before consent

We use TCF (the ad industry consent framework) and Google Consent Mode v2. Before consent, PostHog uses an anonymous ID and GA4 runs with storage denied. The moment consent is given, the wrapper upgrades both. No app writes its own consent check.

### Retention and residency (decisions owed)

These are settings that need a named owner and a recorded value. Recommended defaults:

| Setting | Recommendation | Owner |
|---|---|---|
| PostHog region | EU Cloud (data stays in the EU) | platform owner, confirm current region |
| GA4 retention | 14 months (the max for standard) | analytics owner, confirm it's not the 2-month default |
| PostHog event retention | per plan, record the actual window | platform owner |
| GA4 Google Signals | off unless a specific need justifies it | analytics owner + legal |

Keep only opaque IDs and bands in analytics, and a right-to-erasure request becomes a deletion in one mapping table, not a sweep across both tools.

---

## Who owns what

Roles, not people. Names live in the topic README.

| Role | Owns | Does not own |
|---|---|---|
| **PM** | what to track: the business need in plain language | event names, properties, category, routing |
| **Engineer** | how to track: turns the need into events and properties per this doc, picks category and `surface`, reuses existing events. Proposes events back to the PM if the spec forgets tracking | approving cross-feature catalogue changes |
| **Catalogue owner (UNASSIGNED)** | the catalogue: approves new events, runs the lifecycle and the 30-day deprecation window, checks code against the catalogue | per-feature event design |
| **Wrapper owner (platform team)** | the wrapper: routing, consent, identity order, `$set` rules | per-event business meaning |
| **Sign-off (Calvin)** | changes to this doc and to routing | day-to-day catalogue work |

When in doubt, talk it through during spec writing, not at PR time. A two-minute chat beats two weeks of misrouted data.

The Catalogue owner is the current blocker. Until someone holds it, even on an interim basis, the lifecycle rules and the catalogue drift check are a plan, not a control.

---

## Lifecycle of an event

An event's state lives in the catalogue and is mirrored in PostHog, so analysts see it where they work.

| State | Meaning |
|---|---|
| **proposed** | defined in the wrapper, not firing yet. Hidden from PostHog's picker |
| **live** | firing in production, safe for dashboards. Verified flag set |
| **deprecated** | still firing, has a sunset date and a named replacement |
| **removed** | no longer firing, archived |

Renaming or deleting an event silently breaks saved insights, running experiments, and dbt models that use its name. So you never jump from `live` to `removed`. Go through `deprecated`, with at least 30 days for people to move over, even for a one-off event.

| Move | When |
|---|---|
| `proposed` to `live` | the first time the event is seen in production |
| `live` to `deprecated` | the replacement is firing, sunset date and replacement name written down |
| `deprecated` to `removed` | 30 or more days later, nothing references it |

Event definitions live in code, in a shared OMR frontend package, so the registry is one typed source of truth and not a JSON file, a wiki, or a slide. A new event means a PR to that package plus a row in the catalogue, gated by the catalogue owner. Every customer-facing app depends on the package and fires events only through it.

> **Open question.** Which package actually holds the registry is not settled: the `omr-js` tracking module, `common.js`, or a dedicated tracking package. The principle holds either way, one typed package that every app depends on. The wrapper owner makes the call.

---

## Checking it works

### While designing (run during spec writing)

1. **Category?** If none of the six fit, the event isn't well-defined.
2. **New event or a variant?** A variant means a property (see Decision 2).
3. **Which surface?** Propose a new one in the PR if none fit.
4. **A detail-page view?** That's `page_view` + `page_type`, not a new event.
5. **Name follows the rules?** `snake_case`, present tense, `object_verb`, no values in the name.
6. **Properties follow the rules?** `object_adjective`, `is_`/`has_`, unit suffixes.
7. **Any private data in a value?** Use a hashed or opaque ID.

### In the PR

- TypeScript compiles: the typed registry accepts the event and its properties.
- Name and properties match the catalogue row, or the PR adds the row.
- Category is set on the call.
- No raw PII in any value.
- State is `proposed`.
- Catalogue owner has reviewed it (once the role exists).

### After deploy

- Confirm it fires. PostHog: debug mode and the live events view. GA4: DebugView and the Realtime report. Check it fires once, not twice, and that login stitching works.
- The first production fire flips the state to `live`.
- For shared events, compare GA4 and PostHog counts within a day. They never match exactly (see "Drift").

---

## Examples to copy

Each one is complete and correct. Almost all follow the same shape: `category` first, `surface` second, then the event's own properties. (`page_view` is the one frame event that carries `page_type` instead of `surface`.) Bare names like `product_id` are IDs your code already has in scope. `app`, `experiment_variant`, and identity (`user_id`, `account_type`, `plan_tier`) are added elsewhere, so they never appear here.

### signup (Acquisition)

Fires when an anonymous visitor completes account creation.

```typescript
track('signup', {
  category: 'acquisition',
  surface: 'auth',
  signup_method: 'google',
  account_type: 'reviewer',
  is_invited: false,
});
```

Routing: both tools. GA4 name `sign_up`. `account_type` appears here because signup is the identify moment: the value is set on the person at `identify` and then rides every later event, so you never pass it again.

### page_view (Lifecycle)

Fires on every route change. We fire it ourselves, it is not the tools' automatic pageview. One event for every page; `page_type` drives which IDs are required.

```typescript
track('page_view', {
  category: 'lifecycle',
  page_type: 'product',
  product_id,
  category_id,
});
```

Routing: both tools. Omit IDs that don't apply, don't set them to null.

### review_submit (Meaningful action)

Fires when a reviewer submits a completed review.

```typescript
track('review_submit', {
  category: 'meaningful_action',
  surface: 'editor',
  product_id,
  rating: 4,
  is_first_review: true,
  time_to_submit_seconds: 87,
});
```

Routing: both tools. No GA4 equivalent, fires as `review_submit` in both.

### review_respond (Meaningful action)

Fires when a vendor replies to a review. Role and plan tier come from identity, so the event stays small.

```typescript
track('review_respond', {
  category: 'meaningful_action',
  surface: 'editor',
  review_id,
  product_id,
  is_first_response: true,
  response_length_chars: 247,
});
```

Routing: both tools. `account_type` and `plan_tier` come from identity, never repeated here. `response_length_chars` is derived, never the raw text.

### cta_click (Meaningful action)

Fires when a user clicks a tracked call to action. One event, the button position in a property.

```typescript
track('cta_click', {
  category: 'meaningful_action',
  surface: 'cta',
  cta_id,
  cta_position,
  is_authenticated: true,
});
```

Routing: both tools when high-intent; for a low-intent CTA set `category: 'engagement'` and it goes to PostHog only. `cta_position` ('header', 'hero', ...) stays a property, never part of the name.

### session_reengage (Retention)

Fires when a dormant user returns. The gap goes in a property, never the name.

```typescript
track('session_reengage', {
  category: 'retention',
  surface: 'nav',
  days_since_last_session: 30,
  entry_page,
});
```

Routing: PostHog only. `days_since_last_session` is a property, not `reengage_after_30d`.

### login_fail (Friction)

Fires when a login attempt fails. No identity yet, so it is a drop-off signal, not a success.

```typescript
track('login_fail', {
  category: 'friction',
  surface: 'auth',
  error_type: 'wrong_password',
});
```

Routing: PostHog only. `error_type`: 'wrong_password', 'no_account', 'locked'.

---

## Journeys: events across a real path

Single events are above. Here is how they fire in sequence as a user moves through a flow, and how to read the result. Festival ticketing and the sponsor shopping system are future apps in the catalogue, but the pattern is defined here so it is consistent when they land.

A note that runs through all of these: **there is no "abort" or "bored" event.** Abandonment is the absence of the next step. You measure it as the drop between two events in a funnel, not by firing an event when someone leaves.

### Festival: exploring speakers

```
page_view        { page_type: 'festival_speakers' }              Lifecycle, both
page_view        { page_type: 'festival_speaker', speaker_id }   Lifecycle, both
speaker_select   { speaker_id }                                  Engagement, PostHog   (optional)
```

The two `page_view`s already tell you which speakers draw traffic. Add `speaker_select` only if you want to rank interest from a list (which cards get clicked) rather than just which speaker pages get visited. We don't track anything else on a speaker today; if a PM wants "added to my agenda", that is a separate Meaningful action (`agenda_session_add`).

### Festival: buying a ticket

The cart and checkout steps are Engagement (PostHog builds the funnel); only `purchase` is a Meaningful action that also goes to GA4 for Google Ads.

Path A, the user abandons:

```
page_view        { page_type: 'festival_tickets' }                     Lifecycle, both
cart_item_add    { item_type: 'festival_ticket', item_id, quantity: 1, value_eur }   Engagement, PostHog
cart_item_update { item_id, quantity: 2 }                              Engagement, PostHog   (changed 1 to 2)
checkout_start   { cart_value_eur, item_count: 2 }                     Engagement, PostHog
payment_info_add { }                                                   Engagement, PostHog
(no purchase)
```

Path B, the user buys: identical up to `checkout_start`, then

```
purchase         { order_id, value_eur, quantity, currency: 'EUR', item_type: 'festival_ticket' }   Meaningful, both
```

Read it: the drop from `checkout_start` to `purchase` is your abandonment rate. Path A produced no `purchase`, that is the only signal you need. Changing the quantity is `cart_item_update`, not a new event, because it is the same cart, only the count differs.

### Sponsor shopping cart

```
cart_item_add    { item_id: 'A', value_eur }    Engagement, PostHog
cart_item_add    { item_id: 'B', value_eur }    Engagement, PostHog
cart_item_remove { item_id: 'A' }               Engagement, PostHog
(user leaves, no checkout_start, no purchase)
```

This answers the three questions directly:

- **"How many people had at least one item in the cart?"** In PostHog, a single-event insight: unique users who fired `cart_item_add` (any item) in the period. One number, no funnel needed.
- **"How do I build the funnel?"** A PostHog funnel with three steps: `cart_item_add` then `checkout_start` then `purchase`. Each step shows how many users carried through and the percentage lost. Break it down by `item_type` or sponsor `plan_tier` to see which packages convert.
- **"What if they get bored and leave?"** That is the funnel's drop-off: they entered at `cart_item_add` and never reached `purchase`. You don't fire a "bored" event. If you need to know where they stalled, the funnel shows the step; PostHog session replay shows why.

### Reviews: writing a review

```
page_view        { page_type: 'product', product_id }      Lifecycle, both
review_start     { product_id }                            Engagement, PostHog   (first focus on the form, not page load)
review_draft_save{ product_id, current_step }              Engagement, PostHog   (optional, per answered step)
review_submit    { product_id, rating, is_first_review }   Meaningful, both
```

Read it: `review_start` to `review_submit` is your completion funnel. The questions in between are steps, not separate concerns; only add `review_draft_save` if you want mid-form drop-off. The two ends are usually enough.

### Reviews: from content to contacting a provider

```
page_view      { page_type: 'article', article_id }            Lifecycle, both
cta_click      { cta_id, surface: 'widget' }                   Meaningful, both   (a high-intent widget in the article)
content_select { category_id }                                 Meaningful, both   (clicks a category, GA4 select_content)
filter_apply   { filter_group, filter_value }                  Engagement, PostHog   (the category applies filters)
page_view      { page_type: 'product', product_id }            Lifecycle, both
lead_generate  { lead_type: 'contact', product_id }            Meaningful, both
```

"What then?" `lead_generate` is the conversion. It fires to both tools, so marketing attributes it and Google Ads can bid on it. After that the lead goes to sales in HubSpot, which is a CRM handoff, not analytics. The tracking job ends at the conversion event. Everything before `lead_generate` (the widget, the category, the filter) is PostHog-only context that tells you which path led to the contact.

---

## Reference

Look these up when you need them. You don't need this section to use the doc.

### Anti-patterns

| Wrong (one event per variant) | Right (one event, a property) |
|---|---|
| `review_submit_5_star`, `review_submit_4_star` | `review_submit` + `rating` |
| `signup_email`, `signup_google` | `signup` + `signup_method` |
| `cta_click_header`, `cta_click_hero` | `cta_click` + `cta_position` |
| `reengage_after_30d`, `reengage_after_7d` | `session_reengage` + `days_since_last_session` |
| `subscribe_monthly`, `subscribe_yearly` | `subscribe` + `billing_period` |
| `share_twitter`, `share_linkedin` | `share` + `share_channel` |
| one event per page type | `page_view` + `page_type` |

### Hard limits

| | GA4 | PostHog |
|---|---|---|
| Event name max length | 40 chars | keep to 40 for parity |
| Allowed characters | `[a-zA-Z0-9_]`, starts with a letter | same recommended |
| Max distinct event names | 500 per property. Past it, GA4 stops recording new names | no hard cap |
| Max properties per event | 25 | no hard cap |
| Property value max length | 100 chars (500 in GA4 360) | no hard cap |
| Reserved | `ga_`, `google_`, `firebase_` | `$` |

The 500-name cap is the main reason we don't make one event per variant.

### Why two tools

GA4 owns ad attribution. Google Ads bids well only on conversions reported in GA4, and the bidding integration exists only for GA4. There's no real substitute. PostHog owns product behaviour: funnels, retention, B2B group analytics, session replay, feature flags, experiments. GA4 does none of these well: it samples at scale, has no B2B account concept, no experiment exposure, no replay. Each does a job the other can't.

We don't send everything to both because:

- GA4's 500-name cap fills up and new names stop recording.
- GA4 caps at 25 properties per event. PostHog events often carry more, so mirrored events lose detail.
- Doubled work: every shared event needs setup, consent, and tests in both.
- Right-to-erasure doubles, since every deletion request hits two tools.

### Why object first

Three reasons. Sorting groups related events (`review_*`, `cart_*`), which is how analysts scan. It matches what PostHog (`$pageview`, `survey_shown`) and GA4 (`page_view`, `session_start`) already do. And it mirrors the property convention. The cost is small: a few Google-recommended names are verb first (`sign_up`), so we map ours to theirs once in the GA4 UI.

### Drift

Product metric: PostHog is the source of truth. Paid-ad metric: GA4 is. No metric has two sources of truth. On shared events: within 5% is healthy, 5 to 10% is worth a glance but usually fine (high-volume engagement events naturally run higher), over 10% is a bug worth investigating. GA4 samples and PostHog stores raw, so they never match exactly.
