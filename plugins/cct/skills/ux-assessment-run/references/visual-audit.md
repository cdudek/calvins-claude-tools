# Visual audit: categories, AI slop and grading

Read this for check C20 and C21 of `cct:ux-assessment-run`. It is the rendered-result half of the
audit — what the pixels look like once the behaviour checks in C1-C19 are done. It is the rendered-result half of this skill.

Findings use the audit's own finding format. The two grades below are optional: report them
when the owner asks for a score, otherwise the findings stand on their own.

## The ten visual categories

### First impression

Form a gut reaction before analyzing:
- "The site communicates **[what]**."
- "I notice **[observation]**."
- "The first 3 things my eye goes to are: **[1]**, **[2]**, **[3]**."
- "If I had to describe this in one word: **[word]**."

### Design-system extraction

Extract actual rendered design system: fonts, colors, heading hierarchy, spacing patterns. Flag >3 font families, >12 unique colors, skipped heading levels.

### Page-by-page visual audit

**Trunk Test (every page):** Can you immediately answer: What site? What page? Major sections? Options? Where am I? How to search? Score: PASS/PARTIAL/FAIL.

**Design Audit Checklist (10 categories, ~80 items):**

**1. Visual Hierarchy & Composition** (8 items)
- Clear focal point? One primary CTA per view?
- White space is intentional, not leftover?
- Squint test: hierarchy still visible when blurred?

**2. Typography** (15 items)
- Font count <=3, scale follows ratio (1.25 or 1.333)
- Line-height: 1.5x body, 1.15-1.25x headings
- Measure: 45-75 chars per line (66 ideal)
- Body text >= 16px, caption >= 12px
- No blacklisted fonts (Papyrus, Comic Sans, Lobster, Impact, Jokerman)

**3. Color & Contrast**
- Delegate to the `ux-accessibility-audit` skill (WCAG 2.2) — it owns the canonical
  contrast thresholds and color-use checklist; apply its color/contrast checks here
  rather than restating them

**4. Spacing & Layout** (12 items)
- Grid consistent, spacing uses scale (4px or 8px base)
- Border-radius hierarchy (not uniform bubbly radius)
- No horizontal scroll on mobile

**5. Interaction States** (10 items)
- Hover, focus-visible, active, disabled states present
- Targets >= 24x24 CSS px or spaced (WCAG 2.5.8 AA); 44px on phone primary targets is a recommendation, loading skeletons match content
- Empty states: warm message + primary action

**6. Responsive Design**
- Delegate to the `ux-responsive-audit` skill — it owns the canonical code-smell and
  viewport checklist; apply its checks here rather than restating them
- Design-judgment extra (not in the audit skill): mobile layout makes design sense,
  not just stacked columns

**7. Motion & Animation** (6 items)
- `prefers-reduced-motion` respected
- Only `transform` and `opacity` animated
- Duration: 50-700ms range

**8. Content & Microcopy** (8 items)
- Button labels specific ("Save API Key" not "Submit")
- Active voice, loading states end with `…`
- Happy talk detection and word count

**9. AI Slop Detection** (11 anti-patterns — the blacklist)

The test: would a human designer at a respected studio ever ship this?

1. Purple/violet/indigo gradient backgrounds
2. **The 3-column feature grid:** icon-in-colored-circle + bold title + 2-line description, repeated 3x
3. Icons in colored circles as section decoration
4. Centered everything
5. Uniform bubbly border-radius on every element
6. Decorative blobs, floating circles, wavy SVG dividers
7. Emoji as design elements
8. Colored left-border on cards
9. Generic hero copy ("Welcome to [X]", "Unlock the power of...")
10. Cookie-cutter section rhythm (hero → 3 features → testimonials → pricing → CTA)
11. system-ui as PRIMARY display font

**10. Performance as Design** (6 items)
- LCP < 2.0s, CLS < 0.1
- Images lazy-loaded with dimensions, fonts preloaded

### Goodwill reservoir

Walk 2-3 key flows. Track the Goodwill Reservoir (starts at 70/100):
- Subtract: hidden info (-15), format punishment (-10), interstitials (-15), sloppy appearance (-10)
- Add: obvious tasks (+10), saves steps (+5), graceful errors (+10)

Below 30 = critical UX debt. 30-60 = needs work. Above 60 = healthy.

### Cross-page consistency

Compare navigation, footer, component reuse, tone, spacing across pages.

### Grading, when a score is asked for

**Dual headline scores:**
- **Design Score: {A-F}** — weighted average of all 10 categories
- **AI Slop Score: {A-F}** — standalone grade

**Grade computation:** Each category starts at A. Each Critical or High finding drops one letter. Each Medium drops half. Low findings are noted but don't affect the grade. Severity is the kit's one scale in `finding-format.md`.

## Design Hard Rules

**Classifier — determine before evaluating:**
- **MARKETING/LANDING PAGE** → Landing Page Rules
- **APP UI** → App UI Rules
- **HYBRID** → Apply both where appropriate

**Landing page rules:**
- Brand-first hierarchy: brand > headline > body > CTA
- No flat single-color backgrounds, no cards in hero
- Hero: full-bleed, edge-to-edge
- Motion: 2-3 intentional motions minimum

**App UI rules:**
- Calm surface hierarchy, strong typography, few colors
- Dense but readable, minimal chrome
- Cards only when card IS the interaction

**Universal rules:**
- Define CSS variables for color system
- One job per section
- "If deleting 30% of the copy improves it, keep deleting"
- NEVER use small, low-contrast type (body < 16px or contrast < 4.5:1)
- NEVER placeholder-as-label pattern
- ALWAYS preserve visited vs unvisited link distinction

## Fix loop

For each fixable finding, in impact order:

1. **Locate source** — find CSS/component files responsible
2. **Fix** — minimal change, CSS-only preferred
3. **Commit** — `style(design): FINDING-NNN — short description`. One commit per fix.
4. **Re-test** — verify fix, take before/after screenshots
5. **Classify** — verified / best-effort / reverted

**Self-regulation:** After every 5 fixes or any revert, compute risk level. Stop if risk > 20%. Hard cap: 30 fixes.

## Important Rules

1. Think like a designer, not a QA engineer
2. Screenshots are evidence — every finding needs one
3. Be specific: "Change X to Y because Z"
4. AI Slop detection is your superpower
5. CSS-first — prefer styling changes over structural changes
6. One commit per fix, revert on regression

## Sources

| Origin | Author | License |
|--------|--------|---------|
| [garrytan/gstack](https://github.com/garrytan/gstack) — `design-review` | Garry Tan | MIT |
