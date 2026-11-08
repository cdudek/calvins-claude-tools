---
name: ux-responsive-audit
description: "Audits viewport adaptation both code-wise and visually: greps for known overflow smells, screenshots the running app at 360/768/1280px with the agent-browser CLI, measures real horizontal overflow and judges the rendered layout. Covers adaptation outside WCAG-owned criteria; reflow, text-resize and target-size verdicts are deferred to cct:ux-accessibility-audit. Use when the user says 'responsive audit', 'check screen sizes', 'does this work on mobile', 'test different viewports', 'check for horizontal overflow'. Skip for: WCAG conformance verdicts (cct:ux-accessibility-audit); defining the grid and breakpoints (cct:design-system-write)."
allowed-tools: "Read Grep Glob Bash(agent-browser *) Bash(npx agent-browser *) Bash(command -v *)"
user_invocable: true
metadata:
  version: 1.0.0
  author: calvindudek
context: fork
model: sonnet
effort: high
background: false
---

# Responsive Design Audit

Two-phase audit of one or more UI surfaces: a static code pass for the layout patterns that
break small viewports, then visual verification against the running app at a tiered,
usage-share-weighted viewport matrix (3 / 6 / 15 sizes bracketing ≈95% of real-world
viewports — see Phase B).
Code-only audits miss data-dependent blowouts (long German labels, wide countdown pills);
screenshot-only audits can't tell you which line to fix. Do both, in this order.

## Prerequisites

| Variable / Dependency | Required | Format | How to obtain |
|-----------------------|----------|--------|---------------|
| `agent-browser` CLI | Yes (Phase B) | on PATH | `npm i -g agent-browser && agent-browser install` (Node 24+) |
| Running dev server | Yes (Phase B) | e.g. `http://localhost:3000` | the project's dev command |
| Auth seam for gated surfaces | If auditing auth'd pages | project-specific | check the project's e2e auth helpers / test personas / dev bypass |

The in-kit `/cct:browser-automate` skill documents agent-browser CLI usage
(navigation, screenshots, JS eval) — reference it rather than guessing commands.

## Phase A — code audit (no browser)

Grep the target surface's components for the known overflow smells. Report candidates as
`file:line` with the smell name; these are hypotheses for Phase B, not confirmed findings.

1. **Grid/flex children with unbounded content and no `min-w-0`** — CSS auto tracks size to
   the content's min-width, so a long badge or subject line inflates the track and blows the
   page out sideways. Look for `grid`/`flex` containers whose children hold user data
   (names, emails, subjects, prices) without `min-w-0` on the child.
2. **`truncate` on a flex child whose ancestors can't shrink** — `truncate` only works if
   every ancestor between it and the sized container allows shrinking (`min-w-0`). A
   `truncate` that "doesn't work" is almost always this.
3. **Fixed widths in non-wrapping rows** — `w-64`, `w-56`, `w-[..px]` inside a `flex` row
   without `flex-wrap`. Fine at desktop, guaranteed overflow at 360px.
4. **Multi-button/badge rows without `flex-wrap`** — action rows, chip strips, toolbar rows.
5. **Tables not wrapped in an `overflow-x-auto` container** — wide tables must scroll inside
   their own container; the page body must never scroll horizontally.
6. **Absolutely positioned elements near text** — overlays, pills, and stars anchored over
   content can cover the focal figure when a sibling grows (check what happens when the
   neighbor's text is long).

## Phase B — visual verification (agent-browser)

Confirm `command -v agent-browser` first; if missing, STOP and surface the install command —
never silently skip the visual pass.

### The viewport matrix (evidence-based, StatCounter June 2026)

All sizes are **CSS viewport pixels** — what media queries and layout respond to — never
hardware pixels (a Retina/QHD panel maps 2–3 physical px to 1 CSS px; DPR only matters for
image sharpness, not layout). Device mix worldwide: **mobile 51.5% / desktop 47.1% /
tablet 1.4%** (StatCounter, June 2026).

Pick the tier by task size; every tier is a strict subset of the next:

**Quick (3) — any UI change:** `360x800` · `768x1024` · `1920x1080`
**Standard (6) — new surfaces / redesigns:** + `390x844` · `1280x720` · `1440x900`
**Full (15) — audits / pre-launch:** the whole matrix below.

| Viewport | Class | Represents | Share (worldwide, mobile/desktop/tablet-relative) |
|---|---|---|---|
| 360x800 | Phone | Samsung Galaxy A/S (top Android) | 9.2% of mobile |
| 375x812 | Phone | iPhone X/12–13 mini/SE gen 2–3 | 6.0% (13.6% in DE — #2) |
| 390x844 | Phone | iPhone 12–16 base models | 6.3% |
| 393x873 | Phone | Pixel + Android flagships (393x852 = iPhone 15/16 Pro) | 4.5% (+iPhone Pro tail) |
| 414x896 | Phone | iPhone XR/11, Plus models | 12.1% — #1 worldwide AND #1 in DE (16.3%) |
| 430x932 | Phone | iPhone 14–16 Pro Max/Plus — widest mainstream phone | long-tail upper bracket |
| 768x1024 | Tablet | iPad classic portrait (= the `md` breakpoint) | 9.8% of tablet |
| 820x1180 | Tablet | iPad 10th gen (brackets the 800/810/820 cluster) | ~18% of tablet cluster |
| 1280x720 | Laptop | small/older laptops; also brackets MacBook Air 1280x800/832 logical | 6.0% of desktop |
| 1366x768 | Laptop | legacy budget laptops (still everywhere in B2B) | 5.7% |
| 1440x900 | Laptop | 13" MacBook default scaled resolution | MacBook cluster |
| 1536x864 | Laptop | Windows 125%-scaled 1920 panels; proxies 14" MBP (1512x982) | 6.9% |
| 1728x1117 | Laptop | 16" MacBook Pro logical; brackets 1600x900/1680x1050 | Mac/HiDPI cluster |
| 1920x1080 | Desktop | dominant monitor resolution | 20.2% (24.4% in DE — #1) |
| 2560x1440 | Desktop | large monitors — max-width/container behavior check | 5.6% in DE |

**Coverage method:** viewports between two tested widths are covered by their stricter
neighbor (a layout that survives 360 and 375 survives 368), so the matrix is judged by
*bracketing*: the six phone widths bracket the 360–430 band where virtually all modern
phones render; the desktop set brackets 1280–2560 (4K panels browse at 200% scaling =
1920 logical); tablets bracket 768–820 portrait (landscape ≈ the 1280 laptop entry).
Weighted by the device mix, the matrix brackets **≈95% of real-world viewports**.
Excluded as sub-1% tails: <360 legacy phones (320x568 remains a useful stress floor if
copy-overflow is suspected), unfolded foldables (~673–800, tablet-adjacent), and
unscaled ultrawide/4K. German market note: DE mobile skews iPhone (414/375/390 are the
DE top-3) — for German-market products, test the iPhone widths before the Android ones.

Sources: [StatCounter screen resolutions](https://gs.statcounter.com/screen-resolution-stats)
(worldwide + per-country, mobile/desktop/tablet, June 2026),
[StatCounter platform split](https://gs.statcounter.com/platform-market-share/desktop-mobile-tablet/worldwide),
MacBook logical resolutions per [PixelMeasures](https://www.pixelmeasures.com/screen-sizes/macbook/)
(browser viewports run slightly shorter than the logical height due to browser chrome).
Refresh the numbers when they are more than ~a year stale.

For EVERY target surface, at every width in the chosen tier:

1. **Screenshot TWICE** and store both in a scratch directory:
   - **Viewport shot** (no fullPage) — what the user sees above the fold. Judge fold
     placement here, never on the full-page image.
   - **Full-page shot** (fullPage) — everything below the fold; long pages hide their
     breakage in footers and late sections. Scroll to the bottom once first so
     lazy-loaded content is in the DOM, then capture. Known capture artifact: fixed
     headers/toasts render once at the top of a full-page shot — not a bug.
   If the surface has meaningful STATE, re-shoot after driving it (a selected row, an
   opened accordion/dialog, a filled form, a row with maximum-length real data) — the
   worst blowouts are data- and state-dependent and invisible on the initial render.
2. **Measure real overflow** via JS eval:
   ```js
   document.documentElement.scrollWidth - window.innerWidth  // flag > 1px
   ```
3. **When overflow is found, enumerate the offenders** instead of guessing — eval:
   ```js
   [...document.querySelectorAll("*")]
     .filter(el => el.getBoundingClientRect().right > window.innerWidth + 1)
     .map(el => `${el.tagName}.${el.className} w=${Math.round(el.getBoundingClientRect().width)}`)
   ```
   The narrowest offender with real content is usually the culprit; its ancestors are
   collateral. `position: fixed` overlays (toasts) appear here but do NOT cause document
   scroll — false positives.
4. **LOOK at every screenshot** and judge against this protocol (this is where automated
   checks go blind). Work the groups in order:

   **Above the fold (viewport shot):**
   - Is the surface's primary purpose visible without scrolling — key heading, primary
     CTA, the number/status the user came for? On phones, banners + nav can eat the fold.
   - Does the fold cut an element so it LOOKS complete when it isn't (a card row whose
     continuation is hidden, a form whose submit is just below the cut)?

   **Text:**
   - Truncated labels/values (German runs ~30% longer — readable EN can be "ZEITHO…" in DE)
   - Mid-word breaks and ugly hyphenation of long German compounds
   - Orphans: a single word alone on the last line of a heading; awkward two-line splits
     of short labels ("Speichern" wrapping under its icon)
   - Text split around inline elements (an amount separated from its unit/preposition)
   - Line length: body prose past ~75ch on wide screens, or squeezed under ~20ch in a
     starved column
   - Text overlapping other text or controls (absolute positioning, negative margins)

   **Layout anomalies:**
   - Squashed or overlapping elements (especially positioned pills over prices/labels)
   - Uneven card heights in one row; columns that lost alignment
   - Large unexplained empty regions (collapsed/failed content) or a single element
     stretched absurdly wide (missing max-width — form fields spanning 2560px)
   - Nested/duplicate scrollbars; content escaping rounded corners; grid blowouts
   - Button/badge rows that wrapped into a broken-looking state

   **Interactive & fixed elements:**
   - Targets under 24x24 CSS px whose 24 px circle touches another target (WCAG 2.5.8 AA,
     a finding); 44x44 on phone primary targets is a recommendation (WCAG 2.5.5 AAA, a note)
   - Hover-only affordances with no touch equivalent
   - Sticky/fixed headers, bars, or toasts covering content or the primary CTA
     (especially at short/landscape heights)

   **Media & brand:**
   - Stretched, squished, or blurry images; broken aspect ratios at odd crops
   - Wrong logo/color variant against the background at any breakpoint; text on images
     losing contrast at a different crop

   **Accessibility tie-ins** (report as findings with the criterion):
   - WCAG 1.4.10 Reflow: no two-dimensional scrolling at 320px width (equivalent to
     400% zoom on a 1280 desktop) — run the 320x568 stress floor when auditing.
     It is one width, not 400% of every screen size, and the height stays ordinary:
     1.4.10's 256px height is only for content that scrolls sideways (vertical
     writing), so never test a 320x256 window
   - WCAG 1.4.4: page still usable at 200% browser text zoom (spot-check one surface)

Report "OK" for a surface x width ONLY after actually viewing BOTH its screenshots.

## Output

A findings table — surface x width, severity (high/medium/low), the offending element
(`file:line` when Phase A identified it), and a concrete fix suggestion (usually one of:
`min-w-0` on the grid/flex child, `flex-wrap` on the row, `shrink-0` on the badge,
`overflow-x-auto` container, or wrapping instead of truncating).

## Lock it in — regression guard

If the project has a Playwright e2e suite, recommend encoding the audit as a permanent
360px no-horizontal-overflow guard over the key surfaces:

```ts
const MOBILE = { width: 360, height: 800 } as const;
test.use({ viewport: MOBILE });

test("no horizontal overflow @360", async ({ page }) => {
  await page.goto(path, { waitUntil: "networkidle" });
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - window.innerWidth,
  );
  expect(overflow, `${path}: ${overflow}px overflow at 360px`).toBeLessThanOrEqual(1);
});
```

Auth-gated surfaces that can't join a generic guard spec (feature flags, per-user gates) get
the same check inside their own spec, in the state with the widest content on screen.
