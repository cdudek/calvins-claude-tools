# HeyDiff roadmap

The product was called Snapmark when this was agreed; it is HeyDiff since 2026-10-28 (`2026-10-28-name-heydiff.md`).

Agreed with the owner on 2026-10-25, from the mockups in `design-explorations/2026-10-25-native-round-2/` and the research in `docs/market/`. Milestones run in this order; each one ships on its own and is one or more PRs.

## M1 — The Native look and the session window

- **Two colour systems.** App UI (buttons, active tool, selected tab, focus) in Decision Violet #6E4EF0 (brand v4, 2026-10-30, replacing the logo blue of 2026-10-25); annotations in the colour the owner picks. The main button is Filled violet; gradients stay in the mark and brand artwork, never in the interface (guide page 07), which settles the open point of 2026-10-25.
- **Annotation palette.** 10 presets (Feedback Coral #E54A74 default and remove, orange #F76B15, amber #FFB224, green #30A46C approve, teal #12A594, cyan #05A2C2, Version Blue #226AE6, violet #8B3DFF, pink #EF28A7, graphite #2C2C31) plus Custom… (the macOS colour panel). The default and the blue preset moved to the brand v4 colours on 2026-11-01.
- **Numbered markers as diamonds** (the logo's shape), in the annotation colour.
- **Cards look like speech bubbles**: the text card keeps its pointer line and gets a bubble tail; no new tool.
- **Screenshot count** in the editor toolbar and the session window header.
- **Session window:** Document · Screenshots · Discarded tabs; Screenshots is a grid with Edit Again; Discarded lists what was thrown away in the last 7 days with Reopen; the title renames in place. Discarded per session or for all sessions: still open.

## M2 — Window capture, Copy and Save As

- Capture one window with a clean crop, next to region and last area.
- Copy the marked-up image (⌘C) and Save As… from the editor, without adding it to a session.

## M3 — Scrolling capture

- Capture a page taller than the screen in one screenshot, then mark it up as usual.

## M4 — OCR and auto-redact

- OCR: the text in a screenshot goes into session.md next to the notes, so the agent can read what the image shows.
- Auto-redact, built on the same text recognition: finds emails, keys and tokens and pixelates them before an image leaves the Mac (copy, Save As, export).

## M5 — One-shot mode

- A second mode beside session mode: capture → beautify → copy or save one image, no session.
- Beautify: padding, rounded corners, shadow, background (gradients, none), ratio presets (Auto, 4:3, 3:2, 16:9, 1:1), one saved preset. Session mode stays as it is.

## M6 — Selling it (replaced 2026-10-27)

Replaced by the online-service decisions (`2026-10-27-snapmark-online.md`, section 9): the Mac app and the extension are free; money comes from online seats ($4 per seat per month billed yearly, $6 monthly). The earlier plan was $12.99 one-off through a merchant of record, with licence terms naming the update period (BGB §327h) and download consent (§356(6)); none of that is needed for a free app. The prices show in release 1 (from 1 Nov 2026); online billing and checkout ship in release 2 (`2026-10-31-pricing-display-and-tax.md`): Europe or unknown country sees EUR incl. VAT, everyone else USD + tax, the country from Cloudflare; Paddle or Stripe is decided in release 2.
