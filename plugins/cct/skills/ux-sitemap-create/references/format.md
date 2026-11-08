# The two files: sitemap.md and sitemap.json

Read by `cct:ux-sitemap-create` before writing. The markdown is for people; the JSON is for
tools (state capture, e2e, conformance) that iterate pages. Both come from the same run.

## 1. sitemap.md

Sections in this order. A mode rewrites only its own sections (see the skill's mode table).
Labels are written in every locale the app has, in the order the app lists them, separated by
" / ". A product with one locale writes one.

~~~markdown
# <Product> sitemap

## As built

Read from `<route source>` on `<branch>` at `<short sha>` (<YYYY-MM-DD>). <Locale prefix
rule: which locales, which is the default.> <Hosts, when there are several: which area answers
on which host.> "Reached from" names the ways in that exist today.

### <Area, e.g. the console>

**Navigation**, top to bottom: <items with their groups, foot items, account, sign out>.
<How it collapses on narrow screens.>

**Command menu:** <what it reaches, or "none">.

| Route | Label (<locales>) | Type | Tabs -> header primary | Reached from | Source |
|---|---|---|---|---|---|
| `/<path>` | <label / label> | list | - -> <action> | <every way in> | `<file>:<line>` |

**Redirects:** <old -> new, each with its source>.

### Error pages

| Where | What it shows | Way back |
|---|---|---|

## E-mail and external links

| Mail, notification or link | Leads to | Source |
|---|---|---|

## Proposed

**Status: proposed, <YYYY-MM-DD>.** Nothing here is accepted until a decision file in
`docs/designs/` says so. Items marked **decide** are open choices; the alternative is
named in one line.

### The principles it rests on

| Principle | What it forces here |
|---|---|

### <Area> navigation

| # | Item (<locales>) | Group | Badge | Why here |
|---|---|---|---|---|

**Gone from the navigation, and why:** <one bullet each>.

### Settings

| # | Entry (<locales>) | Route | What it holds | Header primary |
|---|---|---|---|---|

### <Area> routes

| Route | Label (<locales>) | Type | Tabs -> header primary | Reached from |
|---|---|---|---|---|

### Pages whose content changes

| Page | Change | Why |
|---|---|---|

## Changes from as built

| # | Change | Why (job story, law, owner's words, finding) | Findings |
|---|---|---|---|

## Redirects

Additive only: every old address keeps working, existing redirects stay.

| Old address | New address | Carries |
|---|---|---|

## E-mail links that change

| Mail or link | Leads to (proposed) | As built |
|---|---|---|

## Checks

<Counts by impact, then one finding per failed check in the shared finding format. Only when
the skill ran on its own; a calling skill merges them into its own report instead.>
~~~

**Writing the "Tabs -> header primary" cell.** Each tab, its count in brackets when the tab
shows one, an arrow, and its one header primary action, or "none" when the decision is that
there is none. Tabs are written in the first locale and separated by semicolons. A page without tabs writes "-" before the arrow.
A create page names the bar that commits instead. A blank after the arrow means no decision
yet, which is check SM-8.

**Writing "Reached from".** Every way in, separated by semicolons, most visible first:
navigation, a list row, a link on another page (name the page), a breadcrumb, the command menu,
a mail, a redirect, after an action (after sign-in, after create).

## 2. sitemap.json

One file, written whole each run. Unknown values are `null`, never left out, so a tool can tell
"not read" from "empty".

```json
{
  "generated": "YYYY-MM-DD",
  "source": { "stack": "next-app-router", "routeRoot": "src/app", "ref": "<sha>" },
  "locales": ["en", "de"],
  "defaultLocale": "de",
  "localePrefix": "always",
  "hosts": [{ "host": "app.example.com", "areas": ["console", "portal"] }],
  "navigation": [
    {
      "area": "console",
      "items": [
        { "label": { "en": "Invoices", "de": "Rechnungen" }, "route": "/invoices",
          "group": { "en": "Billing", "de": "Abrechnung" }, "position": "body", "status": "as-built" }
      ],
      "settings": [{ "label": { "en": "Team", "de": "Team" }, "route": "/settings/team" }],
      "commandMenu": ["/invoices", "/customers", "/settings/team"],
      "account": { "route": "/account", "position": "foot" },
      "signOut": { "position": "foot" }
    }
  ],
  "pages": [],
  "redirects": [
    { "from": "/clients/[id]", "to": "/customers/[id]", "status": "proposed",
      "carries": ["id"], "source": null }
  ],
  "links": [
    { "kind": "email", "name": "invoice sent", "to": "/invoices/[id]",
      "source": "src/emails/invoice-sent.tsx:42", "status": "as-built" }
  ]
}
```

### A page object

| Key | Type | Notes |
|---|---|---|
| `id` | string | stable, from area and route: `console.invoices.record` |
| `area` | string | the navigation area it belongs to |
| `route` | string | without the locale prefix; params in the router's own bracket form normalised to `[name]` |
| `params` | array of `{ name, kind }` | path params; `kind` is `id`, `slug`, `token` or `catch-all` |
| `query` | array of `{ name, kind, values }` | `kind`: `search`, `filter`, `sort`, `view`, `tab`, `page`, `open`, `prefill`; `values` when the set is closed, else `null` |
| `labels` | object, locale to string | as shown on screen; a dynamic title is `"{name}"` |
| `type` | string | `home`, `list`, `record`, `create`, `edit`, `settings`, `account`, `public`, `auth`, `error`, `embed` |
| `purpose` | string | the job, one line |
| `roles` | array of strings | who uses it |
| `tabs` | array of `{ id, label, route, count, primary }` | `count` true or false; `primary` is a label object, the string `"none"` (decided: no primary action), or `null` (not decided: check SM-8) |
| `sections` | array of label objects | headed sections in order |
| `views` | array of `{ label, query }` | named view tabs and saved filters, with the query string each sets |
| `states` | array of strings | states worth capturing: `empty`, `loading`, `error`, `not-found`, and the product's own |
| `reachedFrom` | array of `{ kind, from, detail, source }` | `kind`: `navigation`, `link`, `row`, `breadcrumb`, `command-menu`, `email`, `notification`, `redirect`, `external`, `after-action` |
| `breadcrumb` | array of `{ label, route }` | where the object lives |
| `back` | string or null | the Back target route |
| `access` | `{ roles, host, public }` | |
| `inboundLinks` | array of link ids or objects | mails, notifications, embeds landing here |
| `status` | string | `as-built`, `proposed` (not built), `removed` (built; the proposal removes it, see `redirectTo`) |
| `redirectTo` | string or null | for `removed` |
| `proposed` | object or null | for an `as-built` page the proposal changes: only the keys that change, same shapes |
| `decide` | string or null | an open choice: the alternative in one line |
| `source` | string or null | `file:line` for every as-built page; `null` only for `proposed` |
| `assumptions` | array of strings | every value that was inferred, not read |

A tool that captures states iterates `pages` where `status` is not `proposed`, builds each URL
from `route`, a test record for each param, and each entry of `views`, and captures each of
`states`.

## 3. Example from a product

Generalised; names changed. One record page in the markdown, then the same page in the JSON.

| Route | Label (EN / DE) | Type | Tabs -> header primary | Reached from |
|---|---|---|---|---|
| `/invoices/[id]` | the invoice number | record | Overview -> Send; Payments (n) -> Record payment; History -> none | a list row; a customer's Invoices tab; the "invoice overdue" mail; command menu by number |

```json
{
  "id": "console.invoices.record",
  "area": "console",
  "route": "/invoices/[id]",
  "params": [{ "name": "id", "kind": "id" }],
  "query": [{ "name": "tab", "kind": "tab", "values": ["overview", "payments", "history"] }],
  "labels": { "en": "{number}", "de": "{number}" },
  "type": "record",
  "purpose": "See one invoice, send it, and record what was paid",
  "roles": ["accountant"],
  "tabs": [
    { "id": "overview", "label": { "en": "Overview", "de": "Uebersicht" }, "route": "/invoices/[id]", "count": false, "primary": { "en": "Send", "de": "Senden" } },
    { "id": "payments", "label": { "en": "Payments", "de": "Zahlungen" }, "route": "/invoices/[id]?tab=payments", "count": true, "primary": { "en": "Record payment", "de": "Zahlung erfassen" } },
    { "id": "history", "label": { "en": "History", "de": "Verlauf" }, "route": "/invoices/[id]?tab=history", "count": false, "primary": "none" }
  ],
  "sections": [],
  "views": [],
  "states": ["loading", "not-found", "draft", "paid"],
  "reachedFrom": [
    { "kind": "row", "from": "/invoices", "detail": "list row", "source": "src/app/invoices/table.tsx:88" },
    { "kind": "email", "from": null, "detail": "invoice overdue", "source": "src/emails/overdue.tsx:31" }
  ],
  "breadcrumb": [{ "label": { "en": "Invoices", "de": "Rechnungen" }, "route": "/invoices" }],
  "back": "/invoices",
  "access": { "roles": ["accountant", "admin"], "host": null, "public": false },
  "inboundLinks": ["invoice overdue"],
  "status": "as-built",
  "redirectTo": null,
  "proposed": null,
  "decide": null,
  "source": "src/app/invoices/[id]/page.tsx:1",
  "assumptions": []
}
```
