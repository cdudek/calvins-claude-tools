# Route conventions

Read by `cct:ux-sitemap-create` for `proposed`, `plan` and check SM-10. A product's own rules
in `docs/ux/setup.md` or its interaction guidelines win over these; write the difference into
the sitemap's Proposed section once, with the reason. A route that breaks one of these is a
finding that names the `RC-` id.

| Id | Rule | Example (generic) |
|---|---|---|
| RC-1 | **A list is a plural noun.** | `/invoices`, never `/invoice-list` or `/invoice` |
| RC-2 | **A record is the list plus its id.** One segment, the stable id. | `/invoices/[id]` |
| RC-3 | **Create is `/new` under the list.** A prefill from context is a query param. | `/invoices/new?customer=<id>` |
| RC-4 | **Edit is the record itself** when fields edit in place; `/[id]/edit` only when editing is a separate mode the guidelines allow. | `/invoices/[id]` |
| RC-5 | **Kebab-case, lowercase, in the product's working language**, one word per meaning, the same word as the label. An address the reader sees is a label too. | `/sender-names`, never `/senderIdentities` |
| RC-6 | **A locale prefix when the app has more than one locale**, the same strategy everywhere (always prefixed, or prefixed except the default). Never mix. | `/en/invoices`, `/de/invoices` |
| RC-7 | **One canonical address per object.** Every other way in links to it; a second address is a redirect, never a second page. | a customer's invoices tab links to `/invoices/[id]` |
| RC-8 | **A child object nests under its parent only when it cannot exist without it**, and never more than one level of nesting. | `/orders/[id]/lines/[lineId]` is fine; `/customers/[id]/orders/[id]/lines/[id]` is not |
| RC-9 | **List state is in the URL**: search, filters, sort, page and the named view are query params, so a link, a reload and Back show the same list. | `/invoices?status=open&sort=-due&view=overdue` |
| RC-10 | **Settings live under one prefix**, each settings page at its own address. | `/settings/team`, `/settings/billing` |
| RC-11 | **No ids or codes in labels.** The address holds the id; the label, title and breadcrumb hold the name. | title "Acme GmbH", not "Customer 4f2a" |
| RC-12 | **Redirects are additive.** A moved address keeps working: the old one redirects to the new one for good, carries its params, and points straight at the final address. | `/clients/[id]` to `/customers/[id]` |
| RC-13 | **Public addresses that people receive (mail links, shared forms, embeds) never change** without a redirect that outlives every mail already sent. | `/confirm/[token]` |
| RC-14 | **Errors keep their area.** Not found inside an area renders inside that area's shell with its way back. | `/admin/<unknown>` shows the admin not-found page |

## Tabs: path segment or query param

Both are allowed. Choose once per product and write the choice into the Proposed section.

| | Tab as a path segment (`/invoices/[id]/payments`) | Tab as a query param (`/invoices/[id]?tab=payments`) |
|---|---|---|
| Good for | tabs that are places in their own right: a list with its own filters, its own primary action, its own page title | tabs that are views of one form or one summary |
| Shareable | yes, and the tab can have its own query params | yes, but its filters share one query string with the page |
| Back | each tab is a history entry unless the app replaces it | usually replaces the entry, so Back leaves the object |
| Server rendering | each tab loads only its own data | the page loads what every tab needs, or loads on switch |
| Cost | more route files | one route, more state handling |

Whichever is chosen, switching tabs should replace the history entry rather than push one, so
Back leaves the object, unless the product decided otherwise.

## Depth

Count levels below the area root (`/admin` or `/` for a single-area app). A record is level
two, its tab level three. A page deeper than three levels needs a reason written next to it in
the Proposed section; without one it is check SM-5.
