---
name: tracking-apply
description: Adds the analytics one change needs through the project's central tracking library - from a feature, plan or success measure decides each event (which tool, new event or property), adds registry entries, wires call sites through the typed helper, adds tests, regenerates the tracking plan and defines the success-measure funnel or query. Outputs an events table for a tech plan. Use for "add tracking", "instrument this", "what should we track", "new event", "success measure". Skip when there is no library yet or it is broken (tracking-setup), or for a read-only check (tracking-audit).
allowed-tools: "Read Grep Glob Edit Write Bash(git *) Bash(gh *) Bash(pnpm *) Bash(npm *) Bash(npx *) Bash(yarn *) Bash(bun *) Bash(uv *) Bash(python3 *)"
user_invocable: true
metadata:
  version: 2.1.0
---

# Tracking apply

Adds the tracking one change needs, through the project's central tracking library. Events are defined in the registry, never at the call site.

Read first:

- `../tracking-setup/references/conventions.md`: the two decisions, naming, categories, properties, identity, privacy, lifecycle, limits.
- `../tracking-setup/references/library.md`: the registry fields, the helper, the tests.
- The project's registry, its tracking doc (`docs/tracking.md`) and the generated plan (`docs/tracking-plan.md`).

No registry yet, direct SDK calls, or a tracking doc with no registry owner? Run `cct:tracking-setup` first and come back.

## 1. Start from the question

Take the input: a feature description, a plan, a PR, or a success measure (in the SDLC, the one in `intent.md`). Write down, in plain words:

- the success measure: the number that says this change worked, its unit (people or events), its window, and the release date it is measured from;
- the questions behind it: what someone will ask of the data (where do people drop off, which option wins, does it bring people back).

No question, no event. A change with no success measure and no question gets no new events; say so in one line.

## 2. Reuse before inventing

Search the registry and the generated plan for each question. An existing event often answers it with one new property (Decision 2). Funnel steps that already exist (`checkout_start`, `purchase`) are reused, never duplicated under a feature-specific name.

## 3. Decide each event

For every candidate, in order (`conventions.md`, "Checks / While designing"):

1. **The question it answers.** One sentence. It goes in the registry.
2. **Category, and so the tool** (Decision 1): lifecycle, acquisition, meaningful action go to both; engagement, retention, friction to product analytics only. Only `cta_click` chooses its category per call.
3. **New event or property** (Decision 2). A variant is a property. A detail-page view is `page_view` + `page_type`.
4. **Name**: `object_verb`, present tense, `snake_case`, no values, 40 characters or fewer, not a GA4 reserved name.
5. **Properties**: `object_adjective`, `is_`/`has_`, units in the name, a fixed set of values wherever possible, IDs not names. No free text, no email, no token. 25 or fewer, with context, if it goes to marketing.
6. **Surface** from the recorded list; propose a new value in the same change if none fits.
7. **Trigger**: the moment it fires, in words for `firedWhen` ("the payment webhook confirms the charge"), and which apps fire it.
8. **Client or server**: revenue and state the database already knows go server-side.
9. **Marketing name and parameters** if it has a recommended equivalent (`sign_up`, `generate_lead`, `purchase` with its ecommerce parameters), and whether the marketing analytics owner must mark it as a key event.

## 4. The events table

The output for a tech plan (`plan.md` in the SDLC, stage 4) and the PR body. Keep it short:

```markdown
### Tracking

Success measure: checkout conversion. People who start checkout in the 28 days after release and `purchase` within 14 days of starting; ordered funnel, unique people, broken down by `has_saved_card` (a property of the first step).

| Event | New? | Category | Goes to | Side | Properties | Fired when | Question |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `checkout_start` | reused | engagement | product | client | + `has_saved_card` | checkout page opens with items | Do saved cards start more checkouts? |
| `purchase` | reused | meaningful_action | both | server | (none new) | payment webhook confirms | Did conversion move? |
| `payment_method_select` | new | engagement | product | client | `payment_method` | a method is picked | Which methods do people try first? |
```

In the SDLC this table is the whole of the tracking work at the plan stage; the build stage does steps 5 to 8.

## 5. Add to the registry

One entry per new event, with every field: `name`, `category`, `capture`, `owner`, `status: "proposed"`, `question`, `firedWhen`, `apps` when not every app fires it, `since` (the next release version), `props` with their kinds, `optional`, `needs` for per-type IDs, and `marketingName` / `marketingParams` when they apply. A new property on an existing event goes into that entry's `props`.

A rename is never an edit of the old name. Add the new entry, mark the old one `deprecated` with `replacedBy`, `deprecatedOn`, a `sunset` 30 or more days later and a `toLegacy` mapping; the library re-sends the old name to product analytics until then. Note the dashboards to repoint in the tracking doc's migration table, and tell the marketing analytics owner to move key events to the new name on release day.

New surface or page type: add it to the lists in the library in the same change.

Check: the typecheck and `registry.test.ts` pass.

## 6. Wire the call sites

```ts
track(events.paymentMethodSelect, { surface: "checkout", payment_method: "paypal" });
await trackServer(ctx, events.purchase, { order_id, value, currency, items, payment_method, is_first_order }); // server: ctx carries user, consent, GA IDs, idempotency key
```

- Import from the library only. No SDK import, no `gtag`, no `dataLayer.push`, no string or variable as the event.
- Fire on the user's action or the confirmed state change, not on render. Fire once: guard effects that run twice in development.
- Server events go through `trackServer` where the state changes (the webhook, the job), never also from the client.
- Never pass `app`, `experiment_variant` or identity; pass the category only for `cta_click`.
- Mobile and server-only projects use their generated bindings with the same rules (`tracking-setup`, steps 5 and 6).

Check: lint passes, with no restricted-syntax hit.

## 7. Tests

With the memory adapter (`library.md`, "Tests"):

- one test per new call site: the action fires the right event with the expected properties, once (`testLog`, cleared in `beforeEach`);
- if the change touches a flow that runs before consent (landing, sign-up), a test on a fresh tracker that nothing is sent before consent;
- a server event: two deliveries of the same webhook send it once.

For E2E coverage, assert on the memory adapter or on intercepted requests to the analytics hosts, in the spec that already covers the flow.

## 8. Regenerate and check

1. Run the plan generator (`tracking:plan`) and commit `docs/tracking-plan.md` with the change.
2. Run the project's typecheck, lint and tests.
3. Run `cct:tracking-audit` on the diff when the change adds more than a couple of events.

## 9. Success-measure query

Name how the measure is read after release, so the outcome step can run it unchanged. A conversion is a funnel of people, in order, within a window, never one event count divided by another (that can pass 100% and moves when instrumentation changes). With `cct:posthog-manage`:

```bash
ph funnel checkout_start purchase --from 2026-01-15 --to 2026-02-12 --window 14 --breakdown has_saved_card --table
ph insights create funnel checkout_start purchase --from 2026-01-15 --to 2026-02-12 --window 14 --breakdown has_saved_card --name "Checkout conversion after new checkout"
```

Break down by a property of the first step: a property only the last step has splits the converters, not the people who started. Read it no earlier than one window after `--to` (here, 2026-02-26), and compare it with the same funnel over the same length of time before the release. For a count rather than a conversion, name the event, the unit (unique people or events) and the window.

## Output

- The events table (for the plan or the PR).
- Registry entries, call sites, tests, the regenerated tracking plan.
- The success-measure funnel or query.
- Anything left open, in one line each (a new surface to agree, a dashboard to repoint, a key event for marketing to mark).
