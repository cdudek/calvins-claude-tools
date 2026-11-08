---
name: ux-sitemap-create
description: "Creates the product's sitemap, the one record of every page and how people reach it: the as-built sitemap read from the router (any stack, detected) with file evidence, a proposed sitemap from the information architecture, guidelines or a spec, a diff of the two with an additive redirect for every moved address, or a greenfield sitemap from job stories. Checks dead ends, orphans, two names for one place, depth, missing canonical addresses and route conventions; writes docs/ux/sitemap.md and sitemap.json. Use when the user says 'create the sitemap', 'map the routes', 'what pages do we have', 'which redirects do we need'. Skip for: judging the whole assessment, which belongs to cct:ux-assessment-run."
user_invocable: true
metadata:
  version: 1.0.0
  author: calvindudek
context: fork
model: sonnet
effort: high
background: false
---

# cct:ux-sitemap-create

**Arguments:** `[as-built | proposed | diff | plan]  [scope: <route prefix | spec folder>]  [base: <git ref>]  [out: <folder>]`

One skill owns the sitemap. `cct:ux-setup`, `cct:ux-assessment-run`, `cct:ux-design-run` and `cct:ux-assessment-run`
call it instead of writing their own. A sitemap is the list of places: every page, how it is
reached and how it is left. Objects, permissions and state machines are the information
architecture's job; this skill reads them, it does not restate them.

Files in this skill's `references/`:

- `references/routers.md`: how to find the routes, locales, labels, redirects and links in each
  stack. Read before `as-built` or `diff`.
- `references/route-conventions.md`: the address rules, ids `RC-1` upward. Read before
  `proposed`, `plan` and the checks.
- `references/format.md`: the templates for `sitemap.md` and `sitemap.json`, with an example
  from a product. Read before writing either file.

Shared files are in `references/`, two levels up from this skill's base directory:
`finding-format.md` (how every check result is written) and `conflicts.md` (when two sources
disagree about a page).

## Modes

| Mode | Reads | Writes |
|---|---|---|
| default (no mode) | the router; the existing `sitemap.md` | As built, refreshed; then `diff` against the existing Proposed section when there is one |
| `as-built` | the router and the code around it | As built, E-mail and external links |
| `proposed` | the IA (`docs/ux/information-architecture.md` or `<spec>/ia.md`), the interaction guidelines, the design spec or brief, the owner's words, the latest audit findings, the decisions log | Proposed: principles, navigation, settings, route tables, pages whose content changes |
| `diff` | As built and Proposed; with `base:`, the router at that git ref against the working tree | Changes from as built, Redirects, E-mail links that change |
| `plan` | a brief and its job stories, the IA when there is one | Proposed only, every row `proposed`, for a product with no router yet |

`scope:` limits every mode to the routes under a prefix, or to the routes a spec folder names.
`out:` writes into another folder. `cct:ux-design-run` passes its spec folder, so a change's
sitemap never overwrites the whole-app one.

## 0. Where it writes

- Read `docs/ux/setup.md`. Its "Where the UX files live" table names the sitemap paths and its
  "Route source" names the router. Neither present: `docs/ux/sitemap.md` and
  `docs/ux/sitemap.json`, and the router is detected in step 1.
- Edit an existing `sitemap.md` in place. A mode rewrites only its own sections and keeps
  every other section, including owner comments and decided items, word for word.
- `sitemap.json` is always written whole from the same run, so the two files never disagree.

## 1. As built: from the router, never from memory

1. **Detect the stack** with `references/routers.md`: the package manifest, the framework's
   config file, and the route files themselves. Two stacks (an app and a docs site, a web app
   and an Electron shell) are two areas. No stack recognised: stop and ask for the route
   source, and write it into `setup.md`.
2. **List every page route** with the file and line that defines it. API routes, assets and
   framework internals are not pages; redirects and rewrites are listed separately.
3. **Read what each page shows:** its title and tabs from the page and layout files; its labels
   from the message catalogue in every locale the app has (a key that resolves nowhere is
   written `<unresolved: key>`); path params; query params the page reads (search, filter,
   sort, view, tab, page, open item), each with its kind.
4. **Read how each page is reached:** navigation config (sidebar, rail, tabs, settings menu,
   command menu, account menu), every link, router push, form action and server redirect that
   targets it, and every mail template and public snippet that carries its address. Each way
   in is a `reachedFrom` entry with its own `file:line`.
5. **Read access:** the guard, middleware, layout or policy that admits or refuses each role,
   and the host it answers on when there are several.
6. **Breadcrumb and Back:** the breadcrumb the page renders, and where its back control goes.

**Never invent a route.** An as-built row exists only with file evidence. Anything inferred
(a label not on screen, a role guessed from a folder name) is marked `assumption` in the row.
Routes that cannot be resolved statically (generated at runtime, from a CMS) are listed as a
pattern with the source that generates them and a note saying so.

## 2. Proposed and plan: every row says why

- Read the inputs in the mode table. Apply `references/route-conventions.md`.
- Every proposed item is marked `proposed` and carries its reason: the job story it serves, a
  principle (name the law), a finding, or the owner's words quoted with their date.
- Open choices are marked **decide** with the alternative in one line. A proposed item becomes
  accepted only through a recorded decision (an ADR in `docs/designs/`), never because it was built
  or written down earlier.
- Open the section with its principles: each one names the choice it forces (a group size, what
  sits in Settings, where search lives).
- For every page record the fields in step 4. Every tab names its header primary action, or
  "none" as a decision. Every list names the query params that make it a shareable view.
- `plan` starts from the job stories: each job names the pages it passes through, each object
  gets the list, record and create pages it needs, and nothing is added that no job reaches.

## 3. Diff: what moves, and how old addresses keep working

- Compare page by page: added, removed, moved (same page, new address), renamed (same address,
  new label), changed (tabs, primary actions, ways in). Each change is one row with its reason.
- **Every moved or removed address gets a redirect.** Redirects are additive: the old address
  keeps working, existing redirects stay, a chain is flattened to point straight at the final
  address, and a redirect carries the params it can (an id, a filter).
- List every mail, notification and public link whose target changes, as built against
  proposed.
- With `base:` (a PR), the comparison is the router at the base ref against the head. A route
  that disappears or moves without a redirect is a finding at least High: bookmarks, sent mails
  and shared links break.

## 4. The page record

Every page, in both files, carries these fields. Names and types are in `references/format.md`.

| Field | What it holds |
|---|---|
| route | the address with path params, and its query params with their kind (search, filter, sort, view, tab, page, open item) |
| labels | in every locale the app has, as shown on screen |
| type | home, list, record, create, edit, settings, account, public, auth, error, embed |
| purpose, roles | the job it does in one line, and who uses it |
| tabs | label, whether a count shows, the one header primary action (or "none") |
| sections, views | headed sections; named view tabs and filters, with the URL that shows each |
| states | the states worth capturing: empty, loading, error, not found, and the product's own |
| reached from | every way in, each with its kind and evidence |
| breadcrumb, back | where the object lives (not the path taken), and the Back target |
| access | roles or permissions, and the host |
| inbound links | mails, notifications, embeds and external links that land here |
| status | as built, proposed, or removed |

Also record the navigation once per area: sidebar or rail order with groups, the settings
structure (its menu and landing list), what the command menu reaches, and where account and
sign out sit.

## 5. Checks

Run every check on every page in scope. Each failure is one finding in the shared
`finding-format.md` format; the check id goes in the supporting notes under "Broken", with the
`file:line` evidence. Impact follows that file's scale.

| Id | Check |
|---|---|
| SM-1 | Dead end: a page with no way on and no way back (no navigation, no breadcrumb, no Back) |
| SM-2 | Orphan: a page no navigation and no other page links to (a mail or a redirect alone does not count) |
| SM-3 | Fewer than two ways in, or no visible way in (a command menu alone is not visible) |
| SM-4 | One object reachable at two addresses, or one place named two ways |
| SM-5 | Deeper than three levels below its area without a written reason |
| SM-6 | A record without one canonical address (reachable only inside a panel, or at two paths) |
| SM-7 | The label differs between navigation, breadcrumb and page title |
| SM-8 | A tab with no decision on its header primary action |
| SM-9 | A list whose search, filters, sort or view are not in the URL |
| SM-10 | A route that breaks a rule in `references/route-conventions.md` (name the `RC-` id) |
| SM-11 | A moved or removed address with no redirect, or a redirect chain |
| SM-12 | A mail or external link that lands on a page other than the one its words name |

## 6. Write and report

1. Write `sitemap.md` and `sitemap.json` from `references/format.md`, in the path from step 0.
   A mermaid graph of the navigation is optional; add it when the user asks or the tree is
   deeper than two levels.
2. When run on its own, the findings go under "Checks" at the end of `sitemap.md`. Called by
   another skill, return them to the caller, which merges them into its own report.
3. Validate the JSON (`python3 -m json.tool <file>`), and check that every page in the markdown
   tables is in the JSON and back.
4. Report in a few lines: the stack and route source, pages by status, findings by impact, the
   redirects proposed, and every `<unresolved>` or `assumption` left in the files. Do not commit
   unless the user asks; follow the repo's own commit rules.
