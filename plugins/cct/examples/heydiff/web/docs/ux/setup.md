---
type: ux-setup
updated: 2026-10-29
---

# UX setup: HeyDiff, the team service

Every `ux:` skill reads this file first. Keep it short and true.

**The app does not run yet.** This file was written on 2026-10-29 from the approved spec (`changes/2026-10-27-online-release-1/spec/`) and the repo, not from screenshots. Three stub pages exist (landing, My Work, Operator Organisations). No audit, screenshot or visual check has run. Update "How to run it", the screenshot recipes and the screens table when milestone 1 ships the first real screens. F16 (the owner starts the app from this file) is checked by hand at the milestone 1 PR.

## The product

- **What it is:** an online service where a team comments on exact elements of running software, decides together, and hands the result to a coding agent through MCP. Named HeyDiff since 2026-10-28.
- **Platform:** web (Next.js 16 App Router, next-intl, English only in release 1), a Chrome extension (`heydiff-chrome`), a landing page and an operator area, all in this repo except the extension's code. The Mac app (`heydiff-desktop`) keeps its own UX docs.
- **Audience file:** `heydiff-context/audience/audiences.md` (decided 2026-10-27). Primary: product teams building with coding agents; founders and solo builders. Secondary: agencies, QA and design QA, engineer-led agentic teams. Personas in `audience/personas.md` (Priya the PM, Dana the designer, Ben the engineer, Eva the founder, Hugo the hobby developer; draft).
- **Scenes the design serves:**
  1. **Reviewing a running build:** click through, point at an element, draw, say what is off (J1).
  2. **Deciding together:** several fixes, options, votes, one decision on record (J2).
  3. **Handing to an agent:** the agent claims open comments over MCP, reports revisions, a member resolves (J3, J4).
  4. **Away from the desk:** reply, vote, decide or resolve from the phone, from the mail link (J6).
- **Jobs to be done:** the job stories J1 to J9 in `changes/2026-10-27-online-release-1/intent.md`, and `heydiff-context/audience/jobs-to-be-done.md` (draft).
- **Products the audience already uses** (for pattern research; to confirm with the owner): Figma comments, Linear, GitHub pull request reviews, Slack. The competitor list is in `heydiff-context/market/2026-10-25-feature-comparison.md`.

## The rules it must follow

- **Design system:** pinned from [design-system-starter](https://github.com/cdudek/design-system-starter); HeyDiff's rules and the colour direction "Clear Sky" are in `heydiff-context/design-system.md`. Tokens and components live in `heydiff-kit` (HeroUI base). Colour, buttons and state layers: `colour.md` and `motion.md` of the change spec, which move into the kit.
- **Glossary:** [glossary-proposal.md](glossary-proposal.md). Checked by `test/docs/glossary.test.ts`.
- **Interaction guidelines:** [interaction-guidelines.md](interaction-guidelines.md), including the section "States and feedback" and its contract [states-contract.md](states-contract.md).
- **Voice and writing rules:** WRD-1 to WRD-7 in the guidelines (Title Case for buttons, tabs, chips, headings; sentence case for fields and messages; no "please", "oops" or exclamation marks); the spec's `microcopy.md` holds every string once.
- **Hard rules** that override UX preferences (from the owner's words):
  - Every string is a next-intl key; no inline or ad hoc design, only tokens (A10).
  - Everything on the customer's page is HeyDiff's overlay in a shadow root and never changes the page (WEB-30).
  - People's text is untrusted: Markdown subset, no raw HTML, and the agent receives it as data (A28).
  - Hosting in the EU: compute in Belgium (`europe-west1`) (`heydiff-context/strategy/2026-10-28-hosting-and-data-residency.md`).
  - Never Firebase.
- **Exceptions register:** the exceptions are in the guidelines (EX-W1 to EX-W8). A separate `docs/ux/exceptions.md` is not created yet.
- **WCAG and EAA scope, one finding per surface:** not asked yet. Default, owner to confirm: every surface is treated as consumer-facing, so WCAG 2.2 AA is the legal floor. Surfaces: web app, extension, landing, operator. The guidelines already bind ACC-1 to ACC-6.

## The owner's words

- **File:** [owner-words.md](owner-words.md), every request, verbatim, dated. Quote from it; never cite a request by number.
- **Feedback folders:** `changes/<change>/asks/` (the owner's asks that arrive as files) and the owner's plan-gate comments in `changes/<change>/`.

## Design inputs

- **Route source:** `src/app/[locale]` (Next.js App Router; groups `(public)`, `(app)`, `(operator)`; locale prefix hidden, English only). The sitemap is [sitemap.md](sitemap.md) and `sitemap.json`.
- **Interaction guidelines:** `docs/ux/interaction-guidelines.md`.
- **Screen goals:** the change spec `changes/2026-10-27-online-release-1/spec/screens.md` and `screens/*.md` (purpose and job stories per screen).
- **UI components live in:** `heydiff-kit/ui/src/<kebab-name>/` (private repo `heydiff-kit`, built in milestone 1).
- **Component catalogue:** none yet; the kit adds one in milestone 1. Until then the spec's component inventory (`screens.md`, `conformance.md`).
- **Screenshot recipe at 100 percent:** `<unknown>`; no app to run yet. Planned: Playwright at a 1440 px window, output under `docs/ux/audits/<date>/shots/`.
- **Screenshot recipe at 150 percent:** `<unknown>`; planned: a 960 CSS px viewport.
- **Phone:** a viewport under 640 px.
- **Specs without a change folder:** `docs/ux/specs/<YYYY-MM-DD>-<slug>/`.

## Where the UX files live

| File                         | Path                                                                         |
| ---------------------------- | ---------------------------------------------------------------------------- |
| Audits                       | `docs/ux/audits/<YYYY-MM-DD>/`                                               |
| Findings (latest)            | `docs/ux/audits/<YYYY-MM-DD>/findings.md`                                    |
| Decisions (one file each)    | `docs/designs/<YYYY-MM-DD>-adr-<slug>.md`, listed in `docs/designs/INDEX.md` |
| Interaction guidelines       | `docs/ux/interaction-guidelines.md`                                          |
| States and feedback contract | `docs/ux/states-contract.md`                                                 |
| Sitemap, for people          | `docs/ux/sitemap.md`                                                         |
| Sitemap, for tools           | `docs/ux/sitemap.json`                                                       |
| Glossary proposal            | `docs/ux/glossary-proposal.md`                                               |
| Owner's words                | `docs/ux/owner-words.md`                                                     |
| Change specs                 | `changes/<date>-<slug>/spec/`                                                |

## Screens and states

Generated from `sitemap.json` on 2026-10-29. "States to capture" are the page's states in the sitemap; the section "States and feedback" says what each state must show. `not-found` is the same 404 for no access.

### Pages

| Screen                                      | Route (under `/[locale]`, prefix hidden) | States to capture                                                                                                                                                                                                                        |
| ------------------------------------------- | ---------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| HeyDiff                                     | `/`                                      | default · loading · error-invalid-email · error-server · joined · signed-in                                                                                                                                                              |
| Privacy                                     | `/privacy`                               | default                                                                                                                                                                                                                                  |
| Confirm Your Place                          | `/waitlist/confirm`                      | confirmed · already confirmed · expired or invalid link                                                                                                                                                                                  |
| Leave the Waitlist                          | `/waitlist/leave`                        | confirm · left · already left or invalid link · error                                                                                                                                                                                    |
| Terms                                       | `/terms`                                 | default                                                                                                                                                                                                                                  |
| Imprint                                     | `/imprint`                               | default                                                                                                                                                                                                                                  |
| Blog                                        | `/blog`                                  | not-found                                                                                                                                                                                                                                |
| {title}                                     | `/blog/[slug]`                           | not-found                                                                                                                                                                                                                                |
| Sign In to HeyDiff                          | `/sign-in`                               | default · loading · error-invalid-email · error-expired-link · error-used-link · error-invalid-link · error-rate-limit · unknown-email                                                                                                   |
| Check Your Email                            | `/sign-in/check`                         | default · send-again-disabled-under-30s                                                                                                                                                                                                  |
| Verifying the link                          | `/sign-in/verify`                        | loading · error-expired · error-used · error-invalid                                                                                                                                                                                     |
| Join {organisation} / Set Up Your Team      | `/invite/[token]`                        | default-signed-out · default-signed-in-same-email · waitlist-signed-out · waitlist-signed-in · waitlist-already-has-organisation · wrong-account · already-a-member · expired · revoked · invalid (404) · no-free-seat · loading · error |
| Allow {client} to use your HeyDiff account? | `/authorize`                             | default · loading · allowed · denied · expired-request                                                                                                                                                                                   |
| A home for your team's decisions.           | `/welcome`                               | default · error-empty-field · error-slug-taken · loading · error-server · has-an-organisation (redirects to Inbox)                                                                                                                       |
| Sign Out                                    | `/sign-out`                              |                                                                                                                                                                                                                                          |
| Inbox                                       | `/[org]/inbox`                           | default · loading · empty · empty-kind · error · live · dismissed · phone                                                                                                                                                                |
| My Work                                     | `/[org]/my-work`                         | default · loading · empty-mine · empty-agent · error · guest-agent-tab-hidden                                                                                                                                                            |
| Comments                                    | `/[org]/[ws]/comments`                   | default · grouped · newest · resolved-trail · empty · empty-filters · live · loading · error · phone                                                                                                                                     |
| {path} comment                              | `/[org]/[ws]/comments/[n]`               | open · deciding · decided · in-progress · revised · resolved · with-moves · guest · no-screenshot · outdated · loading · error · phone                                                                                                   |
| Decisions                                   | `/[org]/[ws]/decisions`                  | default · empty · loading · error                                                                                                                                                                                                        |
| {question}                                  | `/[org]/[ws]/decisions/[n]`              | deciding · not-a-voter · guest-voter · decided · cancelled · loading · error · phone                                                                                                                                                     |
| Revisions                                   | `/[org]/[ws]/revisions`                  | default · empty · loading · error                                                                                                                                                                                                        |
| Sessions                                    | `/[org]/[ws]/sessions`                   | default · loading · error                                                                                                                                                                                                                |
| {session}                                   | `/[org]/[ws]/sessions/[id]`              | default · active · ended · from-mac · empty · loading · error                                                                                                                                                                            |
| {workspace} Settings: General               | `/[org]/[ws]/settings/general`           | default · empty · adding · field-saved · field-invalid · row-deleted · member-read-only · guest (404) · loading · error · phone (desktop-only message)                                                                                   |
| {workspace} Settings: Repos                 | `/[org]/[ws]/settings/repos`             | default · empty · adding · field-saved · field-invalid · row-deleted · member-read-only · guest (404) · loading · error · phone (desktop-only message)                                                                                   |
| {workspace} Settings: Environments          | `/[org]/[ws]/settings/environments`      | default · empty · adding · field-saved · field-invalid · row-deleted · member-read-only · guest (404) · loading · error · phone (desktop-only message)                                                                                   |
| {workspace} Settings: Route Rules           | `/[org]/[ws]/settings/route-rules`       | default · empty · adding · field-saved · field-invalid · row-deleted · member-read-only · guest (404) · loading · error · phone (desktop-only message)                                                                                   |
| {workspace} Settings: Modules               | `/[org]/[ws]/settings/modules`           | default · empty · adding · field-saved · field-invalid · row-deleted · member-read-only · guest (404) · loading · error · phone (desktop-only message)                                                                                   |
| {organisation} Settings: General            | `/[org]/settings/general`                | default · field-saved · field-invalid · member-read-only · guest (404) · loading · error · phone (desktop-only message)                                                                                                                  |
| {organisation} Settings: Members            | `/[org]/settings/members`                | default · invite-dialog · no-free-seat · guest-limit-reached · error-bad-email · change-role · remove-member · last-owner · invitations-empty · member-read-only · loading · error                                                       |
| {organisation} Settings: Workspaces         | `/[org]/settings/workspaces`             | default · new-workspace-dialog · loading · error · member-read-only · guest (404)                                                                                                                                                        |
| Billing                                     | `/[org]/settings/billing`                | not-found                                                                                                                                                                                                                                |
| Integrations                                | `/[org]/settings/integrations`           | not-found                                                                                                                                                                                                                                |
| Profile                                     | `/account/profile`                       | default · loading · error                                                                                                                                                                                                                |
| Sign-In Methods                             | `/account/sign-in-methods`               | default (one row: Email link) · loading · error                                                                                                                                                                                          |
| Connected Apps                              | `/account/connected-apps`                | default · empty · stale (30 days unused) · revoke-confirm · loading · error                                                                                                                                                              |
| Notifications                               | `/account/notifications`                 | default · loading · error                                                                                                                                                                                                                |
| Waitlist                                    | `/operator/waitlist`                     | default · selection · empty · invite-confirm · loading · error · not-an-operator (404)                                                                                                                                                   |
| Invitations                                 | `/operator/invitations`                  | default · empty · revoke-confirm · loading · error · not-an-operator (404)                                                                                                                                                               |
| Organisations                               | `/operator/organisations`                | default · empty · loading · error · not-an-operator (404)                                                                                                                                                                                |
| {organisation}                              | `/operator/organisations/[id]`           | default · change-seats · seats-below-used · loading · error · not-found                                                                                                                                                                  |
| Users                                       | `/operator/users`                        | default · empty · loading · error · not-an-operator (404)                                                                                                                                                                                |
| {name}                                      | `/operator/users/[id]`                   | default · loading · error · not-found                                                                                                                                                                                                    |
| Feature Flags                               | `/operator/flags`                        | default · loading · error · not-an-operator (404)                                                                                                                                                                                        |
| Usage                                       | `/operator/usage`                        | default · loading · error · not-an-operator (404)                                                                                                                                                                                        |
| Not found                                   | `*`                                      | default                                                                                                                                                                                                                                  |

### Surfaces outside the web router

The Chrome extension's overlay, side panel and popup, and the Mac app's online parts.

| Surface                                  | Area      | States to capture                                                                                                                     |
| ---------------------------------------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| Toolbar                                  | extension | default · session-active · others-hidden · unknown-environment · no-commit · bridge-mac-app-not-running · loading · error             |
| Pick mode                                | extension | default · hover · info-card · several-selected · no-source-location · component-only · inside-frame                                   |
| Composer                                 | extension | default · code-chip-open · with-moves · docked · disabled · sending · send-failed · restored · element-not-found · parked · discarded |
| Drawing                                  | extension | default · tool-chosen                                                                                                                 |
| Arranging                                | extension | default · dragging · moved · reset                                                                                                    |
| Pin popover                              | extension | default · revised · guest · agent-working · more-pins · hidden-by-choices · loading · error                                           |
| Visibility menu                          | extension | default                                                                                                                               |
| Device picker                            | extension | default · size-larger-than-screen · emulating · emulation-stopped · new-tab-responsive                                                |
| Session bar and menu                     | extension | active · renaming · end-with-drafts · no-comments                                                                                     |
| Keyboard Shortcuts sheet                 | extension | default                                                                                                                               |
| Share Session dialog                     | extension | default · outsider-email · sharing · error                                                                                            |
| Side panel (This Page, Inbox)            | extension | this-page · drafts · empty · outdated · not-visible-here · inbox · signed-out · loading · error                                       |
| Popup                                    | extension | signed-out · default · drafts · toolbar-off-by-default · guest · bridge-lines · token-revoked · offline · error                       |
| Settings > Online                        | mac       | signed-out · waiting-for-browser · signed-in · bridge-on · error                                                                      |
| Share to Workspace sheet and sync status | mac       | not-signed-in · sheet · synced · syncing · offline · sync-stopped · edited-elsewhere · not-shared                                     |

App-wide parts: the app shell (sidebar, collapsed rail, phone drawer), the command menu (⌘K), the shortcuts dialog (`?`), the offline banner, toasts, dialogs and menus, the toolbar on the customer's page.

## How to run it for an audit

- **Build and run:** `npm ci`, then `make dev-db` (your own database, one-time gcloud setup in `README.md`, "Development database"), then `npm run dev` (`http://localhost:3000`). The first real screens arrive with milestone 1; until then only three stub pages answer.
- **Checks:** `npm run format && npm run lint && npm run typecheck && npm test`.
- **Test data:** `<unknown>`; a fixture workspace is planned with the first screens. Never real customer data.
- **Screenshots go to:** `docs/ux/audits/<YYYY-MM-DD>/shots/`.
- **Window sizes:** 1440 px (100 %), 960 px (150 %), and a phone under 640 px.
- **Builds to audit:** `main`, plus open pull requests by URL.

## Safety

- **Never write to:** the production database and the staging database (your `<name>_dev` database only), production at `heydiff.com`, anyone's real inbox (development mail prints to the terminal).
- **Read only:** staging, for comparison.
- **Writes only against:** your own development database, fixtures and fakes.

## Flows for this product

Beyond the minimum list of the skill. Step-by-step wireflows W1 to W12 are in the change spec and summarised in the guidelines.

- Place a comment on one element, send it (scene 1).
- Pick several elements and comment on all (scene 1).
- Draw and move on the live page (scene 1).
- Start a decision, vote, decide, undo (scene 2).
- Agent claims, reports a revision; a member resolves or replies for the next revision (scene 3).
- Reply, vote or resolve from the phone, from the mail link (scene 4).
- Sign in, join by invitation, create the first organisation (all).
- Lose the connection mid-comment and get it back; session expires mid-draft (all).
- A load, a write and a refetch that fail: the states in "States and feedback" (all).
