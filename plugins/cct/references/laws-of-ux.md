# Laws of UX: the checks

The canonical copy. A byte-identical mirror lives in `ux-usability-audit`
(`plugins/cct/skills/ux-usability-audit/references/laws-of-ux.md`), because a plugin cannot read
another plugin's files at runtime. Edit this file, copy everything from the first horizontal rule
down into the mirror, and `scripts/check-requirements-grammar.py` keeps the two equal.

Read by `cct:ux-assessment-run` (its Laws of UX pass), `cct:ux-assessment-run` (check C22) and the `lenses.md`
index. Research date 2026-10-09: every law page on lawsofux.com read in full, every number with
its source, anything unsourced marked **(heuristic)**.

---

## 0. How to use this checklist

**Verdict per law.** A review marks every law `pass`, `fail` or `n/a`. `n/a` needs the
applicability reason from that law's section. `fail` needs at least one failed check id
(for example `L7.2`) and its evidence. A law passes only when every check that applies passes.

**Evidence codes** (each check names the evidence that proves it):

| Code | Evidence | What the agent does |
|---|---|---|
| S | Static screenshot | Inspect the 100% and 150% zoom shots of every changed screen and state. Pixel measurements are taken from the DOM, not estimated from the image. |
| C | Code | Read the diff and the components it uses: semantics, tokens, attributes, handlers. |
| I | Interaction walk | Operate the running app with mouse and with keyboard only; record each step. |
| T | Timing measurement | Record a performance trace (or Playwright timings) for the interaction; report the measured milliseconds and the machine/throttling used. |
| N | Content count | Count items, options, steps, fields, emphasised elements; report the number. |
| M | Measurement script | Run a small script in the page (for example `getBoundingClientRect()` on every interactive element) and report the numbers. |

**Severity scale.** Mapped to Nielsen's 0-4 scale
(https://www.nngroup.com/articles/how-to-rate-the-severity-of-usability-problems/), which rates
frequency, impact and persistence, plus market impact:

| Level | Nielsen | Use when |
|---|---|---|
| Critical | 4, "usability catastrophe" | Blocks the task, or can produce a wrong outcome in money, consent, access or outgoing mail, or is a legal non-compliance (for example invalid consent). |
| High | 3, "major problem" | Frequent task is slowed or error-prone, or a WCAG 2.2 level A/AA failure. |
| Medium | 2, "minor problem" | Noticeable friction that users recover from without help. |
| Low | 1, "cosmetic" | Polish only. |
| Design choice | 0, "not a usability problem" | No demonstrated problem; a direction to decide. |

This is the same five-level scale as `finding-format.md`, the only one. The
accessibility skill's Critical, Serious, Moderate and Minor are Critical, High, Medium and Low;
build QA's P0 to P3 are the same four.

**B2B escalation rule (heuristic, our own):** any violation located on a money, consent,
access or mail action is raised one level, never above Critical.

**Nielsen heuristics** are cited as H1-H10 using the 2020 wording: H1 Visibility of system
status, H2 Match between system and the real world, H3 User control and freedom, H4
Consistency and standards, H5 Error prevention, H6 Recognition rather than recall, H7
Flexibility and efficiency of use, H8 Aesthetic and minimalist design, H9 Help users
recognize, diagnose, and recover from errors, H10 Help and documentation.

**WCAG 2.2 levels** quoted below were checked against the W3C Recommendation
(https://www.w3.org/TR/WCAG22/) on the research date.

## The coverage table

Every review and every audit returns this table with all thirty rows filled, plus the B rows of
section 5. A blank row is a pass that did not run: say "did not run" and why, never leave it
blank.

| # | Law | Verdict | Failed checks | Evidence |
|---|---|---|---|---|
| L1 | Aesthetic-Usability Effect | pass / fail / n/a | L1.x, ... | screenshot, `file:line`, count or timing |
| ... | ... | ... | ... | ... |
| L30 | Zeigarnik Effect | | | |
| B1 to B14 | one row each | | | |

`n/a` quotes the law's own "Not applicable when" line. `fail` lists every failed check id; each
failed check is also a finding in the shared finding format, with the check id in its supporting
notes. A check covered by a recorded exception reads `pass (EX-n)`, never `n/a`
(`conflicts.md` section 2).

## Which laws matter most, by what changed

Every law is marked on every review. This table only says where to look hardest first.

| The change touches | Start with |
|---|---|
| A form, a create or edit flow | L2, L5, L24, L29, L3, L7; B4, B5, B6 |
| A table, list, filter or bulk action | L3, L10, L12, L13, L15, L18, L21; B2, B3 |
| A dashboard or overview page | L5, L3, L12, L13, L25, L28, L14 |
| A dialog, side panel, menu or popover | L7, L8, L11, L25, L28; B9, B11, B13 |
| Navigation, the sidebar or a page header | L11, L17, L26, L21, L18 |
| Money, consent, access or mail | L4, L23, L28, L6; B5, B10, B12 |
| A long or multi-step job, an import, a sync | L6, L9, L22, L30; B1, B10 |
| Words only | L17, L20, L2; B4 |

## 1. The canonical list on lawsofux.com

**Count: exactly 30.** Verified from `https://lawsofux.com/index.md` and `https://lawsofux.com/llms.txt`.
The site lists the laws alphabetically; it has no numbering of its own. Definitions below are
the site's own one-liners, quoted verbatim (curly quotes and dashes converted to ASCII).

| # | Law | lawsofux.com definition | Site category |
|---|---|---|---|
| 1 | Aesthetic-Usability Effect | "Users often perceive aesthetically pleasing design as design that's more usable." | Theory |
| 2 | Choice Overload | "The tendency for people to get overwhelmed when they are presented with a large number of options, often used interchangeably with the term paradox of choice." | Theory |
| 3 | Chunking | "A process by which individual pieces of an information set are broken down and then grouped together in a meaningful whole." | Psychology |
| 4 | Cognitive Bias | "A systematic error of thinking or rationality in judgment that influence our perception of the world and our decision-making ability." | Psychology |
| 5 | Cognitive Load | "The amount of mental resources needed to understand and interact with an interface." | Psychology |
| 6 | Doherty Threshold | "Productivity soars when a computer and its users interact at a pace (<400ms) that ensures that neither has to wait on the other." | Theory |
| 7 | Fitts's Law | "The time to acquire a target is a function of the distance to and size of the target." | Theory |
| 8 | Flow | "The mental state in which a person performing some activity is fully immersed in a feeling of energized focus, full involvement, and enjoyment in the process of the activity." | Psychology |
| 9 | Goal-Gradient Effect | "The tendency to approach a goal increases with proximity to the goal." | Theory |
| 10 | Hick's Law | "The time it takes to make a decision increases with the number and complexity of choices." | Theory |
| 11 | Jakob's Law | "Users spend most of their time on other sites. This means that users prefer your site to work the same way as all the other sites they already know." | Theory |
| 12 | Law of Common Region | "Elements tend to be perceived into groups if they are sharing an area with a clearly defined boundary." | Theory |
| 13 | Law of Proximity | "Objects that are near, or proximate to each other, tend to be grouped together." | Theory |
| 14 | Law of Prägnanz | "People will perceive and interpret ambiguous or complex images as the simplest form possible, because it is the interpretation that requires the least cognitive effort of us." | Theory |
| 15 | Law of Similarity | "The human eye tends to perceive similar elements as a complete picture, shape, or group, even if those elements are separated." | Theory |
| 16 | Law of Uniform Connectedness | "Elements that are visually connected are perceived as more related than elements with no connection." | Theory |
| 17 | Mental Model | "A compressed model based on what we think we know about a system and how it works." | Psychology |
| 18 | Miller's Law | "The average person can only keep 7 (plus or minus 2) items in their working memory." | Theory |
| 19 | Occam's Razor | "Among competing hypotheses that predict equally well, the one with the fewest assumptions should be selected." | Theory |
| 20 | Paradox of the Active User | "Users never read manuals but start using the software immediately." | Theory |
| 21 | Pareto Principle | "The Pareto principle states that, for many events, roughly 80% of the effects come from 20% of the causes." | Theory |
| 22 | Parkinson's Law | "Any task will inflate until all of the available time is spent." | Theory |
| 23 | Peak-End Rule | "People judge an experience largely based on how they felt at its peak and at its end, rather than the total sum or average of every moment of the experience." | Theory |
| 24 | Postel's Law | "Be liberal in what you accept, and conservative in what you send." | Theory |
| 25 | Selective Attention | "The process of focusing our attention only to a subset of stimuli in an environment - usually those related to our goals." | Psychology |
| 26 | Serial Position Effect | "Users have a propensity to best remember the first and last items in a series." | Theory |
| 27 | Tesler's Law | "Tesler's Law, also known as The Law of Conservation of Complexity, states that for any system there is a certain amount of complexity which cannot be reduced." | Theory |
| 28 | Von Restorff Effect | "The Von Restorff effect, also known as The Isolation Effect, predicts that when multiple similar objects are present, the one that differs from the rest is most likely to be remembered." | Theory |
| 29 | Working Memory | "A cognitive system that temporarily holds and manipulates information needed to complete tasks." | Psychology |
| 30 | Zeigarnik Effect | "People remember uncompleted or interrupted tasks better than completed tasks." | Theory |

**What changed 2024-2026** (measured from Wayback Machine snapshots of the home page,
`https://web.archive.org/web/<date>/https://lawsofux.com/`, and first-capture dates of each page):

- 2022-06 through 2024-01 the site listed **21** laws: the 23 "Theory" laws in the table minus
  Choice Overload and Paradox of the Active User.
- By 2024-06: **22** (Paradox of the Active User added).
- Between 2024-06 and 2025-01: **29**. Added: Cognitive Load (first captured 2024-06-27),
  Selective Attention (2024-07-12), Flow (2024-08-15), Cognitive Bias (2024-08-30), Chunking
  (2024-09-05), Working Memory (2024-11-03), Mental Model (in the 2025-01-01 snapshot).
- By 2025-09: **30** (Choice Overload, first captured 2025-01-21).
- 2025-09 to 2026-10: no change; no law was removed in 2024-2026.
- The additions coincide with the book's second edition (O'Reilly, January 2024,
  https://oreilly.com/library/view/laws-of-ux/9781098146955). All seven pages tagged
  "Category: Psychology" are among the 2024-2025 additions.
- Write-ups that say "21 laws" or "the 20 laws of UX" predate mid-2024.

**Grouping.** The home page shows one flat alphabetical grid; there is no "Gestalt" heading.
Five pages carry the tag `gestalt`: Common Region, Proximity, Prägnanz, Similarity, Uniform
Connectedness. Their shared "Origins" text names five categories of grouping ("Proximity,
Similarity, Continuity, Closure, and Connectedness"), but the site has no pages for Continuity
or Closure, and none for Figure-Ground, Common Fate or Symmetry. Section 5 covers the missing
Gestalt principles that are auditable. The site also files Chunking, Cognitive Bias, Cognitive
Load, Flow, Mental Model, Selective Attention and Working Memory under "Psychology" and the rest
under "Theory"; that split is editorial, not a statement about evidence.

**Overlaps to know about when marking verdicts.** Miller's Law, Working Memory, Chunking and
Cognitive Load describe one underlying capacity limit from four angles; Goal-Gradient and
Zeigarnik share two identical takeaway sentences on lawsofux.com ("Providing artificial progress
towards a goal..." and "Provide a clear indication of progress..."); Jakob's Law and Mental
Model overlap. The checks below are written so that each check id belongs to exactly one law;
a single defect may legitimately fail checks in two laws.

## 2. The 30 laws, one section each

### L1. Aesthetic-Usability Effect

**Definition.** "Users often perceive aesthetically pleasing design as design that's more
usable." (https://lawsofux.com/aesthetic-usability-effect/). Origin: Kurosu and Kashimura
(Hitachi, CHI 1995) had 252 participants rate 26 ATM layouts; aesthetic ratings correlated more
strongly with *perceived* ease of use than with *actual* ease of use (same page;
https://www.nngroup.com/articles/aesthetic-usability-effect/).

**Evidence quality: moderate for "looks affect perceived usability", contested for any effect
on post-use judgement.** Tractinsky, Katz and Ikar 2000 (Interacting with Computers 13(2)
127-145) found aesthetics, not actual usability, affected post-use perceived usability
(https://academic.oup.com/iwc/article/13/2/127/898608). Tuch et al. 2012 (Computers in Human
Behavior; N=80, 2x2 aesthetics x usability online shop) found aesthetics did **not** affect
perceived usability, while poor usability lowered post-use perceived aesthetics
(https://research.google/pubs/is-beautiful-really-usable-toward-understanding-the-relation-between-usability-aesthetics-and-affect-in-hci/).
NN/g: "A pretty design can make users forgiving of minor usability problems, but not of large
ones."

**Auditable checks.**
1. L1.1 Does every colour, type size, weight, radius, shadow and spacing value in the diff come
   from the design system's tokens, with no hard-coded values? [C]
2. L1.2 Do elements that share an edge line up, and do all gaps use values from the spacing
   scale, at 100% and 150%? Report any misalignment of 2 CSS px or more **(heuristic
   tolerance)**. [S, M]
3. L1.3 Is no text clipped, overlapping or truncated without a way to read the full value, at
   100%, 150% and at 390 CSS px width? [S]
4. L1.4 Does body text reach 4.5:1 contrast (3:1 for large text) and do component boundaries
   and states needed to identify a control reach 3:1 against adjacent colours, in light and dark
   themes? (WCAG 1.4.3, 1.4.11) [S, M]
5. L1.5 Are the empty, loading, error and refused states rendered to the same standard as the
   populated state (same tokens, same layout grid)? [S]
6. L1.6 Does every element that looks interactive actually respond, and does every interactive
   element look interactive (no polished but dead chips, no flat text that is secretly a link)? [I]
7. L1.7 Was the verdict on this law reached after at least one operated task walk, not from
   screenshots alone? The reviewer records the walk. [I]

**Thresholds with sources.** Contrast 4.5:1 text, 3:1 large text (WCAG 1.4.3 AA); 3:1 for
non-text UI components and states (WCAG 1.4.11 AA). Alignment tolerance is a heuristic.

**How to test.** Token check in code (C); contrast and alignment by script on the rendered DOM
(M); visual pass over all states (S); a task walk to make sure polish is not masking a defect (I).

**Typical violations in B2B data apps.** Hand-tuned paddings that differ between two tables on
the same page; light-grey secondary text in dense tables below 4.5:1; a beautiful dashboard
whose filters do not apply; empty and error states left unstyled; dark mode borders that vanish.

**Severity.** Contrast failure on content or controls: High (WCAG AA). Token drift or
misalignment: Low to Medium. When polish hides a broken interaction, rate the hidden defect,
not the polish.

**Related.** WCAG 1.4.3, 1.4.11, 1.4.10, 1.4.12. Nielsen H8.

**Not applicable when** the change renders nothing (backend, job, data migration with no screen
change) or only changes words inside an existing, already-reviewed layout.

### L2. Choice Overload

**Definition.** "The tendency for people to get overwhelmed when they are presented with a large
number of options, often used interchangeably with the term paradox of choice."
(https://lawsofux.com/choice-overload/). The site traces the term to Toffler, Future Shock (1970).

**Evidence quality: weak and contested as a general effect; moderate under known moderators.**
Iyengar and Lepper 2000 (24 vs 6 jams): 60% vs 40% of passers-by stopped, about 3% vs about 30%
of those who stopped bought (https://timharford.com/2009/11/given-the-choice-how-much-choice-would-you-like/).
Scheibehenne, Greifeneder and Todd 2010 meta-analysis (J. Consumer Research 37(3) 409-425; 63
conditions, 50 experiments, N=5,036): mean effect size "virtually zero" with large variance
(https://madoc.bib.uni-mannheim.de/30861/). Chernev, Böckenholt and Goodman 2015 (J. Consumer
Psychology 25(2) 333-358): the effect is reliable when four moderators are high: choice-set
complexity, decision-task difficulty, preference uncertainty, effort-minimising goal
(https://www.kellogg.northwestern.edu/faculty/research/detail/2015/when-product-assortment-leads-to-choice-overload-a-conceptual).

**Auditable checks.**
1. L2.1 At each point where the user must pick one option from several (package, template,
   recipient group, object type in a "New" menu), is there a default or a marked recommendation,
   or a stated reason why none is given? [S, I]
2. L2.2 When options must be compared, are they shown side by side with the same attributes in
   the same order, so the user never has to open each option to compare it? [S]
3. L2.3 Does every select, combobox or picker whose options do not all fit in its open panel
   offer type-to-filter or search? [I, N]
4. L2.4 Does every option carry a label that states its distinguishing attribute, with no two
   options sharing a label? [N, S]
5. L2.5 Does the UI say whether the choice can be changed later, and can it be (lowering the
   stakes of the decision)? [I]
6. L2.6 Record the number of competing options at each decision point the change adds. When it
   rises, the review names which Chernev moderator (complexity, difficulty, uncertainty, goal)
   the design reduces. [N]

**Thresholds with sources.** No count threshold is supported by the meta-analytic evidence; do
not fail on a count alone. The 6 vs 24 numbers describe one field study, not a limit.

**How to test.** Count options (N); open every picker and type a partial term (I); compare the
comparison layout (S).

**Typical violations in B2B data apps.** A "New" menu listing a dozen object types with no
description; a column picker with dozens of unordered columns and no search; a package picker
for a charge where packages cannot be compared; a filter panel with every facet expanded.

**Severity.** High when the choice commits money, consent or access and options are not
comparable. Medium for a frequent choice with no search. Low for a rare choice.

**Related.** WCAG 3.3.2 Labels or Instructions, 2.4.6 Headings and Labels. Nielsen H6, H7, H8.

**Not applicable when** the change adds or alters no point where the user chooses among
alternatives.

### L3. Chunking

**Definition.** "A process by which individual pieces of an information set are broken down and
then grouped together in a meaningful whole." (https://lawsofux.com/chunking/). Origin: Miller
1956, "The Magical Number Seven, Plus or Minus Two".

**Evidence quality: strong.** Chunking is one of the best-replicated findings in memory research
and is the basis of Cowan's capacity estimate in chunks (Cowan 2001,
https://pubmed.ncbi.nlm.nih.gov/11515286/). The UI application (grouping, formatting) is direct.

**Auditable checks.**
1. L3.1 Are long identifiers shown in groups (IBAN, phone numbers, long reference codes) as in
   NN/g's phone-number examples (https://www.nngroup.com/articles/chunking/)? [S]
2. L3.2 Does copying a grouped value and pasting it back into the product's own input succeed
   (the grouping must not break round-trips)? [I]
3. L3.3 Are forms with many fields split into labelled groups? NN/g's example: 12 fields read as
   less daunting in 3 groups of 4 (https://www.nngroup.com/articles/gestalt-proximity/). [S, N]
4. L3.4 Are groups exposed in code (fieldset with legend, or a heading per section, or
   role="group" with an accessible name)? (WCAG 1.3.1) [C]
5. L3.5 Is running text broken into short paragraphs with lines of about 50-75 characters, with
   headings and lists where the content is a list (NN/g chunking article)? [S, M]
6. L3.6 Are long tables broken into pages or sections with a visible total ("1-50 of 1,240"),
   so the reader can locate a chunk? [S]

**Thresholds with sources.** Line length about 50-75 characters (NN/g, chunking article).
Group size: no source gives a hard number; the 3x4 example is illustrative.

**How to test.** Screenshot inspection (S), a script measuring characters per line (M), code
inspection of grouping semantics (C), paste test (I).

**Typical violations in B2B data apps.** Settings pages as one long column of 30 fields; an
API key or IBAN shown as one 34-character run; consent text as one paragraph; an audit log as an
undifferentiated stream with no day grouping.

**Severity.** Medium when a long form has no groups or a grouped value cannot be pasted back
(High if that value is a payment identifier). Low for line-length issues.

**Related.** WCAG 1.3.1 Info and Relationships, 2.4.6, 2.4.10 Section Headings (AAA). Nielsen H8.

**Not applicable when** the change shows no multi-part information (a single control or a
one-line message).

### L4. Cognitive Bias

**Definition.** "A systematic error of thinking or rationality in judgment that influence our
perception of the world and our decision-making ability." (https://lawsofux.com/cognitive-bias/).
Origin: Tversky and Kahneman from 1972.

**Evidence quality: strong for several individual biases, but the law is an umbrella, not a
single testable effect.** The default effect is among the strongest for interfaces: Johnson and
Goldstein 2003 (Science, "Do defaults save lives?") found far higher effective organ-donor
consent in opt-out than opt-in countries
(https://business.columbia.edu/press-release/cbs-press-releases/opt-out-best-plan-donors).
For a review the useful frame is: which bias could the design exploit, and does it?

**Auditable checks.**
1. L4.1 Is every consent checkbox (marketing, data sharing, cookies) unticked by default? The
   CJEU ruled a pre-ticked box is not valid consent (Planet49, C-673/17, 2019,
   https://curia.europa.eu/jcms/upload/docs/application/pdf/2019-10/cp190125en.pdf). [C, S]
2. L4.2 Are the accept and decline (or grant and withhold) options for money, consent and access
   given equal visual weight and equally plain wording, with no shaming copy on the decline?
   For consent, refusal must be as easy and as prominent as acceptance (EDPB Guidelines 05/2020;
   EDPB Cookie Banner Taskforce report 2023,
   https://www.edpb.europa.eu/our-work-tools/our-documents/other/report-work-undertaken-cookie-banner-taskforce_en).
   Otherwise see "Scope decides the source" below. [S]
3. L4.3 Is withdrawing consent, unsubscribing or ending a service no more steps than granting
   or starting it? Count both paths. GDPR Art. 7(3): "It shall be as easy to withdraw as to give
   consent." Consumer subscriptions also need the cancellation button of BGB 312k
   (https://www.gesetze-im-internet.de/bgb/__312k.html). [I, N]
4. L4.4 Does the UI avoid asking again for a choice the user already made (no repeat prompts
   after a decline)? See "Scope decides the source" below. [I]
5. L4.5 Does every default on a money, consent, access, mail or personal-data field favour the
   safe outcome for the user (for example, "notify registrants" off until chosen, smallest
   charge, least access, personal data left out of an export)? This wins over L21.4
   (common-case defaults) when the most common choice is the risky one; for personal data it is
   the law (GDPR Art. 25(2), https://eur-lex.europa.eu/eli/reg/2016/679/oj). [C, S]
6. L4.6 Is every number that supports a decision shown with its reference (unit, period,
   before and after, budget left after) so the user does not anchor on a lone figure? [S]
7. L4.7 Do money input placeholders avoid plausible amounts that could anchor or be mistaken for
   a value? **(heuristic)** [S, C]

**Thresholds with sources.** Binary legal tests: unticked consent (Planet49); withdrawal as easy
as granting (GDPR Art. 7(3)). Others are pass/fail by inspection.

**Scope decides the source for L4.2-L4.4.** On a consumer-facing surface, prominence that steers,
harder exits and repeated requests are unfair commercial practices: cite the UCPD (Art. 6-7 and
Annex I, https://eur-lex.europa.eu/eli/dir/2005/29/oj; in Germany the UWG) and route to counsel.
On a surface used only by business customers the consumer law does not bind, and the **honesty
rule (ours)** applies instead: the interface never gives one choice more prominence to steer,
never makes the exit harder than the entry, never repeats a request after a decline, and never
shows manufactured progress, urgency or scarcity. DSA Art. 25 binds providers of online
platforms only (https://eur-lex.europa.eu/eli/reg/2022/2065/oj); do not cite it for a console or
a company's own website.

**How to test.** Read defaults in code and in a fresh session (C, S); walk grant and withdraw
paths and count steps (I, N).

**Typical violations in B2B data apps.** A partner invite that defaults to the highest role; a
"notify all registrants" box pre-ticked; a bulk export that includes personal data by default;
a cancel-subscription path three screens deeper than sign-up; a grey "No thanks" next to a
solid "Yes".

**Severity.** Critical for pre-ticked consent or harder withdrawal (legal). High for defaults
that favour more access, more charge or more mail. Medium for anchoring or framing issues.

**Related.** WCAG 3.3.4 Error Prevention (Legal, Financial, Data). Nielsen H3, H5.

**Not applicable when** the change contains no decision, default, consent, or number that
supports a decision.

### L5. Cognitive Load

**Definition.** "The amount of mental resources needed to understand and interact with an
interface." (https://lawsofux.com/cognitive-load/). Origin: Sweller's cognitive load theory
(1988). The site distinguishes intrinsic load (the task) from extraneous load (the interface).

**Evidence quality: strong as a theory of learning and working-memory limits; moderate as a
direct UI measure** (load is rarely measured in reviews; checks use proxies). NN/g's three
tactics: avoid visual clutter, build on existing mental models, offload tasks
(https://www.nngroup.com/articles/minimize-cognitive-load/).

**Auditable checks.**
1. L5.1 Does every element on the changed screen serve the task of that screen? List each
   element that does not; each is extraneous load. [S, N]
2. L5.2 Is information the system already has prefilled or offered for selection instead of
   re-typed (WCAG 3.3.7 Redundant Entry)? [I]
3. L5.3 Does the UI compute what the user would otherwise compute in their head (totals,
   remaining budget, end dates, counts of affected records)? [S, I]
4. L5.4 Count the distinct text styles (size and weight pairs) on the screen; are all of them
   from the type scale and each used for one meaning? [N, C]
5. L5.5 Are labels in the users' words, consistent with the product glossary, with no internal
   codes, enum keys or untranslated strings? [S]
6. L5.6 Does authentication avoid a cognitive function test (remembering or transcribing)
   unless an alternative or assistance such as paste and password managers is allowed? (WCAG
   3.3.8 AA) [I, C]
7. L5.7 Is there at most one visually dominant next step per view region (see L28.1)? [N, S]

**Thresholds with sources.** None numeric beyond the WCAG criteria named. Clutter counts are
reported, not judged against a number.

**How to test.** Element inventory (N); task walk noting every recall or calculation the user
must do (I); code check of text styles (C).

**Typical violations in B2B data apps.** Dashboards with ten equal-weight cards; tables that
show raw enum values; forms asking for the company name the system already holds; a review step
that shows the amount but not the budget left afterwards.

**Severity.** High when the user must calculate or remember a value to decide a money or
consent action. Medium for redundant entry. Low for clutter.

**Related.** WCAG 3.3.7 (A), 3.3.8 (AA), 3.3.2. Nielsen H6, H8.

**Not applicable when** the change has no rendered UI.

### L6. Doherty Threshold

**Definition.** "Productivity soars when a computer and its users interact at a pace (<400ms)
that ensures that neither has to wait on the other." (https://lawsofux.com/doherty-threshold/).
Origin: Doherty and Thadhani (spelled "Thadani" on lawsofux.com), "The Economic Value of Rapid
Response Time", IBM, 1982, form GE20-0752-0.

**Evidence quality: moderate.** The 1982 document is an IBM report based on IBM field and lab
data (scan at https://archive.computerhistory.org/resources/access/text/2024/03/102751398-05-01-acc.pdf).
Its text argues for "subsecond" response; it reports that cutting system response from 3.0 s
to 0.3 s raised a programmer's transactions from about 180 to 371 per hour (+106%), and a 35%
productivity gain when response went from 0.6 s to 0.25 s. The specific "400 ms" figure is not
stated in the OCR text of that scan (it may sit in a figure); treat 400 ms as the lawsofux
summary, not as a measured cut-off. Better-sourced limits: Nielsen's 0.1 s / 1 s / 10 s
(https://www.nngroup.com/articles/response-times-3-important-limits/, after Miller 1968 and Card
et al. 1991) and Google's RAIL and INP.

**Auditable checks.**
1. L6.1 For every interaction in the change (click, toggle, sort, filter, open panel, inline
   save), does visible feedback (pressed state, optimistic change, or busy state on the control)
   appear within 100 ms? [T]
2. L6.2 Is each measured interaction's Interaction to Next Paint at most 200 ms ("good"; over
   500 ms is "poor")? [T]
3. L6.3 For operations that take about 2-10 s, is there a looped busy indicator on the control
   or region that is waiting, and is a second submit blocked? [T, I]
4. L6.4 For operations of 10 s or more, is there a percent-done or step indicator, and can the
   user keep working elsewhere? [T, I]
5. L6.5 Is no progress indicator shown for operations under 1 s (no spinner or skeleton that
   flashes on and off)? [T, S]
6. L6.6 Is there no artificial delay in the code path of any action (search the diff for
   timers or sleeps around writes and navigation)? [C]
7. L6.7 Is every status that appears without moving focus (saved, failed, 3 results) exposed to
   assistive technology as a status message? (WCAG 4.1.3 AA) [C]

**Thresholds with sources.**
- 0.1 s feels instantaneous; 1 s keeps the flow of thought; 10 s keeps attention (NN/g, above).
- NN/g progress indicators: none under 1 s; looped animation for 2-10 s; percent-done for 10 s
  or more (https://www.nngroup.com/articles/progress-indicators/).
- RAIL: complete the response to input within 100 ms, handle events within 50 ms, frames in
  10 ms (16 ms hard limit at 60 fps) (https://web.dev/articles/rail).
- INP: good at most 200 ms, poor above 500 ms, judged at the 75th percentile
  (https://web.dev/articles/optimize-inp).
- 400 ms: lawsofux summary of Doherty and Thadhani; see the provenance note above.

**How to test.** Performance trace or Playwright timing for each interaction, on a stated
machine and throttling profile, three runs, report the median (T). Code search for timers (C).

**Typical violations in B2B data apps.** Server-side filtering that freezes the table with no
busy state; a "Save" that shows nothing for 2 s; a full-page skeleton that flashes for 150 ms on
every sort; an export that runs 40 s behind a spinner with no progress; a bulk action that can
be submitted twice.

**Severity.** Critical when the lack of feedback lets a money, consent or mail action be
submitted twice. High for frequent interactions over 1 s with no feedback. Medium for INP
between 200 and 500 ms. Low for indicator flashes.

**Related.** WCAG 4.1.3 Status Messages (AA), 2.2.2 Pause, Stop, Hide (for long animations).
Nielsen H1.

**Not applicable when** the change has no interaction (static content only).

### L7. Fitts's Law

**Definition.** "The time to acquire a target is a function of the distance to and size of the
target." (https://lawsofux.com/fittss-law/). Origin: Fitts 1954. HCI uses MacKenzie's Shannon
formulation, MT = a + b log2(D/W + 1) (MacKenzie 1992, https://www.yorku.ca/mack/hci1992.html).

**Evidence quality: strong.** One of the most replicated quantitative models in HCI. Note the
logarithm: doubling an already adequate target buys little.

**Auditable checks.**
1. L7.1 Is every pointer target at least 24x24 CSS px, or does it meet the spacing exception
   (a 24 CSS px diameter circle centred on its bounding box intersects no other target or other
   circle), or another 2.5.8 exception (equivalent control, inline in a sentence, user-agent
   control, essential)? (WCAG 2.5.8 AA) [M]
2. L7.2 On phone-width layouts, are the primary and frequent targets at least 44x44 CSS px?
   This is the WCAG 2.5.5 AAA level, which the 2.5.8 Understanding document suggests "for
   important links/controls"; Apple's HIG asks for a 44x44 pt hit region; Material asks for
   48x48 dp. [M]
3. L7.3 Is the hit area of icon-only buttons, checkboxes and radios the full padded box (or the
   whole row and label), not only the glyph? [M, C]
4. L7.4 Does the control that completes a step sit next to where the step ends (dialog buttons
   at the dialog's end, bulk-action bar next to the selection, submit after the last field)? [S]
5. L7.5 Do menus and popovers open adjacent to their trigger? (NN/g Fitts article) [I]
6. L7.6 Are destructive targets separated from frequent targets (not adjacent in the same
   button row or row menu without spacing or a divider)? [S, M]
7. L7.7 Does no target move under the pointer after it renders (late-loading content pushing
   buttons down)? [T, I]
8. L7.8 Does every drag operation have a single-pointer alternative without dragging? (WCAG
   2.5.7 AA) [I]

**Thresholds with sources.**
- WCAG 2.5.8 (AA): 24x24 CSS px or the spacing exception
  (https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html).
- WCAG 2.5.5 (AAA): 44x44 CSS px; inline targets exempt
  (https://www.w3.org/WAI/WCAG22/Understanding/target-size-enhanced.html).
- Apple HIG: buttons need "a hit region of at least 44x44 pt - in visionOS, 60x60 pt"; iOS
  default control size 44x44 pt, minimum 28x28 pt; macOS default 28x28 pt, minimum 20x20 pt;
  about 12 pt padding around bezelled elements and about 24 pt around borderless ones
  (https://developer.apple.com/design/human-interface-guidelines/accessibility).
- Material / Android: at least 48x48 dp, separated by 8 dp or more
  (https://support.google.com/accessibility/android/answer/7101858).

**How to test.** A script that lists every focusable or clickable element with its bounding
box and checks the 24 px circle rule (M); screenshot inspection for placement (S); pointer and
touch walk (I).

**Typical violations in B2B data apps.** 16 px icon buttons in table rows packed edge to edge;
a row "..." menu adjacent to a delete icon; pagination arrows of 20x20 px; a sticky selection bar
at the top of the page while the user selects at the bottom; column resize handles of 4 px with
no keyboard alternative.

**Severity.** High for a 2.5.8 failure on a frequent control (AA). Critical when a destructive or
money target sits adjacent to a frequent one with no separation and no undo. Medium for distance
issues. Low for 2.5.5-only shortfalls on desktop.

**Related.** WCAG 2.5.8 (AA), 2.5.5 (AAA), 2.5.7 (AA). Nielsen H5, H7.

**Not applicable when** the change adds or moves no pointer target.

### L8. Flow

**Definition.** "The mental state in which a person performing some activity is fully immersed
in a feeling of energized focus, full involvement, and enjoyment in the process of the
activity." (https://lawsofux.com/flow/). Origin: Csikszentmihalyi 1975.

**Evidence quality: moderate as a psychological construct, weak as a UI law.** Nakamura and
Csikszentmihalyi (2002) treat clear goals, immediate feedback and a balance of challenge and
skill as preconditions (https://www.psy.gla.ac.uk/~steve/courses/pospsydocs/oldwikis/2015.20.Flow.pdf).
A review cannot observe flow; it checks the preconditions and the interruptions that break it.

**Auditable checks.**
1. L8.1 Does each screen state its task or object in its title, so the goal is clear on
   arrival? [S]
2. L8.2 Does every action produce feedback on the thing that changed (links to L6.1)? [I]
3. L8.3 Do frequent actions have an accelerator for experienced users (keyboard shortcut,
   command menu entry, bulk action) alongside the visible control? [I, C]
4. L8.4 After save, close, Back or reload, does the user keep their place: scroll position,
   selection, open row, filters, sort and page? [I]
5. L8.5 Are routine actions free of confirmation dialogs and blocking modals (confirmation only
   where consequences are serious; see Section 5)? [I, N]
6. L8.6 Does no background event (toast, autosave, refetch) move focus or change context while
   the user is typing? (WCAG 3.2.1, 3.2.2) [I]
7. L8.7 Can the user postpone or suppress non-urgent interruptions? (WCAG 2.2.4 AAA) [I]

**Thresholds with sources.** Feedback timing per L6. No flow-specific numbers are sourced.

**How to test.** Keyboard-only and mouse task walks of the main job, repeated three times to
simulate an experienced user (I); count interruptions per walk (N).

**Typical violations in B2B data apps.** Opening a record navigates away and loses the list's
filters; every inline edit asks "Are you sure?"; a refetch resets the table scroll; a toast
steals focus; no keyboard path for the action done fifty times a day.

**Severity.** High when place or input is lost (rework). Medium for missing accelerators on
frequent tasks. Low otherwise.

**Related.** WCAG 2.4.3 Focus Order, 3.2.1 On Focus, 3.2.2 On Input, 2.2.4 Interruptions (AAA).
Nielsen H1, H3, H7.

**Not applicable when** the change has no task flow (a static page or a mail template).

### L9. Goal-Gradient Effect

**Definition.** "The tendency to approach a goal increases with proximity to the goal."
(https://lawsofux.com/goal-gradient-effect/). Origin: Hull 1932, rats running faster nearer food.

**Evidence quality: moderate, narrow.** Kivetz, Urminsky and Zheng 2006 (J. Marketing Research
43, 39-58): in a cafe reward card, inter-purchase times fell 20% (0.7 days) as customers neared
the reward; a 12-stamp card with 2 bonus stamps was completed in 12.7 days vs 15.6 days for a
plain 10-stamp card (https://business.columbia.edu/sites/default/files-efs/pubfiles/1200/goalgradient.pdf).
Evidence is from reward programmes and rating tasks; transfer to B2B forms is plausible but
untested.

**Auditable checks.**
1. L9.1 Does every multi-step flow show the current step and total ("Step 2 of 4") or an
   equivalent list of steps with the current one marked? [S]
2. L9.2 Does a setup or completion checklist name each remaining item and link to it ("still
   missing")? [S, I]
3. L9.3 Is shown progress true: computed from real completion, never padded or fixed? [C]
4. L9.4 Is progress kept when the user leaves and returns? [I]
5. L9.5 Are there no surprise steps at the end that were not in the step list at the start? [I, N]
6. L9.6 Is the completion state explicit (the thing is now live, sent or done) rather than
   implied by the disappearance of the form? [S]

**Thresholds with sources.** None numeric for UI.

**How to test.** Walk the flow, leave midway, return (I); read how progress is computed (C).

**Typical violations in B2B data apps.** A partner onboarding with no indication of how much is
left; a progress bar that jumps from 20% to 100%; a "Finish" that reveals two more mandatory
screens; a setup checklist that says "3 items left" without naming them.

**Severity.** High if progress misreports completion of something that gates money or mail
(for example, "ready to send" while a required field is empty). Medium for missing step
indicators in long flows. Low otherwise.

**Related.** WCAG 1.3.1 (step list semantics, aria-current="step"), 3.3.2. Nielsen H1.

**Not applicable when** the change has no multi-step task or completion state.

### L10. Hick's Law

**Definition.** "The time it takes to make a decision increases with the number and complexity
of choices." (https://lawsofux.com/hicks-law/). Origin: Hick 1952 and Hyman 1953: choice
reaction time grows with the logarithm of the number of equally likely alternatives (more
precisely, with information transmitted in bits).

**Evidence quality: strong in the lab, weak or contested for UI design.** Liu, Gori, Rioul,
Beaudouin-Lafon and Guiard, "How Relevant is Hick's Law for HCI?" (CHI 2020) argue that (1)
Hick's law "speaks against, not for, the popular principle that 'less is better'", (2)
logarithmic data is not necessarily Hick's law, (3) the stimulus-response paradigm is rarely
relevant to HCI tasks, and (4) visual search and decision making explain more
(https://researchportal.ip-paris.fr/en/publications/how-relevant-is-hicks-law-for-hci/).
For randomly ordered lists the user must scan, time grows linearly and Hick's law does not apply
(https://en.wikipedia.org/wiki/Hick%27s_law).

**Auditable checks.**
1. L10.1 Record the number of options at each decision point the change adds or alters. [N]
2. L10.2 Is every list of options ordered by a rule the user can predict (frequency, workflow
   order, or alphabetical for named items) so the user can search rather than scan? [S]
3. L10.3 Where one option is right for most users, is it marked as recommended or set as the
   default (lawsofux takeaway)? [S]
4. L10.4 Was a list kept flat rather than split into nested submenus only to reduce the count
   per level? (Logarithmic growth means one longer, ordered level usually beats extra levels;
   see Liu et al. 2020 and NN/g's 2-level limit for progressive disclosure.) [S, I]
5. L10.5 Are rarely used options moved behind a clearly labelled secondary control rather than
   mixed with frequent ones? [S, N]
6. L10.6 Do long option lists support keyboard type-ahead? [I]

**Thresholds with sources.** No sourced maximum number of options. Do not fail on a count alone.

**How to test.** Count options (N); judge ordering (S); keyboard walk of each picker (I).

**Typical violations in B2B data apps.** A row menu with 14 actions in creation order; a
status filter whose values are in database order; nested "More > Advanced > Export" for a
frequent export; two equally styled primary paths on a create screen.

**Severity.** Medium for unordered or unprioritised option lists on frequent tasks. Low for
rare ones. Raise to High only when a wrong choice commits money, consent or access.

**Related.** WCAG 2.4.6, 3.3.2. Nielsen H6, H7, H8.

**Not applicable when** the change adds no decision point with more than one option.

### L11. Jakob's Law

**Definition.** "Users spend most of their time on other sites. This means that users prefer
your site to work the same way as all the other sites they already know."
(https://lawsofux.com/jakobs-law/; https://www.nngroup.com/videos/jakobs-law-internet-ux/).
Coined by Jakob Nielsen.

**Evidence quality: moderate.** It is an observation grounded in transfer of learning and mental
models (see L17), widely corroborated by usability testing, but "the law" as stated has not been
tested as a quantitative effect. NN/g itself discusses when inconsistency is justified.

**Auditable checks.**
1. L11.1 Do links navigate and buttons act, using real `<a href>` and `<button>` elements, so
   middle-click, open-in-new-tab and copy-link work on links? [C, I]
2. L11.2 Do standard keys behave as on the web: Enter submits a single-form dialog, Space
   toggles a checkbox, Escape closes the top overlay, arrow keys move in menus, listboxes and
   tabs? [I]
3. L11.3 Does browser Back return to the previous view with its state, and does reload keep the
   current view (state in the URL)? [I]
4. L11.4 Are icons used with their conventional meaning (trash = delete, pencil = edit, gear =
   settings, magnifier = search) and labelled? [S]
5. L11.5 Are links visually distinguishable from body text by more than colour alone (or meet
   the 3:1 contrast with surrounding text plus a non-colour cue on focus and hover, as in WCAG
   technique G183)? (lawsofux Similarity takeaway; WCAG 1.4.1) [S]
6. L11.6 Does the change reuse the product's existing component for the same job (internal
   consistency), with the same name for the same action across screens? (WCAG 3.2.4) [C]
7. L11.7 Are repeated navigation elements in the same relative order on every page? (WCAG 3.2.3) [S]
8. L11.8 When the change replaces a familiar pattern, is the change announced or eased (the
   lawsofux takeaway: let users keep the familiar version for a limited time, or explain)? [S, I]

**Thresholds with sources.** Binary checks; WCAG 3.2.3, 3.2.4 (AA), 1.4.1 (A).

**How to test.** Keyboard walk (I), code semantics (C), side-by-side with existing screens (S).

**Typical violations in B2B data apps.** Table rows that navigate on click but are not links
(no new tab, no copy link); a custom dropdown where arrow keys do nothing; filters not in the
URL so Back loses them; a "Remove" on one screen and "Delete" for the same action on another; a
custom date picker that ignores typing.

**Severity.** High when a keyboard convention fails on a primary task (also a WCAG 2.1.1
failure). Medium for broken Back or new-tab behaviour. Low for icon convention issues with
labels present.

**Related.** WCAG 2.1.1 Keyboard (A), 3.2.3 (AA), 3.2.4 (AA), 4.1.2 Name, Role, Value (A), 1.4.1
(A). Nielsen H4, H2.

**Not applicable when** the change introduces no interactive pattern (copy-only or data-only).

### L12. Law of Common Region

**Definition.** "Elements tend to be perceived into groups if they are sharing an area with a
clearly defined boundary." (https://lawsofux.com/law-of-common-region/). Origin: Gestalt
grouping; common region was named by Palmer (1992).

**Evidence quality: strong as a perceptual effect.** Reviewed in Wagemans et al. 2012
(Psychological Bulletin 138(6), https://pubmed.ncbi.nlm.nih.gov/22845751/). NN/g: "Creating a
clear boundary is a strong visual cue that can overpower other grouping principles such as
proximity or similarity" (https://www.nngroup.com/articles/common-region/).

**Auditable checks.**
1. L12.1 Does every bordered or filled region (card, panel, section, fieldset, toolbar) contain
   only items that belong together, and are related items not split across regions? [S]
2. L12.2 Where a boundary is the only visual cue that identifies a control (an input's outline,
   a toggle track), does it reach 3:1 against adjacent colours? (WCAG 1.4.11) Purely decorative
   card borders are not required to. [M]
3. L12.3 Are regions still distinguishable in dark mode and at 150% zoom? [S]
4. L12.4 Is box-in-box nesting limited so that each boundary means something? Report the
   nesting depth; flag more than two nested bordered regions **(heuristic)**. [N, S]
5. L12.5 Do visual regions match code structure (section with heading, fieldset with legend,
   role="group" or landmark with a name)? (WCAG 1.3.1) [C]
6. L12.6 Does a region that acts on another (bulk-action bar, table toolbar) visibly attach to
   the region it acts on? [S]

**Thresholds with sources.** 3:1 for boundaries needed to identify a component (WCAG 1.4.11).
Nesting depth is a heuristic.

**How to test.** Screenshot pass in both themes and zooms (S); DOM structure (C); contrast
script (M).

**Typical violations in B2B data apps.** A card per field in a settings page (everything boxed,
nothing grouped); a filter bar boxed together with unrelated page actions; a side panel whose
sections have no boundaries or headings; input borders at 1.5:1.

**Severity.** High for a 1.4.11 failure on input boundaries. Medium for misleading groupings.
Low for over-boxing.

**Related.** WCAG 1.3.1 (A), 1.4.11 (AA). Nielsen H8.

**Not applicable when** the change adds no grouping or container.

### L13. Law of Proximity

**Definition.** "Objects that are near, or proximate to each other, tend to be grouped together."
(https://lawsofux.com/law-of-proximity/).

**Evidence quality: strong** as a perceptual grouping principle (Wertheimer; Wagemans et al.
2012). NN/g: proximity "can override competing visual cues such as similarity of color or shape"
(https://www.nngroup.com/articles/gestalt-proximity/).

**Auditable checks.**
1. L13.1 Is each field label closer to its own field than to any other field (gap label to
   field smaller than gap field to next label)? Report both gaps in px. [M]
2. L13.2 Is spacing within a group smaller than spacing between groups everywhere on the screen
   (forms, cards, toolbars, detail panels)? [M, S]
3. L13.3 Does helper text and error text sit directly under (or beside) the field it belongs to,
   closer to it than to the next field? [S, M]
4. L13.4 Is every action placed next to the object it acts on (row actions in the row, section
   actions in the section)? [S]
5. L13.5 Are units, currencies and status adjacent to the value they qualify? [S]
6. L13.6 Are the groupings preserved at 390 CSS px width and at 150% zoom (NN/g warns proximity
   relationships shift on small screens)? [S]
7. L13.7 In tables, is each header visually closer to its column than to neighbouring columns
   (alignment matches the cell content alignment)? [S]

**Thresholds with sources.** Relative rule only (within-group gap smaller than between-group
gap). No absolute px value is sourced.

**How to test.** Script measuring gaps between labels, fields and groups (M); screenshots at
three widths (S).

**Typical violations in B2B data apps.** Equal spacing everywhere in a long form, so labels float
between fields; an error message closer to the next field's label; a "Delete" button floating at
the far right of a wide row, nearer the next column than its row; header text left-aligned over
right-aligned numbers.

**Severity.** Medium for ambiguous label-field pairing (High if it is a money field). Low for
other spacing issues.

**Related.** WCAG 1.3.1 (the visual association must also exist in code), 3.3.2. Nielsen H8.

**Not applicable when** the change adds no layout (copy change in place).

### L14. Law of Prägnanz

**Definition.** "People will perceive and interpret ambiguous or complex images as the simplest
form possible, because it is the interpretation that requires the least cognitive effort of us."
(https://lawsofux.com/law-of-pr%C3%A4gnanz/). Origin: Wertheimer and the Gestalt school.

**Evidence quality: moderate, hard to operationalise.** Simplicity is central to Gestalt theory,
but Wagemans et al. 2012 discuss its conceptual problems (what "simplest" means is not fixed).
Use it as a check against ambiguous shapes, not as a measurement.

**Auditable checks.**
1. L14.1 Is every icon recognisable at its rendered size (16-24 px) without its label, or does it
   carry a visible label? [S]
2. L14.2 Do composite visuals (stacked avatars, overlapping badges, status dots on icons) still
   read unambiguously at 100% zoom, with a text alternative? [S, C]
3. L14.3 Does the screen use a small number of distinct shapes and treatments (border styles,
   corner radii, divider styles)? Report the counts; each must come from the design system. [N, C]
4. L14.4 Do charts avoid decoration that adds shapes without data (3D, gradients, heavy
   gridlines)? [S]
5. L14.5 Does the layout follow one grid, so columns and edges form simple lines? [S]

**Thresholds with sources.** None numeric.

**How to test.** Screenshot inspection (S); token and component audit (C); counting treatments (N).

**Typical violations in B2B data apps.** A status shown as an icon with an overlay badge and a
coloured ring; three different card corner radii on one page; donut charts with 12 slices.

**Severity.** Medium when an ambiguous shape carries status that drives a decision. Low otherwise.

**Related.** WCAG 1.1.1 Non-text Content (text alternative), 1.4.1. Nielsen H8.

**Not applicable when** the change adds no icons, graphics, charts or new layout.

### L15. Law of Similarity

**Definition.** "The human eye tends to perceive similar elements as a complete picture, shape,
or group, even if those elements are separated." (https://lawsofux.com/law-of-similarity/).

**Evidence quality: strong** as a perceptual grouping principle (Wagemans et al. 2012).

**Auditable checks.**
1. L15.1 Do all elements with the same function look the same across the change (every
   destructive button the same variant, every link the same style, every status of one kind the
   same badge)? [S, C]
2. L15.2 Do elements with different functions look different (clickable chips vs static tags,
   links vs plain text, editable vs read-only fields)? [S]
3. L15.3 Is each colour used for one meaning only across the screen (for example, red only for
   errors and destructive actions, not also for a brand accent or a chart series)? [S]
4. L15.4 Is meaning never carried by colour alone; is there also text, an icon or a shape?
   (WCAG 1.4.1) [S]
5. L15.5 Does the change use the shared component for each job rather than a hand-built look-
   alike (search the diff for duplicated styles of existing components)? [C]
6. L15.6 Are hover, focus, selected and disabled states styled the same way as elsewhere in the
   product? [S, I]

**Thresholds with sources.** Binary; WCAG 1.4.1 (A), 3.2.4 (AA).

**How to test.** Inventory of components and variants per screen (C, N); visual comparison (S).

**Typical violations in B2B data apps.** A secondary action styled like a status badge; two
shades of "danger" red; "Active" green in one table and blue in another; a hand-rolled button
that looks like the shared one but has no focus ring.

**Severity.** High when colour alone signals status or error (1.4.1 A). Medium for inconsistent
variants on related actions. Low for minor style drift.

**Related.** WCAG 1.4.1 (A), 3.2.4 (AA), 1.4.11 (AA). Nielsen H4.

**Not applicable when** the change adds no visual element.

### L16. Law of Uniform Connectedness

**Definition.** "Elements that are visually connected are perceived as more related than
elements with no connection." (https://lawsofux.com/law-of-uniform-connectedness/). Proposed as
a grouping principle by Palmer and Rock 1994 (Psychonomic Bulletin and Review 1, 29-55).

**Evidence quality: moderate to strong** perceptually (Palmer and Rock argue it precedes other
grouping; Wagemans et al. 2012 review it).

**Auditable checks.**
1. L16.1 Do joined controls (segmented buttons, button groups, input with attached button) join
   only options that belong to one decision? [S]
2. L16.2 Does a stepper or timeline connect steps in their real order with a visible line or
   track? [S]
3. L16.3 When a row opens a side panel, is the open row visibly marked as the one the panel
   shows (selected background or indicator)? [S, I]
4. L16.4 Do row hover or zebra striping connect the cells of one record across wide tables? [S]
5. L16.5 Are connectors (lines, arrows) never used decoratively between unrelated elements? [S]

**Thresholds with sources.** None numeric.

**How to test.** Screenshot inspection with a row open and a step active (S, I).

**Typical violations in B2B data apps.** A segmented control mixing a view switch and an action;
an open side panel with no indication which row it belongs to; very wide tables with no row
hover, so users misread values across columns.

**Severity.** Medium when the user may act on the wrong record (High if the panel holds money,
consent or access actions). Low otherwise.

**Related.** WCAG 1.3.1 (connection also exposed: aria-current, aria-selected,
aria-controls). Nielsen H1, H8.

**Not applicable when** the change adds no grouped controls, steps, master-detail or tables.

### L17. Mental Model

**Definition.** "A compressed model based on what we think we know about a system and how it
works." (https://lawsofux.com/mental-model/). Origin: Craik 1943.

**Evidence quality: moderate.** A well-established concept in cognitive science and HCI
(Norman's conceptual models), but not a quantitative law; checks test the match between what
the UI says and what the system does.

**Auditable checks.**
1. L17.1 Does each object and action use the product glossary's term, the same term in both
   portals and in mails? [S]
2. L17.2 After each action, does the system state match what the label promised (operate it:
   "Archive" hides and can restore; "Delete" removes; "Save" persists across reload)? [I]
3. L17.3 Does each object show where it lives and its lifecycle status in the users' terms
   (not internal states)? [S]
4. L17.4 Are consequences outside the screen stated before they happen (mail sent to N people,
   sync to an external CRM, charge to a budget)? [S, I]
5. L17.5 Does the same object have one canonical place and name, so the user does not meet two
   versions of it? [I]
6. L17.6 Does the UI explain what happened when the system did something the user did not
   trigger (automatic status changes, imports, retries)? [S]

**Thresholds with sources.** None numeric.

**How to test.** Operate every action and compare result with label (I); compare terms against
the glossary and other screens (S).

**Typical violations in B2B data apps.** "Cancel" on a booking that only hides it from the
list; "Sync" that queues a job without saying when it runs; "Partner", "Customer" and "Account"
used for the same thing; a status that changes overnight with no explanation.

**Severity.** Critical when the label understates an irreversible or external effect (a
"Save" that also mails registrants). High for label and behaviour mismatches. Medium for
terminology drift.

**Related.** WCAG 2.4.6 (AA), 3.2.4 (AA), 3.3.2 (A). Nielsen H2, H4.

**Not applicable when** the change adds no object, action or term.

### L18. Miller's Law

**Definition.** "The average person can only keep 7 (plus or minus 2) items in their working
memory." (https://lawsofux.com/millers-law/). Origin: Miller 1956.

**Evidence quality: the capacity limit is strong; the number 7 and its UI use are weak.**
Cowan 2001 (Behavioral and Brain Sciences 24(1) 87-114) concludes the central limit is about 4
chunks (3 to 5), and that Miller's 7 was "a rough estimate and a rhetorical device"
(https://pubmed.ncbi.nlm.nih.gov/11515286/). NN/g: "It's a common misconception that limited
short-term memory implies that menus should be similarly limited to 7 items. It's fine to have
longer menus (if needed)" (https://www.nngroup.com/articles/short-term-memory-and-web-usability/).
lawsofux.com's own first takeaway: "Don't use the 'magical number seven' to justify unnecessary
design limitations."

**Auditable checks.**
1. L18.1 Does the review avoid failing or passing anything on "more than 7 items" alone? (A
   menu, list or nav that is visible on screen relies on recognition, not memory.) [process]
2. L18.2 Count the items the user must hold in mind *without seeing them* to finish the task
   (codes to copy, values from another screen, instructions shown earlier). Is the count at most
   about 4 (Cowan)? [N, I]
3. L18.3 Are values the user must transfer (codes, amounts, IDs) available to copy or select
   rather than read and retype? [I]
4. L18.4 Are long numbers and codes chunked for reading (see L3.1)? [S]

**Thresholds with sources.** About 4 chunks, range 3-5 (Cowan 2001). 7 plus or minus 2 is
historical (Miller 1956), not a design limit.

**How to test.** Task walk listing every item the user must remember across steps (I, N).

**Typical violations in B2B data apps.** Asking the user to note a booking reference on one
screen and type it on another; a confirmation code shown in a toast that disappears; review
pages that show changes without the original values.

**Severity.** High when a memorised value feeds a money or access action. Medium otherwise.

**Related.** WCAG 3.3.7 Redundant Entry (A), 3.3.8 (AA). Nielsen H6.

**Not applicable when** the change involves no information carried between steps or screens.

### L19. Occam's Razor

**Definition.** "Among competing hypotheses that predict equally well, the one with the fewest
assumptions should be selected." (https://lawsofux.com/occams-razor/). A principle of parsimony
attributed to William of Ockham. Takeaways: "Analyze each element and remove as many as
possible, without compromising the overall function."

**Evidence quality: weak as an empirical UX law.** It is a philosophical heuristic with no UX
experiment behind it. It is still a useful review discipline.

**Auditable checks.**
1. L19.1 List every element added by the change and its job; does each have one? Any element
   with no job is a finding. [N, S]
2. L19.2 Is there at most one visible control per action within one view (the command menu and
   keyboard shortcuts excepted)? [N]
3. L19.3 Is no information repeated within one view region (title, breadcrumb and heading that
   all say the same; a count shown twice)? Repetition across views for consistency is allowed
   and often required: a status shown in the list row and again in the quick look passes
   (judicious redundancy, Gerhardt-Powals principle 10,
   https://www.tech.dmu.ac.uk/~mstacey/handouts/Sets-of-Design-Principles.docx; L29 keeps
   context visible). [S]
4. L19.4 Is each control the simplest that does the job (a switch, not a two-option select;
   a checkbox, not a yes/no radio pair, unless both answers need explicit choice such as
   consent)? [S, C]
5. L19.5 Does the diff add no option, setting, variant or prop that no requirement asked for? [C]

**Thresholds with sources.** None numeric.

**How to test.** Element inventory against the spec (N, C).

**Typical violations in B2B data apps.** An "Edit" button and an inline edit for the same
field; a page header repeating the breadcrumb; a settings toggle for behaviour nobody can
explain; two export buttons with different formats that could be one.

**Severity.** Medium when duplicate controls behave differently. Low otherwise.

**Related.** Nielsen H8. No direct WCAG criterion.

**Not applicable when** the change only removes elements or only changes logic.

### L20. Paradox of the Active User

**Definition.** "Users never read manuals but start using the software immediately."
(https://lawsofux.com/paradox-of-the-active-user/). Origin: Carroll and Rosson 1987, from IBM
user studies (https://www.nngroup.com/articles/paradox-of-the-active-user/).

**Evidence quality: moderate.** Observational studies in the 1980s, consistently corroborated
by later field research; Carroll and Rosson also describe the related "assimilation paradox"
(prior knowledge from other software misleads).

**Auditable checks.**
1. L20.1 Can a first-time user complete the screen's main task without leaving it to read
   documentation (cold walk, no prior knowledge beyond the role)? [I]
2. L20.2 Does every empty state say what the place is for and offer the next step the reader
   can take? [S]
3. L20.3 Is help in context (hint text under the field, a short explanation next to a complex
   setting) rather than only in a separate help page? [S]
4. L20.4 Can the user try things safely: draft, undo, or a preview before anything reaches money,
   consent, access or mail? [I]
5. L20.5 Do error messages explain how the system works and what to do next (NN/g error
   guideline 12, "concisely educate on how the system works")? [S]
6. L20.6 If a help mechanism exists on several pages, is it in the same relative place on each?
   (WCAG 3.2.6 Consistent Help, A) [S]
7. L20.7 Is no mandatory tour or modal tutorial placed in front of the task? [I]

**Thresholds with sources.** None numeric.

**How to test.** Cold task walk by an agent instructed not to read docs (I); empty and error
state screenshots (S).

**Typical violations in B2B data apps.** An empty table that just says "No data"; a complex
budget rule explained only in a PDF; a first-run tour that blocks the console; a setting whose
effect is only discoverable by trying it on live data.

**Severity.** High when the only way to learn is on live money, consent or mail. Medium for
empty states without a next step. Low otherwise.

**Related.** WCAG 3.2.6 (A), 3.3.2 (A), 3.3.5 Help (AAA). Nielsen H10, H9.

**Not applicable when** the change touches no task a new user would perform (internal
maintenance screen used by one trained operator may still apply; mark n/a only for non-UI
changes).

### L21. Pareto Principle

**Definition.** "The Pareto principle states that, for many events, roughly 80% of the effects
come from 20% of the causes." (https://lawsofux.com/pareto-principle/). Origin: Vilfredo Pareto
on Italian land ownership.

**Evidence quality: weak as a law.** Skewed distributions are common, but the 80/20 split is a
rule of thumb, not a constant; it must be shown with the product's own data each time.

**Auditable checks.**
1. L21.1 Does the change (or its spec) name the top tasks for this screen, with a source (usage
   data, job stories, owner ranking)? If not, mark the law "cannot verify", not pass. [process]
2. L21.2 Are the top tasks reachable from the screen's entry point in the fewest steps of any
   task on it? Count steps for each named task. [I, N]
3. L21.3 Are the top tasks' controls visible without opening a menu, while rare tasks sit in
   menus? [S]
4. L21.4 Do defaults match the most common case for each field? Not on money, consent, access,
   mail or personal data: there the safe default of L4.5 wins even when the risky choice is the
   most common one. [S, C]
5. L21.5 Are the most used columns visible by default in tables, with rarer ones in the column
   picker? [S]

**Thresholds with sources.** None; 80/20 is not a threshold.

**How to test.** Step counts per task (I, N); compare with usage data where it exists.

**Typical violations in B2B data apps.** The daily export hidden under "More" while a once-a-year
setting sits in the toolbar; default sort by creation date when everyone sorts by due date;
a dashboard led by a rarely used metric.

**Severity.** Medium when a top task needs extra steps. Low otherwise.

**Related.** Nielsen H7, H8. No direct WCAG criterion.

**Not applicable when** the change does not alter what is visible, default or reachable.

### L22. Parkinson's Law

**Definition.** "Any task will inflate until all of the available time is spent."
(https://lawsofux.com/parkinsons-law/). Origin: Parkinson's 1955 essay in The Economist.

**Evidence quality: weak.** The source is a humorous essay about the civil service. The nearest
experimental work (Bryan and Locke 1967, "Parkinson's law as a goal-setting phenomenon",
Organizational Behavior and Human Performance 2, 258-275; https://link.springer.com/article/10.3758/BF03210823
lists the citation) reframes it as goal setting. The lawsofux takeaways reduce to "shorten the
task" (autofill, prefill), which is checkable.

**Auditable checks.**
1. L22.1 Do personal-data inputs carry the correct `autocomplete` tokens so browsers can fill
   them? (WCAG 1.3.5 Identify Input Purpose, AA) [C]
2. L22.2 Is information already entered in the same process prefilled or selectable? (WCAG
   3.3.7, A) [I]
3. L22.3 Does the UI impose no time limit; if it must, can the user turn it off, adjust it, or
   extend it after a warning with at least 20 seconds to respond? (WCAG 2.2.1, A) [I, C]
4. L22.4 If a session expires, is entered data kept so the user continues after signing in
   again? (WCAG 2.2.5 Re-authenticating, AAA) [I]
5. L22.5 Is there no artificial urgency (countdowns, "only today") on decisions? [S]
6. L22.6 For long tasks, does the UI say up front what is needed (documents, data) so the user
   is not stopped midway? [S]

**Thresholds with sources.** 20 seconds to extend a time limit (WCAG 2.2.1). Others binary.

**How to test.** Code check of `autocomplete` (C); session-expiry walk (I).

**Typical violations in B2B data apps.** Partner sign-up forms without `autocomplete`; a
magic-link or access-link page that times out and loses a half-filled form; reservation holds
with a silent countdown.

**Severity.** High for a time limit that loses user input or cannot be extended (2.2.1 A).
Medium for missing autocomplete on long personal-data forms (1.3.5 AA). Low otherwise.

**Related.** WCAG 1.3.5 (AA), 2.2.1 (A), 2.2.5 (AAA), 2.2.6 Timeouts (AAA), 3.3.7 (A). Nielsen H7.

**Not applicable when** the change has no input, time limit or session behaviour.

### L23. Peak-End Rule

**Definition.** "People judge an experience largely based on how they felt at its peak and at its
end, rather than the total sum or average of every moment of the experience."
(https://lawsofux.com/peak-end-rule/). Origin: Kahneman, Fredrickson, Schreiber and Redelmeier
1993, "When More Pain Is Preferred to Less: Adding a Better End".

**Evidence quality: strong for retrospective judgement.** In the 1993 study 22 of 32 subjects
(69%) chose to repeat the longer cold-water trial (81% among those who felt the warmer end)
(https://ius.uzh.ch/dam/jcr:5ae9adc9-61ec-4174-b37c-4b752f36c23b/Kahnemann%20et%20al.%20-%20When%20More%20Pain%20is%20Preferred%20to%20Less%20(1993).pdf).
Alaybek et al. 2022 meta-analysis (Organizational Behavior and Human Decision Processes 170; 174
effect sizes): peak-end effect r = 0.581, robust across boundary conditions; effect of duration
essentially nil (https://ideas.repec.org/a/eee/jobhdp/v170y2022ics0749597822000334.html).
Transfer to software flows is plausible and moderate.

**Auditable checks.**
1. L23.1 Does every flow end in an explicit outcome state that names what happened, to what, and
   what happens next (sent to 120 registrants; charged 300.00 EUR, 1,200.00 EUR left)? [S, I]
2. L23.2 For the likely negative peaks of the change (failed save, refused action, failed sync,
   timeout), does the message follow NN/g's error guidelines: near the source, human language,
   precise, constructive, no blame, input preserved (https://www.nngroup.com/articles/error-message-guidelines/)? [S, I]
3. L23.3 Do long-running jobs end with a visible outcome on the thing (and a notification if
   the user left), including partial failure counts? [I]
4. L23.4 Is there no guilt or "please don't go" step at the end of cancel, unsubscribe or
   withdrawal flows (NN/g peak-end article)? [I]
5. L23.5 For frequent tasks, is the ending quiet (inline confirmation on the item, no blocking
   celebration)? [I, N]

**Thresholds with sources.** None numeric for UI.

**How to test.** Walk each flow to its end, including forced failures (network off, invalid
data) (I); screenshot every end and error state (S).

**Typical violations in B2B data apps.** A bulk action that ends with the dialog closing and no
summary; "Something went wrong" after a failed charge; a CSV import that silently skips rows; a
retention modal on cancel.

**Severity.** Critical when the end state is silent or ambiguous about money, consent or mail
(the user cannot tell whether it happened). High for vague errors on primary tasks. Medium
otherwise.

**Related.** WCAG 3.3.1 Error Identification (A), 3.3.3 Error Suggestion (AA), 4.1.3 (AA).
Nielsen H1, H9.

**Not applicable when** the change has no flow with an end or failure state.

### L24. Postel's Law

**Definition.** "Be liberal in what you accept, and conservative in what you send."
(https://lawsofux.com/postels-law/). Origin: Jon Postel's robustness principle for TCP (RFC 761,
1980).

**Evidence quality: weak and contested.** It is an engineering maxim, not a tested UX effect,
and the IETF itself now argues it can harm ecosystems: RFC 9413 "Maintaining Robust Protocols"
(Thomson, 2023) says that for actively maintained protocols the principle "can, and should, be
avoided" (https://datatracker.ietf.org/doc/rfc9413/). In UI terms: accept harmless variation in
format, never guess at meaning.

**Auditable checks.**
1. L24.1 Do inputs accept harmless format variation: leading and trailing spaces, spaces or
   dashes in IBANs and phone numbers, any letter case in e-mail addresses, the locale's decimal
   and thousands separators in amounts? Test each with at least three variants. [I]
2. L24.2 Is ambiguous input refused with an explanation instead of guessed (03/04/2026 when the
   locale is unclear; "1.000" in an amount field when "." could be a decimal point)? [I]
3. L24.3 Before a money, consent or mail action commits, is the normalised value shown back to
   the user ("1,000.00 EUR", the parsed date in words)? [S, I]
4. L24.4 Does every error say which format is accepted, with an example? (WCAG 3.3.3) [S]
5. L24.5 Is what the system sends strictly consistent: exports with stable headers, encoding and
   number format; mails and API payloads in one format? [C, I]
6. L24.6 Is validation enforced on the server, not only in the browser? [C]
7. L24.7 Does paste work in every field, including codes and passwords? [I]

**Thresholds with sources.** None numeric.

**How to test.** Input fuzzing with format variants (I); export inspection (I); server code
check (C).

**Typical violations in B2B data apps.** An amount field that rejects "1.234,50" in a German
locale; an e-mail field that rejects trailing spaces from a paste; a date field that silently
reads 03/04 as March in a German UI; CSV exports whose decimal separator changes with the
browser locale.

**Severity.** Critical when an amount or date is silently misparsed. High for rejecting common
valid formats on primary inputs. Medium for missing format hints.

**Related.** WCAG 3.3.1 (A), 3.3.3 (AA), 1.3.5 (AA), 3.3.4 (AA). Nielsen H5, H9.

**Not applicable when** the change has no input and no output format.

### L25. Selective Attention

**Definition.** "The process of focusing our attention only to a subset of stimuli in an
environment - usually those related to our goals." (https://lawsofux.com/selective-attention/).
Origins on the page: Cherry 1953, Broadbent 1958, Treisman 1960, Deutsch and Deutsch 1963.
Takeaways name banner blindness and change blindness.

**Evidence quality: strong** for attention limits; banner blindness and change blindness are
documented in eyetracking and lab work (https://www.nngroup.com/videos/banner-blindness/;
https://www.nngroup.com/articles/change-blindness-definition/).

**Auditable checks.**
1. L25.1 After each action, does the feedback appear where the user is looking (on or next to
   the control or item acted on), not only in a distant corner? [I, S]
2. L25.2 After each action, count the screen regions that change. If more than one changes,
   is the most important change marked (highlight, focus, or message near the trigger)? [N, I]
3. L25.3 Is no important information styled like an advertisement (banner shape, right rail,
   animation, promo colours) or placed next to promotional content? [S]
4. L25.4 Does a message that needs action stay until handled (not an auto-dismissing toast)? [I, T]
5. L25.5 Is motion used only to signal a real change, and can motion from interactions be
   turned off (respects `prefers-reduced-motion`)? (WCAG 2.3.3 AAA; 2.2.2 A for anything
   moving more than 5 seconds) [C, I]
6. L25.6 Do content changes that the user did not trigger (live updates, refetch) avoid moving
   content the user is reading or about to click? [I]

**Thresholds with sources.** 5 seconds for auto-moving content needing pause control (WCAG
2.2.2). Others binary.

**How to test.** Act and record which regions change (I, N); screenshot the post-action state
(S); check reduced-motion media query handling (C).

**Typical violations in B2B data apps.** A toast at the bottom left confirming an action taken in
a right-side panel; a failed-sync badge on a list the user is not viewing; an important notice
styled as a coloured banner across the top that users ignore; the selection bar appearing at
the top of a long table while the user selects at the bottom.

**Severity.** High when a failure or required action can go unnoticed (especially money,
consent, mail). Medium for misplaced success feedback. Low for decorative motion.

**Related.** WCAG 4.1.3 (AA), 2.2.2 (A), 2.3.3 (AAA), 2.4.11 Focus Not Obscured (Minimum) (AA).
Nielsen H1.

**Not applicable when** the change has no feedback, message or dynamic content.

### L26. Serial Position Effect

**Definition.** "Users have a propensity to best remember the first and last items in a
series." (https://lawsofux.com/serial-position-effect/). Origin: Ebbinghaus; primacy and recency
effects in list recall (Murdock 1962 is the standard free-recall study).

**Evidence quality: strong for free recall of word lists; weak for interfaces.** Menus, toolbars
and navigation are seen, not recalled (see L18), so primacy and recency of *memory* matter
mainly for content read once (instructions, reviews, mails).

**Auditable checks.**
1. L26.1 In text the user reads once (review steps, confirmation mails, instructions), does the
   key fact (amount, recipients, irreversible effect) come first or last, not in the middle? [S]
2. L26.2 In option lists, is the recommended or most frequent option first? [S]
3. L26.3 In long forms, are the critical fields not buried in the middle of an undifferentiated
   run (they are first in their group or in their own group)? [S]
4. L26.4 Does applying this law never override a convention (L11) or the design system's fixed
   positions (for example, where the account menu or primary action lives)? [S]

**Thresholds with sources.** None numeric for UI.

**How to test.** Read review steps and mails top to bottom and locate the key fact (S).

**Typical violations in B2B data apps.** A review dialog listing ten details with the charge
amount sixth; a confirmation mail with the cancellation deadline in the middle paragraph.

**Severity.** High when a money or consent consequence is buried in a review. Low otherwise.

**Related.** Nielsen H8. No direct WCAG criterion.

**Not applicable when** the change has no list, sequence, review or read-once text.

### L27. Tesler's Law

**Definition.** "Tesler's Law, also known as The Law of Conservation of Complexity, states that
for any system there is a certain amount of complexity which cannot be reduced."
(https://lawsofux.com/teslers-law/). Origin: Larry Tesler, Xerox PARC, mid-1980s; documented in
an interview in Dan Saffer's "Designing for Interaction". Tesler argued an engineer should spend
an extra week rather than make millions of users spend an extra minute.

**Evidence quality: weak.** A practitioner principle with anecdotal support; Tognazzini argues
the opposite dynamic too: simplify a task and people take on more complex ones
(https://asktog.com/columns/011complexity.html).

**Auditable checks.**
1. L27.1 List the inputs the task genuinely needs. For each one the system could derive, look
   up or default, does it? Count user-typed fields vs derivable fields. [N, C]
2. L27.2 Is complexity absorbed rather than hidden: no hidden required setting that makes a
   later step fail? [I]
3. L27.3 Does the system compute and validate cross-field rules (budget limits, date order,
   capacity) and explain them, rather than leaving the user to work them out? [I, C]
4. L27.4 Are advanced options still reachable for the users who need them (not removed to make
   the screen look simple)? [I]
5. L27.5 Do refusals name the rule and the way forward (for example, "Budget left 120.00 EUR;
   this charge is 300.00 EUR")? [S]

**Thresholds with sources.** None numeric.

**How to test.** Field inventory against the data model (N, C); walk with edge-case data (I).

**Typical violations in B2B data apps.** Asking for a company's country when the VAT ID already
gives it; a create dialog that looks simple but fails at publish because a hidden setting is
missing; a budget rule the user discovers only by being refused.

**Severity.** High when hidden complexity causes failure on a money, consent or mail action.
Medium for fields the system could derive. Low otherwise.

**Related.** WCAG 3.3.7 (A), 3.3.3 (AA). Nielsen H5, H7.

**Not applicable when** the change adds no input or rule.

### L28. Von Restorff Effect

**Definition.** "The Von Restorff effect, also known as The Isolation Effect, predicts that when
multiple similar objects are present, the one that differs from the rest is most likely to be
remembered." (https://lawsofux.com/von-restorff-effect/). Origin: Hedwig von Restorff 1933.

**Evidence quality: strong for the memory isolation effect; moderate for its UI use as
salience.** Hunt 1995, "The subtlety of distinctiveness: What von Restorff really did"
(Psychonomic Bulletin and Review 2, 105-112; https://link.springer.com/article/10.3758/BF03211374)
shows distinctiveness is relative to its context: emphasis works only when it is rare.

**Auditable checks.**
1. L28.1 Count the visually dominant controls (solid primary buttons) per view region. Is it at
   most one, as the design system defines? [N]
2. L28.2 Is the most distinctive element in each region the most important one for the task? [S]
3. L28.3 Count emphasised elements per screen (bold, coloured, badged, highlighted). Report the
   count; flag when emphasis is so common that nothing stands out **(heuristic)**. [N]
4. L28.4 Does distinctiveness never rely on colour alone (lawsofux takeaway; WCAG 1.4.1)? [S]
5. L28.5 Is emphasis never styled like an advertisement (L25.3)? [S]
6. L28.6 Is a newly created or just-changed item marked so the user can find it in the list
   (temporary highlight or focus)? [I]
7. L28.7 Does motion-based emphasis respect reduced-motion settings (lawsofux takeaway)? [C]

**Thresholds with sources.** None numeric beyond the design system's own rule.

**How to test.** Count emphasis (N); screenshot review (S); create an item and look for it (I).

**Typical violations in B2B data apps.** Three solid purple buttons in one header; every status
badge in a saturated colour; destructive "Delete" styled as the most prominent action; a new row
inserted silently in the middle of a sorted table.

**Severity.** High when the most prominent action is destructive or commits money. Medium for
competing primaries. Low otherwise.

**Related.** WCAG 1.4.1 (A), 2.3.3 (AAA). Nielsen H8.

**Not applicable when** the change adds no emphasis, primary action or new item.

### L29. Working Memory

**Definition.** "A cognitive system that temporarily holds and manipulates information needed to
complete tasks." (https://lawsofux.com/working-memory/). Takeaways: limited to "4-7 chunks"
fading "after 20-30 seconds"; support recognition over recall; "Place burden of memory on the
system, not the user."

**Evidence quality: strong.** Baddeley and Hitch's model and Cowan 2001's capacity estimate
(about 4 chunks) are central, replicated findings. NN/g puts short-term memory decay at about 20
seconds (https://www.nngroup.com/articles/short-term-memory-and-web-usability/).

**Auditable checks.**
1. L29.1 Does the current location stay visible (page title, breadcrumb or rail state)? [S]
2. L29.2 Are applied filters, sort and search shown on screen (chips, field values), not only
   remembered by the user? [S]
3. L29.3 Is the selection count, and what it covers (this page or all matching), visible while
   the user acts on a selection? [S]
4. L29.4 Does every field keep a visible label while the user types (no placeholder-only
   labels)? (WCAG 3.3.2) [S, I]
5. L29.5 Does a review step show the objects and values being changed, and their before and
   after, without making the user recall the earlier screen? [S]
6. L29.6 Are previously entered values carried forward in multi-step processes? (WCAG 3.3.7) [I]
7. L29.7 Are visited or already-handled items marked (read, done, exported)? [S]
8. L29.8 Can items be compared on one screen rather than by switching between pages? [S, I]

**Thresholds with sources.** About 4 chunks (Cowan 2001); decay about 20 s (NN/g). lawsofux
quotes 4-7 chunks and 20-30 s; use the more conservative figures.

**How to test.** Task walk noting every fact the user must carry between views (I); screenshots
of state indicators (S).

**Typical violations in B2B data apps.** A selection bar that says "3 selected" without saying
whether hidden rows are included; filters that vanish into a closed panel; a bulk review that
shows only "update 40 records"; placeholder labels in a partner form.

**Severity.** High when a remembered value or unseen selection drives a money, consent, access
or mail action. Medium otherwise.

**Related.** WCAG 3.3.2 (A), 3.3.7 (A), 3.3.8 (AA), 2.4.8 Location (AAA). Nielsen H6.

**Not applicable when** the change carries no state across views and adds no input.

### L30. Zeigarnik Effect

**Definition.** "People remember uncompleted or interrupted tasks better than completed tasks."
(https://lawsofux.com/zeigarnik-effect/). Origin: Bluma Zeigarnik, 1920s (published 1927).

**Evidence quality: weak; the memory claim failed meta-analysis.** Ghibellini and Meier 2025,
"Interruption, recall and resumption: a meta-analysis of the Zeigarnik and Ovsiankina effects"
(Humanities and Social Sciences Communications 12): "We found no memory advantage for unfinished
tasks but found a general tendency to resume tasks ... the Ovsiankina effect represents a general
tendency, whereas the Zeigarnik effect lacks universal validity"
(https://ideas.repec.org/a/pal/palcom/v12y2025i1d10.1057_s41599-025-05000-w.html). Secondary
summaries report a weighted recall ratio of about 0.99 across studies excluding Zeigarnik's own,
and resumption of about 67% against a 50% baseline (https://en.wikipedia.org/wiki/Zeigarnik_effect).
Audit the supported half: people tend to resume interrupted tasks, so make resuming easy.
Note: two of the three lawsofux takeaways for this law are copied verbatim from Goal-Gradient.

**Auditable checks.**
1. L30.1 Is unfinished work saved (draft or autosave) when the user leaves mid-task? [I]
2. L30.2 Is unfinished work visible as unfinished where the user will see it again (status
   "draft", "still missing" list, a resume entry on the start page)? [S]
3. L30.3 Does resuming return the user to where they stopped, with their input intact? [I]
4. L30.4 Are there clear signifiers of additional content where content is cut off ("Show
   more", "1-50 of 240", partially visible next row) (lawsofux takeaway)? [S]
5. L30.5 Is incompleteness never manufactured to drive engagement (fake unread counts, fake
   incomplete profiles)? [S, C]

**Thresholds with sources.** None numeric.

**How to test.** Leave a task midway, sign out, return (I); inspect lists for draft states (S).

**Typical violations in B2B data apps.** A long create form that loses everything on navigation;
drafts that exist but are not listed anywhere; a table with more rows than shown and no total.

**Severity.** High when interruption loses input on a long task. Medium when drafts exist but
cannot be found. Low for missing "more" signifiers.

**Related.** WCAG 2.2.5 (AAA), 3.3.7 (A). Nielsen H3, H1.

**Not applicable when** the change has no task that can be interrupted and no truncated content.

## 3. Conflicts between laws and how to resolve them

Conflicts live in `conflicts.md`, next to this file. It holds the precedence ladder that settles
any conflict, listed or not: R1 legal floor, R2 WCAG 2.2 A and AA, R3 safety of money, consent,
access, mail and the user's work, R4 the product's accepted rules, R5 laws with strong evidence,
R6 laws with weaker evidence and AAA not adopted, R7 taste. The highest rung with an opinion
decides; a lower rung decides how a higher one is met, never whether. It also holds the exception
register format (`EX-<n>`) and the full conflict table: C01-C31 law vs law, W01-W16 law vs WCAG,
G01-G10 law vs the legal floor, and P01-P06 worked examples of a product's own rules.

The seventeen conflicts that used to be listed here are C01-C17 there, with the same numbers.
Conflict 14 is now error 18 below; conflict 16 is a ladder rule.

## 4. Errors to watch for in Laws-of-UX write-ups

1. **"WCAG 2.5.8 recommends 44x44 px" - false.** SC 2.5.8 Target Size (Minimum), Level AA,
   requires "at least 24 by 24 CSS pixels", with five exceptions (Spacing, Equivalent, Inline,
   User agent control, Essential); the spacing exception uses a 24 CSS px diameter circle
   (https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html). 44x44 CSS px is SC
   2.5.5 Target Size (Enhanced), Level **AAA**, which already existed in WCAG 2.1
   (https://www.w3.org/WAI/WCAG22/Understanding/target-size-enhanced.html). The only link is an
   informative sentence in the 2.5.8 Understanding text: "For important links/controls, consider
   aiming for the stricter 2.5.5 Target Size (Enhanced)", and technique C42 lists "C44: Using CSS
   to ensure targets are at least 44 by 44 CSS pixels" as related
   (https://www.w3.org/WAI/WCAG22/Techniques/css/C42). Apple's 44x44 pt and Material's 48x48 dp
   are platform guidelines, not WCAG. Correct wording: "WCAG 2.2 AA requires 24x24 CSS px or
   sufficient spacing; 44x44 is AAA and a platform recommendation."
2. **"Keep menus to 7 items (Miller's law)."** Miller's 7 was "a rough estimate and a
   rhetorical device" (Cowan 2001, who puts the limit near 4 chunks); NN/g calls the menu limit
   "a common misconception"; lawsofux.com itself warns against it. Visible menus use
   recognition, not working memory.
3. **"Hick's law says fewer choices is always better."** Liu et al. (CHI 2020) argue Hick's law
   "speaks against, not for" less-is-better, because time grows with the logarithm; it applies
   to choice-reaction with known stimulus-response mappings, not to scanning unfamiliar or
   unordered lists, where time grows linearly.
4. **"Choice overload is proven (the jam study)."** One field study; the 2010 meta-analysis
   found a mean effect near zero; a 2015 meta-analysis found the effect only under specific
   moderators. Cite the moderators, not the jam.
5. **"Unfinished tasks are remembered better (Zeigarnik)."** The 2025 meta-analysis found no
   memory advantage; the resumption tendency (Ovsiankina) holds. Write-ups that cite Zeigarnik
   for progress bars are really describing goal-gradient or resumption. lawsofux.com reuses two
   Goal-Gradient takeaways verbatim on the Zeigarnik page.
6. **"Beautiful designs are more usable."** Kurosu and Kashimura measured *perceived*
   usability; Tuch et al. 2012 found the reverse direction after use (poor usability lowers
   perceived beauty). The claim supported by evidence: attractive design can make users more
   forgiving of minor problems and can mask problems in testing.
7. **Doherty Threshold provenance and meaning.** The 1982 source is an IBM report (form
   GE20-0752-0) by Doherty and Thadhani (lawsofux spells "Thadani" and says it appeared in the
   IBM Systems Journal); its scanned text argues for subsecond response and reports gains at
   0.3 s and 0.25 s, and the explicit "400 ms" number does not appear in the OCR text we could
   read. More importantly, 400 ms is not a pass mark for UI feedback: Nielsen's limit for
   "instantaneous" is 0.1 s, RAIL targets 100 ms, and INP "good" is 200 ms or less.
8. **Peak-end "80% preferred the longer trial."** The 1993 paper reports 22 of 32 (69%) overall;
   81% only among subjects who felt the decrement. NN/g's article cites 80%.
9. **"Gestalt principles = the five on lawsofux."** The site's own origin text lists Proximity,
   Similarity, Continuity, Closure and Connectedness, yet it has pages for Common Region and
   Prägnanz and none for Continuity, Closure, Figure-Ground or Common Fate. Audits that use
   only the five pages miss figure-ground (overlays) and common fate (things that change
   together); see Section 5.
10. **"Fitts's law: make everything bigger" and "screen edges are infinite targets."** The
    relation is logarithmic: gains shrink as size grows. Edge and corner advantages apply to a
    mouse at the physical screen edge, not to targets inside a browser page, and not to touch
    (NN/g: on touchscreens edge placement offers no advantage).
11. **"Postel's law is a UX best practice."** It is a 1980 network robustness maxim; RFC 9413
    (2023) explains how liberal acceptance harms maintained ecosystems. In UI it holds only for
    harmless format variation.
12. **"80/20" as a fact about your product.** Pareto is a heuristic about skewed distributions;
    the ratio must come from the product's own data.
13. **"Serial position: put key navigation at the ends."** The evidence is free recall of word
    lists. Navigation is recognised on screen; do not reorder conventional navigation for it.
14. **"Parkinson's law is research."** The source is a satirical 1955 essay; the empirical
    follow-up (Bryan and Locke 1967) reframes it as goal setting. Its UX takeaways (autofill,
    prefill) stand on other grounds (WCAG 1.3.5, 3.3.7).
15. **"Goal-gradient: give users fake progress."** Kivetz et al.'s bonus stamps were a framing
    of real requirements (12 stamps with 2 given), not a false display. False progress is
    deceptive design.
16. **Out-of-date counts.** "21 laws" was correct until mid-2024; the site lists 30 since 2025.
17. **Response-time misquotes.** "1 second is the limit for instant response" is wrong: 0.1 s is
    instant, 1 s keeps the flow of thought, 10 s keeps attention (NN/g).
18. **"Parkinson's law justifies a time limit."** It does not. lawsofux's Parkinson takeaways
    are autofill and prefill, never "impose a deadline". Never impose a time limit to speed
    users up; any unavoidable limit must be adjustable or extendable, with a warning and at
    least 20 seconds to extend (WCAG 2.2.1 Timing Adjustable, Level A,
    https://www.w3.org/WAI/WCAG22/Understanding/timing-adjustable.html).

## 5. Beyond the 30: other auditable principles a B2B review should check

Each item has an id (B1 to B14) so findings can cite it like a law check. A review marks
each one pass, fail or n/a in the same coverage table as the thirty laws.

**B1. Response-time limits and progress indicators.** Nielsen's 0.1 s / 1 s / 10 s limits and
NN/g's indicator rules (none under 1 s, looped animation for 2-10 s, percent-done for 10 s or
more; https://www.nngroup.com/articles/progress-indicators/), plus INP at most 200 ms at p75
(https://web.dev/articles/optimize-inp). These are better sourced than the Doherty 400 ms and are
already embedded as L6.1-L6.5; when the review does not use L6 they apply on their own.
*Check:* every interaction measured against these bands.

**B2. Recognition rather than recall (Nielsen H6).** "Recall involves fewer cues than
recognition" (https://www.nngroup.com/articles/recognition-and-recall/). *Check:* commands,
recent items, options and previously entered values are shown or suggested (menus, recently
viewed, autocomplete, saved views) rather than typed from memory; icons in early use carry text
labels.

**B3. Progressive disclosure.** "Initially, show users only a few of the most important
options. Offer a larger set of specialized options upon request"; "designs that go beyond 2
disclosure levels typically have low usability"; "It must be obvious how users progress from
the primary to the secondary disclosure levels"
(https://www.nngroup.com/articles/progressive-disclosure/). *Check:* at most 2 disclosure levels;
the control that reveals more is labelled with what it reveals; frequently needed items are never
behind it.

**B4. Error-message guidelines (NN/g, 12 guidelines).** Visibility: near the source;
noticeable, redundant and accessible indicators; designed by impact; not premature.
Communication: human-readable; concise and precise; constructive advice; positive tone, no
blame. Efficiency: safeguard against likely mistakes; preserve input; reduce correction effort;
concisely educate (https://www.nngroup.com/articles/error-message-guidelines/). *Check:* each
error state in the change is scored against the 12; any "Something went wrong" without a cause
and a next step fails. Overlaps WCAG 3.3.1 (A) and 3.3.3 (AA).

**B5. Error prevention, confirmation and undo.** NN/g: confirm only serious consequences,
label buttons with the outcome ("Delete file" / "Keep file", not Yes/No), state what "this" is,
and prefer undo (https://www.nngroup.com/articles/confirmation-dialog/). WCAG 3.3.4 (AA)
requires, for legal commitments, financial transactions and changes to user data, that
submissions are reversible, checked, or confirmed. *Check:* every money, consent, access and
mail action has a review naming the consequence; routine reversible actions act immediately
with undo; no Yes/No buttons.

**B6. Form guidelines (Baymard Institute).** Mark both required and optional fields explicitly
(only 14% of tested e-commerce checkouts do; https://baymard.com/blog/required-optional-form-fields);
do not use placeholder text as the label (https://baymard.com/blog/mobile-forms-avoid-inline-labels);
use inline validation but never prematurely, and remove the error as soon as the field is
corrected (31% of sites have no inline validation; https://baymard.com/blog/inline-form-validation).
*Check:* each form in the change passes these four.

**B7. Shneiderman's Eight Golden Rules** (https://www.cs.umd.edu/users/ben/goldenrules.html):
consistency; universal usability; informative feedback; dialogs that yield closure; prevent
errors; easy reversal of actions; keep users in control; reduce short-term memory load. Most map
onto laws above; the three that add checks are *closure* (every action sequence has a clear end,
L23.1), *easy reversal* (undo or a stated irreversibility, B5) and *keep users in control* (no
surprise automatic actions, L17.6, L8.6).

**B8. Norman: signifiers, mapping, constraints, feedback.** Norman: "Forget affordances: what
people need, and what design must provide, are signifiers" (https://jnd.org/signifiers-not-affordances/).
NN/g measured weak signifiers costing 22% more time and 25% more fixations
(https://www.nngroup.com/articles/flat-ui-less-attention-cause-uncertainty/). *Check:* every
clickable element has a visible signifier at rest (not only on hover); controls map spatially to
what they change (a panel's controls inside that panel); constraints prevent invalid input
(disabled impossible dates, bounded steppers) with the reason stated.

**B9. Gestalt principles missing from lawsofux.com.** *Figure-ground:* overlays (dialogs,
drawers, command menu) separate clearly from the page (scrim or elevation) and only one layer is
active. *Common fate:* things that change together are perceived as a group, so an update that
changes several regions at once must make the intended relationship clear (pairs with L25.2).
*Continuity / alignment:* items on one line or column read as a sequence; misalignment breaks
tables and forms. *Closure:* partial shapes are completed, so a half-visible next row signals
more content (pairs with L30.4). Research base: Wagemans et al. 2012
(https://pubmed.ncbi.nlm.nih.gov/22845751/). *Check:* one active overlay at a time with a
visible scrim or boundary; columns and form fields align on one grid.

**B10. Visibility of system status (Nielsen H1), on the object.** *Check:* every asynchronous
state (saving, syncing to an external system, failed, queued, sent) is shown on the record it
concerns, persists until resolved, and is exposed to assistive technology (WCAG 4.1.3 AA).

**B11. User control and freedom (Nielsen H3).** *Check:* every overlay can be dismissed with
Escape and a visible Close; every multi-step flow can be left without losing input; Back works;
destructive actions have undo or a review.

**B12. Deceptive-design and consent floor (legal on consumer surfaces, the honesty rule
elsewhere).** Pre-ticked consent is invalid (CJEU Planet49, C-673/17); withdrawal must be as easy
as giving consent (GDPR Art. 7(3)). On a consumer-facing surface, steering prominence, repeated
requests and harder termination are unfair commercial practices (UCPD Art. 6-7 and Annex I,
https://eur-lex.europa.eu/eli/dir/2005/29/oj; in Germany the UWG), and consumer subscriptions
need the cancellation button of BGB 312k. On a business-only surface the same patterns fail the
honesty rule (ours, L4). DSA Art. 25 names the same patterns but binds providers of online
platforms only (https://eur-lex.europa.eu/eli/reg/2022/2065/oj). See also EDPB Guidelines
03/2022 on deceptive design patterns
(https://www.edpb.europa.eu/our-work-tools/our-documents/guidelines/guidelines-032022-deceptive-design-patterns-social-media_en).
*Check:* L4.1-L4.4 pass on every consent and subscription surface. Severity of a failure is
Critical.

**B13. Keyboard reachability and visible focus.** Not a "law", but the most common B2B failure
the 30 laws do not cover directly. *Check:* everything operable by keyboard (WCAG 2.1.1 A); focus
order follows meaning (2.4.3 A); focus visible (2.4.7 AA); focused element not entirely hidden
by sticky headers, toolbars or banners (2.4.11 AA); content shown on hover or focus is
dismissible, hoverable and persistent (1.4.13 AA).

**B14. Goal-gradient vs Zeigarnik: which to cite.** Goal-gradient has field evidence in humans
(Kivetz et al. 2006: 20% faster purchase rates near the reward; bonus-stamp cards completed in
12.7 vs 15.6 days) but only in reward programmes; Zeigarnik's memory advantage failed a 2025
meta-analysis, while the tendency to resume interrupted tasks (Ovsiankina) held. *Rule for
reviews:* cite Goal-Gradient for showing progress and remaining steps; cite Ovsiankina
(resumption) for drafts and resume points; do not cite Zeigarnik as evidence for either.

## 6. Summary

Evidence codes: S screenshot, C code, I interaction walk, T timing, N count, M measurement
script. Quality: strong, moderate, weak (or contested).

| # | Law | Checks | Evidence needed | Evidence quality |
|---|---|---|---|---|
| L1 | Aesthetic-Usability Effect | 7 | C, S, M, I | Moderate for perception; contested after use (Tuch 2012) |
| L2 | Choice Overload | 6 | S, I, N | Weak/contested; mean effect near zero, moderators matter |
| L3 | Chunking | 6 | S, I, C, M, N | Strong |
| L4 | Cognitive Bias | 7 | C, S, I, N | Strong for individual biases (defaults); umbrella term |
| L5 | Cognitive Load | 7 | S, N, I, C | Strong as theory; moderate as UI measure |
| L6 | Doherty Threshold | 7 | T, I, S, C | Moderate; 400 ms provenance unclear, Nielsen/RAIL/INP better sourced |
| L7 | Fitts's Law | 8 | M, C, S, I, T | Strong |
| L8 | Flow | 7 | S, I, C, N | Moderate construct; weak as UI law |
| L9 | Goal-Gradient Effect | 6 | S, I, C, N | Moderate, narrow (reward programmes) |
| L10 | Hick's Law | 6 | N, S, I | Strong in lab; weak/contested for UI (Liu 2020) |
| L11 | Jakob's Law | 8 | C, I, S | Moderate (observation, not tested law) |
| L12 | Law of Common Region | 6 | S, M, N, C | Strong (perceptual) |
| L13 | Law of Proximity | 7 | M, S | Strong (perceptual) |
| L14 | Law of Prägnanz | 5 | S, C, N | Moderate; hard to operationalise |
| L15 | Law of Similarity | 6 | S, C, I | Strong (perceptual) |
| L16 | Law of Uniform Connectedness | 5 | S, I | Moderate to strong |
| L17 | Mental Model | 6 | S, I | Moderate (concept, not law) |
| L18 | Miller's Law | 4 | N, I, S | Limit strong (about 4, Cowan); "7" and menu use weak |
| L19 | Occam's Razor | 5 | N, S, C | Weak (philosophical heuristic) |
| L20 | Paradox of the Active User | 7 | I, S | Moderate (observational) |
| L21 | Pareto Principle | 5 | I, N, S, C | Weak (heuristic; needs product data) |
| L22 | Parkinson's Law | 6 | C, I, S | Weak (satirical origin) |
| L23 | Peak-End Rule | 5 | S, I, N | Strong (meta-analysis r = 0.581) |
| L24 | Postel's Law | 7 | I, S, C | Weak/contested (RFC 9413) |
| L25 | Selective Attention | 6 | I, S, N, T, C | Strong |
| L26 | Serial Position Effect | 4 | S | Strong for list recall; weak for UI |
| L27 | Tesler's Law | 5 | N, C, I, S | Weak (practitioner principle) |
| L28 | Von Restorff Effect | 7 | N, S, I, C | Strong for memory; moderate as UI salience |
| L29 | Working Memory | 8 | S, I | Strong |
| L30 | Zeigarnik Effect | 5 | I, S, C | Weak; memory claim failed 2025 meta-analysis |

Total: 184 law checks (L1.1-L30.5) plus 14 supplementary principles (B1-B14).

### Sources consulted (primary list)

- lawsofux.com law pages and `index.md`, `llms.txt`; Wayback Machine snapshots 2022-06 to 2026-06.
- W3C: WCAG 2.2 Recommendation; Understanding 2.5.8 and 2.5.5; Technique C42.
- NN/g: response-time limits; progress indicators; aesthetic-usability effect; short-term
  memory; chunking; minimize cognitive load; error-message guidelines; confirmation dialogs;
  severity ratings; progressive disclosure; recognition and recall; proximity; common region;
  flat UI signifiers; banner blindness; change blindness; peak-end rule; Jakob's law; paradox of
  the active user; Fitts's law.
- Primary and meta-analytic papers: Doherty and Thadhani 1982 (IBM GE20-0752-0, CHM scan);
  MacKenzie 1992; Liu et al. CHI 2020; Cowan 2001; Kahneman et al. 1993; Alaybek et al. 2022;
  Tractinsky et al. 2000; Tuch et al. 2012; Iyengar and Lepper 2000; Scheibehenne et al. 2010;
  Chernev et al. 2015; Kivetz et al. 2006; Ghibellini and Meier 2025; Hunt 1995; Palmer and
  Rock 1994; Wagemans et al. 2012; Johnson and Goldstein 2003; Bryan and Locke 1967.
- Platform guidance: Apple Human Interface Guidelines (Accessibility, Buttons); Google Android
  accessibility help (Material touch targets); web.dev RAIL and INP.
- Law and standards: CJEU C-673/17 Planet49; GDPR Art. 7(3) and 25(2); UCPD (Directive
  2005/29/EC) Art. 6-7 and Annex I; BGB 312k; DSA Art. 25 (online platforms only); EDPB
  Guidelines 03/2022 and 05/2020; EDPB Cookie Banner Taskforce report 2023; IETF RFC 9413.
- Larson and Czerwinski, CHI 1998; Gerhardt-Powals 1996, principle 10.
- Baymard Institute: required and optional fields; inline labels; inline validation.
- Shneiderman, Eight Golden Rules; Norman, "Signifiers, not affordances"; Tognazzini, AskTog on
  complexity.

### Limits of this research

- The Doherty 1982 scan was read through OCR; figures were not inspected, so a 400 ms value
  inside a chart cannot be ruled out.
- The Material Design 3 page itself was not fetched; the 48x48 dp and 8 dp figures come from
  Google's Android accessibility help page that applies Material guidance.
- Zeigarnik meta-analysis figures beyond the abstract (0.99 recall ratio, 67% resumption) come
  from secondary summaries; the full text is paywalled.
- GDPR Art. 7(3) is quoted from the regulation's well-known text, not fetched in this session.
