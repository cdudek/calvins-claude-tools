# Laws of UX: worked examples and stakeholder scripts

Read this only when a review needs a worked example of laws combining on one component, or when
someone has to defend a design decision to a stakeholder. The checks themselves are in
`laws-of-ux.md`.

## Combined Application: How Laws Work Together

Real design never applies one law in isolation. Here's how they combine on common components:

### A Well-Designed Card Component

```
┌─────────────────────────────────┐  ← Common Region (boundary groups content)
│ 📊 Revenue        $12,400      │  ← Similarity (icon + label + value pattern)
│                         ↑ +8%   │  ← Von Restorff (trend badge pops — ONE emphasis)
│                                 │
│ ─────── ─────── ───────       │  ← Uniform Connectedness (lines = related)
│ Jan    Feb    Mar            │     sub-items
└─────────────────────────────────┘  ← Prägnanz (simple layout, scannable)
     ↑                           ← Proximity (title close to chart, far from next card)
```

Laws applied: **Common Region + Similarity + Von Restorff + Uniform Connectedness + Prägnanz + Proximity** = 6 laws on one component. This is normal.

### A Multi-Step Signup Form

```
Step 1: Create Account    ●━━━━●━━━━○━━━━○   ← Uniform Connectedness (progress)
                        ↑                ← Doherty (inline feedback within 0.1 s)
  Email: [____________]                  ← Postel's (accepts any email format)
  Password: [__________]                 ← Tesler's (password strength meter;
                                         shows requirements inline)

Step 2: Your Profile                     ← Hick's (only 3 fields — not 10)
  Name: [_____________]                 ← Fitts's (44px inputs, spaced 8px apart)
  Avatar: [Upload]                      ← Von Restorff (primary "Upload" button pops)

Step 3: Preferences  (collapsed ▾)      ← Progressive disclosure (Hick's again)
  [ ] Email updates                    ← Unticked by default (Cognitive Bias, L4.1: pre-ticked consent is invalid)
  [  ] SMS notifications               ← Zeigarnik (overall progress: 66%)
                                       ← Working Memory (steps 1-2 summarized here)
```

Laws applied: **9 laws working together** across 3 steps. This is what real design looks like.

### A Dashboard Page

```
┌─ Navigation ──────────────┐  ← Jakob's (conventional left-nav)
│ Home  Analytics  Settings  │     Hick's (5 items, grouped)
│                            │
├──────────────┬─────────────┤  ← Proximity (two regions, loosely spaced)
│             │             │
│  ANALYTICS  │  QUICK ACTS  │  ← Common Region (cards = regions)
│  ┌─────┐    │  ┌─────┐    │
│  │ Rev │    │  │ +Add│    │  ← Similarity (same card structure)
│  │Users│    │  │Export│   │
│  └─────┘    │  └─────┘    │
│  ┌─────┐    │             │
│  │Bounce│   │             │  ← Von Restorff (alert card pops if error)
│  └─────┘    │             │
└──────────────┴─────────────┘  ← Prägnanz (whole thing describable in one sentence)
   ↑ Cognitive Load: one concept per region
   ↑ Selective Attention: highest metrics in scan path (top-left of main)
   ↑ Serial Position: most important metric first (Revenue)
```

**Takeaway:** Don't try to apply laws one-at-a-time. Design the component, then audit against relevant laws to find gaps.

---

## Real-World Teardowns

### Teardown 1: GitHub Settings Page (Before → After)

**Before (typical SaaS anti-pattern):**
- 50+ toggles in a flat alphabetical list
- No grouping, no search, no indication of which settings matter
- "Advanced" toggle mixed with basic preferences
- Each toggle identical visual weight
- No way to understand impact of changing a setting

**Laws violated:** Cognitive Load (🔴), Hick's Law (🔴), Chunking (🔁), Von Restorff (none — nothing stands out), Miller's Law (🔴), Tesler's Law (complexity dumped on user)

**After (applying laws):**
- **Chunked into 4 categories:** Account, Notifications, Integrations, Advanced (Chunking + Cognitive Load)
- **Search bar at top** (Postel's — accepts fuzzy queries)
- **Each category collapsed by default** (Hick's — progressive disclosure)
- **"Danger Zone" for destructive actions in separate red-bordered card** (Von Restorff + Common Region + Fitts's — dangerous actions far from frequent ones)
- **Most-common settings have smart defaults pre-selected** (Tesler's + Cognitive Bias)
- **"Reset to defaults" button at bottom** (Paradox of Active User — recovery from bad changes)

**Result:** Settings went from overwhelming to navigable in one redesign pass.

---

### Teardown 2: Typical SaaS Pricing Page (Before → After)

**Before:**
- 3 pricing tiers in identically styled cards
- No recommendation (user must figure out which plan)
- All features listed for all plans (decision fatigue)
- CTA buttons identical weight/color
- No urgency or social proof

**Laws violated:** Von Restorff (🔴 — no standout), Choice Overload (🔴), Hick's Law (🔴), Cognitive Bias (missing — no anchoring/social proof/defaults), Peak-End Rule (weak end state)

**After:**
- **Middle plan (recommended) has highlighted border + "Most Popular" badge** (Von Restorff — one pops)
- **Left plan crossed-out original price next to current** (Cognitive Bias — anchoring)
- **"Basic / Pro / Enterprise" → "For individuals / For teams / For companies"** (chunking by user type, not feature count)
- **Only 3-5 differences between plans shown** (others collapsed under "Everything in Basic plus...") (Hick's — reduced comparison scope)
- **Primary CTA larger + colored, secondary "Contact Sales" muted** (Von Restorff + Fitts's)
- **"Join 10,000+ teams" below CTA** (Social proof — genuine)
- **After clicking CTA: warm confirmation with setup timeline** (Peak-End Rule)

**Result:** Conversion typically increases 15-30% with these changes (based on aggregated case studies from nngroup.com, conversionciencia.com).

---

### Teardown 3: E-commerce Checkout Flow (Before → After)

**Before:**
- All 15 fields on one page
- Strict date/phone formatting (errors if user types "naturally")
- No progress indicator
- Generic "Order confirmed" text at end
- Error messages: "Invalid input" (no guidance)
- Loading spinner on submit, no feedback during wait

**Laws violated:** Postel's (🔴), Hick's (🔴), Doherty (🔴), Working Memory (🟡), Peak-End Rule (🔴), Fitts's (🟡)

**After:**
- **3 steps:** Cart → Shipping/Payment → Confirm (Hick's + Miller's)
- **Phone field accepts any format, displays formatted** (Postel's)
- **Inline validation on blur** (feedback within 0.1 s, B1; 400 ms is not a pass mark)
- **Optimistic "Processing..." with confetti animation** (Doherty perceived perf + Peak-End delight)
- **"Step 2 of 3" header summarizes cart contents** (Working Memory)
- **Large 44px touch targets throughout** (Fitts's)
- **Final screen: order summary + tracking link + "You might also like"** (Peak-End strong finish + Goal-Gradient)

**Result:** Cart abandonment typically drops 20-35% with optimized checkout flows (Baymard Institute benchmark data).

---

## Stakeholder Communication

Scripts for pushing back, adapted by audience.

### Evidence-Based (for PMs, tech leads, data-driven teams)

**"Add more options/features":**
> "This screen presents N options. Hick's Law shows decision time grows logarithmically with choices — we're slowing users down with every addition. Recommend: (a) progressive disclosure under Advanced, or (b) smart defaults with power-user override. We can A/B test; the research favors ordering and grouping options over cutting ones the task needs (laws-of-ux.md, section 4, error 3)."

**"Make the button smaller":**
> "Fitts's Law: target acquisition time scales with size, inversely with distance. Below 24 CSS px it fails WCAG 2.5.8 (AA); on phones 44px is the platform recommendation. Let's keep 44px, or track mis-click rate. Prediction: smaller = more support tickets."

**"Users will read the tooltip":**
> "Paradox of the Active User is well-documented — users don't read docs before using software. They start clicking. Whatever they need must be discoverable inline: hints, defaults, contextual help. Relying on tooltips being read = designing for a user who doesn't exist."

**"Good enough, let's ship":**
> "Aesthetic-Usability Effect cuts both ways — users rate prettier interfaces as more usable even when they're not, masking problems in testing. Suggest: quick task-completion test (not just subjective ratings) before shipping. Risk: pretty interface users struggle with."

**"Why spend time on confirmation screen?":**
> "Peak-End Rule: people judge experiences by peak + end. This confirmation IS the lasting impression. Generic 'Thank you' = wasted opportunity. Mailchimp's 'High Five' built brand loyalty. Low effort, high impact."

**"Let users configure it":**
> "Tesler's Law — complexity lives somewhere. Pushing it to users = cognitive load per setting exposed. Better: pick good defaults in code, expose config for the 10% who need it."

**"But competitor does it this way":**
> "That's evidence FOR Jakob's Law, not against. Their users learned patterns there. We leverage that mental model (lower curve, faster value) or fight it (novelty cost). What specific advantage does our different approach give the user?"

### Metrics-Focused (for product managers, founders, growth teams)

**"Add more options":**
> "Every option we add has measurable cost. Our data shows [X]% drop-off per additional field in this flow. Hick's Law isn't just theory — it predicts our specific conversion decline. Test: hide half these options behind 'Advanced' and measure completion rate change."

**"Make the button smaller":**
> "Smaller button = predicted [X]% increase in mis-taps based on Fitts's research. On mobile that means accidental form submits, wrong-page navigations, frustrated users. Cost of keeping it 44px: zero. Cost of shrinking: support volume + rage-taps."

**"Good enough, ship it":**
> "I hear 'ship it.' Question: will pretty-but-clunky cost us in retention? Aesthetic-Usability Effect means users give us credit now but may churn 2-3 weeks from frustration. Suggest: 1-week shadow test — watch 5 real users attempt core tasks. If >2 struggle on the same thing, fix it before broad ship."

**"Why spend time on confirmation screen?":**
> "This screen = final touchpoint before user leaves flow. Peak-End research shows this moment weights disproportionately in overall satisfaction. Our NPS correlates more with checkout-complete experience than with mid-funnel experience. Investment here has outsized ROI."

### Standards-Based (for clients, enterprise, regulated industries)

**"Add more options":**
> "Industry standard for [this type of form] is [N] fields per step (per Nielsen Norman Group / Interaction Design Foundation benchmarks). We're currently at [2N]. Recommendation: split into steps following established patterns. This aligns with WCAG 2.2's cognitive accessibility guidance too."

**"Make the button smaller":**
> "WCAG 2.2 sets a floor: SC 2.5.8 (level AA) requires pointer targets of at least 24x24 CSS px, or enough spacing around a smaller one. SC 2.5.5 (level AAA), Apple's HIG (44pt) and Material (48dp) recommend more. Going below 24 px is an AA failure; staying at 44 px or more meets every one of them."

**"Competitor does it differently":**
> "Our competitors follow established conventions because those conventions are based on decades of usability research (Nielsen Norman, Interaction Design Foundation, W3C WAI-AG). Deviating from convention requires justification beyond differentiation — we need measurable user benefit to offset the learning cost we're imposing."

---
