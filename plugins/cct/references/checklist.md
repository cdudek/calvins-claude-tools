# The checklist, point by point

Every point gets **pass · fail · not applicable**, with a one-line reason and the evidence. A
point written for websites is adapted to the platform, never skipped silently. The project's
`docs/ux/setup.md` says the platform (web, desktop, mobile) and any fixed adaptations.

## Navigation and information architecture

1. **Clear first screen:** within five seconds, does the user understand what the product offers?
   (Desktop: the first screen after launch.)
2. **Predictable menu:** does the main navigation hold the categories users expect, in their
   words? Never pass or fail on the number of items alone (`laws-of-ux.md` L18.1).
3. **Location on deep pages:** does a nested screen show where it sits in the hierarchy?
4. **Search where content is heavy:** visible on every content-heavy screen?
5. **Logo or home goes home:** is there always one way back to the start?
6. **Two paths to main screens:** at least two ways to reach each main screen?
7. **Useful footer or status bar:** does it hold what users look for there?
8. **Helpful not-found:** does a missing page or object help the user back? (Desktop: a deleted
   or missing document, a broken deep link.)

## Forms and inputs

1. Visible labels on every field, not placeholder-only.
2. Required fields marked.
3. Specific errors: what went wrong and how to correct it.
4. Validation on blur, not only on submit.
5. Entered data kept after an error.
6. The right input type for each field (number, email, date, path).
7. Autofill or suggestions where they help.
8. A clear primary button, distinct from Cancel or Reset.

## Accessibility (WCAG 2.2 AA)

1. Text contrast at least 4.5:1 (3:1 for large text).
2. Control and icon contrast at least 3:1 against what is next to it.
3. Targets at least 24 × 24 px.
4. Everything reachable and operable by keyboard.
5. Visible focus on every interactive element.
6. Alt text on informative images; empty alt on decorative ones.
7. Language declared (`<html lang>`).
8. No meaning carried by colour alone.
9. Captions on video. Not applicable when there is no video: say so.
10. A skip link, or its platform equivalent.

## Responsive, or window sizes on desktop

1. Viewport meta tag (web).
2. Targets at least 24x24 CSS px, or spaced so a 24 px circle on each touches no other target
   (WCAG 2.5.8). 44x44 on phone primary targets is a recommendation (L7.2), not a pass mark.
3. Body text readable without zoom (16 px on mobile).
4. No horizontal scroll at any supported size.
5. Standard gestures work (touch, or trackpad on desktop).
6. Inputs suited to the device.
7. Orientation, or on desktop every supported window size: the project's widths plus the minimum.
8. Critical controls within reach (thumb on mobile; not buried at the far edge on desktop).

## Performance and technical

1. First contentful paint under 1.8 s (desktop: time from launch to the first usable screen).
2. Largest contentful paint under 2.5 s.
3. Layout shift under 0.1, including when data arrives.
4. Images optimised: modern formats, lazy loading, correct size.
5. Web fonts efficient: `font-display: swap`, subset.
6. No console errors in the production build.
7. HTTPS on every page (desktop: not applicable; say so).
8. Semantic structure: header, main, nav, footer, sections, headings in order.

## Content and microcopy

1. Descriptive headings, not generic ones.
2. Buttons name their action, never "Submit" or "Click here".
3. Scannable text: short paragraphs, lists, headings.
4. No typos or grammar errors.
5. One tone across the product.
6. Helpful empty states, never a blank screen.
7. Clear confirmation after important actions.
8. Privacy and terms reachable where the product needs them; if it does not, say why.
