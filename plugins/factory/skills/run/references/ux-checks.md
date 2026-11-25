# UX checks per screen

Run by `factory:ux-verifier` for every UI milestone. Never Claude in Chrome. Evidence goes to `changes/<slug>/evidence/<milestone>/`.

## Capture path per surface
- **Web:** the `agent-browser` CLI. Check `command -v agent-browser` first; if it is not on PATH, use `npx agent-browser`.
- **Chrome extension:** Playwright with the unpacked extension loaded (`launchPersistentContext` with `--disable-extensions-except=<dir>` and `--load-extension=<dir>`); open the popup, options and side panel by their `chrome-extension://<id>/...` URLs.
- **Electron (Mac app):** Playwright's `_electron.launch({ args: [<main file>] })`, then `firstWindow()` and screenshots.
The checks below apply to every surface.

## Design fidelity, self-verified
- The reference is the design boards the person approved at the single approval, as mapped in the delta's design-mapping table.
- Screenshot the app next to its design board at two widths (desktop and 320 px reflow). Compare by vision, not pixel diff.
- Every element exists, with the same structure, hierarchy, spacing rhythm, tokens and copy.
- Perform the primary action and check its effect (for example, data survives a reload).
- Differences go back to the builder, at most 3 passes.

## States
Check each: empty, loading, error, partial, full, no permission. A missing state is a finding.

## Laws of UX
All 30. Each is `pass`, `fail` or `not applicable`, with evidence (screenshot or observed behaviour). No law is skipped silently.

## Information architecture
- One purpose per screen.
- A clear hierarchy.
- Labels come from the product glossary.

## Navigation
- Where am I, how did I get here, how do I get back.
- No dead ends, no orphans; deep links and Back work.

## Accessibility
- Keyboard path through the primary action, in a sensible focus order.
- Contrast, accessible names, visible focus.
- Reflow at 320 px without horizontal scroll.

## Copy
In the product's voice, in every locale the product ships.

## Report format
Per screen: board (`board-<n>`), screenshots, open defects as `finding-<n>` after an explainer ("save button hidden at 320 px (finding-1)"), then one line per check: `check | verdict | evidence`. End with `UX VERDICT: pass` or `UX VERDICT: fail` and the open defects. Deviations that remain are listed, not hidden. Save the report and the gallery in the evidence folder.

## The gallery (no stop)
- One gallery per UI milestone, written to `changes/<slug>/evidence/<milestone>/gallery.md`: each screen next to its board, with only the remaining deviations flagged.
- The release PR links every milestone's gallery. The person reviews them once, there. No run stops for it.
- The boards were approved at the single approval, so they are the reference. Earlier galleries are the reference for later milestones. They are not pixel-diff tests.
