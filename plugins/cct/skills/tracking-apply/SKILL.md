---
name: tracking-apply
description: Adds the analytics a feature needs: from a feature, plan or success measure, decides the events and properties (which tool, new event or property), adds them to the central tracking registry, wires call sites through the typed helper, adds tests (right event fired, nothing before consent), regenerates the tracking plan and names the success-measure query. Outputs an events table for a tech plan. Use for "add tracking", "instrument this", "what should we track", "new event", "success measure". Skip when no registry exists yet (tracking-setup) or for a read-only check (tracking-audit).
allowed-tools: "Read Grep Glob Edit Write Bash(git *) Bash(gh *) Bash(pnpm *) Bash(npm *) Bash(npx *) Bash(yarn *) Bash(bun *) Bash(uv *) Bash(python3 *)"
user_invocable: true
metadata:
  version: 2.0.0
---

# Tracking apply

Adds the tracking one change needs, through the project's central tracking library. Events are defined in the registry, never at the call site.

Read first:

- `../tracking-setup/references/conventions.md`: the two decisions, naming, categories, properties, identity, privacy, lifecycle, limits.
- `../tracking-setup/references/library.md`: the registry fields, the helper, the test adapter.
- The project's registry, its tracking doc (`docs/tracking.md`) and the generated plan (`docs/tracking-plan.md`).

No registry yet (direct SDK calls, or no tracking at all)? Run `cct:tracking-setup` first and come back.

## 1. Start from the question

Take the input: a feature description, a plan, a PR, or a success measure (in the SDLC, the one in `intent.md`). Write down, in plain words:

- the success measure: the number that says this change worked, and over what window;
- the questions behind it: what someone will ask of the data (where do people drop off, which option wins, does it bring people back).

No question, no event. A change with no success measure and no question gets no new events; say so in one line.

## 2. Reuse before inventing

Search the registry for each question. An existing event often answers it with one new property (Decision 2). Funnel steps that already exist (`checkout_start`, `purchase`) are reused, never duplicated under a feature-specific name.

## 3. Decide each event

For every candidate, in order (`conventions.md`, "Checks / While designing"):

1. **The question it answers.** One sentence. It goes in the registry.
2. **Category, and so the tool** (Decision 1): lifecycle, acquisition, meaningful action go to both; engagement, retention, friction to product analytics only.
3. **New event or property** (Decision 2). A variant is a property. A detail-page view is `page_view` + `page_type`.
4. **Name**: `object_verb`, present tense, `snake_case`, no values, 40 characters or fewer.
5. **Properties**: `object_adjective`, `is_`/`has_`, units in the name, a fixed set of values wherever possible, IDs not names. No free text, no email, no token. 25 or fewer if it goes to marketing.
6. **Surface** from the recorded list; propose a new value in the same change if none fits.
7. **Client or server**: revenue and state the database already knows go server-side.
8. **Marketing name** if it has a recommended equivalent (`sign_up`, `generate_lead`, `purchase`).

## 4. The events table

This is the output for a tech plan (`plan.md` in the SDLC, stage 4) and the PR body. Keep it short:

```markdown
### Tracking

Success measure: checkout conversion (purchase / checkout_start), 14 days after release, by payment_method.

| Event | New? | Category | Goes to | Side | Properties | Fired when | Question |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `checkout_start` | reused | engagement | product | client | + `has_saved_card` | checkout page opens with items | Do saved cards start more checkouts? |
| `purchase` | reused | meaningful_action | both | server | (none new) | payment webhook confirms | Did conversion move? |
| `payment_method_select` | new | engagement | product | client | `payment_method` | a method is picked | Which methods do people try first? |

Query: see "Success-measure query" below.
```

In the SDLC this table is the whole of the tracking work at the plan stage; the build stage does steps 5 to 8.

## 5. Add to the registry

One entry per new event, with every field: `name`, `category`, `capture`, `owner`, `status: "proposed"`, `question`, `since` (the next release version), `props` with their kinds, `optional`, `marketingName` when it applies. A new property on an existing event goes into that entry's `props`.

A rename is never an edit of the old name. Add the new entry, mark the old one `deprecated` with `replacedBy` and a sunset 30 or more days out; the library dual-fires both until then. Note the dashboards to repoint in the tracking doc's migration table.

New surface or page type: add it to the lists in the library in the same change.

## 6. Wire the call sites

```ts
track(events.paymentMethodSelect, { surface: "checkout", payment_method: "paypal" });
```

- Import from the library only. No SDK import, no `gtag`, no `dataLayer.push`, no string literal or variable as the event.
- Fire on the user's action or the confirmed state change, not on render. Fire once: guard effects that run twice in development.
- Server events go through `trackServer` where the state changes (the webhook, the job), never also from the client.
- Never pass `app`, the category, `experiment_variant` or identity; the library adds them.

## 7. Tests

With the memory adapter (`library.md`, "Tests"):

- one test per new call site: the action fires the right event with the expected properties, once;
- if the change touches a flow that runs before consent (landing, sign-up), a test that nothing is sent before consent;
- the registry test passes with the new entries (naming, fields, limits, unique names).

For E2E coverage, assert on the memory adapter or on intercepted requests to the analytics hosts, in the spec that already covers the flow.

## 8. Regenerate and check

1. Run the plan generator (`tracking:plan` or the project's equivalent) and commit `docs/tracking-plan.md` with the change.
2. Run the project's typecheck, lint and tests.
3. Run `cct:tracking-audit` on the diff when the change adds more than a couple of events.

## 9. Success-measure query

Name how the measure is read after release, so the outcome step can run it unchanged. For PostHog, a HogQL query that `cct:posthog-manage` can run:

```sql
SELECT
  countIf(event = 'purchase') / nullIf(countIf(event = 'checkout_start'), 0) AS conversion
FROM events
WHERE event IN ('checkout_start', 'purchase')
  AND timestamp >= toDateTime('2026-01-15') AND timestamp < toDateTime('2026-01-29')
```

Or name the saved insight to create (type, events, breakdown, window). For a funnel, give the steps in order and the conversion window.

## Output

- The events table (for the plan or the PR).
- Registry entries, call sites, tests, the regenerated tracking plan.
- The success-measure query or insight definition.
- Anything left open, in one line each (a new surface to agree, a dashboard to repoint).
