# Event tracking conventions

The rules every analytics event follows: what it is called, what it carries, where it goes and who may change it. A number should mean the same thing in every tool, and an event name should still make sense to someone a year from now.

This is a reference. Find the rule you need, apply it, move on. The events that exist live in the project's registry (`library.md`); the generated tracking plan is the readable copy, with each event's question, trigger, coverage per app, owner and status.

**Reading path.** PMs, designers and marketers need only the first two sections and the generated tracking plan. Engineers and analysts use the rest as a reference.

**Before the first event ships, name the registry owner** (see "Who owns what"). Without one, nobody gates new events against this document and the lifecycle below is a plan, not a control.

Shared by `tracking-library-run`, `tracking-apply` and `tracking-audit`. Where a rule says "the project records", the answer goes in the project's tracking doc (`docs/tracking.md`), written by `tracking-library-run`.

## The whole idea in five points

1. **Events live in one central library, like an i18n catalogue.** One typed registry holds every event. Call sites pass a registry key to one helper and never name a tool, never call an analytics SDK.
2. **Two kinds of tool, on purpose.** Marketing analytics (GA4 in the examples) does ad attribution: it tells the ad platforms what to bid on. Product analytics (PostHog in the examples) does product behaviour: funnels, retention, experiments, session replay.
3. **Route by category, not by event.** The event's category in the registry decides where it goes. Nobody picks a tool at the call site.
4. **Name things the same way every time.** Lowercase `snake_case`, object then verb (`review_submit`), one name everywhere.
5. **Keep private data out.** No personal names, emails, free text or tokens. Only IDs, numbers, bands and fixed labels.

## The two decisions you actually make

### Decision 1: which tool does the event go to?

You pick the category; the category picks the tools. Work down the list and stop at the first match.

| Ask | Category | Goes to |
| --- | --- | --- |
| Is it a session or page-frame event (`page_view`, `consent_update`)? | `lifecycle` | both |
| Is it the moment an anonymous visitor becomes known, and could marketing tie it to an ad (`signup`, `lead_generate`)? | `acquisition` | both |
| Would a leadership dashboard report it, or would marketing bid on it? Money, pipeline, first value, high intent (`purchase`, `demo_book`, `note_create`) | `meaningful_action` | both |
| A smaller step toward one of those (`filter_apply`, `cart_item_add`) | `engagement` | product only |
| People returning or adopting a feature (`session_reengage`, `notification_click`) | `retention` | product only |
| Where people get stuck (`login_fail`, `form_submit_fail`) | `friction` | product only |

Every event is in exactly one category. Lifecycle reaches both tools, identity and consent included. Sanity check: for any key KPI you can point at one event, or a small set, that produces it. Business areas (money, pipeline, core value, discovery, onboarding) only group meaningful actions for reading; each is still `meaningful_action`.

**The category lives in the registry, not at the call site.** This is a deliberate choice over setting the category on each call: one reviewed line per event, and no call site can misroute it.

**One exception, and only one: `cta_click`.** It is a meaningful action for a high-intent button and engagement for the rest, so its registry entry lists both and the call passes one (`{ category: "meaningful_action" }`). The registry test allows one such event.

### Decision 2: new event, or a property on an existing one?

| Situation | Do this |
| --- | --- |
| A different action, or a funnel step with its own drop-off, dashboard or experiment | **New event** |
| The same action, only the kind differs (rating, method, channel, threshold, plan) | **Property** |

Gut check: you want to count it separately. Is that because it is a different action, or the same action with a filter? Filter means property. Funnel steps are not variants: `checkout_start`, `payment_info_add` and `purchase` each have their own drop-off. A detail-page view is never its own event: it is `page_view` with a `page_type`.

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
| No versions in the name | `note_export`, never `note_export_v2`; a replacement gets a new honest name and the old one is deprecated |
| One name in code and in every tool | the registry is the only place a name is written; a marketing alias (below) is mapped in the library |
| A registry key, never a string or a variable | `track(events.reviewSubmit, ...)`, never `track("review_submit", ...)` or `track(name, ...)` |

Why object first: sorting groups related events (`cart_*`, `note_*`), it matches what the tools already do (`survey_shown`, `session_start`), and it mirrors the property rule. The cost is that a few recommended marketing names are verb first (`sign_up`); the library maps those once.

Never use a prefix GA4 reserves (`_`, `ga_`, `google_`, `firebase_`, `gtag.`) or PostHog's `$`, a GA4 reserved event name (`error`, `click`, `scroll`, `form_start`, `form_submit`, `first_visit`, `session_start`, `user_engagement` and the rest of Google's list[^reserved]), or a `category:name` prefix (the colon breaks GA4). `page_view` is reserved too, but it is Google's own manual page-view event and fits `object_verb`, so it is kept with automatic page views off. The registry test holds the full list.

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
| Timestamps end in `_at`, UTC; dates in `_date` | `created_at`, `signup_date` |
| Durations and amounts name the unit | `time_on_step_seconds`, `value_eur` |
| A fixed set of values wherever possible | `signup_method`: `email`, `google`, `magic_link` |
| IDs, never names or full values | `product_id`, then join the name in the warehouse |

## Properties you will reuse

| Property | Set by | Reaches | Values |
| --- | --- | --- | --- |
| `app` | the library | both | the deployed app (`shop-web`, `notes-ios`); the list is in the tracking doc |
| `surface` | the call site, required outside lifecycle | both | the functional zone of the UI: `auth`, `onboarding`, `search`, `filter`, `nav`, `cta`, `billing`, `checkout`, `editor`, `profile`, `dashboard`; the project's list is in the library |
| `release` | the library, optional | both | the app version, for spotting broken releases |
| `experiment_variant` | the library, during an experiment | product | the variant the person sees |
| identity: `user_id`, `account_type`, `company_id`, `plan_tier` | the library's `identify` | both, as person and group properties | see Identity |

`app`, `surface` and `account_type` answer three separate questions and never overlap: which deployed app, which zone of it, and who the person is. "A seller edited a listing in the editor of the shop's web app" is `app: shop-web`, `account_type: seller`, `surface: editor`, never one packed field.

Use the canonical names below; do not invent variants. The exact values per product live in the registry, so this list does not go stale when a plan is renamed.

| Property | Used on | Values |
| --- | --- | --- |
| `product_id`, `order_id`, `note_id`, `company_id` | per-entity events, identity | IDs |
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
| `value`, `currency`, `items` | `purchase` | a number, an ISO 4217 code, the items bought (ID, price, quantity) |

**Role, plan and purchases are three different things.** Role (`account_type`): who the person is, set at identify. Standing plan (`plan_tier`): what the account subscribes to, a group property, only where plans exist. One-time purchase: a `purchase` event, never a standing property.

## page_view and page types

`page_view` is one event for every page. One router hook in the library fires it after every navigation, client-side ones included, and the tools' automatic page views are off so nothing is counted twice. Each fire carries `page_type` plus the IDs that page type needs; the type check and the guard require those IDs and refuse the others. Leave out what does not apply; never send `null`.

| `page_type` | Needs |
| --- | --- |
| `home`, `auth`, `dashboard`, `settings`, `checkout`, `other` | nothing (checkout steps are events) |
| `product` | `product_id` |
| `category` | `category_id` |
| `article` | `article_id` |

The project's page types live in the registry. Adding one is a one-line change there, never a new event like `product_view`. Two `page_view`s already show which detail pages draw traffic; add a selection event (`content_select`) only to rank interest within a list.

## Identity

The library's `identify` sets the current person in every granted tool. It runs when the session loads, right after login, and again when the role, plan or company changes; `reset` runs at logout. Call sites never do either.

```ts
posthog.identify(user_id, { account_type })         // links this browser's earlier anonymous events to the person
posthog.group(groupType, company_id, { plan_tier }) // B2B only; groupType is the project's (company, workspace, account)
```

| Call | What it does |
| --- | --- |
| `identify` | "This browser is now user X." Earlier anonymous events on it are linked to the person too.[^identify] |
| `group` | "User X belongs to company Y." Needed for B2B funnels and group experiments. Call `resetGroups` when the person leaves a company. |
| `reset` | Forgets the person on this device, so the next one starts anonymous.[^identify] |
| `alias` | Not part of login. Only to join two IDs the tool cannot link itself (a backend ID and a frontend ID for one person); the library owns any such call. |

Identify before group: a group call needs the person. Identify before the first experiment exposure in the session, so the exposure belongs to the person. A different user ID resets first (an account switch), so nothing of the old account carries over.

Product analytics creates person profiles for identified users only (PostHog: `person_profiles: "identified_only"`); a server event about nobody in particular sends `$process_person_profile: false`. **The marketing tool gets the same identity:** GA4's User-ID is the same opaque `user_id`, set to `null` at logout[^userid], with user properties `account_type`, `company_id`, `plan_tier`, under consent. Never an email, a name or a company name: a company label can be a person's name (a sole trader). Identity properties describe the person now; if an analysis needs a value at the time of an event (the plan when they bought), that event carries it as its own property.

**A successful login is not an event by default; a failed one is.** Identified sessions are not a login count: `identify` also runs when a session is restored. When the question is how often people log in (security, a login-frequency KPI), add `login` as a `retention` event fired by the auth handler on a successful sign-in. `login_fail` has no identity to attach and diagnoses drop-off, so it is `friction`.

| Scope | Describes | Set with |
| --- | --- | --- |
| Event | the event | its registry properties |
| Person | the user, across events | `identify(id, { ... })`, `$set`, `$set_once` |
| Group | the company | `group(groupType, id, { ... })` |

`$set` overwrites: use it for things that change (`plan_tier`). `$set_once` sets a key only if it was never set: use it for things that never change (`signup_date`, `initial_referrer`). Both follow the order the tool ingests events, not their timestamps: the first event ingested claims a `$set_once` key, so a later backfill of older events cannot correct it, and a late event can overwrite a `$set` value.[^props]

## Marketing names and ecommerce

GA4 has recommended event names. Keep the `object_verb` name in the registry and give the entry a `marketingName`; the library sends that name to the marketing tool and the canonical name everywhere else. This is a deliberate choice over mapping names in the GA4 admin UI: the mapping is versioned, reviewed and tested with the registry. Two registry events never map to one marketing name.

| Registry name | GA4 name | What it makes possible |
| --- | --- | --- |
| `signup` | `sign_up` | a key event you can mark and import into the ad platform |
| `lead_generate` | `generate_lead` | the lead reports; a key event |
| `subscribe`, `share`, `search`, `page_view` | the same | engagement and site-search reports |
| `content_select` | `select_content` | content reports |
| `checkout_start` | `begin_checkout` | the ecommerce funnel, when it goes to marketing (a recorded exception) |
| `purchase` | `purchase` | revenue and the purchase conversion, with the parameters below |

The name alone turns nothing on. Marking an event as a key event in GA4 and importing it into the ad platform are manual steps in those tools; `tracking-library-run` records who does them.

**Count-only or ecommerce.** By default the cart and checkout steps are engagement (product only) and only `purchase` reaches marketing. A conversion count needs nothing more. Revenue and ecommerce reports need GA4's parameters on `purchase`: `transaction_id`, a numeric `value`, `currency` and `items` (each with `item_id`, `price`, `quantity`)[^purchase]; the registry entry carries them through `marketingParams`, and a band such as `order_value_band` cannot produce revenue. Sending the earlier steps to marketing is a recorded exception with their own recommended parameters.

## Hard limits

Vendor limits, from GA4's documentation[^limits][^dims][^reserved], and the project budgets this document adds.

| | GA4 | PostHog |
| --- | --- | --- |
| Event and parameter name | 40 characters, starts with a letter, letters, digits and `_` | the same, as a project rule |
| Distinct event names | 500 per app user on app streams; no limit on web streams | no hard cap |
| Parameters per event | 25 | no hard cap |
| Parameter value | 100 characters (`page_title` 300, `page_referrer` 420, `page_location` 1000) | no hard cap |
| User properties | 25; names 24 characters, values 36 | no hard cap |
| User-ID | 256 characters | no hard cap |
| Custom dimensions | 50 event-scoped, 25 user-scoped (360: 125 and 100); a parameter shows in reports only once registered; predefined parameters need no registration | not needed |
| Reserved | prefixes `_`, `ga_`, `google_`, `firebase_`, `gtag.`; event names per platform; parameter names such as `user_id`, `session_id`, `currency` (allowed on ecommerce events); user property names such as `first_open_time` | `$` prefix |

The project budget: keep distinct event names well under 500 on web too, because every name routed to marketing also costs a custom dimension per parameter and setup time. The registry test checks each marketing event as GA4 receives it, before it ships.

## Client side or server side

Default: the browser, through the library. Move an event to the server when:

- it is revenue or a state change the database already knows (`purchase`, `subscribe`, `subscription_cancel`): the server is the truth and ad blockers cannot drop it;
- it happens without a browser (webhooks, jobs, emails, an API client);
- measured ad-blocker loss on a key event passes about 10% against billing or auth records.

A server event uses the same registry entry with `capture: "server"` and `trackServer`, which takes a context with:

- the same opaque `user_id`, so identity stitches;
- the consent the user gave in the browser, stored with the user or the order and checked before sending;
- the GA4 `client_id` and `session_id`, read from the `_ga` cookies of the request that started the action and stored with it; the Measurement Protocol needs `client_id` (or `app_instance_id` for an app) to attribute the event[^mp];
- when it happened (`occurredAt`), within GA4's 72-hour backdating window;
- an idempotency key, recorded in the same transaction as the state change, so a retried webhook sends nothing twice. As a second line, the same key gives PostHog a stable event UUID[^dedup] and GA4 drops a repeated `transaction_id` from the same user on web streams[^txn].

Never fire the same event from both sides.

## Consent and privacy

### Never put private data in a property value

| Use | Example |
| --- | --- |
| Internal ID | `user_id: "a7b3f1..."` |
| Company ID; a company domain only where the project records that its accounts are organisations | `company_id: "c_42"` |
| Bands, numbers and fixed labels | `order_value_band: "25-100"`, `value: 59.9`, `country_code: "DE"` |
| A hashed email (SHA-256 with a project salt), only when a join truly needs it, with its purpose and destination recorded. It is pseudonymous, still personal data, not anonymous | `email_hash: "e3b0..."` |

| Never send | Instead |
| --- | --- |
| Email, a person's name, phone number | an ID |
| Postal address, precise location | country only |
| Card or bank details | leave to the payment provider |
| Free text (a note body, a search query, an error message from user input) | a derived number (`note_length_chars`) or a fixed value (`error_type`) |
| Tokens, session IDs, magic-link codes, URLs with query strings | leave out; strip query strings from URLs |

The library enforces this: each event allowlists its properties and their kinds; the guard refuses unknown keys, nested objects, `null`, emails, tokens and strings over 100 characters, and checks identity and context values the same way.

**IP addresses** are the tools' business, and neither discards them by itself. PostHog stores the client IP with each event unless the project turns on "Discard client IP data"[^ip]; GA4 does not log or store IP addresses[^gaip]. The project records its PostHog setting and checks it in the project settings.

### No event before consent

The library asks the consent state before every send. The default, and the meaning of "nothing before consent" here: no analytics SDK is initialised and no tag is loaded until its destination is granted, so no request at all leaves the browser before then (Google calls this basic consent mode[^consent]). Events before consent are dropped, or held in memory and sent once granted, per the project's choice. Logout drops what is held. On withdrawal the library opts the tool out and clears what it stored. No app writes its own consent check.

Both vendors offer a looser mode: PostHog recommends loading the SDK opted out (`opt_out_capturing_by_default: true`) so it can count visitors who never answer the banner[^phconsent]; GA4's advanced consent mode sends cookieless pings while consent is denied[^consent]. A project may choose either, records it, and then says "no tracking before consent" instead of "nothing leaves the browser".

### Decisions the project records

| Setting | Recommended default |
| --- | --- |
| Product analytics region and IP setting | the region the users' law expects (EU cloud for EU users); "Discard client IP data" on unless a stated need |
| Marketing analytics retention | what the analysis and the legal basis need; standard GA4 offers 2 or 14 months |
| Product analytics retention | the plan's actual window, written down |
| Google Signals (cross-device ad data) | off unless a stated need justifies it |
| Consent mechanism | which banner or framework, and which purposes map to which destination and which Google consent types |
| Before-consent behaviour | strict (default) or the vendor's looser mode; hold in memory or drop |
| Right to erasure | how a deletion request reaches each tool; keeping only IDs and bands makes it one mapping |

## Who owns what

Roles, not people. The tracking doc names a person or team for each role; on a small team one person holds several. A decision goes to the role that owns it, not to whoever is nearest.

| Role | Owns | Does not own |
| --- | --- | --- |
| **Product owner** | what to track: the question in plain language, the success measure | names, properties, category |
| **Engineer** | how to track: turns the question into events per this doc, picks category and surface, reuses existing events, proposes tracking when a spec forgets it | approving cross-feature registry changes |
| **Registry owner** | the registry: reviews every new or changed entry, runs the lifecycle, the deprecation window and the drift check | per-feature event design |
| **Library owner** | the library: routing, consent, identity, privacy guard, adapters | the business meaning of an event |
| **Conventions owner** | changes to this document and to routing | day-to-day registry work |
| **Marketing analytics owner** | key events and ad-platform imports in the marketing tools | event design |

The registry owner is a prerequisite, not a nice-to-have: `tracking-library-run` does not ship events until the tracking doc names one, and the registry file has that person or team as its code owner. Talk tracking through when the spec is written, not at review time.

## Lifecycle of an event

The state lives in the registry and is mirrored in the product-analytics tool's event definitions, so analysts see it where they work.

| State | Meaning | In the product tool |
| --- | --- | --- |
| `proposed` | in the registry, not seen in production yet | hidden from the event picker where the tool supports it |
| `live` | firing in production, safe for dashboards | marked verified |
| `deprecated` | still firing, with a replacement, a deprecation date and a sunset | description names the replacement and the sunset |
| `removed` | no longer fired; the entry stays as a tombstone so the name is never reused | hidden |

Renaming or deleting an event silently breaks saved insights, running experiments and warehouse models. Never jump from `live` to `removed`, not even for a one-off event or an old one nobody seems to read: go through `deprecated`.

| Move | When |
| --- | --- |
| `proposed` to `live` | the first time it is seen in production |
| `live` to `deprecated` | the replacement is firing; replacement, deprecation date and sunset written in the registry |
| `deprecated` to `removed` | 30 days or more later, and nothing references it |

A rename is a new entry plus the old one marked `deprecated` with `replacedBy`, `deprecatedOn`, `sunset` and a `toLegacy` mapping of the new properties to the old shape. Until the sunset the library also sends the old name, validated against its own properties, to product analytics only, so dashboards keep working while they are repointed. The marketing tool only ever gets the new name: move the key event and the ad-platform import to it on the day the rename ships, so no conversion is counted twice.

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
- The entry has owner, category, question, trigger (`firedWhen`), since and status `proposed`.
- The call site goes through the helper with a registry key. No SDK call.
- No private data in any value. No event before consent (a test proves it).
- The generated tracking plan is up to date.
- The registry owner reviewed the registry change.

### After deploy

- Confirm it fires once, not twice. Product analytics: debug mode and the live events view. GA4: DebugView and the realtime report. Check that login stitching works.
- The first production fire moves the state to `live`.
- For events in both tools, compare counts within a day (Drift, below).

## Order of work

Each step starts only when the one before it is live in production, not merely merged.

1. **Foundation:** the registry owner named, the library with consent, the privacy guard and the router `page_view`, automatic page views off.
2. **Identity:** `identify`, `group` and `reset` wired in every app, and `consent_update`.
3. **The key conversions:** the events behind the success measures (`signup`, `purchase`, the first-value event).
4. **Funnels and the rest,** feature by feature through `tracking-apply`.
5. **Clean-up:** remove legacy events whose replacements have been live 30 days or more, and old tags.

## Drift

Product metrics: product analytics is the source of truth. Paid-ad metrics: marketing analytics is. No metric has two sources of truth.

Compare like with like before calling a gap a bug: the same event, the same consented population, the same counting unit (events or users), the same time zone and the same window. Consent, ad blockers, identity stitching and sampling make the tools differ by design. Start with a threshold of 5% as healthy and 10% as worth a look, then set the project's own from a few weeks of baseline and record it. The registry owner runs `tracking-audit` with the live comparison monthly and after every release that changes tracking.

## Examples to copy

Registry entries are in `library.md`. Call sites never pass `app`, `experiment_variant` or identity; the category only for `cta_click`.

```ts
track(events.signup, { surface: "auth", signup_method: "google", is_invited: false });            // acquisition
track(events.noteCreate, { surface: "editor", note_id, template: "blank", is_first_note: true, note_length_chars: 412 }); // derived length, never the text
track(events.sessionReengage, { surface: "nav", days_since_last_session: 30 });                   // the gap is a property
track(events.loginFail, { surface: "auth", error_type: "wrong_password" });                       // a fixed set, never the raw message
track(events.ctaClick, { surface: "cta", cta_id: "pricing_hero", cta_position: "hero" }, { category: "meaningful_action" });
```

`page_view` is fired by the library's router hook: `track(events.pageView, { page_type: "product", product_id })`. A purchase comes from the payment webhook, with the context described under "Client side or server side":

```ts
await trackServer(ctx, events.purchase, { order_id, value: 59.9, currency: "EUR", items, payment_method: "card", is_first_order: true });
```

## Journeys

There is no "abort" or "bored" event. Abandonment is the absence of the next step, measured as the drop between two events in a funnel.

### A shop: buying

```
page_view          { page_type: "product", product_id }                 lifecycle, both
cart_item_add      { product_id, quantity: 1, item_value_band }          engagement, product
cart_item_update   { product_id, quantity: 2 }                           engagement, product
checkout_start     { item_count: 2, cart_value_band }                    engagement, product
payment_info_add   { payment_method }                                    engagement, product
purchase           { order_id, value, currency, items }                  meaningful action, both (server)
```

The drop from `checkout_start` to `purchase` is checkout abandonment. "How many people had something in the cart?" is unique users with `cart_item_add` in the period; the funnel is `cart_item_add`, `checkout_start`, `purchase`; session replay shows why people stall.

### A form

```
signup_start       { signup_method }        engagement, product   on the first focus in the form, not on page load
signup             { signup_method }        acquisition, both     on success
```

The two ends are usually enough: their drop is the form's completion rate. Add a per-step event (`signup_step_complete` with `step_name`) only when the question is where inside the form people stop. Never `form_start` or `form_submit`: GA4 reserves them.

### A notes app: first value

```
signup               { signup_method }                                   acquisition, both
onboarding_complete  { onboarding_flow, time_to_complete_seconds }       meaningful action, both
note_create          { note_id, template, is_first_note }                meaningful action, both
note_share           { note_id, share_channel }                          engagement, product
session_reengage     { days_since_last_session }                         retention, product
```

`signup` to the first `note_create` is activation. The supporting steps around it (`note_share`) are product-only context about the path.

### From content to a lead

```
page_view       { page_type: "article", article_id }       lifecycle, both
cta_click       { cta_id, cta_position }                    meaningful action, both (a high-intent call to action)
filter_apply    { filter_group, filter_value }              engagement, product
lead_generate   { lead_type: "contact", product_id }        acquisition, both
```

`lead_generate` is the conversion: marketing attributes it and the ad platform can bid on it. The tracking job ends at the conversion event; what happens to the lead afterwards (the CRM, sales) is a handoff, not analytics.

## Anti-patterns

| Wrong | Right |
| --- | --- |
| `review_submit_5_star`, `signup_google`, `cta_click_header`, `subscribe_monthly`, `share_twitter` | one event + a property (`rating`, `signup_method`, `cta_position`, `billing_period`, `share_channel`) |
| one event per page type | `page_view` + `page_type` |
| `posthog.capture("Signup")` or `gtag("event", ...)` in a component | `track(events.signup, ...)` |
| the same event fired from client and server | one side, recorded in the registry |
| counting identified sessions as logins | a `login` event, if logins are the question |

## Why two tools

Marketing analytics owns ad attribution: the ad platforms bid well on the conversions they receive, and their bidding integrations are built for their own analytics. Product analytics owns product behaviour: funnels, retention, B2B groups, session replay, feature flags, experiments, which the marketing tool covers poorly (no account concept, no experiment exposure, sampling in explorations).

Not everything goes to both: every shared event costs custom dimensions, 25-parameter payloads, double setup, consent and tests, and every erasure request then reaches two tools. A project that runs only one tool still uses the categories: they keep the routing decision cheap when a second tool arrives.

[^identify]: PostHog, identifying users: https://posthog.com/docs/product-analytics/identify
[^props]: PostHog, person properties ($set, $set_once, ingestion order): https://posthog.com/docs/product-analytics/person-properties
[^ip]: PostHog, data storage and "Discard client IP data": https://posthog.com/docs/privacy/data-storage
[^phconsent]: PostHog, data collection and consent: https://posthog.com/docs/privacy/data-collection
[^dedup]: PostHog, duplicate events and the event UUID: https://posthog.com/docs/cdp/troubleshooting
[^limits]: GA4 collection limits: https://support.google.com/analytics/answer/9267744
[^reserved]: GA4 reserved names: https://support.google.com/analytics/answer/13316687
[^dims]: GA4 custom dimension limits: https://support.google.com/analytics/answer/14240153
[^purchase]: GA4 recommended events, purchase: https://developers.google.com/analytics/devguides/collection/ga4/reference/events
[^txn]: GA4 ecommerce, transaction ID de-duplication: https://support.google.com/analytics/answer/12313109
[^mp]: GA4 Measurement Protocol, sending events: https://developers.google.com/analytics/devguides/collection/protocol/ga4/sending-events
[^userid]: GA4 User-ID: https://developers.google.com/analytics/devguides/collection/ga4/user-id
[^gaip]: GA4 and IP addresses: https://support.google.com/analytics/answer/2763052
[^consent]: Google consent mode, basic and advanced: https://developers.google.com/tag-platform/security/concepts/consent-mode
