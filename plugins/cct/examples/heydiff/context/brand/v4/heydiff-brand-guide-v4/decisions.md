# HeyDiff brand decisions, guide v4

As of 30 Oct 2026. Owner: Calvin Dudek. The full reasoning is on the pages named in brackets; the canvas is the source for the guide, heydiff-kit for tokens in code.

## Logo

- **Mark A, coral left, blue right.** Two speech bubbles, each 40 x 36 with corner radius 6 and one square outer corner, sheared 16.7 degrees; the front bubble sits 8 right and 4 down. Violet where they overlap. Chosen on 30 Oct 2026 over mark F (round bubbles with curved tails), which stays in appendix A2 as the record. [03, A2]
- **Wordmark:** lower-case `heydiff`, outlines from Plus Jakarta Sans 800, drawn, never typed. Always one colour; a grey "diff" was tested and not adopted. [03, A4]
- **Lockup 5:4:** mark 5 units, wordmark 4, gap 1 unit, clear space the height of the e. At least 24 px tall; under 24 px use the mark alone, flat, from 16 px. [04]
- **Files:** place the masters in `heydiff-context/brand/v4` (primary, reverse, flat, mono, mark, app icons, favicon, PNG). `brand/v3` (mark F) and earlier exports are retired. [35]
- **Gradients live in the mark** and in brand artwork only (covers, social, slides), never in the product UI. [07]

## Colour

- **Brand colours:** Feedback Coral (the hey, gradient #FFB46A to #F25A82), Version Blue (the build, #22B7F2 to #226AE6), Decision Violet (the diff, #9B5CF6 to #6E4EF0). [01, 08]
- **Product accent:** Decision Violet #6E4EF0, dark #7357F6, replacing Clear Sky blue. One Filled button per region. [09, 16]
- **Focus:** violet ring, 2 px, keyboard focus only: #8071FE light, #9A98FF dark. **Links:** violet. [16]
- **Danger:** solid red #CA3429 with white text. [16, 17]
- **Dark mode:** Graphite, canvas #121214, surface #19191C. [09]
- **Statuses:** Open, Deciding, In Progress, Revised, Resolved. Each is a tinted background, text, a dot and always the word; colour is never the only signal. [16]

## Type

- Plus Jakarta Sans for brand and app, 13 and 14 px for UI text. JetBrains Mono for code, ids and labels. [10]

## Components

- Control heights 32 / 40 / 48 px, app default 32. [16, 17]
- Radius: 999 for buttons, chips, switches, avatars and segmented controls; 6 for checkboxes, keys and code tags; 12 for fields, menus, popovers, tooltips and table frames; 16 for cards, toasts, alerts and panels; 24 for dialogs, drawers and sheets. [15]
- Button kinds: Filled, Tonal, Outlined, Text, Danger. Pressed shows a ripple at 10 percent; under reduced motion a flat 10 percent layer. [17]
- Built on HeroUI v3 with the HeyDiff theme. [17]
- Icons: Lucide line icons, 2 px stroke. Comment, the action, uses the comment bubble with a plus (Lucide message-square-plus); a pin on the page is the numbered avatar pin, never a map pin. [12, 25]

## Products

- **Chrome extension:** toolbar, pick mode, composer, side panel and popup as in heydiff-web's extension spec. [29]
- **Mac app (proposal):** a new Electron app in `heydiff-mac`. Menu bar icon: the knockout mark as a template image, 16 pt, a cut dot when something waits. A click opens the HeyDiff panel (inbox, Pick an Element, Region, running apps); a native menu is the fallback. [30]
- **Landing page:** prices Free EUR 0, Team EUR 4 per seat a month billed yearly (EUR 6 monthly), Enterprise later. Hosted in the EU (compute in Belgium, storage in the EU). Emails, keys and tokens are pixelated on the device before upload, a launch requirement in the strategy. [34]
- **Landing footer:** "From the first hey to the final diff." beside Product and Resources; bottom row "Made with ♥ in Hamburg." left, Privacy, Terms, Imprint and © 2026 HeyDiff right; on phones the brand first, two link columns, legal links wrap. [34]

## Changing a rule

Comment on the canvas page, the owner decides in the thread, the page and heydiff-kit change together, then log it on page 35: v4.1 adds, v5 changes a rule.
