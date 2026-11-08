---
type: ux-setup
updated: <YYYY-MM-DD>
---

# UX setup: <product name>

Every `ux:` skill reads this file first. Keep it short and true.

## The product

- **What it is:** <one sentence>
- **Platform:** web · desktop (Electron, native) · mobile — <which>
- **Audience file:** <path, e.g. AUDIENCE.md> — the scenes the design serves: <list them>
- **Jobs to be done:** <path, or the list here>
- **Products the audience already uses** (for pattern research): <list>

## The rules it must follow

- **Design system:** <path, e.g. DESIGN.md>
- **Glossary:** <path>
- **Voice and writing rules:** <paths or sections>
- **Hard rules** that override UX preferences: <e.g. "the library is read only">
- **Exceptions register:** `docs/ux/exceptions.md` (`EX-<n>`, format in `conflicts.md`)
- **WCAG and EAA scope, one finding per surface:** <surface>: consumer-facing, so WCAG 2.2 AA is
  the legal floor (R1) | business customers only, so WCAG 2.2 AA is R2. Who decided, date,
  reasoning.

## The owner's words

- **File:** <path, e.g. docs/ux/owner-words.md> — every request, verbatim, dated. Quote from it;
  never cite a request by number.
- **Feedback folders:** <paths or globs read for new asks>

## Design inputs

Read by `cct:ux-design-run` and `cct:ux-spec-validate`; `cct:ux-sitemap-create` reads the route source.

- **Route source:** <path, e.g. app router, routes file, or route manifest>
- **Interaction guidelines:** <path, e.g. docs/ux/interaction-guidelines.md, or a router file>
- **Screen goals:** <path, or a section in this file>
- **UI components live in:** <path>
- **Component catalogue:** <path or route that shows the real components>
- **Screenshot recipe at 100 percent:** <command, viewport, zoom, output path>
- **Screenshot recipe at 150 percent:** <command, viewport, zoom, output path>
- **Specs without a change folder:** `docs/ux/specs/<YYYY-MM-DD>-<slug>/`, or <path>

## Where the UX files live

| File | Path |
|---|---|
| Audits | `docs/ux/audits/<YYYY-MM-DD>/` (briefing, evaluator notes, findings, shots) |
| Findings (latest) | `docs/ux/audits/<YYYY-MM-DD>/findings.md` |
| Decision lists (one per round, built by ux:decision) | `docs/ux/decisions-<YYYY-MM-DD>.md` |
| Decisions (one file each, written by ux:decision; listed in `docs/designs/INDEX.md`) | `docs/designs/<YYYY-MM-DD>-adr-<slug>.md` |
| Exceptions register | `docs/ux/exceptions.md` |
| Interaction guidelines | `docs/ux/interaction-guidelines.md` |
| Sitemap, for people (written by `cct:ux-sitemap-create`) | `docs/ux/sitemap.md` |
| Sitemap, for tools: one object per page | `docs/ux/sitemap.json` |
| Glossary proposal | `docs/ux/glossary-proposal.md` |
| Decision page (optional) | <path of the local HTML file> |

## Screens and states

| Screen | Route or entry | States to capture |
|---|---|---|
| <name> | <route> | empty · loading · error · not found · <product-specific> |

App-wide parts: <navigation, header, footer, transport, dialogs, menus, notifications>.

## How to run it for an audit

- **Build and run:** <commands>
- **Test data:** <fixture, cloned data, fake devices; env vars>
- **Screenshots go to:** <path>
- **Window sizes:** <e.g. 1280, 1440, 1920, 2560 wide, and the minimum>
- **Builds to audit:** main, plus <open draft PRs, by URL>

## Safety

- **Never write to:** <user data, real devices, production>
- **Read only:** <e.g. the real device, for checks that need it>
- **Writes only against:** <fakes, fixtures>

## Flows for this product

<Beyond the minimum in rule-areas.md, and which audience scene each belongs to.>
