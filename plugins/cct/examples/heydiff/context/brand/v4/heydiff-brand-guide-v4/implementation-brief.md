# Implementation brief: HeyDiff design system v4

For the coding agents in `heydiff-kit`, `heydiff-web`, `heydiff-chrome` and, once it exists, `heydiff-mac`. From Calvin Dudek (owner), 30 Oct 2026.

## The ask

Build brand guide v4 into the products: tokens and components in heydiff-kit first, then the web app, the landing page, the Chrome extension, and the Mac app when its repo exists. The guide is decided. Build to it; do not redesign it. Anything the guide leaves open goes to the owner as a question, it does not get decided in code.

## Sources and what wins

1. This brief and `decisions.md` (same folder): the decisions.
2. The guide pages in this folder: `md/` for text, `png/` for the screen. Page 16 wins on token values; the screen pages win on layout.
3. The heydiff-web spec (`heydiff-web/changes/2026-10-27-online-release-1/spec/`) for behaviour, words and states. Where it differs from the guide on look (colour, type, sizes, radius, focus, links, danger, logo, icons), the guide wins. Record that as a decision in each repo (see Process).
4. Current code.

The canvas (https://claude.ai/artifact/Pqz7YxXwnWB3666JzAsXxv) is the master but needs the owner's login. Agents work from this export.

## Resources

Paths are relative to `~/projects/heydiff/`.

| What | Where |
| --- | --- |
| This export (start with `llms.txt`) | `heydiff-context/brand/v4/heydiff-brand-guide-v4/` |
| Decisions, one line each | `.../heydiff-brand-guide-v4/decisions.md` |
| Every page as text / screen / standalone HTML | `.../md/`, `.../png/`, `.../html/` |
| Whole guide as one PDF, bookmarked | `.../heydiff-brand-guide-v4.pdf` |
| Guide tokens, light and dark | `.../tokens/tokens.json`, `.../tokens/tokens.css` |
| Page index with file paths | `.../manifest.json` |
| Logo masters (SVG, PNG, app icons, favicon) | `heydiff-context/brand/v4/` |
| Mac menu bar template icons | `heydiff-context/brand/v4/mac-menubar/` |
| Canvas boards and build scripts | `.../source/` |

## What changes in heydiff-kit (today → v4)

| | Today (kit `milestone/online-release-1-3`) | v4 |
| --- | --- | --- |
| Accent | Clear Sky `#0f72db` | Decision Violet `#6E4EF0`, dark `#7357F6` |
| Focus ring | neutral (`#b2b8c0` dark) | violet 2 px, keyboard only: `#8071FE` light, `#9A98FF` dark |
| Links | underlined text | violet |
| Danger | tonal | solid `#CA3429`, white text |
| UI font | Inter | Plus Jakarta Sans |
| Mono font | system mono | JetBrains Mono |
| Controls | 28 / 32 / 40 | 32 / 40 / 48, app default 32 |
| Radius | 8 / 12 / 999 | 6 / 12 / 16 / 24 / 999 (see below) |
| Dark neutrals | `#0b1015` ground, `#13181e` panel | Graphite: `#121214` canvas, `#19191C` surface |
| Status colours | open grey, deciding amber, progress teal, revised purple | open coral, deciding violet, progress blue, revised amber, resolved green |
| Logo | placeholder S in `LogoMark` | mark A from `brand/v4`; `--logo-blue` goes |

Keep the kit's theme behaviour (dark by default, light by system setting or `data-theme`) unless the owner says otherwise. Change values in `packages/tokens/design/overlay.json`; do not rename system roles (the overlay's own rule). Add product roles with the `x-` prefix where the system has none.

## Token mapping (guide value → kit role)

| Kit role | Light | Dark | Guide name |
| --- | --- | --- | --- |
| ground | `#F8F9FC` | `#121214` | bg (canvas) |
| panel | `#FFFFFF` | `#19191C` | surface |
| raise | `#F0F2F7` | `#232327` | surface2 |
| overlay, lift | `#FFFFFF` | `#19191C` plus the ring shadow | surface (menus, popovers: page 20) |
| edge | `#E3E6EE` | `#303036` | border (dividers only, 1.3:1) |
| edge-hi | `#808695` | `#6B6B74` | border.control (3:1 or more) |
| ink | `#101627` | `#F7F7F8` | text |
| dim | `#494F61` | `#D2D2D7` | text.muted |
| faint | `#626979` | `#9C9CA5` | text.subtle |
| accent | `#6E4EF0` | `#7357F6` | accent |
| on-accent | `#FFFFFF` | `#FFFFFF` | |
| accent-wash | `#EAEDFF` | `#2D274C` | accent soft |
| accent-text | `#5A3CC3` | `#BABEFE` | accent text |
| focus | `#8071FE` | `#9A98FF` | focus |
| error | `#CA3429` | `#CA3429` | danger (solid) |
| error-wash / error-text | `#FFF4F2` / `#A4271E` | `#3E2323` / `#FFAB9E` | |
| keep-wash / keep-text | `#F0F9F4` / `#026E43` | `#1A322A` / `#89D9AB` | success |
| warn-wash / warn-text | `#FBF6EE` / `#824F01` | `#3A2D18` / `#ECBB70` | warning |
| info-wash / info-text | `#F4F7FE` / `#1155BC` | `#1B2944` / `#A7C4FF` | info |

Shadows: light `0 1px 2px rgba(16,22,39,.06), 0 2px 12px rgba(16,22,39,.04)` (sm), `0 4px 16px rgba(16,22,39,.10)` (md), `0 16px 40px rgba(16,22,39,.16)` (lg). Dark uses a 1 px ring in `#303036` plus a darker drop shadow (`tokens.json`).

### Status tokens (page 16, both themes; text ratios 5.9 to 9.5)

| Status | Light bg / text | Dark bg / text | Dot |
| --- | --- | --- | --- |
| Open | `#FEF4F6` / `#A42044` | `#3E222C` / `#FFA7BB` | `#E54A74` |
| Deciding | `#F5F6FE` / `#5A3CC3` | `#2D274C` / `#BABEFE` | `#6E4EF0` |
| In Progress | `#F4F7FE` / `#1155BC` | `#1B2944` / `#A7C4FF` | `#226AE6` |
| Revised | `#FBF6EE` / `#824F01` | `#3A2D18` / `#ECBB70` | `#BC7B07` |
| Resolved | `#F0F9F4` / `#026E43` | `#1A322A` / `#89D9AB` | `#1DA469` |
| Guest (role) | `#F0F2F7` / `#494F61` | `#2A2A2F` / `#D2D2D7` | |
| Agent (role) | `#101627` / `#FFFFFF` | `#F7F7F8` / `#121214` | |

A status is always a tinted background, the text, a dot and the word. Colour is never the only signal. Some guide boards draw the Deciding chip on `#EAEDFF`; page 16 is the spec.

## Type, size, shape, motion

- **Families:** Plus Jakarta Sans 400 to 800, JetBrains Mono 400 to 600. Self-host both (next/font or files in the kit), not the Google Fonts CDN, which sends visitor IPs to Google.
- **Scale (size/line, weight, tracking):** 64/68 800 -3.5%; 44/50 800 -3%; 32/40 700 -2%; 22/30 700 -1.5%; body L 18/28 400; body 16/24 400; UI 14/20 500; caption 12/16 500; code 13/20 400 mono; label 11/16 600 mono +6% uppercase. Sentence case everywhere else; ExtraBold only for display and the wordmark. [page 10]
- **Controls:** 32 / 40 / 48 px; touch targets 44 or more. [page 16]
- **Radius:** 999 buttons, chips, switches, avatars, segmented controls; 6 checkboxes, keys, code and file tags; 12 fields, menus, popovers, tooltips, table frames; 16 cards, toasts, alerts, panels; 24 dialogs, drawers, sheets. A nested corner is the outer radius minus the padding. [page 15]
- **Buttons:** Filled (kit `filled`, HeroUI `primary`, one per region, last in its row), Tonal (`tonal` / `secondary`), Outlined (`outlined` / `outline`), Text (`text` / `ghost`), Danger (`danger`, solid red). [page 16, 17]
- **State layers:** hover 8%, pointer only; focus 10% plus the ring, keyboard only; pressed 10% plus a ripple from the press point; disabled 38%. Filled and Danger take a black layer, the others a layer in the text colour. Rendered Filled hover is `#6548DD` light, `#6A50E2` dark. Rows, menu items, chips and tabs use the layers without the ripple. Size never changes on press. [page 16]
- **Motion:** instant 120 ms (state layers, tooltips), quick 160 (exits, ripple fade), standard 200 (menus, popovers, pins, toasts), considered 240 (dialogs, panels, ripple growth). Ease standard `(0.2, 0, 0, 1)`, emphasised `(0.16, 1, 0.3, 1)` for entering surfaces. Only opacity and transform animate. Reduced motion: no distance, fades at 120 ms, ripple becomes a flat 10% layer. [page 16]
- **Icons:** Lucide, 2 px stroke, 16 in rows and chips, 20 in toolbars, 24 alone. Comment, the action, is the comment bubble with a plus (Lucide `message-square-plus`). A pin on the page is the numbered avatar pin (page 25), never a map pin. An icon alone needs an aria-label and a tooltip. [page 12]

## Milestones, in order

Each one ends green in its repo and is usable on its own. Kit milestones release a kit version before an app takes it.

### M1 Tokens (heydiff-kit, `packages/tokens`)

- Values from the tables above into `design/overlay.json` (light value, dark in `$extensions.mode.dark`), status tokens included; fonts, controls, radius, focus, motion.
- Rebuild with `npm run build -w @pokbytes/heydiff-tokens`; HeroUI and Tailwind themes follow.
- Pages: 08, 09, 15, 16.
- Done when: `tokens.css` carries every value above in both themes, the raw-colour and motion lint rules pass, and every text pair meets 4.5:1 and every control edge and focus ring 3:1.

### M2 Components (heydiff-kit, `packages/ui`)

- Button kinds, sizes, state layers and ripple; Chip and status chips; fields, select, autocomplete; menus, popovers, tooltips, dialogs, drawers; tables; toasts and alerts; Link in violet; Kbd; avatars with the agent badge; empty, error and loading states; command menu (⌘K means one thing, page 19).
- `LogoMark` draws mark A from `heydiff-context/brand/v4/heydiff-mark.svg` (gradient, 24 px and up) and `heydiff-mark-flat.svg` (under 24 px). Add a lockup component that places `heydiff-logo-primary.svg` / `heydiff-logo-reverse.svg`; never rebuild the lockup from the mark and text. Remove `--logo-blue`.
- Pages: 17 to 24, plus 25 to 27 for pins, threads, decisions, agents and code.
- Done when: each component matches its page in light and dark at 100%, keyboard focus shows the ring only for keyboard, and the component tests pass.

### M3 Logo and icons in the apps

- heydiff-web: favicon (`heydiff-favicon.svg`, `png/favicon-16.png`, `favicon-32.png`), `apple-touch-icon-180.png`, app icons, the lockup in the header and footer.
- heydiff-chrome: extension icons 16 and 32 from the flat mark, 48 and 128 from the gradient mark; the toolbar's More button shows the flat mark.
- Pages: 03 to 07, 35.
- Done when: no placeholder S remains anywhere (`grep` for the old LogoMark glyph and `--logo-blue` is empty).

### M4 Web app (heydiff-web)

- Take the new kit release. Bring the screens to the guide: dashboard and inbox (page 33), pins and threads (25), decisions and agents (26), code and selections (27), the journey (31, 32 for phones), navigation and overlays (19, 20), forms, feedback states and tables (21 to 24).
- Write the decision record that superseded Clear Sky (see Process) and update `spec/colour.md`, `motion.md` and `interaction.md` where they still say Clear Sky, Inter, neutral focus, underlined links or tonal danger.
- Done when: each screen's headless screenshot matches its guide page in light and dark, and the E2E suite passes.

### M5 Landing page (heydiff-web, `src/app/[locale]/(public)/page.tsx`, `src/features/public/PublicPage.tsx`)

- Build page 34 (light and dark) with its sections, the before-and-after, pricing and FAQ. Copy as on the page.
- Prices: Free EUR 0; Team EUR 4 per seat a month billed yearly, EUR 6 monthly; Enterprise later.
- Claims: hosted in the EU (compute in Belgium, storage in the EU); "Emails, keys and tokens are pixelated on your device before upload." Auto-redaction is a launch requirement in `heydiff-context/strategy/2026-10-27-snapmark-online.md` (decision 9); release 1 only has the manual Redact tool. Keep the line behind a flag until detection ships, or ask the owner.
- Footer: logo and "From the first hey / to the final diff." (26 px, medium, two lines) on half the width; Product (How it works, Pricing, Chrome extension, Mac app) and Resources (MCP setup, Changelog, Status, Contact). Bottom row: "Made with ♥ in Hamburg." left with a small coral heart, then Privacy, Terms, Imprint and "© 2026 HeyDiff" right. 64 px above, 48 px before the divider, 28 px below, inside the 1200 px content width with 24 px margins. Under 720 px: brand first, the two link columns side by side, legal links wrap (board "34 Landing footer / Phone"). llms.txt is not a footer link; it belongs in the developer docs.
- Done when: the page matches page 34 at 1440 px and the phone footer at 390 px, an axe check finds no violations, and fonts load self-hosted.

### M6 Chrome extension (heydiff-chrome)

- Toolbar, pick mode, composer, drawing tools, side panel and popup as on page 29, giving feedback step by step as on page 28. The Comment button uses `message-square-plus`.
- The spec stays `heydiff-web/changes/2026-10-27-online-release-1/spec/screens/extension.md`; the guide only changes the look.
- Done when: every screen state in extension.md renders with the kit tokens and matches pages 28 and 29.

### M7 Mac app (heydiff-mac, once the repo exists)

- Page 30 is a proposal built on `heydiff-context/strategy/2026-10-29-new-mac-app-brief.md` and the brainstorm next to it. Start when the owner turns those into decisions.
- Decided already: menu bar icon is the knockout mark as a template image, `heydiff-context/brand/v4/mac-menubar/iconTemplate.png` and `@2x` (a waiting variant with the cut dot is next to it); a click opens the HeyDiff panel (Pick an Element, Region, inbox, running apps), closes on Esc, a click outside or a second click; the native menu is the fallback.
- Done when: the icon tints correctly on light, dark and highlighted menu bars, and the panel matches page 30.

## Rules for every repo

- Place the logo files. Never retype the wordmark, recolour the mark, or put gradients in the product UI; gradients are for the mark and brand artwork only.
- The wordmark is lower case and one colour. The name in text is HeyDiff.
- One Filled button per region. Danger only confirms what cannot be undone.
- No raw colours or sizes in components; tokens only (the kit's lint rules).
- Contrast: text 4.5:1, control edges, focus ring and meaningful icons 3:1.
- Words: page 11 (voice) and the product glossary (`heydiff-web/docs/ux/glossary-proposal.md`): Comment, Pin, Revision, Decision and the five statuses. Prices with currency codes (EUR).

## Process

- Follow each repo's SDLC (`docs/sdlc.md`): one change per repo, started from this brief. Quote the asks from this brief in `intent.md`.
- Copy the guide pages a milestone uses (their `png/` and `md/` files) into `changes/<id>/asks/2026-10-30/` and link the rest of this folder.
- Record the look change as a decision of its own in `docs/designs/` (an ADR that supersedes Clear Sky, Inter and the old sizes), then run `python3 scripts/design_index.py write`.
- Track tasks in beads (`bd`), as the repos' `AGENTS.md` says.
- Order: M1 and M2 in heydiff-kit and a kit release first; M3 to M6 can run in their repos after that; M7 waits for the Mac app decisions.

## Open, for the owner

- Theme default: the kit is dark first; the guide shows both themes. Kept as it is unless decided.
- The landing's redaction line before auto-detection ships.
- Where llms.txt lives in the developer docs.
- Mac app scope (page 30 is a proposal).
