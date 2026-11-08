# HeyDiff context

Strategy for HeyDiff: why it exists, who it is for, what it costs, what comes next. No code. Every code repo's `CLAUDE.md` imports this file.

## The repos

One repo per product, all checked out under `~/projects/heydiff/`, each folder named like its repo. The product was called Snapmark until 2026-10-28 (`strategy/2026-10-28-name-heydiff.md`); GitHub redirects the old repo names.

- [heydiff-context](https://github.com/pokbytes/heydiff-context) (`~/projects/heydiff/heydiff-context`): this repo; strategy, audiences, decisions.
- [heydiff-desktop](https://github.com/pokbytes/heydiff-desktop) (`~/projects/heydiff/heydiff-desktop`): the Mac app only (HeyDiff for Mac).
- [heydiff-web](https://github.com/pokbytes/heydiff-web) (`~/projects/heydiff/heydiff-web`): HeyDiff, the team service; web app, landing, operator area, API, MCP. Holds the online plan (`changes/`, `docs/designs/`) for the extension and the infrastructure too.
- [heydiff-chrome](https://github.com/pokbytes/heydiff-chrome) (`~/projects/heydiff/heydiff-chrome`): the Chrome extension.
- [terraform-infra](https://github.com/pokbytes/terraform-infra) (`~/projects/heydiff/terraform-infra`): Terraform for the GCP project `heydiff`. The old project `snapmark-ai` still holds the Mac app's release pipeline until the Mac app's new ids ship.

## What is where

- `strategy/roadmap.md`: the agreed milestones (M1 to M6).
- `strategy/2026-10-28-name-heydiff.md`: the name HeyDiff, the story behind it, why the product exists, the positioning, and what the rename changes.
- `strategy/2026-10-28-hosting-and-data-residency.md`: compute in Belgium (europe-west1), Cloud Storage and BigQuery in the EU, scale to zero, deploy on merge to `main`.
- `strategy/2026-10-31-pricing-display-and-tax.md`: prices in release 1 (EUR incl. VAT for Europe or unknown, USD + tax elsewhere, country from Cloudflare); checkout and billing in release 2, Paddle or Stripe still open.
- `strategy/2026-10-27-snapmark-online.md`: the team service (written as "Snapmark online"), with the owner's decisions in section 9.
- `market/2026-10-25-pricing-research.md`: competitor prices and pricing options.
- `market/2026-10-25-feature-comparison.md`: feature-by-feature comparison with competitors.
- `market/2026-10-25-marketing-brief.md`: positioning and message.
- `market/2026-10-25-mac-app-store.md`: Mac App Store vs direct sale.
- `design-system.md`: where the design system and brand rules live.
- `scripts/brand-check.mjs`: finds retired brand values (the brand v3 colours, font and theme name, and wrong spellings of the name) outside the history paths in `scripts/brand-retired.json`; run `node scripts/brand-check.mjs`, no install needed.
- `brand/v4/`: the logo master files (mark A, gradient; flat only under 24 px). `brand/explorations/`: the other mark variants, kept for a later change. `brand/v3/` is retired.
- `audience/audiences.md`: primary and secondary audiences (decided).
- `audience/jobs-to-be-done.md`: the jobs across roles, step by step, and how to measure them (draft).
- `audience/personas.md`: personas, goals and jobs per role (draft).
- The product's UX rules stay in the code repos' `docs/ux/` (`setup.md`, `interaction-guidelines.md`, `glossary-proposal.md`, `owner-words.md`, `sitemap.md`), because the UX skills read and write them there:
  - Mac app: `heydiff-desktop/docs/ux/`.
  - HeyDiff, the team service (web app, Chrome extension, landing, operator): `heydiff-web/docs/ux/`. The web UX docs moved there from the desktop repo on 2026-10-28.

## Rules

- A strategic decision (price, audience, positioning, scope, brand) is written here, dated, with what was chosen over what.
- Newer decisions win. When one replaces an older one, update the older file and say so; do not leave both standing.
- Sources are cited as URLs, never as local paths.
