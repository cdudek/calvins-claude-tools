# WCAG 2.2 Guidelines — Detailed Code Examples

Detailed code examples and patterns organized by WCAG principle. For the checklist of WCAG criteria, see `WCAG.md`. For reusable component patterns, see `A11Y-PATTERNS.md`.

---

## Perceivable

### Text Alternatives (1.1)

**Images require alt text:**
```html
<!-- Bad: Missing alt -->
<img src="chart.png">

<!-- Good: Descriptive alt -->
<img src="chart.png" alt="Bar chart showing 40% increase in Q3 sales">

<!-- Good: Decorative image (empty alt) -->
<img src="decorative-border.png" alt="" role="presentation">

<!-- Good: Complex image with longer description -->
<figure>
  <img src="infographic.png" alt="2024 market trends infographic" 
       aria-describedby="infographic-desc">
  <figcaption id="infographic-desc">
    <!-- Detailed description -->
  </figcaption>
</figure>
```

**Icon buttons need accessible names:**
```html
<!-- Bad: No accessible name -->
<button><svg><!-- menu icon --></svg></button>

<!-- Good: Using aria-label -->
<button aria-label="Open menu">
  <svg aria-hidden="true"><!-- menu icon --></svg>
</button>

<!-- Good: Using visually hidden text -->
<button>
  <svg aria-hidden="true"><!-- menu icon --></svg>
  <span class="visually-hidden">Open menu</span>
</button>
```

**Visually hidden class:**
```css
.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
```

### Color Contrast (1.4.3, 1.4.6)

| Text Size | AA minimum | AAA enhanced |
|-----------|------------|--------------|
| Normal text (below large scale) | 4.5:1 | 7:1 |
| Large text (>= 18pt, about 24 CSS px; or >= 14pt bold, about 18.66 CSS px bold) | 3:1 | 4.5:1 |

Large scale is defined in points, not CSS pixels (https://www.w3.org/TR/WCAG22/#dfn-large-scale):
regular text under 24 CSS px, and bold text under 18.66 CSS px, is normal text and needs 4.5:1.
| UI components & graphics | 3:1 | 3:1 |

```css
/* Bad: Low contrast (2.5:1) */
.low-contrast {
  color: #999;
  background: #fff;
}

/* Good: Sufficient contrast (7:1) */
.high-contrast {
  color: #333;
  background: #fff;
}

/* Good: Focus states need contrast too */
:focus-visible {
  outline: 2px solid #005fcc;
  outline-offset: 2px;
}
```

**Don't rely on color alone:**
```html
<!-- Bad: Only color indicates error -->
<input class="error-border">
<style>.error-border { border-color: red; }</style>

<!-- Good: Color + icon + text -->
<div class="field-error">
  <input aria-invalid="true" aria-describedby="email-error">
  <span id="email-error" class="error-message">
    <svg aria-hidden="true"><!-- error icon --></svg>
    Please enter a valid email address
  </span>
</div>
```

### Media Alternatives (1.2)

```html
<!-- Video with captions -->
<video controls>
  <source src="video.mp4" type="video/mp4">
  <track kind="captions" src="captions.vtt" srclang="en" label="English" default>
  <track kind="descriptions" src="descriptions.vtt" srclang="en" label="Descriptions">
</video>

<!-- Audio with transcript -->
<audio controls>
  <source src="podcast.mp3" type="audio/mp3">
</audio>
<details>
  <summary>Transcript</summary>
  <p>Full transcript text...</p>
</details>
```

---

## Operable

### Keyboard Accessible (2.1)

**All functionality must be keyboard accessible:**
```javascript
// Bad: Only handles click
element.addEventListener('click', handleAction);

// Good: Handles both click and keyboard
element.addEventListener('click', handleAction);
element.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' || e.key === ' ') {
    e.preventDefault();
    handleAction();
  }
});
```

**No keyboard traps.** Users must be able to Tab into and out of every component. Use the [modal focus trap pattern](A11Y-PATTERNS.md#modal-focus-trap) for dialogs -- the native `<dialog>` element handles this automatically.

### Focus Visible (2.4.7)

```css
/* Bad: Never remove focus outlines */
*:focus { outline: none; }

/* Good: Use :focus-visible for keyboard-only focus */
:focus {
  outline: none;
}

:focus-visible {
  outline: 2px solid #005fcc;
  outline-offset: 2px;
}

/* Good: Or custom focus styles */
button:focus-visible {
  box-shadow: 0 0 0 3px rgba(0, 95, 204, 0.5);
}
```

### Focus Not Obscured (2.4.11) -- New in 2.2

When an element receives keyboard focus, it must not be entirely hidden by other author-created content such as sticky headers, footers, or overlapping panels. At Level AAA (2.4.12), no part of the focused element may be hidden.

```css
/* Good: Account for sticky headers when scrolling to focused elements */
:target {
  scroll-margin-top: 80px;
}

/* Good: Ensure focused items clear fixed/sticky bars */
:focus {
  scroll-margin-top: 80px;
  scroll-margin-bottom: 60px;
}
```

### Skip Links (2.4.1)

Provide a skip link so keyboard users can bypass repetitive navigation. See the [skip link pattern](A11Y-PATTERNS.md#skip-link) for full markup and styles.

### Target Size (2.5.8) -- New in 2.2

Interactive targets must be at least **24 x 24 CSS pixels** (AA). Exceptions: spacing (a target under 24x24 passes when a 24 CSS px circle centred on its bounding box intersects no other target or other undersized target's circle), an equivalent control that meets the size, inline targets in a sentence, user-agent controls, and essential presentation. 44x44 is 2.5.5 Target Size (Enhanced), Level AAA: recommended for primary targets on phones, not required.

```css
/* Good: Minimum target size */
button,
[role="button"],
input[type="checkbox"] + label,
input[type="radio"] + label {
  min-width: 24px;
  min-height: 24px;
}

/* Better on phones: 2.5.5 (AAA) size for primary targets */
.touch-target {
  min-width: 44px;
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
```

### Dragging Movements (2.5.7) -- New in 2.2

Any action that requires dragging must have a single-pointer alternative (e.g., buttons, inputs). See the [dragging movements pattern](A11Y-PATTERNS.md#dragging-movements) for a sortable-list example.

### Timing (2.2)

```javascript
// Allow users to extend time limits
function showSessionWarning() {
  const modal = createModal({
    title: 'Session Expiring',
    content: 'Your session will expire in 2 minutes.',
    actions: [
      { label: 'Extend session', action: extendSession },
      { label: 'Log out', action: logout }
    ],
    timeout: 120000
  });
}
```

### Motion (2.3)

```css
/* Respect reduced motion preference */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

---

## Understandable

### Page Language (3.1.1)

```html
<!-- Bad: No language specified -->
<html>

<!-- Good: Language specified -->
<html lang="en">

<!-- Good: Language changes within page -->
<p>The French word for hello is <span lang="fr">bonjour</span>.</p>
```

### Consistent Navigation (3.2.3)

```html
<!-- Navigation should be consistent across pages -->
<nav aria-label="Main">
  <ul>
    <li><a href="/" aria-current="page">Home</a></li>
    <li><a href="/products">Products</a></li>
    <li><a href="/about">About</a></li>
  </ul>
</nav>
```

### Consistent Help (3.2.6) -- New in 2.2

If a help mechanism (contact info, chat widget, FAQ link, self-help option) is repeated across multiple pages, it must appear in the **same relative order** each time. Users who rely on consistent placement shouldn't have to hunt for help on every page.

### Form Labels (3.3.2)

Every input needs a programmatically associated label. See the [form labels pattern](A11Y-PATTERNS.md#form-labels) for explicit, implicit, and instructional examples.

### Error Handling (3.3.1, 3.3.3)

Announce errors to screen readers with `role="alert"` or `aria-live`, set `aria-invalid="true"` on invalid fields, and focus the first error on submit. See the [error handling pattern](A11Y-PATTERNS.md#error-handling) for full markup and JS.

### Redundant Entry (3.3.7) -- New in 2.2

Don't force users to re-enter information they already provided in the same session. Auto-populate from earlier steps, or let users select from previously entered values. Exceptions: security re-confirmation and content that has expired.

```html
<!-- Good: Auto-fill shipping address from billing -->
<fieldset>
  <legend>Shipping address</legend>
  <label>
    <input type="checkbox" id="same-as-billing" checked>
    Same as billing address
  </label>
  <!-- Fields auto-populated when checked -->
</fieldset>
```

### Accessible Authentication (3.3.8) -- New in 2.2

Login flows must not rely on cognitive function tests (e.g., remembering a password, solving a puzzle) unless at least one of:
- A copy-paste or autofill mechanism is available
- An alternative method exists (e.g., passkey, SSO, email link)
- The test uses object recognition or personal content (AA only; AAA removes this exception)

```html
<!-- Good: Allow paste in password fields -->
<input type="password" id="password" autocomplete="current-password">

<!-- Good: Offer passwordless alternatives -->
<button type="button">Sign in with passkey</button>
<button type="button">Email me a login link</button>
```

---

## Robust

### ARIA Usage (4.1.2)

**Prefer native elements:**
```html
<!-- Bad: ARIA role on div -->
<div role="button" tabindex="0">Click me</div>

<!-- Good: Native button -->
<button>Click me</button>

<!-- Bad: ARIA checkbox -->
<div role="checkbox" aria-checked="false">Option</div>

<!-- Good: Native checkbox -->
<label><input type="checkbox"> Option</label>
```

**When ARIA is needed,** use the correct roles and states. See the [ARIA tabs pattern](A11Y-PATTERNS.md#aria-tabs) for a complete tablist example.

### Live Regions (4.1.3)

Use `aria-live` regions to announce dynamic content changes without moving focus. See the [live regions pattern](A11Y-PATTERNS.md#live-regions-and-notifications) for markup and a `showNotification()` helper.
