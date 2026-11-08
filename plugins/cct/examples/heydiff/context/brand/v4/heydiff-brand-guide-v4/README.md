# HeyDiff brand guide v4, export

Exported 30 Oct 2026 from the HeyDiff Brand Guide canvas (https://claude.ai/artifact/Pqz7YxXwnWB3666JzAsXxv). Owner: Calvin Dudek. The canvas stays the place to change the guide; this folder is a snapshot for reading, sharing and for AI agents.

## Where to start

- **Coding agents building the design system:** start with `implementation-brief.md`.
- **Agents:** read `llms.txt`, then `decisions.md` for the rules in short, then the page you need in `md/` and look at its screen in `png/`.
- **People:** open `heydiff-brand-guide-v4.pdf` (one page per board, bookmarked) or `overview.png` for all pages at a glance.
- **Code:** `tokens/tokens.json` and `tokens/tokens.css` hold the guide's colour tokens, light and dark. heydiff-kit `packages/tokens` is the source of truth in code.
- **Logo files:** `heydiff-context/brand/v4`. Place those files; never rebuild the lockup.

## What is in here

| Path | What |
| --- | --- |
| `heydiff-brand-guide-v4.pdf` | All pages in one PDF, selectable text, a bookmark per page, page 1 is the overview |
| `overview.png` | Every page as a thumbnail |
| `png/` | Every board as a 1x screen, named by page number |
| `md/` | Every board's text as Markdown, with links to its screen |
| `brand-guide.md` | All pages' text in one file, in page order |
| `html/` | Every board as a standalone HTML page (images inlined, fonts from Google Fonts) |
| `implementation-brief.md` | What to build, in which repo, in which order, and when it is done |
| `decisions.md` | The rules and decisions, one line each, with the page to read |
| `tokens/` | Colour, status, brand, type, control and radius tokens |
| `manifest.json` | Machine-readable index: page, title, group, theme, size, file paths, PDF page |
| `source/boards/` | The canvas boards (`.dc.html`) and `canvas.json` as published |
| `source/scripts/` | The scripts that build the boards, logo files and this export (paths point at the session that made them) |

## Notes

- The Markdown is extracted from the rendered boards. Mock-up screens inside a page (menus, panels, landing sections) come out as their visible text, so read them next to the screen.
- Dark boards 17, 31, 33 and 34 are the same pages rendered in the dark theme.
- Appendix A1 and A2 images were rebuilt from the logo generator for this export; spacing in their lockups can differ slightly from the canvas thumbnails.

## Pages

| Page | Title | Theme | Screen | Text | HTML | PDF page |
| --- | --- | --- | --- | --- | --- | --- |
| 00 | 00 Contents | light | [png](png/00-contents.png) | [md](md/00-contents.md) | [html](html/00-contents.html) | 2 |
| 01 | 01 Cover | light | [png](png/01-cover.png) | [md](md/01-cover.md) | [html](html/01-cover.html) | 3 |
| 02 | 02 Positioning | light | [png](png/02-positioning.png) | [md](md/02-positioning.md) | [html](html/02-positioning.html) | 4 |
| 03 | 03 Logo | light | [png](png/03-logo.png) | [md](md/03-logo.md) | [html](html/03-logo.html) | 5 |
| 04 | 04 Lockup and spacing | light | [png](png/04-lockup-and-spacing.png) | [md](md/04-lockup-and-spacing.md) | [html](html/04-lockup-and-spacing.html) | 6 |
| 05 | 05 Logo use | light | [png](png/05-logo-use.png) | [md](md/05-logo-use.md) | [html](html/05-logo-use.html) | 7 |
| 06 | 06 Name | light | [png](png/06-name.png) | [md](md/06-name.md) | [html](html/06-name.html) | 8 |
| 07 | 07 Artwork and gradients | light | [png](png/07-artwork-and-gradients.png) | [md](md/07-artwork-and-gradients.md) | [html](html/07-artwork-and-gradients.html) | 9 |
| 08 | 08 Colour palette | light | [png](png/08-colour-palette.png) | [md](md/08-colour-palette.md) | [html](html/08-colour-palette.html) | 10 |
| 09 | 09 Product colour | light | [png](png/09-product-colour.png) | [md](md/09-product-colour.md) | [html](html/09-product-colour.html) | 11 |
| 10 | 10 Typography | light | [png](png/10-typography.png) | [md](md/10-typography.md) | [html](html/10-typography.html) | 12 |
| 11 | 11 Voice | light | [png](png/11-voice.png) | [md](md/11-voice.md) | [html](html/11-voice.html) | 13 |
| 12 | 12 Visual language | light | [png](png/12-visual-language.png) | [md](md/12-visual-language.md) | [html](html/12-visual-language.html) | 14 |
| 13 | 13 In use | light | [png](png/13-in-use.png) | [md](md/13-in-use.md) | [html](html/13-in-use.html) | 15 |
| 14 | 14 Templates | light | [png](png/14-templates.png) | [md](md/14-templates.md) | [html](html/14-templates.html) | 16 |
| 15 | 15 Layout | light | [png](png/15-layout.png) | [md](md/15-layout.md) | [html](html/15-layout.html) | 17 |
| 16 | 16 Tokens | light | [png](png/16-tokens.png) | [md](md/16-tokens.md) | [html](html/16-tokens.html) | 18 |
| 17 | 17 Components / Light | light | [png](png/17-components-light.png) | [md](md/17-components-light.md) | [html](html/17-components-light.html) | 19 |
| 17 | 17 Components / Dark | dark | [png](png/17-components-dark.png) | [md](md/17-components-dark.md) | [html](html/17-components-dark.html) | 20 |
| 18 | 18 Component rules | light | [png](png/18-component-rules.png) | [md](md/18-component-rules.md) | [html](html/18-component-rules.html) | 21 |
| 19 | 19 Navigation | light | [png](png/19-navigation.png) | [md](md/19-navigation.md) | [html](html/19-navigation.html) | 22 |
| 20 | 20 Overlays and menus | light | [png](png/20-overlays-and-menus.png) | [md](md/20-overlays-and-menus.md) | [html](html/20-overlays-and-menus.html) | 23 |
| 21 | 21 Forms | light | [png](png/21-forms.png) | [md](md/21-forms.md) | [html](html/21-forms.html) | 24 |
| 22 | 22 System feedback | light | [png](png/22-system-feedback.png) | [md](md/22-system-feedback.md) | [html](html/22-system-feedback.html) | 25 |
| 23 | 23 Tables | light | [png](png/23-tables.png) | [md](md/23-tables.md) | [html](html/23-tables.html) | 26 |
| 24 | 24 Files, search and structure | light | [png](png/24-files-search-and-structure.png) | [md](md/24-files-search-and-structure.md) | [html](html/24-files-search-and-structure.html) | 27 |
| 25 | 25 Pins and threads | light | [png](png/25-pins-and-threads.png) | [md](md/25-pins-and-threads.md) | [html](html/25-pins-and-threads.html) | 28 |
| 26 | 26 Decisions and agents | light | [png](png/26-decisions-and-agents.png) | [md](md/26-decisions-and-agents.md) | [html](html/26-decisions-and-agents.html) | 29 |
| 27 | 27 Code and selections | light | [png](png/27-code-and-selections.png) | [md](md/27-code-and-selections.md) | [html](html/27-code-and-selections.html) | 30 |
| 28 | 28 Giving feedback | light | [png](png/28-giving-feedback.png) | [md](md/28-giving-feedback.md) | [html](html/28-giving-feedback.html) | 31 |
| 29 | 29 Chrome extension | light | [png](png/29-chrome-extension.png) | [md](md/29-chrome-extension.md) | [html](html/29-chrome-extension.html) | 32 |
| 30 | 30 Mac app | light | [png](png/30-mac-app.png) | [md](md/30-mac-app.md) | [html](html/30-mac-app.html) | 33 |
| 31 | 31 Journey / Light | light | [png](png/31-journey-light.png) | [md](md/31-journey-light.md) | [html](html/31-journey-light.html) | 34 |
| 31 | 31 Journey / Dark | dark | [png](png/31-journey-dark.png) | [md](md/31-journey-dark.md) | [html](html/31-journey-dark.html) | 35 |
| 32 | 32 Journey on a phone | light | [png](png/32-journey-on-a-phone.png) | [md](md/32-journey-on-a-phone.md) | [html](html/32-journey-on-a-phone.html) | 36 |
| 33 | 33 Example screen / Light | light | [png](png/33-example-screen-light.png) | [md](md/33-example-screen-light.md) | [html](html/33-example-screen-light.html) | 37 |
| 33 | 33 Example screen / Dark | dark | [png](png/33-example-screen-dark.png) | [md](md/33-example-screen-dark.md) | [html](html/33-example-screen-dark.html) | 38 |
| 34 | 34 Landing page / Light | light | [png](png/34-landing-page-light.png) | [md](md/34-landing-page-light.md) | [html](html/34-landing-page-light.html) | 39 |
| 34 | 34 Landing page / Dark | dark | [png](png/34-landing-page-dark.png) | [md](md/34-landing-page-dark.md) | [html](html/34-landing-page-dark.html) | 40 |
| 34 | 34 Landing footer / Phone | light | [png](png/34-landing-footer-phone.png) | [md](md/34-landing-footer-phone.md) | [html](html/34-landing-footer-phone.html) | 41 |
| 35 | 35 Assets and ownership | light | [png](png/35-assets-and-ownership.png) | [md](md/35-assets-and-ownership.md) | [html](html/35-assets-and-ownership.html) | 42 |
| A1 | A1 Appendix / Ratio test | light | [png](png/a1-appendix-ratio-test.png) | [md](md/a1-appendix-ratio-test.md) | [html](html/a1-appendix-ratio-test.html) | 43 |
| A2 | A2 Appendix / Mark exploration | light | [png](png/a2-appendix-mark-exploration.png) | [md](md/a2-appendix-mark-exploration.md) | [html](html/a2-appendix-mark-exploration.html) | 44 |
| A3 | A3 Appendix / Golden ratio research | light | [png](png/a3-appendix-golden-ratio-research.png) | [md](md/a3-appendix-golden-ratio-research.md) | [html](html/a3-appendix-golden-ratio-research.html) | 45 |
| A4 | A4 Appendix / Wordmark grey test | light | [png](png/a4-appendix-wordmark-grey-test.png) | [md](md/a4-appendix-wordmark-grey-test.md) | [html](html/a4-appendix-wordmark-grey-test.html) | 46 |
