---
type: ux-sitemap
created: 2026-10-27
updated: 2026-10-29
status: proposed
---

# HeyDiff sitemap

Copied on 2026-10-29 from the approved spec sitemap, written by `cct:ux-sitemap-create` in diff mode on 2026-10-28: the earlier proposed sitemap (2026-10-27) against the new IA (`ia.md`, rewritten around the approved journey, A59). Machine copy: `sitemap.json` beside this file, 47 pages, 14 surfaces, 19 redirects, 21 mail and external links (the two waitlist pages and three mail links added on 2026-10-28, S146).

## As built

Read from `src/app/[locale]` on 2026-10-29. Six pages exist; three are stubs from the foundation work, three are the sign-in screens (1.12). Every other route is `proposed`. English is the only locale and its prefix is hidden.

| Route                     | File                                                          | Page id                  |
| ------------------------- | ------------------------------------------------------------- | ------------------------ |
| `/`                       | `src/app/[locale]/(public)/page.tsx`                          | `public.landing`         |
| `/[org]/my-work`          | `src/app/[locale]/(app)/[org]/my-work/page.tsx`               | `app.my-work`            |
| `/operator/organisations` | `src/app/[locale]/(operator)/operator/organisations/page.tsx` | `operator.organisations` |
| `/sign-in`                | `src/app/[locale]/(public)/sign-in/page.tsx`                  | `auth.sign-in`           |
| `/sign-in/verify`         | `src/app/[locale]/(public)/sign-in/verify/page.tsx`           | `auth.sign-in-verify`    |
| `/account/sign-in-methods` | `src/app/[locale]/(app)/account/sign-in-methods/page.tsx`    | `account.sign-in-methods` |

Check Your Email (`/sign-in/check` in the proposed sitemap) is built as a state of `/sign-in`, not as a route of its own: `/sign-in/check` has no `page.tsx`.

The test `test/docs/sitemap.test.ts` fails when a built page is missing here.

## Proposed

**Status: proposed, 2026-10-28.** Labels are English only (release 1). Roles: owner, admin, member, guest; visitor (signed out); operator (a platform role). Locale rule unchanged: every route sits under `/[locale]`, English is the only locale, and its prefix is hidden.

### The principles it rests on

| Principle                                                                           | What it forces here                                                                                                                                                                          |
| ----------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| One address per object, tenant then product then thing (`/[org]/[ws]/comments/[n]`) | Two nesting levels, a departure from RC-8 recorded once (F16 of the earlier sitemap, kept). The journey's address bar shows `/kestrel-shop/comments`; read as the workspace part of the path |
| One list per object, status as a filter                                             | Comments is one list with a Status filter, not four status lists. Decisions, Revisions and Sessions are their own objects, so their own lists                                                |
| Every list's filters, grouping and search live in the URL (nuqs)                    | `?status=`, `?commit=`, `?people=`, `?group=` and the rest; defaults omitted                                                                                                                 |
| Tabs that filter one list are query params                                          | Inbox `kind`, My Work `tab`, Decisions and Revisions `status`                                                                                                                                |
| Create is a dialog; the one create page is `/welcome`                               | Start a Decision, Share Session, Invite People, New Workspace add no history entry                                                                                                           |
| No access and not found look the same                                               | A link never reveals what exists                                                                                                                                                             |
| Redirects are additive; a renamed slug keeps redirecting                            | Old organisation and workspace slugs stay reserved for good                                                                                                                                  |
| A label is the route's word                                                         | "Connected Apps" at `/account/connected-apps`; "Revisions" at `/revisions`                                                                                                                   |

### Reserved first segments

`blog`, `privacy`, `terms`, `imprint`, `waitlist`, `sign-in`, `sign-out`, `invite`, `authorize`, `welcome`, `account`, `operator`, `api`, `mcp`, `internal`, `help`, `settings`, `new`, `.well-known`, and every locale code.

### Hosts

This table is the one place hosts are named (A72: "Cloud Run from release 1"; A65: "I bought the domain."). Every other file links here. Each host serves every area (public, sign-in, app, account, operator, `/api`, `/mcp`) on one origin; no `app.` subdomain (S145).

| Host                                | Who uses it                                                             | Runs on                                                                                                                                    | Mail                                                          | MCP address                 |
| ----------------------------------- | ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------- | --------------------------- |
| `https://heydiff.com`               | everyone: production                                                    | Cloud Run service `heydiff-web`, project `heydiff`, europe-west1, Cloud SQL; domain mapping (A81); scales to zero, no warm instance (A66)  | sent from `noreply@heydiff.com` (S145)                        | `https://heydiff.com/mcp`   |
| staging's private `run.app` address | the owner and invited testers, signed in with an allowed Google account | Cloud Run service `heydiff-web-staging`, same project; scales to zero; not indexed (`noindex`); previews are tagged revisions of it (S163) | sent from `noreply@heydiff.com`, subject prefixed "[Staging]" | `{staging address}/mcp`     |
| `http://localhost:3000`             | development on the owner's Mac                                          | `next dev` and the developer's database from `make dev-db` (S166)                                                                          | printed to the terminal (`console` provider)                  | `http://localhost:3000/mcp` |

- Mail links, the MCP address in Connect an Agent, the extension's server and the phone all use the host the person is on. Nothing names a host in a string; screens read it from the server's config as `{host}`.
- The extension's build names its server: the release build uses `heydiff.com`, a staging build the staging host, a dev build localhost (S145).
- The DNS host for `heydiff.com` is still open (A65); it changes nothing here.
- The first request after an idle spell waits for a cold start. Every action already shows its busy state, so nothing else is added (S145). `device` is released: no device-code page exists (A35). Reserved workspace slugs: `inbox`, `my-work`, `settings`, `billing`, `integrations`, `new`.

### Public navigation

| #   | Item (en)                        | Group  | Why here                                                    |
| --- | -------------------------------- | ------ | ----------------------------------------------------------- |
| 1   | Privacy, Terms, Imprint, Sign In | footer | The placeholder has no header (A58); trust for the waitlist |

### App navigation (one sidebar, A27)

| #   | Item (en)                                                                                          | Badge     | Key | Why here                                                               |
| --- | -------------------------------------------------------------------------------------------------- | --------- | --- | ---------------------------------------------------------------------- |
| 1   | Workspace switcher (Organisation › Workspace; More: Workspace Settings)                            | none      |     | One workspace at a time, as drawn                                      |
| 2   | Search                                                                                             | none      | ⌘K  | Reaches every page                                                     |
| 3   | Inbox                                                                                              | new items | G I | What needs me, first                                                   |
| 4   | My Work                                                                                            | none      | G M | My comments and my agent's work; not drawn in the journey (default S3) |
| 5   | Comments                                                                                           | none      | G C | The workspace's comments, grouped by page                              |
| 6   | Decisions                                                                                          | voting    | G D | Open votes                                                             |
| 7   | Revisions                                                                                          | none      | G R | The review queue (default S4)                                          |
| 8   | Sessions (once the workspace has one)                                                              | none      |     | Review passes (A52); not drawn in the sidebar (default S3)             |
| 9   | Settings (hidden for guests)                                                                       | none      | G S | Organisation settings                                                  |
| 10  | Avatar menu: Profile, Sign-In Methods, Connected Apps, Notifications, Keyboard Shortcuts, Sign Out | none      |     | Account is per user                                                    |

Narrow screens: a 56 px rail under 1100 px (⌘\), a drawer on a phone. **Command menu:** every page above, a comment by number (`#118`), settings pages, switching workspace, actions on this page.

**Gone from the navigation:** Open, Needs Decision, In Review, Done (replaced by the Status filter, Decisions and Revisions); Modules (a filter now, managed in Workspace Settings › Modules).

### Operator navigation

Unchanged: Waitlist, Invitations, Organisations, Users, Feature Flags, Usage; header Back to App.

### Settings

Unchanged, except Account › Devices is now Account › Connected Apps.

| #   | Entry (en)                | Route                               | Header primary   |
| --- | ------------------------- | ----------------------------------- | ---------------- |
| 1   | Organisation › General    | `/[org]/settings/general`           | none             |
| 2   | Organisation › Members    | `/[org]/settings/members`           | Invite People    |
| 3   | Organisation › Workspaces | `/[org]/settings/workspaces`        | New Workspace    |
| 4   | Workspace › General       | `/[org]/[ws]/settings/general`      | none             |
| 5   | Workspace › Repos         | `/[org]/[ws]/settings/repos`        | Add Repo         |
| 6   | Workspace › Environments  | `/[org]/[ws]/settings/environments` | Add Environment  |
| 7   | Workspace › Route Rules   | `/[org]/[ws]/settings/route-rules`  | Add Route Rule   |
| 8   | Workspace › Modules       | `/[org]/[ws]/settings/modules`      | Add Module       |
| 9   | Account › Profile         | `/account/profile`                  | none             |
| 10  | Account › Sign-In Methods | `/account/sign-in-methods`          | none             |
| 11  | Account › Connected Apps  | `/account/connected-apps`           | Connect an Agent |
| 12  | Account › Notifications   | `/account/notifications`            | none             |

### Public routes

| Route                            | Label (en)              | Type   | Header primary     | Reached from                                  | Serves                                                                             |
| -------------------------------- | ----------------------- | ------ | ------------------ | --------------------------------------------- | ---------------------------------------------------------------------------------- |
| `/`                              | HeyDiff                 | public | Join the Waitlist  | search, shared links, logo, 404 Go to HeyDiff | J8, A58: placeholder with name, one line, form, legal links; joined state in place |
| `/privacy`, `/terms`, `/imprint` | Privacy, Terms, Imprint | public | none               | footer; every email's footer                  | J8: trust; real pages (S147)                                                       |
| `/waitlist/confirm?token=`       | Confirm Your Place      | public | none               | waitlist confirm email                        | J8: double opt-in; shows the joined state (S146)                                   |
| `/waitlist/leave?token=`         | Leave the Waitlist      | public | Leave the Waitlist | every waitlist email; the joined state        | J8: leaving in one click; then "You've left the waitlist." (S146)                  |
| `/blog`, `/blog/[slug]`          | Blog                    | public | none               | none (reserved)                               | Release 2; 404 until then                                                          |

### Signing in and joining routes

Unchanged from the earlier sitemap: `/sign-in` (Send Sign-In Link), `/sign-in/check`, `/sign-in/verify`, `/invite/[token]` (Join {organisation} or Set Up Your Team), `/authorize` (no Filled button; Outlined Deny and Allow), `/welcome` (Create Organisation; lands on Comments), `/sign-out`.

### App routes

| Route                                         | Label (en)            | Type     | Tabs or views → header primary                                                                               | Reached from                                                                                               | Serves             |
| --------------------------------------------- | --------------------- | -------- | ------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------- | ------------------ |
| `/[org]/inbox`                                | Inbox                 | list     | kind chips All, Votes, Revisions, Mentions, Replies, Shared Sessions → none                                  | sidebar, mails, `/[org]` 308, sign-in, side panel Inbox tab, ⌘K                                            | J2, J4, J6         |
| `/[org]/my-work`                              | My Work               | list     | My Comments · Claimed by My Agent → none                                                                     | sidebar, ⌘K                                                                                                | J3, J4             |
| `/[org]/[ws]/comments`                        | Comments              | list     | Group by Page · Newest; filters Environment, Branch, Commit, Status, People (+ Session, Module, Page) → none | sidebar, `/[org]/[ws]` 308, comment breadcrumb and Back, side panel Open in HeyDiff, Welcome, ⌘K           | J1, J2, J4         |
| `/[org]/[ws]/comments/[n]`                    | {path} comment        | record   | `?revision=`, `?compare=side·slider` → Resolve (members; Reopen when Resolved)                               | every list, Inbox, Revisions, Session, Decision, pin popover, mails, MCP, J/K, ⌘K `#118`                   | J1, J2, J4, J5, J9 |
| `/[org]/[ws]/decisions`                       | Decisions             | list     | Deciding · Decided · Cancelled · All → none                                                                  | sidebar, ⌘K                                                                                                | J2                 |
| `/[org]/[ws]/decisions/[n]`                   | {question}            | record   | → Decide (members, while voting)                                                                             | Decisions, Start Decision, Decided card, Inbox, vote mail                                                  | J2                 |
| `/[org]/[ws]/revisions`                       | Revisions             | list     | Waiting for Review · All → none                                                                              | sidebar, ⌘K                                                                                                | J4                 |
| `/[org]/[ws]/sessions`                        | Sessions              | list     | → none                                                                                                       | sidebar (with 1+ session), ⌘K                                                                              | J12                |
| `/[org]/[ws]/sessions/[id]`                   | {session}             | record   | → Share                                                                                                      | Sessions, shared link and mail, extension Share…, Mac View Online, Inbox                                   | J12, A52, A26      |
| `/[org]/[ws]/settings/…`, `/[org]/settings/…` | as Settings above     | settings | tabs → Add {object}                                                                                          | workspace switcher More, Comments header More, Organisation › Workspaces, Module filter Manage Modules, ⌘K | J10, J5            |
| `/[org]/settings/billing`, `/integrations`    | Billing, Integrations | settings | none                                                                                                         | none (reserved)                                                                                            | Release 2          |

Breadcrumbs: Comment `Comments › {path}` (the path links to Comments `?path=`); Decision `Decisions`; Session `Sessions`. Back on a comment returns to `from`, else Comments with defaults.

### Account and operator routes

Account: `/account/profile`, `/account/sign-in-methods`, `/account/connected-apps` (was `/account/devices`), `/account/notifications`. Operator: unchanged (`/operator/waitlist`, `/invitations`, `/organisations`, `/organisations/[id]`, `/users`, `/users/[id]`, `/flags`, `/usage`). Not found: `*`, rendered in the shell the person may see.

### Surfaces outside the web router

| Surface                                        | Purpose                                                                           | Reached from                                | Goes to                                           |
| ---------------------------------------------- | --------------------------------------------------------------------------------- | ------------------------------------------- | ------------------------------------------------- |
| Toolbar (extension)                            | S mark (More), session chip, context chip, eye, count, device, Comment            | Chrome icon (Show Toolbar), ⌘⇧K             | pick mode, menus, side panel                      |
| Pick mode (extension)                          | Select one or several elements; DOM and code location                             | Comment, `C`                                | composer                                          |
| Composer (extension)                           | Write, mention, draw, move, send                                                  | pick mode                                   | drawing, arranging; the pin                       |
| Drawing, Arranging (extension)                 | Mac drawing tools; move and align inside the parent                               | composer Draw, Move; Draw · Move switch     | composer                                          |
| Pin popover (extension)                        | Read, reply, resolve where the comment sits                                       | a pin, side panel row                       | `/[org]/[ws]/comments/[n]`                        |
| Visibility menu (extension)                    | Everyone · Only Mine · Hide Others; Not Resolved · Resolved; Show Earlier Commits | eye                                         | the page                                          |
| Device picker (extension)                      | The eight device choices                                                          | device button                               | the page                                          |
| Session bar and menu (extension)               | Active session; Rename, End Session, Share…                                       | session chip; S mark (More) › Start Session | Share Session                                     |
| Share Session (extension, web)                 | Link, email, agent prompt                                                         | session menu; Session page                  | `/[org]/[ws]/sessions/[id]`                       |
| Side panel: This Page, Inbox (extension)       | This page's comments with code location; the Inbox                                | toolbar count, Chrome side panel menu       | pin popover, `/comments?path=`, `/inbox`          |
| Popup (extension)                              | Sign in, workspace, drafts, Show Toolbar, Open Side Panel                         | Chrome icon                                 | toolbar, side panel, a draft's page, `/authorize` |
| Keyboard Shortcuts sheet (extension)           | Every key the extension takes, by group                                           | S mark (More) › Keyboard Shortcuts          | `chrome://extensions/shortcuts`                   |
| Settings › Online (Mac)                        | Sign in; localhost bridge                                                         | Mac menu › Settings                         | `/authorize`                                      |
| Share to Workspace sheet and sync status (Mac) | Share a Mac session as a Session                                                  | session window, menu bar                    | `/[org]/[ws]/sessions/[id]`                       |

### Redirects

Additive only; chains flattened (RC-12). Rows marked "earlier plan" close addresses that existed only in the 2026-10-27 proposal.

| Old address                                         | New address                                | Carries                                                                                             |
| --------------------------------------------------- | ------------------------------------------ | --------------------------------------------------------------------------------------------------- |
| `/[org]`                                            | `/[org]/inbox`                             | org; 308                                                                                            |
| `/[org]/[ws]`                                       | `/[org]/[ws]/comments`                     | org, ws; 308                                                                                        |
| `/[org]/settings`, `/[org]/[ws]/settings`           | `…/settings/general`                       | 308                                                                                                 |
| `/account`                                          | `/account/profile`                         | 308                                                                                                 |
| `/operator`                                         | `/operator/waitlist`                       | 308                                                                                                 |
| `/[old-org]/[...rest]`, `/[org]/[old-ws]/[...rest]` | the current slug                           | rest, query; 308                                                                                    |
| `/[org]/[ws]/open`                                  | `/[org]/[ws]/comments`                     | query; 308; earlier plan                                                                            |
| `/[org]/[ws]/needs-decision`                        | `/[org]/[ws]/decisions`                    | 308; earlier plan                                                                                   |
| `/[org]/[ws]/in-review`                             | `/[org]/[ws]/revisions`                    | 308; earlier plan                                                                                   |
| `/[org]/[ws]/done`                                  | `/[org]/[ws]/comments?status=resolved`     | 308; earlier plan                                                                                   |
| `/[org]/[ws]/feedback`, `/[org]/[ws]/feedback/[n]`  | `/[org]/[ws]/comments`, `/comments/[n]`    | n; drops `version`, `compare`, `tab`; 308; earlier plan                                             |
| `/[org]/[ws]/modules`, `/modules/[module]`          | `/[org]/[ws]/comments`, `?module=[module]` | 308; earlier plan                                                                                   |
| `/account/devices`                                  | `/account/connected-apps`                  | 308; earlier plan                                                                                   |
| `/waitlist`, `/waitlist/joined`                     | `/`                                        | 308; the joined state is shown in place; `/waitlist/confirm` and `/waitlist/leave` are pages (S146) |

### Mail and external links

| Mail or link                                            | Leads to                                                  | Note                                                    |
| ------------------------------------------------------- | --------------------------------------------------------- | ------------------------------------------------------- |
| sign-in link                                            | `/sign-in/verify?token=`                                  | once, 15 minutes                                        |
| invitation, waitlist invitation                         | `/invite/[token]`                                         | 7 days                                                  |
| waitlist confirm                                        | `/waitlist/confirm?token=`                                | 7 days; unconfirmed entries are deleted then (S146)     |
| Leave the Waitlist (every waitlist email, joined state) | `/waitlist/leave?token=`                                  | also as the `List-Unsubscribe` header, one click (S146) |
| legal links (every email's footer)                      | `/privacy`, `/imprint`                                    |                                                         |
| mention, reply                                          | `/[org]/[ws]/comments/[n]#reply-[id]`                     |                                                         |
| vote request                                            | `/[org]/[ws]/decisions/[n]`                               |                                                         |
| revision posted                                         | `/[org]/[ws]/comments/[n]?revision=[k]`                   | to the author and the thread                            |
| session shared                                          | `/[org]/[ws]/sessions/[id]`                               |                                                         |
| daily digest                                            | `/[org]/inbox`                                            |                                                         |
| Copy Link on a comment                                  | `/[org]/[ws]/comments/[n]`                                | approved extension 2                                    |
| Share Session: Copy Link; agent prompt                  | `/[org]/[ws]/sessions/[id]`; `get_session [id]`           |                                                         |
| extension Open in HeyDiff                               | `/comments/[n]` (popover), `/comments?path=` (side panel) | new tab                                                 |
| extension and Mac app Sign In                           | `/authorize`                                              | OAuth PKCE; Mac by loopback (A35)                       |
| Mac app View Online                                     | `/[org]/[ws]/sessions/[id]`                               |                                                         |
| MCP responses                                           | `/[org]/[ws]/comments/[n]`                                |                                                         |

## Every route

One row per page of `sitemap.json`, so the prose and the machine copy can be checked against each other.

| Page id                         | Route                               | Label                                       | Roles                                | Status   |
| ------------------------------- | ----------------------------------- | ------------------------------------------- | ------------------------------------ | -------- |
| `public.landing`                | `/`                                 | HeyDiff                                     | visitor                              | as-built |
| `public.privacy`                | `/privacy`                          | Privacy                                     | visitor                              | proposed |
| `public.waitlistConfirm`        | `/waitlist/confirm`                 | Confirm Your Place                          | visitor                              | proposed |
| `public.waitlistLeave`          | `/waitlist/leave`                   | Leave the Waitlist                          | visitor                              | proposed |
| `public.terms`                  | `/terms`                            | Terms                                       | visitor                              | proposed |
| `public.imprint`                | `/imprint`                          | Imprint                                     | visitor                              | proposed |
| `public.blog`                   | `/blog`                             | Blog                                        | visitor                              | proposed |
| `public.blog-post`              | `/blog/[slug]`                      | {title}                                     | visitor                              | proposed |
| `auth.sign-in`                  | `/sign-in`                          | Sign In to HeyDiff                          | visitor                              | as-built |
| `auth.sign-in-check`            | `/sign-in/check`                    | Check Your Email                            | visitor                              | proposed |
| `auth.sign-in-verify`           | `/sign-in/verify`                   | Verifying the link                          | visitor                              | as-built |
| `auth.invite`                   | `/invite/[token]`                   | Join {organisation} / Set Up Your Team      | visitor, owner, admin, member, guest | proposed |
| `auth.authorize`                | `/authorize`                        | Allow {client} to use your HeyDiff account? | visitor, owner, admin, member, guest | proposed |
| `auth.welcome`                  | `/welcome`                          | A home for your team's decisions.           | owner                                | proposed |
| `auth.sign-out`                 | `/sign-out`                         | Sign Out                                    | owner, admin, member, guest          | proposed |
| `app.inbox`                     | `/[org]/inbox`                      | Inbox                                       | owner, admin, member, guest          | proposed |
| `app.my-work`                   | `/[org]/my-work`                    | My Work                                     | owner, admin, member, guest          | as-built |
| `app.comments`                  | `/[org]/[ws]/comments`              | Comments                                    | owner, admin, member, guest          | proposed |
| `app.comment`                   | `/[org]/[ws]/comments/[n]`          | {path} comment                              | owner, admin, member, guest          | proposed |
| `app.decisions`                 | `/[org]/[ws]/decisions`             | Decisions                                   | owner, admin, member, guest          | proposed |
| `app.decision`                  | `/[org]/[ws]/decisions/[n]`         | {question}                                  | owner, admin, member, guest          | proposed |
| `app.revisions`                 | `/[org]/[ws]/revisions`             | Revisions                                   | owner, admin, member, guest          | proposed |
| `app.sessions`                  | `/[org]/[ws]/sessions`              | Sessions                                    | owner, admin, member, guest          | proposed |
| `app.session`                   | `/[org]/[ws]/sessions/[id]`         | {session}                                   | owner, admin, member, guest          | proposed |
| `app.ws-settings-general`       | `/[org]/[ws]/settings/general`      | {workspace} Settings: General               | owner, admin, member                 | proposed |
| `app.ws-settings-repos`         | `/[org]/[ws]/settings/repos`        | {workspace} Settings: Repos                 | owner, admin, member                 | proposed |
| `app.ws-settings-environments`  | `/[org]/[ws]/settings/environments` | {workspace} Settings: Environments          | owner, admin, member                 | proposed |
| `app.ws-settings-route-rules`   | `/[org]/[ws]/settings/route-rules`  | {workspace} Settings: Route Rules           | owner, admin, member                 | proposed |
| `app.ws-settings-modules`       | `/[org]/[ws]/settings/modules`      | {workspace} Settings: Modules               | owner, admin, member                 | proposed |
| `app.org-settings-general`      | `/[org]/settings/general`           | {organisation} Settings: General            | owner, admin, member                 | proposed |
| `app.org-settings-members`      | `/[org]/settings/members`           | {organisation} Settings: Members            | owner, admin, member                 | proposed |
| `app.org-settings-workspaces`   | `/[org]/settings/workspaces`        | {organisation} Settings: Workspaces         | owner, admin, member                 | proposed |
| `app.org-settings-billing`      | `/[org]/settings/billing`           | Billing                                     | owner                                | proposed |
| `app.org-settings-integrations` | `/[org]/settings/integrations`      | Integrations                                | owner, admin                         | proposed |
| `account.profile`               | `/account/profile`                  | Profile                                     | owner, admin, member, guest          | proposed |
| `account.sign-in-methods`       | `/account/sign-in-methods`          | Sign-In Methods                             | owner, admin, member, guest          | as-built |
| `account.connected-apps`        | `/account/connected-apps`           | Connected Apps                              | owner, admin, member, guest          | proposed |
| `account.notifications`         | `/account/notifications`            | Notifications                               | owner, admin, member, guest          | proposed |
| `operator.waitlist`             | `/operator/waitlist`                | Waitlist                                    | operator                             | proposed |
| `operator.invitations`          | `/operator/invitations`             | Invitations                                 | operator                             | proposed |
| `operator.organisations`        | `/operator/organisations`           | Organisations                               | operator                             | as-built |
| `operator.organisation`         | `/operator/organisations/[id]`      | {organisation}                              | operator                             | proposed |
| `operator.users`                | `/operator/users`                   | Users                                       | operator                             | proposed |
| `operator.user`                 | `/operator/users/[id]`              | {name}                                      | operator                             | proposed |
| `operator.flags`                | `/operator/flags`                   | Feature Flags                               | operator                             | proposed |
| `operator.usage`                | `/operator/usage`                   | Usage                                       | operator                             | proposed |
| `error.not-found`               | `*`                                 | Not found                                   | owner, admin, member, guest, visitor | proposed |

## Changes from the earlier proposed sitemap

| #   | Change                                                                                                        | Why                                                   |
| --- | ------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| 1   | `/` becomes a placeholder; `/waitlist/joined` goes, the joined state shows in place                           | A58                                                   |
| 2   | Four status lists become one Comments list with a Status filter                                               | A43, A44; brief status words                          |
| 3   | `/feedback/[n]` becomes `/comments/[n]`; no title in the label                                                | A42                                                   |
| 4   | New `/decisions` and `/decisions/[n]` (a decision has its own page)                                           | A44; image 09                                         |
| 5   | New `/revisions`                                                                                              | image 06 sidebar; default S4                          |
| 6   | Sessions change meaning: a review pass from the extension or the Mac app                                      | A52                                                   |
| 7   | Modules list pages go; Module is a filter                                                                     | default S24                                           |
| 8   | `/account/devices` becomes `/account/connected-apps`                                                          | "Device" names the screen size now (A50); default S27 |
| 9   | Inbox kinds become Votes, Revisions, Mentions, Replies, Shared Sessions                                       | new model                                             |
| 10  | Extension surfaces replaced: toolbar, pick mode, composer, drawing, arranging, pin popover, menus, side panel | A41 to A57                                            |
| 11  | `device` released from the reserved segments                                                                  | A35 (no device-code page)                             |

## Checks

Run on 47 pages and 14 surfaces, proposed only.

| Check                                     | Result                                                                                                                           |
| ----------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| SM-1 dead end                             | pass: every page has a way on and back; the placeholder links to legal pages and Sign In                                         |
| SM-2 orphan                               | pass. Exempt: reserved `/blog`, billing, integrations; `/sign-in/verify` and `/authorize` are entered from mail or another app   |
| SM-3 fewer than two ways in               | Sessions list has one visible way in (sidebar, once one exists) plus ⌘K; accepted, as before for operator pages                  |
| SM-4 one object at two addresses          | pass: the extension's "Open in HeyDiff" lands on the same canonical addresses                                                    |
| SM-5 deeper than three levels             | pass: deepest are `/comments/[n]`, `/decisions/[n]`, `/sessions/[id]`, `/settings/[page]`                                        |
| SM-6 record without one canonical address | pass                                                                                                                             |
| SM-7 label differs                        | pass after renaming Devices; the journey's "Implemented" and "Voting" chips are image faults, the words are Revised and Deciding |
| SM-8 tab with no header primary decision  | pass: every page above names its primary or none                                                                                 |
| SM-9 list state not in the URL            | pass                                                                                                                             |
| SM-10 route convention                    | F16 kept (two nesting levels); nothing new                                                                                       |
| SM-11 moved address without a redirect    | pass: every earlier-plan address has one                                                                                         |
| SM-12 mail lands elsewhere than its words | pass                                                                                                                             |

## Findings for the spec

- **F17 (new): the journey's address bar shows one segment.** Images show `app.snapmark.dev/kestrel-shop/comments`. The sitemap keeps `/[org]/[ws]/…` so an organisation can hold several workspaces. Recorded as default S1.
- **F18 (new): My Work and Sessions are not drawn in the sidebar.** The journey's sidebar shows Inbox, Comments, Decisions, Revisions. Both are kept, Sessions only once one exists (default S3).
- F1 to F16 of the earlier sitemap are folded in or kept as written; F3, F10 and F14 no longer apply (modules list gone, Agent decided, module tabs gone).
