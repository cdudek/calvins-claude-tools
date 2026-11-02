# Conflicts: the precedence ladder and the conflict table

A mirror. The canonical copy is `omr-ux`'s `references/conflicts.md`; edit that one and copy
everything from the first horizontal rule down into this file.
`scripts/check-requirements-grammar.py` fails the build when the two differ.
---

## 1. The precedence ladder

Any conflict between two rules, laws, guidelines or goals is settled by the **highest rung that
has an opinion**. A lower rung may decide **how** a higher rung is met, never **whether**. Within
a rung, that rung's tie-break applies. The table in section 3 settles the conflicts met so far;
a conflict not in it is settled by this ladder, never by whoever reviews.

| Rung | What sits here | Why it ranks here | Tie-break inside the rung | Exception possible? |
|---|---|---|---|---|
| **R1 Legal floor** | GDPR (consent Art. 4(11), 7; transparency Art. 12-13; privacy by default Art. 25; erasure Art. 17); CJEU Planet49; UCPD and German UWG for consumer-facing surfaces (incl. UWG 7 for marketing mail, double opt-in); BGB 312k for consumer subscriptions; DSA Art. 25 **only** for online platforms; EAA / BFSG, which make WCAG 2.2 AA (via EN 301 549) law on in-scope consumer surfaces. | Non-compliance is a legal defect regardless of usability. W3C itself notes WCAG becomes binding only through policy (https://www.w3.org/WAI/policies/). | Counsel decides; the review records the scope finding. | No. Only a **scope finding** (who, date, reasoning, for example "BFSG does not apply: console usable only by business customers") or a **deferral** (known failure, owner, dated fix). |
| **R2 WCAG 2.2 A and AA** | All 55 A/AA success criteria with their own normative exceptions (https://www.w3.org/TR/WCAG22/), ISO/IEC 40500:2025 (https://www.w3.org/WAI/news/2025-10-21/wcag22-iso). On EAA-scope surfaces this rung is part of R1. | A testable, internationally standardised floor. WCAG conformance is per complete page and complete process (https://www.w3.org/TR/WCAG22/#conformance-reqs). Example from a product (LeadHub): it ranks its accessibility floor above all its principles, and its design-system departures table already lets WCAG override the design system. | Both criteria must pass; find a design that satisfies both. There is no trade-off between two SCs. | Only the SC's own exceptions, named (for example 1.4.10 two-dimensional layout, 2.5.8 spacing, inline or essential, 3.3.7 security), and deferrals. |
| **R3 Safety of money, consent, access, mail and the user's work** | No wrong or silent outcome; no lost input; review before consequence; undo for the rest. | ISO 9241-110:2020 "use error robustness" (https://www.iso.org/standard/75258.html); NN/g confirmation dialogs (https://www.nngroup.com/articles/confirmation-dialog/); Tognazzini "Protect users' work" (https://asktog.com/atc/principles-of-interaction-design/); the kit's B2B escalation rule. Below R2 because a safety mechanism must itself be accessible (a review dialog that traps focus fails both). | The more irreversible or external consequence wins (mail sent beats a local edit). | Owner only, with a compensating control (for example undo plus history instead of a review for an internal, low-value adjustment). |
| **R4 The product's accepted rules** | Owner-accepted principles and interaction guidelines, the design system as adopted with its recorded departures, dated decisions, business goals **once the owner records them as decisions**, and WCAG AAA criteria the product adopts. | Internal consistency is the first half of Nielsen H4 (https://www.nngroup.com/articles/consistency-and-standards/); a product's rule encodes context a general law cannot see. | The product's own order. Example from a product (LeadHub): the floor, then principles 1-9 ranked; ground truth over foundation over the owning document. | Owner, through a recorded decision (one ADR file per decision). |
| **R5 Laws and guidelines with strong evidence** | Laws rated strong in `laws-of-ux.md` section 6 (Fitts, Chunking, Proximity, Similarity, Common Region, Selective Attention, Working Memory, Peak-End), NN/g research-based guidelines (error messages, progress indicators, response times), platform conventions not already in R2. | Replicated effects. | Stronger evidence first; then frequency of the task (product data); then the owner. | The reviewer may record "deliberate" with a reason; an R4 rule overrides silently (no finding, a note). |
| **R6 Laws with moderate, weak or contested evidence; AAA not adopted** | Hick (for UI), Choice Overload, Occam, Pareto, Parkinson, Postel, Tesler, Zeigarnik, Doherty's 400 ms, Aesthetic-Usability's post-use claim, Serial Position for UI, Miller's 7; WCAG AAA unless the product adopts it (then R4). | The evidence ratings in `laws-of-ux.md` section 6. | As R5. | As R5. |
| **R7 Taste** | Reviewer or stakeholder preference with no rule or evidence. | `omr-ux`'s `finding-format.md`: preferences are labelled. | Owner. | Always; never above "Design choice". |

### Severity follows the rung that is broken

R1 is Critical. R2 is High, or Critical when the failure also blocks a task. R3 is Critical or
High. R4 is rated as the product rates it. R5 and R6 are rated by Nielsen's frequency, impact and
persistence (https://www.nngroup.com/articles/how-to-rate-the-severity-of-usability-problems/).
R7 is Design choice. The B2B escalation rule (one level up on money, consent, access and mail,
never above Critical) still applies. The levels are the one scale of `omr-ux`'s `finding-format.md`.

### Where business goals sit

A business goal (conversion, upsell, a launch date) is not a rung. It enters at R4 when the owner
records it as a decision, and it can then beat R5 to R7, never R1 to R3. "Conversion vs honesty"
is therefore never a trade-off: R1 (consumer surfaces) or R3 (business-only surfaces) has decided
it.

Goals that recur, settled by the ladder without a row of their own: conversion vs honesty (G01,
G05, G06, C07); upsell banners in a partner portal vs Selective Attention L25.3 (R5, unless the
owner records the goal at R4, and never above R1 on consumer surfaces); launch date vs WCAG
(G10); density for operators vs simplicity for occasional users (C20, a per-audience rule at R4).

### Scope decides where WCAG sits

The EAA and the German BFSG cover consumer-facing services; business-to-business relationships
are out of scope, but "in doubt a B2C activity is assumed; the mere possibility that consumers use
the service suffices"
(https://www.e-recht24.de/ecommerce/13236-barrierefreiheitsstaerkungsgesetz.html). So WCAG 2.2 AA
is R1 on an in-scope surface and R2 everywhere else. For a product like LeadHub: public
registration and confirmation pages are candidates for R1; the operator console is R2. Record the
scope finding once per surface, in the product's `docs/ux/setup.md`.

## 2. Recording an exception

A deliberate exception is written down once, in the product repo's `docs/ux/exceptions.md`, and
cited by its id. The register is modelled on a design-system departures table that requires a
named reason for every departure.

```markdown
### EX-<n> <plain title>
- Overridden: <rule id> (rung Rn)          e.g. L7.4 (R5)
- Decided by: <rule id or decision> (rung Rm, m < n)   e.g. IG-8 (R4)
- Kind: product rule wins | owner exception | SC exception named | scope finding | deferral
- Situation and screens: where it applies, nowhere else
- Why: one sentence
- Compensating measure: what keeps the overridden rule's intent (e.g. sticky bar never obscures focus)
- Decided: who, date, owner's words quoted
- Revisit when: a trigger (usage data, launch, design-system release), never "later"
```

- **In a finding**, the supporting notes gain one line: `Rung: R4 (IG-8) over R5 (L7.4), EX-3`.
- **In the Laws of UX coverage table**, a check covered by an exception reads `pass (EX-3)`, not
  `n/a`.
- **R1 and R2 accept only** "SC exception named", "scope finding" or "deferral".
- **A deferral keeps its severity** and, on an EAA-scope surface, appears in the published
  accessibility information.
- **A lower rung can never be cited to except a higher one.**
- **Every report lists the exceptions it relied on**, by id.

## 3. The conflict table

Columns: id; side A; side B; situation; resolution rule; the rung that decides; source. "Ours"
marks a rule without an external source. Numbering C01-C17 follows the seventeen conflicts of the
earlier `laws-of-ux.md` section 3 (C01 was item 1).

### a. The original seventeen, revised (C01-C17)

| Id | Side A | Side B | Situation | Resolution rule | Rung | Source |
|---|---|---|---|---|---|---|
| C01 | Hick, Choice Overload, Occam (fewer options) | Tesler, Pareto (irreducible complexity) | Removing options pushes work onto the user or into a later failure | Keep every option the task needs; order and prioritise; rare options behind one labelled second level, never more than two. Both sides are R6, so task need (Tesler) and the product's usage data decide | R6 | Liu et al. CHI 2020; https://www.nngroup.com/articles/progressive-disclosure/ |
| C02 | Hick (flatten) | Cognitive Load, Common Region (group) | Long option lists | Group within one level with headings or dividers; do not nest to cut counts | R5 | Larson and Czerwinski 1998, https://doi.org/10.1145/274644.274657 |
| C03 | Minimalism H8 (show less) | Recognition H6, Working Memory (show more) | Hiding information forces recall | Anything needed to decide stays visible; only rare detail is disclosed; visible lists never fail on length | R5 | https://www.nngroup.com/articles/short-term-memory-and-web-usability/ |
| C04 | Fitts (bigger, spaced targets) | Density (Pareto columns) | Data tables | 24x24 CSS px, or the spacing exception (an undersized target whose 24 px circle intersects nothing), is the floor; above it density wins on desktop; 44 px on phone primary targets is a recommendation. See W01, W02 | R2 floor, then R5 | https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html |
| C05 | Von Restorff (stand out) | Similarity, Jakob, Selective Attention | Emphasis | One dominant action per region; product components only, no promo styling; status salience is separate (C22) | R4 if the design system rules it, else R5 | Hunt 1995 |
| C06 | Doherty (be fast) | lawsofux "add delay to increase perceived value" | Slow real work | Never add artificial delay; show what is really happening | R3 (honesty) / R5 | Buell and Norton 2011, https://doi.org/10.1287/mnsc.1110.1376 |
| C07 | Goal-Gradient, Zeigarnik ("artificial progress") | Honesty, Cognitive Bias | Progress displays | Progress computed from real completion; manufactured progress or incompleteness is deceptive | R1 on consumer surfaces (UCPD Art. 6), R3 elsewhere | https://eur-lex.europa.eu/eli/dir/2005/29/oj; ours for B2B |
| C08 | Postel (accept liberally) | Error prevention 3.3.4 | Money, dates, consent input | Liberal on format, strict on meaning; echo the normalised value before commit (the "checked or confirmed" route of 3.3.4) | R2 / R3 | RFC 9413; https://www.w3.org/WAI/WCAG22/Understanding/error-prevention-legal-financial-data.html |
| C09 | Jakob (web conventions) | Design system, internal consistency | A product pattern differs from the web | Internal consistency wins unless it breaks a convention that is a WCAG SC (2.1.1, 4.1.2, 3.2.4: R2, cannot be overridden) or that users rely on (Back, links, keys); record departures | R2 or R4 | https://www.nngroup.com/articles/consistency-and-standards/ |
| C10 | Peak-End (design the ending) | Flow, Doherty (no interruption) | Frequent tasks | Frequency decides: a milestone gets an end state; a daily task ends with an inline confirmation | R5 | Shneiderman rule 3, https://www.cs.umd.edu/users/ben/goldenrules.html |
| C11 | Error prevention by confirmation | Flow | Any action | Review for money, consent, access, mail, even when reversible; undo for everything else that is reversible | R3 | https://www.nngroup.com/articles/confirmation-dialog/ |
| C12 | Chunking, pagination | Bulk actions | Select all across pages | The selection bar states page vs all matching, with the count | R3 | Ours |
| C13 | Serial Position | Jakob, Fitts | Ordering | Reorders read-once content and option lists only; never chrome; DOM order follows visual order (W14) | R5 (R2 for order) | Ours; WCAG 1.3.2 |
| C14 | Moved: Parkinson vs 2.2.1 | | Not a conflict; a misapplication guard, now `laws-of-ux.md` section 4, error 18 | Never impose a time limit to speed users up; any limit adjustable | R2 | https://www.w3.org/WAI/WCAG22/Understanding/timing-adjustable.html |
| C15 | Common Region | Prägnanz, Cognitive Load | Box-in-box | Proximity first, a boundary only to separate, shallow nesting | R5 | https://www.nngroup.com/articles/common-region/ |
| C16 | Ladder rule: Aesthetic-Usability | every law | Polished but broken | R7 never overrides a failed check | Ladder | Tuch et al. 2012 |
| C17 | Paradox of the Active User | Error prevention | First irreversible step | Exploration free where reversible; the first irreversible step gets a review naming the consequence | R3 | Ours; https://www.nngroup.com/articles/paradox-of-the-active-user/ |

### b. Law vs law (C18-C31)

| Id | Side A | Side B | Situation | Resolution rule | Rung | Source |
|---|---|---|---|---|---|---|
| C18 | Flow, H7 accelerators (L8.3) | Paradox of the Active User (L20), discoverability | Shortcuts and a command menu that novices never find | Every accelerator duplicates a visible control; shortcuts are shown beside their menu items and in tooltips; nothing is accelerator-only; single-key shortcuts obey 2.1.4 | R2 for 2.1.4, else R5 | Tognazzini "Discoverability"; https://www.nngroup.com/articles/complex-application-design/ (guideline 2) |
| C19 | Jakob (behave like the tools they know) | Mental Model (truthful outcome, L17.2) | A familiar word predicts the wrong outcome (users from a CRM expect "Delete" to erase; the product archives) | Where the familiar label would predict a different result, the truthful term and stated consequence win; where outcomes match, use the familiar term | R3 if money, consent, access or mail, else R5 | Carroll and Rosson, assimilation paradox; Norman, conceptual models |
| C20 | Cognitive Load, Occam (declutter) | Pareto (most-used columns), Working Memory (compare on one screen) | Dense operator tables | Clutter is an element without a job (L19.1), not a count of data values; dense views for daily experts, simpler views for occasional users (per audience) | R4 if the product names audiences, else R5 | https://www.nngroup.com/articles/complex-application-design/ (guideline 6); Gerhardt-Powals principle 3 |
| C21 | Visibility of status on every object (B10) | Selective Attention (banner blindness, noise) | A status badge on every row | Show status on the object when it deviates from normal; aggregate what needs a person in one place (Home, inbox); success is transient | R4 if the product rules it, else R5 | https://www.nngroup.com/articles/indicators-validations-notifications/ |
| C22 | Von Restorff budget (one dominant element) | Selective Attention, H1 for errors | An error must stand out where a primary action already does | Errors and warnings use the colour of meaning and an icon, not primary-button emphasis; the emphasis budget applies to actions, not to status | R4 (the design system's colour meaning) | Ours |
| C23 | Doherty, optimistic UI (L6.1) | Mental Model, true state (L17.2, B10) | "Saved" shown while an external write (CRM, mail) is still queued | Optimistic for local reversible state only; external effects show a pending status on the object until confirmed; failure rolls back with a message at the source; money, consent and mail outcomes are never shown optimistically | R3 | Ours |
| C24 | Autosave (Ovsiankina L30.1, Flow) | Error prevention for content others read | Mail text, public form text | Autosave as a draft; publishing or sending is an explicit reviewed step | R3 | NN/g confirmation dialogs |
| C25 | Pareto, Tesler defaults (L21.4, L27.1) | Safe defaults (L4.5), privacy by default | The most common choice is the risky one ("notify registrants", an export with personal data) | On money, consent, access, mail and personal data the safe default wins; elsewhere the common-case default | R1 for personal data (GDPR Art. 25(2)), R3 otherwise | https://eur-lex.europa.eu/eli/reg/2016/679/oj Art. 25 |
| C26 | Chunking via pagination (L3.6) | Working Memory, browser find (Ctrl+F), compare | Long lists | Paginate tables that carry actions, with totals and stable URLs; offer server search so the user never has to page to find; never infinite scroll on a table with bulk actions | R5 | Ours; https://www.nngroup.com/articles/data-tables/ |
| C27 | Undo (H3, B5) | True state, Mental Model | "Undo" after an effect already left the system (mail sent, CRM synced) | Undo only what can truly be reversed; otherwise label it what it does ("Restore", "Send correction") or delay the external effect visibly until the undo window closes | R3 | Ours |
| C28 | Autosave on blur (Flow) | Concurrent edits by colleagues | Two people edit one record | Detect version conflicts; never overwrite silently; show who changed what and let the user choose | R3 | https://martinfowler.com/eaaCatalog/optimisticOfflineLock.html |
| C29 | Serial Position, Jakob | Platform-specific button order | Dialog button order (OK-Cancel vs Cancel-OK) | Follow the product's design system consistently on the web; never mix | R4 | https://www.nngroup.com/articles/ok-cancel-or-cancel-ok/ |
| C30 | Occam "no repeated information" (L19.3) | Judicious redundancy, Working Memory | Status shown in the list row and in the quick look; title and breadcrumb | Repetition across views for consistency is allowed; repetition within one view region is not | R5 | Gerhardt-Powals principle 10, https://www.tech.dmu.ac.uk/~mstacey/handouts/Sets-of-Design-Principles.docx |
| C31 | Hick, Choice Overload "mark a recommendation" (L2.1, L10.3) | Cognitive Bias neutrality on consent and money (L4.2) | A recommended package, a highlighted "Accept" | Recommendations allowed for operational choices; never on consent; on money only with the stated reason and no pre-selection of the dearer option | R1 (consent) / R3 | EDPB Guidelines 05/2020, https://www.edpb.europa.eu/our-work-tools/our-documents/guidelines/guidelines-052020-consent-under-regulation-2016679_en |

### c. Law vs WCAG 2.2 (W01-W16)

WCAG always decides how; the law decides only among WCAG-conformant designs.

| Id | Side A (law) | Side B (WCAG) | Situation | Resolution rule | Rung | Source |
|---|---|---|---|---|---|---|
| W01 | Density, fixed row height (Pareto, for example 40 px rows) | 1.4.12 Text Spacing, 1.4.4 Resize Text | Fixed-height containers with truncation clip text when users raise spacing or text size | Rows use a minimum height, not a fixed one; truncated values remain fully available (title, quick look, expand); pass the text-spacing injection test | R2 | https://www.w3.org/WAI/WCAG22/Understanding/text-spacing.html |
| W02 | Density, wide tables (Pareto, L29.8 compare) | 1.4.10 Reflow | Tables wider than 320 CSS px | The table itself is excepted (two-dimensional layout); its heading, search, filters, toolbar and pagination are not and must reflow | R2 | https://www.w3.org/WAI/WCAG22/Understanding/reflow.html |
| W03 | Occam, Prägnanz (reveal row actions on hover) | 1.4.13 Content on Hover or Focus, 2.1.1 Keyboard; B8 signifiers | Row actions or tooltips shown only on hover | Revealed content also appears on focus, is dismissible (Esc) without moving pointer or focus, hoverable and persistent; actions are visible at rest on touch | R2, then R5 for visible at rest | https://www.w3.org/WAI/WCAG22/Understanding/content-on-hover-or-focus.html; https://www.nngroup.com/articles/flat-ui-less-attention-cause-uncertainty/ |
| W04 | Flow, autosave without confirm (L8.5) | 3.3.4 Error Prevention (Legal, Financial, Data) | Changes to stored user data and financial actions | Autosave passes 3.3.4 only through "reversible": undo or restore must exist; financial and legal actions additionally get the review (R3) | R2 | https://www.w3.org/WAI/WCAG22/Understanding/error-prevention-legal-financial-data.html |
| W05 | Von Restorff, Similarity by colour | 1.4.1 Use of Color, 1.4.11 Non-text Contrast | A selected row as pale fill only; status dots | A second cue (border, icon, text, weight) and `aria-selected` or text for assistive technology; the selection boundary at 3:1 | R2 | https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html |
| W06 | Motion as feedback (L28.6 highlight, B9 common fate) | 2.2.2 Pause, Stop, Hide (A), 2.3.1, 2.3.3 (AAA), `prefers-reduced-motion` | Highlight animation, slide-in panels | Under reduced motion only fades or static highlights; nothing auto-moves for over 5 s without pause; no flashing | R2 for 2.2.2 and 2.3.1; R4 when the product adopts 2.3.3 | https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html |
| W07 | Sticky chrome to keep context visible (L29.2, L7.4 selection bar near, B3) | 2.4.11 Focus Not Obscured (Minimum) | Sticky headers, toolbars, selection bars and toasts hide the focused element | Scroll margins equal to the measured chrome height; toasts never placed over the focus path; test with Tab and Shift+Tab | R2 | https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html |
| W08 | "The thing that changed is the feedback", optimistic UI (Doherty) | 4.1.3 Status Messages | A visual-only change has no announcement for screen-reader users | "No toast" never means "no announcement": every status change gets a polite live-region message (or focus moves to it); rollbacks are announced | R2 | https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html |
| W09 | Calm, quiet endings (L23.5), auto-dismissing messages | 2.2.1 Timing Adjustable | Undo or an error in a 4-second toast | Messages with an action or an error persist, or their action is durably available elsewhere (Restore on the item); timers pause on hover and focus | R2 | https://www.w3.org/WAI/WCAG22/Understanding/timing-adjustable.html |
| W10 | Accelerators (L8.3, H7) | 2.1.4 Character Key Shortcuts | Single-letter shortcuts (j, k, e) | An off switch, remapping, or active only when the component has focus; never fire inside text inputs | R2 | https://www.w3.org/WAI/WCAG22/Understanding/character-key-shortcuts.html |
| W11 | Constraints, grey-out (B8, Shneiderman "grey out") | 4.1.2, 2.1.1, discoverability | Native `disabled` removes the control from the tab order, so keyboard and screen-reader users cannot learn why | `aria-disabled` with the reason reachable (description or adjacent text); WCAG exempts inactive controls from contrast, so legibility of the reason is the product's job | R2 for state exposure, R5 for the reason | https://www.nngroup.com/articles/button-states-communicate-interaction/ |
| W12 | Calm "no description line under the title" (a product rule), Occam | 3.3.2 Labels or Instructions, 2.4.6 | Inputs that need instructions | Instructions required by 3.3.2 sit at the field, not under the title; such a product rule holds for page headers only | R2 | https://www.w3.org/WAI/WCAG22/Understanding/labels-or-instructions.html |
| W13 | Icon-only toolbars (Occam, density) | 2.5.3 Label in Name, 1.1.1, 4.1.2 | Icon buttons with tooltips | The accessible name equals the tooltip and starts with any visible text | R2 | https://www.w3.org/WAI/WCAG22/Understanding/label-in-name.html |
| W14 | Serial Position, Fitts (visual reorder with CSS `order` or grid placement) | 1.3.2 Meaningful Sequence, 2.4.3 Focus Order | A layout reordered at breakpoints | DOM order matches visual order; reorder in markup, not in CSS | R2 | https://www.w3.org/WAI/WCAG22/Understanding/focus-order.html |
| W15 | One vocabulary, Jakob (a German UI with English product names) | 3.1.2 Language of Parts | Mixed-language strings | Mark passages in another language with `lang`; proper names and loan words are exempt | R2 | https://www.w3.org/WAI/WCAG22/Understanding/language-of-parts.html |
| W16 | Flow, no interruptions (L8.5) | 2.2.1 (session time limits) | Security session expiry | Warn before expiry, offer an extension, preserve input (2.2.5 AAA when the product adopts it) | R2 / R3 | https://www.w3.org/WAI/WCAG22/Understanding/timing-adjustable.html |
| W17 | Reflow testing (responsive-audit, E2E zoom tests, "400 % zoom" facts) | 1.4.10 Reflow | Testing 400 % zoom as a 320 × 256 window, or as 400 % of every screen size | One width: 320 CSS px (1280 at 400 %) at an ordinary height, tested at 320 × 640 (or the 320 × 568 floor). 256 CSS px applies only to content that scrolls horizontally (vertical writing); the two bounds are never combined. A product may test narrower phones too, never a stricter height | R2 | https://www.w3.org/WAI/WCAG22/Understanding/reflow.html |

### d. Law vs the legal floor (G01-G10)

**Not legal advice.** Each row names the rule a reviewer must route to counsel; counsel decides.
Record the scope of the surface first (section 1).

| Id | Side A (law or goal) | Side B (legal) | Situation | Resolution rule | Rung | Source |
|---|---|---|---|---|---|---|
| G01 | Cognitive Bias defaults, Hick "recommend", conversion | GDPR valid consent; Planet49; equal prominence of refusal | Consent and cookie choices | Unticked by default; granular per purpose; "Reject" as easy and as prominent as "Accept" on the same layer | R1 | Planet49 C-673/17; EDPB 05/2020; EDPB Cookie Banner Taskforce report 2023, https://www.edpb.europa.eu/our-work-tools/our-documents/other/report-work-undertaken-cookie-banner-taskforce_en |
| G02 | Progressive disclosure, Cognitive Load (hide details) | GDPR Art. 7(2), 12-13 transparency | Consent text and privacy information behind "more" | Layered notices are allowed, but the first layer carries the controller, the purposes, the right to withdraw and the consequences | R1 | Art. 29 WP Transparency Guidelines WP260 rev.01, https://ec.europa.eu/newsroom/article29/items/622227 |
| G03 | Occam, Goal-Gradient, fewer steps | Double opt-in for marketing mail (UWG 7(2), BGH I ZR 164/09, 2011) | Signup flows | The extra confirmation step is mandatory; optimise it (a clear "check your inbox", resend, the state of a pending confirmation) rather than remove it | R1 | https://www.gesetze-im-internet.de/uwg_2004/__7.html; BGH I ZR 164/09 (docket cited, URL not verified) |
| G04 | Tesler, Pareto prefill and rich defaults | GDPR Art. 25(2) privacy by default, Art. 5(1)(c) minimisation | Exports and views that include personal data by default | Personal data off by default in exports and shares; included on explicit choice | R1 | GDPR Art. 25 |
| G05 | Peak-End "save the customer" step, business retention | GDPR Art. 7(3) withdrawal as easy as consent; BGB 312k cancellation button (consumer contracts); DSA Art. 25 (platforms) | Unsubscribe, withdraw, cancel | The same number of steps as granting, or fewer; no retention interstitial before the withdrawal takes effect | R1 | https://www.gesetze-im-internet.de/bgb/__312k.html |
| G06 | Parkinson, Zeigarnik urgency, conversion | UCPD Annex I no. 7 (false limited-time offers), UWG Annex no. 7 | Countdowns, "only 3 seats left" | Only real deadlines and real counts; on business-only surfaces the same as an honesty rule (R3) | R1 / R3 | https://eur-lex.europa.eu/eli/dir/2005/29/oj |
| G07 | Undo, soft delete, Archive (H3, B5) | GDPR Art. 17 erasure | A person asks to be erased | Erasure is a distinct action from Archive and withdrawal, says it cannot be undone and gets a review; the label never says "Delete" for a soft delete | R1 | GDPR Art. 17 |
| G08 | Precise error messages (B4, H9: "this e-mail is already registered") | GDPR confidentiality, security (account and registration enumeration) | Public signup, magic-link login | On unauthenticated surfaces use neutral messages ("If this address is registered, we sent a link") | R1 / R3 | https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html |
| G09 | Occam (fewest elements), a minimal footer | EAA Annex V / BFSG para. 14 and Anlage 3 service information | Public pages in EAA scope | Accessibility information about the service is published, and is itself accessible | R1 | https://eur-lex.europa.eu/eli/dir/2019/882/oj; https://www.gesetze-im-internet.de/bfsg/ |
| G10 | Business: launch on a date | EAA, BFSG, WCAG on in-scope surfaces | Known A/AA failures at launch | A deferral record with an owner and a dated fix; known limitations named in the published information; never reclassified as an exception | R1 | EAA Art. 4 and Annex V |

### e. Law vs a product's own rules: worked examples (P01-P06)

These rows cite one product's rules. Each is an **example from a product (LeadHub)**, kept
because it shows the pattern: the product rule wins over R5 to R7 automatically, and the review
still records the exception (section 2) so the overridden intent gets a compensating measure.
Another product writes its own rows with its own rule ids.

| Id | Side A (law) | Side B (product rule or goal) | Situation | Resolution rule | Rung | Source |
|---|---|---|---|---|---|---|
| P01 | Fitts L7.4 (act next to the selection), and its typical violation "sticky selection bar at the top" | Example from a product (LeadHub): IG-8, the selection bar replaces the toolbar above the table | Bulk actions | The product rule wins; compensate: the bar stays visible (sticky) without obscuring focus (W07), with a keyboard path from the selection | R4 over R5 | LeadHub IG-8; an EX entry is required |
| P02 | Pareto L21.3, Tognazzini discoverability (top tasks visible) | Example from a product (LeadHub): IG-3, the title row has no buttons; object actions sit in "..." | A frequent object action hidden in a menu | The product rule wins if the top task is visible elsewhere (toolbar, quick look, selection bar, command menu); otherwise raise it as an R4 change request, not a finding against the page | R4 over R5 and R6 | LeadHub IG-3 |
| P03 | Jakob (forms have Save), Mental Model (did it save?) | Example from a product (LeadHub): IG-6, no Save button, saves on blur | Inline edit | The product rule wins; compensate: the saved state is shown on the field (L17.2) and announced (W08), with undo (W04) | R4 over R5, under R2 | LeadHub IG-6 |
| P04 | Von Restorff L28.2 (the most important element is the most distinct) | Example from a product (LeadHub): IG-4, solid purple only for the step that finishes | "New" is the most frequent action but uses outline | The product rule wins; "New" stays reachable at a fixed place and by shortcut | R4 over R5 | LeadHub IG-4 |
| P05 | The accessibility skill's manual check "content usable at 200% zoom" (1.4.4) | Example from a product (LeadHub): decision of 2026-10-01, 200% zoom is not a requirement | Review matrices | R2 beats R4 only as far as 1.4.4 reaches: text must still resize to 200% without loss (text-only zoom or equivalent). The decision keeps text resizing and reflow, so it conforms if read narrowly; the check says "text resize 200%", not "zoom 200%" | R2 | https://www.w3.org/WAI/WCAG22/Understanding/resize-text.html; LeadHub decisions, 2026-10-01 |
| P06 | Similarity L15.3 (one colour, one meaning) | Example from a product (LeadHub): brand purple is brand, primary and selection | Colour meaning | The design system's colour-meaning section decides; a value failing contrast is overridden by WCAG through the design system's departures table | R4, R2 for contrast | LeadHub DESIGN.md "Colour Meaning" and "Where we differ" |
