# Design system

## Brand v4 (2026-10-30, owner)

Decided in the HeyDiff Brand Guide (https://claude.ai/artifact/Pqz7YxXwnWB3666JzAsXxv), version 4. It replaced the colour, type and logo decisions of 2026-10-25 and 2026-10-28 (brand v3), which are no longer listed here; heydiff-kit and the web spec follow it.

- **Accent:** Decision Violet `#6E4EF0` (dark `#7357F6`) is the one filled accent, one Filled button per region, chosen over the blue accent of brand v3 (2026-10-28). Focus ring and links are violet too.
- **Type:** Plus Jakarta Sans for brand and app, JetBrains Mono for code, chosen over the sans-serif of brand v3.
- **Controls:** 32 / 40 / 48 px (app default 32), chosen over 28 / 32 / 40. Pill buttons and chips, 12 px fields and menus, 24 px dialogs, chosen over 8 px everywhere.
- **Buttons:** Filled, Tonal, Outlined, Text, Danger (solid red). Pressed shows the ripple.
- **Dark mode:** Graphite neutrals (`#121214` canvas, `#19191C` surface).
- **Logo:** mark A, two speech bubbles with one square corner each (coral left, blue right, violet overlap), lower-case wordmark `heydiff`, 5:4 lockup, one colour wordmark. Chosen on 2026-10-30 over mark F (round bubbles with curved tails, brand v3), which stays in the guide as appendix A2. Master files in `brand/v4/`; `brand/v3/`, the 03A pack and earlier exports are retired.
- **Mac menu bar icon:** the knockout mark as a template image (one colour, tinted by macOS), 16 pt, a cut dot when something waits. Chosen on 2026-10-30.
- **Mac menu bar menu:** clicking the icon opens the HeyDiff panel: a frameless window under the icon with the inbox (people, statuses), Pick an Element and Region, and running apps. It takes keyboard focus while open and closes on Esc or a click outside. Chosen on 2026-10-30 over a native macOS menu (the fallback) and click-to-pick.


HeyDiff does not keep its own copy of the design system; it pins one.

- **Source:** [design-system-starter](https://github.com/cdudek/design-system-starter). HeyDiff's own rules are its `examples/snapmark.md` (to be renamed heydiff.md).
- **How the app uses it:** the version is pinned in the Mac repo's `snapmark-app/design/tokens.lock.json` (the folder keeps its name until the Mac app's new ids ship); `npm run tokens` builds it into `snapmark-app/src/tokens.css`. Change the system there, then bump the pin.
- **Brand and mark (2026-10-28, `strategy/2026-10-28-name-heydiff.md`):** HeyDiff is a friendly name with a precise, restrained design. The mark connects a comment, a precise point and a change. No mascot, no AI sparkle, no code brackets. The logo is mark A of brand v4 (above).
- **Annotation colours (2026-10-25; default and blue preset moved to brand v4 colours on 2026-11-01):** annotations use the colour the user picks: 10 presets with Feedback Coral `#E54A74` as default, plus custom. Full list in `strategy/roadmap.md`, M1.
- **Style:** calm and native, HeroUI-like; the accent only on primary buttons; no blue outlines.
- **Icons and logo:** the masters are in `brand/v4/`; place those files, never redraw them (guide page 35).
- **Mockups and visual explorations:** each code repo's `design-explorations/` (Mac app in `heydiff-desktop`, the team service in `heydiff-web`).
