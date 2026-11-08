---
type: interaction-guidelines
status: proposed
created: 2026-10-29
updated: 2026-10-29
product: HeyDiff, the team service (web app, Chrome extension, landing, operator)
change: 2026-10-27-online-release-1
---

# HeyDiff interaction guidelines: editing, navigation, dialogs, and feedback

This guide says how the HeyDiff team service behaves, in one place: the web app, the Chrome extension, the landing page and the operator area. A builder, human or agent, checks a screen against it. Every rule can be answered yes or no.

The Mac app keeps its own guide in `heydiff-desktop/docs/ux/interaction-guidelines.md`. This file holds the Mac rules that bind on the web, with what changes, and the web rules.

**Status.** The web rules WEB-1 to WEB-36 and the design-system rules were approved with the plan of change 2026-10-27-online-release-1. The owner reads them against the spec at the milestone 1 PR (F14); until then they are `proposed`. The Mac rules are accepted on the Mac (2026-10-26). The section "States and feedback" was asked for by the owner on 2026-10-29 and revised after the owner's review the same day. Each of its rules has one status, `in force` or `proposed`, in its tag, and PRE-1 says which source wins. Acceptance is never inferred.

**How to read a rule.** The first line is the rule. Mac rules show their text and, under it, **On the web** (what binds or changes). Web rules end with their reason in italics. Rule IDs: EDT, NTE, KEY, FBK, WIN, WRD, ACC, EX come from the Mac guide; WEB from the web spec; LOD, TOA, EMP, ERR, STA, PRE and KEF from "States and feedback".

Where to look next: the glossary in [glossary-proposal.md](glossary-proposal.md), the pages in [sitemap.md](sitemap.md), the component contract for states in [states-contract.md](states-contract.md), the setup in [setup.md](setup.md).

## Principles

1. **Point at the thing.** Feedback is about an exact element of running software. Everything else serves that. Example: a comment is a pin on its element, not a ticket in a list.
2. **Quiet and calm.** One Filled button per region, neutral chrome, the page's marks in coral. Example: the consent page has no Filled button because Deny and Allow are equals.
3. **Nothing is lost.** Drafts, text, drawings and choices survive reloads, failures, offline and expired sessions. Example: a failed Send keeps the text and the drawing (WEB-17).
4. **Act first, undo after.** Routine changes happen at once with Undo. Ask first only for what cannot be undone (WEB-5).
5. **Feedback in proportion.** A change shows itself. A toast is for what you cannot see. A wait under 400 ms shows nothing (WEB-4, WEB-13).
6. **The browser is the browser.** Back, links, keys and the address bar keep their meaning. Filters live in the URL (WEB-1, WEB-2, WEB-8).
7. **One word per thing.** The glossary decides the word; the same word means the same everywhere. Example: Agent, never Copilot, on screen (A32).
8. **Every state is designed.** Loading, empty, partial, error, offline, disabled and permission-limited exist for every screen (States and feedback).

## Rules that come from the Mac app

Each line is a rule from the Mac guide that binds here, with the rule's text and what changes on the web and in the extension. Rules that are Mac-only and not bound: CAP-1 to CAP-13, WIN-3, WIN-6, WIN-8, REC-1, REC-2, KEY-1, WRD-8, NTE-1, NTE-8, EX-3, EX-7, EX-8, EX-10 and EX-11. Where a line says "Not bound", the Mac rule is shown for context only.

- **EDT-1.** A box, ellipse or arrow starts where the pointer goes down and grows with the drag.
- **EDT-2.** After a tool key, the next shape shows as a ghost under the pointer before you click.
- **EDT-3.** Drawing tools always draw, even on top of marks. Only Select moves, resizes or deletes.
- **EDT-4.** Select (C) works like Preview. Click selects, drag moves, ⌫ deletes, arrows nudge 1 pt (⇧ 10), ⌘A selects all.
- **EDT-5.** ⌘Z undoes every change to marks and notes, and ⇧⌘Z redoes it. The toolbar has both buttons.
- **EDT-6.** A key with two tools swaps tools when pressed again. Its icon shows the current tool, stacked to show there is another.
- **EDT-7.** Remove marks are always coral red (#e5484d). Highlight marks are always yellow (#facc15), whatever colour is picked.
- **EDT-8.** Buttons and chrome use HeyDiff's own palette. Only marks use the picked colour.
  - **On the web, EDT-1 to EDT-8:** Drawing on the live page and on a reply use the Mac editor's renderer (`heydiff-kit/annotations`) and its behaviour: shapes start at the pointer, a tool key shows a ghost, drawing tools always draw, ⌘Z and ⇧⌘Z, second press swaps the tool, the Remove and Highlight groups and Redact keep their own colour (C8)
- **NTE-2.** Placing a Reference (1) puts the cursor in its note at once.
- **NTE-3.** Each reference note's placeholder asks about its number: "What about 1?".
- **NTE-4.** Reference notes have 12 pt between them. Each starts with its number in a diamond of the mark's colour.
- **NTE-5.** Notes grow to fit their text, the column scrolls, and Discard and Add to session stay in view.
- **NTE-6.** The general comment and reference notes render Markdown as you type. Cards stay plain text.
- **NTE-7.** A card is a yellow speech bubble whose tail and line point at what it is about. You type on the card.
  - **On the web, NTE-2 to NTE-7:** Not bound: Reference diamonds number themselves as on the Mac, but their notes are written in the comment's text, not in a list under the image (C8). The comment's text field grows to fit its text (NTE-5's intent) and renders a Markdown subset as you type (NTE-6)
- **KEY-2.** In every HeyDiff window, Mac keys keep their Mac meaning: ⌘W, ⌘S, ⌘C, ⌘Z, ⌘, for Settings, ⌘/ for Keyboard Shortcuts.
  - **On the web:** Browser keys keep their browser meaning (WEB-8). A list row deletes with ⌫
- **KEY-3.** Single-key tools (C, 1–7) are on by default and can be switched off in Settings. They never fire while typing.
  - **On the web:** Single keys (`C`, J, K, E, Y, R, tool keys) never fire while typing
- **KEY-4.** ⌘1–⌘7 always pick a tool, even while typing a note.
  - **On the web:** **Not bound.** ⌘1 to ⌘9 switch Chrome tabs (owner, 2026-09-28)
- **KEY-5.** Esc steps back one level: out of the text, then the selection, then back to Select, then the editor closes.
- **WIN-4.** Esc closes or steps back in the front HeyDiff window only. One press never closes two things. Only the capture bar and a countdown take Esc from every app (CAP-12, EX-7).
  - **On the web, KEY-5, WIN-4:** Esc steps back one level, top surface first (WEB-3)
- **KEY-6.** Every key is listed in the Keyboard Shortcuts window. The list and the keys come from one source.
  - **On the web:** One source for every key: the `?` list, ⌘K and tooltips read one table
- **KEY-7.** New editor keys use ⌘ chords, never a plain ⌥ letter, which types a character.
  - **On the web:** No plain ⌥-letter shortcuts
- **FBK-1.** A routine success shows itself in the changed thing, with no message. Adding closes the editor and the menu count goes up.
  - **On the web:** A visible change is its own message: a sent comment becomes a pin; a reply appears in the thread
- **FBK-2.** A macOS notification appears only for results you cannot see: copied, exported, a new session, a failure.
- **FBK-7.** A notification is never the only copy of something you need. The file, path or text stays reachable.
  - **On the web, FBK-2, FBK-7:** Toasts only for results off screen or to carry Undo, never the only copy (WEB-4)
- **FBK-3.** An error says what happened, what it means, and what to do next.
  - **On the web:** Errors read event · consequence · action (WEB-14)
- **FBK-4.** Removing acts at once and can be undone or recovered. Use ⌘Z or Discarded, not an "Are you sure?" question.
- **FBK-5.** Ask first only before what cannot be undone. The button names the action; Cancel is the default.
  - **On the web, FBK-4, FBK-5:** Act at once with Undo; ask first only for what cannot be undone (WEB-5). Access and mail rank above FBK-4: Revoke, Remove from Organisation and Send Invitations ask first
- **FBK-6.** Anything over a second shows progress where you look. Anything under 400 ms shows nothing.
  - **On the web:** Nothing under 400 ms; progress from 1 s (WEB-13)
- **WIN-1.** Every icon-only control has a tooltip with its name and key, e.g. "Undo (⌘Z)", "Close (Esc)".
- **WRD-2.** A tooltip is "Name (key)". A short hint may follow after a colon or a "·". A label on the control itself shows the key as a keycap instead, e.g. "Window `2`" (WIN-2).
  - **On the web, WIN-1, WRD-2:** Every icon-only control has a tooltip "Name (key)"
- **WIN-2.** A panel that never shows native tooltips names its controls on the panel itself. The capture bar shows each mode's name and key under its icon, and Capture its ↩ keycap. It draws no hover label.
  - **On the web:** The extension toolbar shows names in tooltips on hover and focus
- **WIN-5.** The editor has tools on top in key order, the image in the middle, notes on the right. Discard and Add to session sit bottom right, Add as the primary button.
  - **On the web:** The composer keeps Send bottom right as the one primary
- **WIN-7.** Settings is one window with General, Capture and Shortcuts tabs. A change applies at once, with no Save button.
  - **On the web:** Settings apply at once (WEB-16). The Mac app's Settings has four tabs (General, Capture, Shortcuts, Online)
- **WIN-9.** The menu bar menu stays short. Current session actions first, then sessions, then Settings… and Quit. Each item names its object.
  - **On the web:** The extension popup stays short: workspace, environment, Show Toolbar, Open Side Panel
- **WRD-1.** Menus, buttons, tabs and window titles use title case, as macOS does. Headings, labels, placeholders and messages use sentence case.
  - **On the web:** Web case rule: Title Case for buttons, menu items, tabs, sidebar items, chips, table headers, titles and headings; sentence case for field labels, switch labels, placeholders, messages and full-sentence headlines. The Mac app keeps sentence case
- **WRD-3.** A placeholder asks or gives an example. It never replaces the label, because it vanishes when you type.
  - **On the web:** Bound unchanged
- **WRD-4.** One word per thing, everywhere: session, screenshot, mark, reference, card, Discarded.
  - **On the web:** Bound unchanged
- **WRD-5.** Use macOS's words: Settings, Trash, Finder, Quit. "…" ends a label only when more input follows.
  - **On the web:** Bound unchanged
- **WRD-6.** Keys use Mac symbols in Mac order: ⌃ ⌥ ⇧ ⌘, then ↩, ⌫, Esc and the arrows.
  - **On the web:** Bound unchanged
- **WRD-7.** Messages have no exclamation marks, no "please", no "oops". Outcomes are past tense and give the number.
  - **On the web:** Bound unchanged
- **EX-1.** Remove and Highlight ignore the picked colour (bends EDT-8). Red and yellow carry a meaning the agent reads (EDT-7).
  - **On the web:** Bound unchanged
- **EX-2.** Single-key tools (bends KEY-2). On Mac, plain letters type. On a canvas they pick tools, as the owner asked. They can be switched off and never fire in text.
  - **On the web:** Bound unchanged
- **EX-4.** Redactions cannot be moved, resized or pasted (bends EDT-4). Moving one would uncover what it hides.
  - **On the web:** Bound unchanged
- **EX-6.** Pen strokes are pointer only (no keyboard route). A freehand path cannot be typed.
  - **On the web:** Bound unchanged
- **EX-5.** References have a fixed size (bends EDT-4). An even size keeps every number readable across a session.
  - **On the web:** Bound for the Reference tool (C8): its notes are lines in the comment's text
- **ACC-1.** Every control has a name a screen reader reads. An icon-only button has an `aria-label`; a control with a key also has `aria-keyshortcuts`.
  - **On the web:** Bound unchanged. ACC-5 (reduced motion) is made exact in `motion.md`
- **ACC-3.** Text reaches 4.5:1 against its background, and controls and focus rings 3:1, in light and dark.
  - **On the web:** Bound unchanged. ACC-5 (reduced motion) is made exact in `motion.md`
- **ACC-4.** Click targets are at least 24 × 24 pt; the capture bar's are 40 × 40 pt.
  - **On the web:** Bound unchanged. ACC-5 (reduced motion) is made exact in `motion.md`
- **ACC-5.** With Reduce Motion on, nothing slides or zooms; changes simply appear.
  - **On the web:** Bound unchanged. ACC-5 (reduced motion) is made exact in `motion.md`
- **ACC-6.** Every status line in a capture panel, and every inline error, is a polite live region.
  - **On the web:** Bound unchanged. ACC-5 (reduced motion) is made exact in `motion.md`
- **ACC-2.** Everything the pointer can do, the keyboard can do, except EX-6. Focus always shows as a 2 pt blue ring.
  - **On the web:** **Departs, a proposed web exception (owner-decisions.md #12).** The ring is 2 px in the neutral `focus` token (slate, never blue) on keyboard focus only (`:focus-visible`), not after a click. WCAG 2.4.7 holds

## Rules for the web, the extension, landing and operator

One rule per line, with its reason. WEB-1 to WEB-30 carry over from the earlier spec; WEB-31 to WEB-36 are new from the journey. Wording is the spec's, unchanged.

- **WEB-1.** Every filter, sort, grouping, revision and compare mode lives in the URL; dialogs, menus and focus do not. _Why:_ Jakob's Law.
- **WEB-2.** Back is the browser's: opening an object pushes, changing a filter replaces, returning restores filters, scroll and the focused row. _Why:_ Mental Model.
- **WEB-3.** Esc steps back one level: menu or popover, then drawing or arranging, then the composer, then pick mode; on a detail page it returns to the list (a history pop). One press never closes two things. _Why:_ Mental Model (KEY-5, WIN-4).
- **WEB-4.** A toast is only for a result off screen or to carry Undo; it is a sentence with a full stop; one at a time; it pauses on hover or focus; a failure stays until closed. _Why:_ Selective Attention.
- **WEB-5.** Removing and closing act at once with an Undo toast (8 s); ask first only for what cannot be undone. Resolve, Decide, Cancel Decision and Change Status carry Undo because they move work for others. _Why:_ Paradox of the Active User.
- **WEB-6.** Your own small writes show at once with a quiet pending mark; a failure keeps the item with Try Again and never loses text. _Why:_ Doherty Threshold.
- **WEB-7.** ⌘K opens one command menu on every app page. _Why:_ Flexibility and efficiency.
- **WEB-8.** Single keys work only outside text fields, are listed in `?` and ⌘K from one source, can be turned off, and never take a key the browser or OS owns. On a customer's page the extension takes keys only while its toolbar shows. _Why:_ Flow without breaking Jakob's Law. (Edited: the page rule.)
- **WEB-9.** Opening a surface moves focus into it; closing returns focus; the ring shows on keyboard focus only, 2 px in the neutral `focus` token. _Why:_ Cognitive Load; the owner's calm rule. (Edited: neutral, never blue.)
- **WEB-10.** On a phone: one column, fixed bottom bar, 44 px targets; commenting on a page, drawing, moving and settings show "works on a larger screen". _Why:_ Fitts's Law; A18.
- **WEB-11.** Other people's changes arrive by themselves and never move what you read; pins appear in place. _Why:_ Selective Attention.
- **WEB-12.** An empty state names the outcome, says what fills it, and offers at most one action; empty by filters offers Clear Filters. _Why:_ Paradox of the Active User.
- **WEB-13.** Nothing for waits under 400 ms; then a skeleton; from 1 s progress where you look. _Why:_ Doherty Threshold.
- **WEB-14.** Errors appear at the thing that failed and read event · consequence · action; not found and no access look the same. _Why:_ Peak-End Rule; safety.
- **WEB-15.** A control that cannot act now stays visible and focusable, `aria-disabled`, with the reason in its tooltip and, on touch, beside it. _Why:_ Mental Model.
- **WEB-16.** Settings apply at once; a text field saves on Enter or blur with "Saved" for 2 s; new objects come through a dialog. _Why:_ Jakob's Law.
- **WEB-17.** Unsent text, drawings, selections and moves are kept per object (web) or per workspace and page address (extension, several per address, never per tab; S120) until sent or discarded; a parked extension draft shows as a draft pin (S121). _Why:_ Ovsiankina effect; "nothing is lost". (Edited: selections and moves.)
- **WEB-18.** Offline shows one banner, keeps what is loaded readable, disables writes with the reason, keeps drafts. In the extension, offline means HeyDiff does not answer, and picking, composing, drawing and arranging still work (S126). _Why:_ never lose work to a state.
- **WEB-19.** Keys show in tooltips, menus, ⌘K and `?`, never as captions on controls, except "Search ⌘K". _Why:_ Aesthetic-Usability Effect.
- **WEB-20.** One Filled button per region, marking the next move (Comment on the toolbar, Send in the composer, Resolve on a comment, Decide on a decision, Start Decision and Share in their dialogs, Open in HeyDiff in the side panel). The consent page has none (an equal pair), nor do the signed-in extension popup (S74) and the Desktop-only message (one Tonal Back): their next move is elsewhere. _Why:_ Von Restorff Effect. (Edited: the journey's primaries.)
- **WEB-21.** An object with a URL gets a page; a short form a dialog; filters and pickers a popover; on the customer's page, popovers and a docked composer. _Why:_ uxpatterns `modal-vs-drawer`. (Edited: the page rule.)
- **WEB-22.** Links inside HeyDiff open in the same tab; links out, and the extension's Open in HeyDiff, open a new tab. _Why:_ you never lose your place.
- **WEB-23.** Copy actions confirm with a toast naming what was copied. _Why:_ EX-9.
- **WEB-24.** Anything an agent did reads "{person} via {client}" with the person's avatar, the agent ring and the Agent chip; no agent entry ever votes, decides or resolves. _Why:_ Mental Model. (Edited: the new verbs.)
- **WEB-25.** People's text renders as a Markdown subset without raw HTML; guest entries carry a Guest chip everywhere. _Why:_ safety (A28).
- **WEB-26.** Times relative under 24 hours, then dates; the full time in a tooltip; a row's age is its latest event (VIS-009). _Why:_ Cognitive Load. (Edited: VIS-009.)
- **WEB-27.** A click on a row opens it; hover actions also show on focus, in More and on touch; a row is a link. _Why:_ Law of Similarity.
- **WEB-28.** Light and dark follow the system setting; dark is the reference design and the fallback (A45, default); no theme switch in release 1. _Why:_ design-system decision (2026-10-26). (Edited: A45.)
- **WEB-29.** Motion follows `motion.md`: tokens only, short, ease-out, and nothing moves under reduced motion. _Why:_ A61; ACC-5. (Edited: points to `motion.md`.)
- **WEB-30.** Overlays on a customer's page live in a shadow root, never change or inherit the page's styles, never reflow the page, take keys only while shown, and never appear in the screenshot except the selection and drawing. _Why:_ the screenshot shows the page as reviewed. (Edited: no reflow; selection and drawing are evidence.)
- **WEB-31 (new).** A pin is a comment bubble filled with the author's avatar colour and initials, pointing at its element's top right; pins sit above outlines, and outlines stop 4 px short of a pin (VIS-027). A pin follows its element through scroll and resize. _Why:_ Law of Common Region; A41.
- **WEB-32 (new).** Selection and suggested changes on the page are annotation coral `#E5484D`, 2 px; HeyDiff's own controls stay neutral. Labels and tags (element tag, "Moved", badges) sit outside the outline, 4 px clear of neighbours, white with a coral border and dark text; never white text on coral (VIS-001, VIS-013, VIS-023). _Why:_ Von Restorff Effect: the page's marks read as evidence, the chrome as tools.
- **WEB-33 (new).** Moving and aligning change only the reviewer's browser, inside the element's own parent; every change is a row with its own Undo; Reset and a reload restore the page. _Why:_ Mental Model: a suggestion, never an edit.
- **WEB-34 (new).** The visibility control is an eye, never a funnel; while anything is hidden by a people or status choice that is not the default, a neutral count dot shows how many (S129). _Why:_ A55; Visibility of system status.
- **WEB-35 (new).** Before and After compare the same captured region at the same scale; Side by Side and Slider are the two modes; the phone shows one at a time. _Why:_ VIS-024; Law of Proximity.
- **WEB-36 (new).** A device size changes the window or emulates a device, labelled with the device and its page area size (never a screen resolution); a phone size states that Chrome shows its debugging bar; a size never comes back by itself on the next visit (S123, S124). _Why:_ honesty about what the browser does.

### Design-system rules

- **Primary last (owner, 2026-10-28, F171).** The primary is the last button in its row; More (…) goes first. The consent page keeps no Filled button.
- **Clear Sky colour (A37).** Every colour comes from `colour.md`, in light and dark.

## States and feedback

The owner asked for this on 2026-10-29: "do we have rulesets on loading e.g. when and what e.g. when using skeleton, progress bar, or spinner? if not we should define this. this is essential for good ux. same for toast messages, different states including empty, as well as error handling. I want this defined and always taken care of."

The owner then reviewed the first draft on 2026-10-29 and settled seven points: recovery that does not hang on a toast, failed submissions as their own items, a loading table with no overlaps, one waiting budget, who owns keys and focus, stronger accessibility checks, and one status per rule. Those rules carry the tag **owner, 2026-10-29**. The review is quoted in `owner-words.md`.

This section says what a screen shows while it waits, when it has nothing, when it fails and when it tells you something. The component contract for the kit builder is in [states-contract.md](states-contract.md).

### Status, precedence and proof

Every rule in this section has one status in its tag. There is no third state.

- **in force: owner, 2026-10-29.** The owner's review settled it. It binds now.
- **in force: spec.** The approved spec of change 2026-10-27-online-release-1 already decided it (FBK, WEB, motion, the state tables, the Errors table). This section only gathers it.
- **proposed.** The spec was silent and the owner has not answered. A builder may follow it, and checks report it as `proposed`. It binds only after the owner confirms it at the milestone 1 PR (F14). A proposed rule never overrides an in force rule.

- **PRE-1 (in force: owner, 2026-10-29). Which source wins.** When two sources disagree, the first in this list wins.
  1. The owner's decisions: `spec/owner-decisions.md` (approved) and the dated quotes in `owner-words.md`.
  2. This ruleset: "States and feedback", with the key and focus rules of section 5.
  3. The older rules: the WEB rules of the spec, the FBK, KEY, EDT and ACC rules of the Mac guide.

  A rule here that bends an older rule names it, and the bend is listed in Exceptions (EX-W9 to EX-W12). The older rule's text is not edited, so the spec stays traceable.

- **PRE-2 (in force: owner, 2026-10-29). Status is not proof.** A rule's tag says whether it binds. It says nothing about whether the build obeys it. Only a passing check proves that, and the enforcement map says which check.
- **PRE-3 (in force: owner, 2026-10-29). A test title only registers a state.** The title `@state:<page id>:<state>` tells the coverage test that the state exists. It proves nothing about behaviour. Each state test must also assert what its kind requires, through the helpers in `e2e/support/states.ts`.
  - **Loading and refresh:** `expectTransition` (nothing before 400 ms, the skeleton or indicator after, then the content) and `expectFocus` (focus did not move).
  - **Failed write or failed load:** `expectKept` (the typed text, drawing, choices and files are still there), `expectRecovered` (Try Again ends in one saved item, never two) and `expectFocus` (where focus is after the error).
  - **Destructive action:** `expectRecovered` after the toast is gone and after a reload, through the lasting handle (TOA-13).
  - **Navigation:** `expectFocus` for Back, Forward, a new page and Esc (KEF-1 to KEF-4).
  - **Every state:** axe is clean, at 100 %, 150 % and 200 % text size, at 320 CSS px and on the phone (STA-8).

  `test/states/coverage.test.ts` fails a state whose test title exists but whose body calls none of the helpers its kind requires.

### Principles

1. **Every state is designed.** Every screen has its loading, empty, partial, error, offline, disabled and permission-limited state in its state table. A screen without them is unfinished.
2. **Show it where the eye already is.** A wait, an error or an empty list appears in its own region, never in a far corner. Example: a failed reply error sits at the reply.
3. **Proportion.** A quick wait shows nothing. A routine success shows itself in the changed thing. Only what the person cannot see gets a toast (FBK-1, FBK-2).
4. **Nothing is lost.** Text, drawings, choices and files survive every failure, offline spell and expired session (WEB-17). A newer draft is never overwritten by an older one.
5. **One component per state.** A spinner, skeleton, toast, empty state or error is the kit's component, never a hand-built one. That is how the timings and the screen-reader behaviour stay the same everywhere.
6. **Never the only copy, never on a timer.** Anything a toast, a colour or a spinner says is also said by text on the screen. Any way back from an action stays available after its toast is gone (TOA-13).
7. **Honest about time and cause.** No fake progress bars. No "Oops". Say what happened, what it means and what to do (FBK-3). When the answer never came, say so: do not claim a failure that may not have happened (ERR-5).

### 1. Loading

#### Operation types

First decide what is happening. The types do not overlap, because each question below is asked in this order and the first yes ends it. Time comes second, in the timeline.

1. **Navigation (N).** The person moves to another route.
2. **Upload or long job (U).** A file or batch is being sent or processed.
3. **Optimistic write (O).** The person's own small write on the LOD-7 list.
4. **Button write (B).** Any other write started from a button: a dialog's create, access and mail, seats, operator writes.
5. **Refresh (R).** A read of content that is already on screen for the same query: a live refetch, a reconnect, a return to a list, Try Again after a failed refresh. A filter or sort change is a new query: it is R while the old rows stay, and the rows are labelled when it fails (LOD-8).
6. **First load, layout known (K).** A read for a region with nothing on screen yet, whose shape we know: Inbox rows, a thread's entries.
7. **First load, layout unknown (X).** A read with no shape to mimic: a single value, a menu's items, a sign-in handover.

#### The timeline

Elapsed time runs from the moment the operation starts. **Exempt from the 400 ms delay:** the pressed state of any control, and the busy state of a pressed Button, including the spinner inside it (LOD-6). They answer the person's own action at once. The delay applies to everything the screen starts by itself.

- **N, navigation.**
  - 0: nothing; the old page stays, the browser shows its own progress.
  - 400 ms: the new route's `loading.tsx` skeleton inside the unchanged shell (`Skeleton`).
  - 10 s: add "Still loading…". Budget end: the page error state (ERR-7).
  - Focus: on arrival, the page heading, unless it is a history pop (KEF-1).
- **U, upload or long job.**
  - 0: the starting button is busy.
  - 1 s: a progress bar with the file name where the file is: determinate when the amount is known (`ProgressBar`), indeterminate when it is not. A Cancel button is always there.
  - The budget is 30 s without progress, not 30 s in total. A moving upload never times out. A stalled one becomes an item error with Try Again (ERR-5).
- **O, optimistic write.**
  - 0: the result shows at once.
  - 400 ms: a quiet pending mark on the item, so a quick success never flashes it.
  - 10 s: the mark reads "Sending…" as text. Budget end: "Not confirmed" (ERR-5).
- **B, button write.**
  - 0: the button is busy; presses are ignored; the busy label is announced once.
  - 10 s: the busy label becomes "Still sending…".
  - Budget end: "Not confirmed" at the button's region (ERR-5).
- **R, refresh.**
  - 0: the region is `aria-busy`. Nothing visible changes.
  - 400 ms: a thin indeterminate bar along the region's top edge (`RefreshIndicator`). The rows keep full colour and full contrast (LOD-8).
  - 1 s: the text "Refreshing…" shows beside the region's heading. It is also the polite status line.
  - 10 s: "Still refreshing…". Budget end: an error beside the kept content (LOD-8, ERR-4).
- **K, first load, layout known.**
  - 0: nothing.
  - 400 ms: a static skeleton of that layout (`Skeleton`), kept at least 300 ms.
  - 10 s: add "Still loading…". Budget end: the section error state with Try Again, replacing the skeleton.
- **X, first load, layout unknown.**
  - 0: nothing.
  - A small control (a field check, a menu's items): at 400 ms a small spinner with a text label (`Spinner`).
  - A region: at 1 s an indeterminate bar with one line of text, in the region (`ProgressBar`).
  - 10 s: add "Still loading…". Budget end: the section error state.

**The waiting budget** is 30 s per operation (LOD-11). It counts from the first request and includes every retry (ERR-4). One "Still…" line at 10 s. One outcome at 30 s at the latest. No other timeout exists in this section.

**Never:** a full-page spinner; a loading bar at the top of the page (conformance D29); shimmer or pulse on skeletons; a progress bar that is not tied to real progress; a skeleton for something that is not coming; dimmed text.

#### Rules

- **LOD-1 (in force: spec; FBK-6, WEB-13).** A wait under 400 ms shows nothing: no spinner flash, no skeleton flash. The 400 ms delay lives inside `Skeleton`, `Spinner`, `ProgressBar` and `RefreshIndicator`, so no screen times it.
  - **Why:** Doherty Threshold. Under 400 ms feels instant.
- **LOD-2 (in force: spec; WEB-13, motion.md).** After 400 ms a region of type K shows a static skeleton of its layout. No shimmer, no pulse.
- **LOD-3 (in force: spec; FBK-6).** Anything over 1 s shows progress where you look, in the region that waits.
- **LOD-4 (proposed).** Once shown, a skeleton, spinner, bar or refresh indicator stays for at least 300 ms. Data that arrives at 450 ms does not make a skeleton flash.
- **LOD-5 (proposed).** Use a determinate bar when the amount is known (bytes, files, steps). Use an indeterminate bar only when the wait is long, the amount is unknown and there is no layout to mimic. It sits in the affected region, never at the top of the page. This follows conformance D29.
- **LOD-6 (in force: owner, 2026-10-29; was spec: motion.md, Composer state table).** A pressed control shows its pressed state at once, and a pressed Button turns busy at once, with no delay. A small spinner replaces its icon, its label and width stay, further presses are ignored, and the wait is announced. The 400 ms delay never applies to the person's own press.
- **LOD-7 (in force: spec; WEB-6. The list is proposed).** Your own small writes (type O) show the result at once with a quiet pending mark. A failure keeps the item and shows its error with Try Again; text is never lost (ERR-13).
  - **Optimistic:** Resolve, Reopen, Change Status, Vote, Dismiss, Reply, Copy.
  - **Not optimistic, busy button instead (type B):** anything that creates an object through a dialog (Start a Decision, Share Session, New Workspace), access and mail (Revoke, Remove from Organisation, Send Invitations), seats, feature flags and every operator write. Uploads are type U.
- **LOD-8 (in force: owner, 2026-10-29; replaces the 60 % dimming).** Content already on screen stays on screen while it refreshes (type R). Its text keeps its colour and its 4.5:1 contrast (ACC-3). It is never dimmed, greyed or covered. The refresh shows separately: the `RefreshIndicator` at 400 ms and "Refreshing…" at 1 s. No skeleton replaces rows the person is reading.
  - **When a refresh fails,** the readable content stays and the error shows beside it, above the rows, with Try Again (ERR-4). After a filter or sort change the error says so: "Couldn’t apply the filter. These are the earlier results."
  - **A refresh that succeeds** removes the indicator and changes only what changed (WEB-11). It announces nothing.
- **LOD-9 (proposed).** Loading shows at the smallest region that waits.
  - **Page:** `loading.tsx` of the route draws the body skeleton inside the shell. The shell, the title and the filter bar never turn into skeletons.
  - **Section:** a `Suspense` boundary around each independently slow region: the thread, the tally, the context panel, a screenshot.
  - **Inline:** a busy button, a field check, an "Uploading {file}…" row.
- **LOD-10 (proposed).** Next.js: every route folder with a `page.tsx` under `src/app/[locale]/(app)`, `(operator)` and `account` has its own `loading.tsx` drawing the kit skeleton of that page, because each page's shape differs. A slow server component inside a page is wrapped in `<Suspense fallback={<…Skeleton />}>`. The shell, heading and toolbar stay outside `Suspense`, so they stream first. Public pages are static and need none. A screenshot is an `<img>` in a box with its final aspect ratio, so nothing jumps.
- **LOD-11 (in force: owner, 2026-10-29; replaces the earlier 10 s and 30 s wording).** One waiting budget of 30 s per operation, counted from the first request, retries included. At 10 s the region adds "Still loading…" (or "Still refreshing…", "Still sending…"). At 30 s the operation ends in its outcome: a read becomes an error (ERR-4), a write becomes "Not confirmed" (ERR-5). Uploads and long jobs count 30 s without progress. New words for `microcopy.md`: `common.loading.slow`.
- **LOD-12 (in force: spec; motion.md, ACC-5).** Skeletons are static anyway. Under reduced motion the busy spinner becomes a static three-dot mark, and a bar fills without easing. The refresh bar becomes a static full-width bar with its text.
- **LOD-13 (in force: owner, 2026-10-29; builds on ACC-6).** What screen readers hear, and where focus goes.
  - A waiting region has `aria-busy="true"`; skeleton blocks are `aria-hidden`.
  - Each region has one polite status line. It says "Loading the {things}…" only when the skeleton appears, so a wait under 400 ms is silent. A refresh says "Refreshing…" only from 1 s.
  - A busy button announces its action: "Sending the comment…".
  - The result is not announced a second time. It is a visible change, an inline error (polite live region, ACC-6) or a toast (TOA-10).
  - A load finishing never moves focus.
  - Focus on a route change follows KEF-1: the page heading on a push, the remembered row on a history pop. LOD-13 and WEB-2 do not compete.
- **LOD-14 (proposed).** Skeletons take the final size: the row height, the avatar, the line count. Loading never shifts the layout.

#### Examples from our screens

- **Inbox, first visit:** nothing for 400 ms, then 8 row skeletons (type K). Error at 30 s: "Couldn’t load your Inbox. HeyDiff had a problem. Try again."
- **Inbox, live refetch:** the 8 rows stay at full contrast. A thin bar runs along the region's top edge from 400 ms; "Refreshing…" shows from 1 s (type R).
- **Pin popover, first open:** three entry skeletons after 400 ms (type K).
- **Composer, Send:** the button is busy at once, the label stays "Send", the status says "Sending the comment…" (type B). The comment's screenshot uploads after the comment is saved, with "Uploading the screenshot…" in the sent message (type U).
- **Resolve:** the chip turns Resolved at once, a quiet mark shows from 400 ms, a toast offers Undo (type O). If the write fails the item says "Couldn’t resolve this. HeyDiff had a problem. It’s still open. Try again."

### 2. Toasts

A toast is the smallest, rarest feedback. Most feedback is the changed thing itself (FBK-1). A toast is never the only way back from an action (TOA-13).

#### When, and when never

| Use a toast when                                                                                               | Never use a toast for                                                        |
| -------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| the result is off screen or invisible: a copy, an export, "Shared {session} with 2 people."                    | a result you can see: a new pin, a sent reply, a vote, a new status chip     |
| a change needs a quick Undo: Resolve, Decide, Cancel Decision, Change Status, Dismiss, Delete Comment, Discard | a failed write on screen: it is inline at the item (FBK-3, FBK-7)            |
| a problem happened to something off screen: "Chrome stopped the {device} view."                                | a field error, an offline state, a permission reason, a load error           |
|                                                                                                                | other people's changes (WEB-11), live updates, "Saved" for settings (WEB-16) |
|                                                                                                                | anything the person must read twice or act on beyond Undo or Try Again       |

#### Kinds

There is no "success" style. A routine success has no toast, so a toast is never decoration. Three kinds exist.

| Kind    | For                                         | Looks                                                       | Stays        |
| ------- | ------------------------------------------- | ----------------------------------------------------------- | ------------ |
| Result  | an off-screen result: "Copied link to #12." | one sentence, no icon                                       | 5 s          |
| Undo    | a change that has a lasting way back        | one sentence and an Undo button, last in the row            | 8 s          |
| Problem | a failure of something off screen           | a danger-text icon, one sentence, Close, optional Try Again | until closed |

#### Where each undo lives after the toast

The toast is a shortcut. The lasting handle is the way back. Both do the same thing, and the handle never expires with the toast.

| Action                                    | Lasting handle                                                                                              |
| ----------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Resolve, Change Status                    | the item's own control (Reopen, Change Status) and an activity line on the thread, with the person and time |
| Decide, Cancel Decision                   | the reverse action on the decision's page, for as long as the decision stands, and its activity line        |
| Dismiss (an Inbox item)                   | Recently removed, with Restore                                                                              |
| Delete Comment                            | Recently removed, with Restore; in the extension also ⌘Z history while its page is open                     |
| Discard (a draft)                         | Recently removed, with Restore, with the text, drawing and choices                                          |
| Moves and drawings on the customer's page | the change list's own Undo per row (WEB-33) and the surface's ⌘Z history (KEF-2)                            |

Recently removed is a view of the list it came from (`?view=removed`, WEB-1), kept 30 days. It holds what a person deleted, discarded or dismissed, newest first, each with Restore. Restore puts the item back where it was and tells the person where it went. The sitemap gets the view when it is built.

#### Rules

- **TOA-1 (in force: spec; WEB-4, FBK-2, FBK-7).** A toast only for a result that is off screen, or to carry a quick Undo. It is never the only copy of something the person needs.
- **TOA-2 (in force: spec; WEB-4, WRD-7).** A toast is one sentence with a full stop, in the past tense, naming the thing: "Copied link to #12." No exclamation mark, no "please".
- **TOA-3 (retired 2026-10-29).** "One toast at a time" is replaced by TOA-7. The id is not reused.
- **TOA-4 (in force: spec; WEB-5, WEB-4).** An Undo toast stays 8 s. A Problem toast stays until closed. The timer pauses while the pointer or focus is inside the toast.
- **TOA-5 (proposed).** A Result toast stays 5 s. After a pause the timer restarts with at least 3 s left.
- **TOA-6 (in force: spec for the extension, S131; proposed for the web).**
  - **Extension:** 12 px above the toolbar, or above the docked composer, inside the shadow root.
  - **Web, desktop:** bottom centre of the main column, 24 px above the window edge. The sidebar never shifts it.
  - **Web, phone:** full width minus the 16 px gutter, 12 px above the fixed bottom bar.
- **TOA-7 (in force: owner, 2026-10-29; replaces the earlier "a new toast replaces the one showing").** Two slots, so a new toast never removes a way back and never hides a problem.
  - **The note slot** holds Result and Undo toasts, one at a time. A newer note replaces the one showing at `--motion-quick`. A replaced Undo toast only leaves the screen. Its action stays available through its lasting handle (TOA-13), so nothing is lost.
  - **The problem slot** holds Problem toasts, one at a time. A Problem is never replaced and never hidden by a Result or Undo toast. It leaves by Close, by Try Again succeeding, or when its cause is gone. A second Problem waits behind the first and shows "1 of 2".
  - **Order:** the problem slot sits nearer the edge, the note slot above it.
  - Identical text raised again within 2 s refreshes the timer and does not stack. A toast raised by a dialog's action shows after the dialog closes.
- **TOA-8 (proposed).** At most one action: Undo on an Undo toast, Try Again on a Problem toast. No links in a toast.
- **TOA-9 (in force: owner, 2026-10-29; replaces the earlier ⌘Z rule).** The toast's ⌘Z (Ctrl+Z elsewhere) is the last owner in the order of KEF-2: it runs only when focus is not in a text field and not on a drawing or arranging surface. Then it undoes the Undo toast in the note slot. A toast never takes focus. Tab reaches its buttons; Esc closes a toast that has focus.
- **TOA-10 (in force: spec for the extension, S131; proposed for the roles on the web).** Screen readers: the toast region is in the page before any toast shows. A Result or Undo toast is `role="status"`, polite. A Problem toast is `role="alert"`. An Undo toast reads "{sentence} Press ⌘Z to undo." Under reduced motion a toast fades in place, with no slide.
- **TOA-11 (in force: spec; FBK-7).** Never the only copy: copied text is on the clipboard, an undone action is visible, and a Problem toast's cause is also visible in the state of the thing it names (the device button reads Responsive again).
- **TOA-12 (proposed).** Words come only from `microcopy.md` keys named `*.toasts.*`. A new toast starts as a new key.
- **TOA-13 (in force: owner, 2026-10-29). Recovery does not depend on a toast.** Every action that offers Undo (Resolve, Decide, Cancel Decision, Change Status, Dismiss, Delete Comment, Discard) has a lasting handle from the table above. `toast.undo` needs the name of that handle and does not compile without it. Copying a link, a second toast or a timeout can never remove a way back.
- **TOA-14 (in force: owner, 2026-10-29). Every timed action has an untimed equivalent** (WCAG 2.2.1, Timing Adjustable). The 5 s and 8 s are a convenience and are never the only chance: the lasting handle has no timer, and a Problem toast has none either. Hover and focus pause the timer.

#### Examples

- "Resolved the comment." with Undo (8 s), above the bar on a phone. The thread's own Reopen is there after the toast is gone.
- "Copied link to #12." (5 s). The link is on the clipboard. An Undo toast that was showing leaves the screen, and its handle stays.
- "Chrome stopped the {device} view." The toolbar already shows Responsive. No other toast hides it.
- Not a toast: "Couldn’t send the comment…" stays at the comment as an item with Try Again.

### 3. Empty states

An empty state says what the outcome is, what will fill the place, and offers at most one next move (WEB-12). It is never used for loading or for a failure.

#### The kinds

| Kind                   | Holds                                               | Example (words from `microcopy.md`)                                                                                        |
| ---------------------- | --------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| First use              | title naming the outcome, one sentence, one primary | "Point at what should change." · "Install the extension, open your product and press C." · Install the Extension           |
| Nothing yet            | one line, no button when nothing can be done here   | "No decisions yet." · "No sessions yet. Start one from the extension’s More menu."                                         |
| No results for filters | one line and Clear Filters; the filter bar stays    | "No comments match these filters." · Clear Filters. Search: "Nothing matches “{q}”. Search comments by number, like #118." |
| All done               | one line, never a button                            | "Nothing waits on you." · "Votes, revisions and replies for you show up here."                                             |
| No access, not found   | the same page for both, one way back                | "This page doesn’t exist, or you don’t have access." · Go to Inbox                                                         |
| Error instead of empty | not an empty state: the error state of section 4    | "Couldn’t load the comments. HeyDiff had a problem. Try again."                                                            |

#### Rules

- **EMP-1 (in force: spec; WEB-12).** Name the outcome, say what fills it, offer at most one action. An empty list produced by filters offers Clear Filters.
- **EMP-2 (proposed).** An empty state is a title (sentence case, one short sentence), one sentence of explanation and at most one Filled button. No illustration in release 1; a neutral 24 px icon is allowed. Words come from `*.empty.heading` and `*.empty.text` keys.
- **EMP-3 (proposed).** The primary shows only if this person can do the thing here and now. A guest or a member without the right sees the sentence only.
- **EMP-4 (proposed).** An empty state fills the list area, not the window. The header, tabs and filter bar stay, so the person can change the filter.
- **EMP-5 (in force: spec; Inbox state table).** An empty Inbox is the goal: no primary. Each Inbox kind has its own line ("No votes for you.").
- **EMP-6 (proposed).** A small section with nothing in it (a thread with no replies, a decision with no comments) is one plain line, with no title and no button.
- **EMP-7 (in force: spec; WEB-14).** No access and not found look the same, and the page never says which. It renders inside the shell the person may see (sitemap F11).
- **EMP-8 (in force: owner, 2026-10-29; replaces the earlier order "loading, error, empty, content").** Check in this order. 1: content already on screen for this query wins, whatever else is true. A refresh over it, or a failed refresh, never hides it (LOD-8). 2: loading with nothing on screen. 3: error with nothing on screen. 4: empty. An empty state is never shown while loading, after a failed load, or over content.
- **EMP-9 (proposed).** Accessibility: the title is a heading at the right level. When a filter change empties a list, the list's polite status line says the empty sentence. A first render announces nothing.
- **EMP-10 (proposed).** Every list has an empty key set: `empty` (or `empty.heading` and `empty.text`), plus `emptyFiltered` when it has filters.

### 4. Error handling

#### The levels

| Level        | Where it shows                                                | Component                       | What is kept                      | Action                                      |
| ------------ | ------------------------------------------------------------- | ------------------------------- | --------------------------------- | ------------------------------------------- |
| Field        | under the field, text plus icon, `aria-invalid`               | `InlineError`                   | the typed value                   | fix it; focus goes to the first bad field   |
| Item         | at the row, card or reply that failed, until resolved         | `FailedSubmission`              | text, drawing, choices, files     | Try Again, Edit, Discard                    |
| Section      | in the region that failed to load; the rest of the page works | `ErrorState`                    | filters, scroll, what else loaded | Try Again                                   |
| Refresh      | beside the content that stayed readable                       | `ErrorState` (placement beside) | the content, scroll, focus        | Try Again                                   |
| Page         | in the shell, from `error.tsx`                                | `ErrorState` (page)             | the URL, the shell, drafts        | Try Again (calls `reset`), then Go to Inbox |
| App: offline | one banner on the main column                                 | `OfflineBanner`                 | what is loaded, every draft       | none; it goes by itself when back           |
| Auth expired | sign-in with `next`                                           | sign-in page                    | every draft                       | Sign In, then return to the same page       |

#### The catalogue

The `## Errors` table of the spec (every event, consequence and action) is the catalogue. A new error is a new row there first, then a `microcopy.md` key, then code. It moves into `microcopy.md` and the state tables of each screen; this file does not repeat it.

#### Rules

- **ERR-1 (in force: spec; FBK-3, WEB-14).** An error appears at the thing that failed and reads event, consequence, action: "Couldn’t send the reply. HeyDiff had a problem. Your text is kept. Try again."
- **ERR-2 (in force: owner, 2026-10-29; builds on spec: WEB-6, WEB-17).** Never lose input, and never overwrite a newer draft with an older one. A failed write keeps the text, drawing, selection, moves, chosen files and people, as its own item (ERR-13). A failing server action returns the input with the error; it never resets the form.
- **ERR-3 (in force: owner, 2026-10-29; was proposed).** Try Again shows only when trying again can help: no answer, a 5xx, a timeout. It repeats the same request with the same idempotency key, unless the payload was edited (ERR-14). The button is busy while it retries. A refusal by a rule (already resolved, no free seat, claim refused) shows the next step instead, with no Try Again.
- **ERR-4 (in force: owner, 2026-10-29; replaces the earlier retry wording).** Retries run inside the 30 s budget of LOD-11.
  - **Reads** (loads, refetches, the live stream) retry silently up to 3 times, after 1 s, 2 s and 4 s with jitter. No retry starts when less than 5 s of the budget is left. The error shows when the retries are used up or the budget ends, whichever is first.
  - **A failed refresh** keeps the content and shows the error beside it (LOD-8). The error says when the content was loaded: "Couldn’t refresh the Inbox. Showing what loaded at 10:42. Try again."
  - **Writes** never retry by themselves, except the kept screenshot upload (Errors table), which retries with backoff while the page is open and again when the connection returns.
  - **Offline:** nothing retries until the browser is online, then one refetch (Live updates).
- **ERR-5 (in force: owner, 2026-10-29; replaces "a request times out at 30 s").** A write has two different bad outcomes. Never mix them up.
  - **Confirmed failure.** The server answered with an error, or the request never left (offline). Nothing was saved. The item reads "Couldn’t send the reply. HeyDiff had a problem. Your text is kept. Try again." Try Again repeats the request.
  - **No confirmation.** The budget ended with no answer, or the connection dropped after the request left. The server may have saved it. The item reads "Not confirmed. HeyDiff didn’t answer, so the reply may have been sent. Check again or try again." The item offers Try Again, and the client also asks the server whether the key was saved.
  - **Late answers are reconciled** (ERR-14). A late success turns the item into the saved item.
  - A load that times out becomes a section error, or a refresh error (ERR-4).
- **ERR-6 (proposed).** Logging. Every error a person sees is also logged with a code, the route, a request id and the level. Never the text people wrote (A28). A page-level error shows a short "Reference: {id}" line. The logger itself is the tech plan's choice.
- **ERR-7 (in force: owner, 2026-10-29; replaces the earlier "error file in every route" and "ancestor boundary" wording).** One rule for error boundaries: **the nearest ancestor boundary counts.**
  - `error.tsx` sits in `(app)`, `(operator)` and `account`, and in any folder whose recovery differs (it must keep a draft or offer another way back). A route inside one of those groups needs no file of its own.
  - **Why an ancestor and not a file per route:** Next.js catches a segment's error at the nearest `error.tsx` above it, the layout and shell stay on screen, and one file means one recovery behaviour to test. A copy per route only drifts. `loading.tsx` stays per route because each page's skeleton has its own shape (LOD-10).
  - Focus goes to the boundary's heading.
  - `not-found.tsx` at the locale root and in each shell group, rendering the 404 of the Errors table.
  - `global-error.tsx` at `src/app` for a failure in the root layout. It brings its own `html` and `body`, uses only static English text and tokens, and says "Something went wrong. Reload the page."
  - The extension's overlay sits in its own boundary. If it crashes it removes itself, leaves the customer's page untouched (WEB-30) and logs.
- **ERR-8 (in force: spec; Errors table).** When someone else changed the thing first ("{name} resolved this {time}."), the item refreshes in place with that line. No Try Again.
- **ERR-9 (proposed).** A field is checked on blur after the first edit and on submit, never while typing the first time. A submit with bad fields moves focus to the first one. Validation never uses a toast or a banner.
- **ERR-10 (in force: spec; ACC-6; offline banner in screens).** Item and field errors are polite live regions. The offline banner and a Problem toast are `role="alert"`, announced once.
- **ERR-11 (in force: spec; WRD-7).** No "Oops", no "please", no exclamation mark, no error codes in the sentence.
- **ERR-12 (in force: spec; WEB-14, WEB-17).** Not found and no access look the same. A signed-out visit to an app route goes to `/sign-in?next=` and brings the person back; drafts are kept.
- **ERR-13 (in force: owner, 2026-10-29). A failed submission is its own item.** It follows WEB-6.
  - It stays in the place where it was sent, marked "Not sent" or "Not confirmed", with its full text, Try Again, Edit and Discard.
  - It never goes back into the composer by itself. The composer keeps whatever the person is writing now.
  - **Edit** opens the item's own text field in place, so it never touches the composer.
  - **Move to the composer** is offered only when the composer is empty. If it has content, the button is disabled with the reason "Finish or send your current reply first." If text arrives in the composer while the move runs, the move stops and both texts are kept.
  - Each failed submission is separate. Two failures are two items.
  - It survives a reload, an offline spell and an expired session (WEB-17) until Try Again succeeds or the person discards it. Discard goes to Recently removed.
  - Focus does not move when it fails. After Try Again succeeds, focus goes to the saved item. After Discard, to the next item, or to the composer when none is left.
- **ERR-14 (in force: owner, 2026-10-29). Keys, late answers and edited retries.** Every write carries an idempotency key made when the person presses Send.
  - **Same payload:** Try Again reuses the key. The server returns the saved item if it exists, so there is never a duplicate.
  - **Late success:** if the answer comes after the item showed a problem, or the live stream shows the item with that key, the item becomes the saved item in place. The error goes. One polite line says "Reply sent." No duplicate, no toast.
  - **Edited payload:** Try Again after an Edit makes a new key and sends `replaces: <old key>`. The old key is abandoned. If the old one was saved, the server updates that item with the new text; if not, it creates one item and refuses the old key afterwards. Either way the thread holds one item.
  - **Late failure after success** never happens: a saved key stays saved.
  - The server side of this is the tech plan's work. The behaviour is not optional.

#### Example flow: reply fails

The long version is example B in section 7. In short:

1. Ben types a reply on a comment and presses ⌘↩. The reply shows at once, with a quiet pending mark (LOD-7).
2. HeyDiff does not answer. At 30 s the item becomes "Not confirmed" at its place in the thread, with his text and Try Again (ERR-5, ERR-13). The composer is untouched.
3. He presses Try Again. The button is busy. The same request runs with the same key.
4. It works. The error goes, the reply stays, once. No toast: the reply is visible (TOA-1).

### 5. Other states, keys and focus

#### Other states

- **STA-1 Partial (proposed; spec: Errors table).** Show what loaded. Mark the part that failed in place with its own Try Again. A thumbnail that fails reads "The screenshot didn’t load. Try again." A batch that half worked says how many: "Shared {session} with 2 of 3 people." and lists who is missing. A kept screenshot upload shows nothing until it fails for good.
- **STA-2 Disabled with a reason (in force: spec; WEB-15).** A control that cannot act now stays visible and focusable, `aria-disabled`, with the reason in its tooltip and, on touch, beside it. Examples: "Only members can resolve." and "Write something, draw or move an element."
  - **Proposed:** when a control can never apply to a role (Settings for a guest), hide it. Disabled-with-reason is for controls that may work later in the same screen. A reason says what to do or who can.
- **STA-3 Stale or outdated (proposed; spec: Live updates, state tables).** Data does not flag itself as old. These are the only marks: the "{n} new" pill for rows that arrived; the Outdated group for comments whose element is gone ("The element is no longer on the page."); the offline banner while the connection is down; the "Showing what loaded at {time}" line of a failed refresh (ERR-4). After a reconnect there is one refetch and nothing shows unless something changed.
- **STA-4 Offline (in force: spec; WEB-18).** One banner on the main column. Reading still works. Writes are `aria-disabled` with the reason ("Offline. Replying is off until you’re back."). Drafts and failed submissions are kept. In the extension, offline means HeyDiff does not answer; picking, composing, drawing and arranging still work (S126).
- **STA-5 Permission-limited, the guest (in force: spec; WEB-14, state tables).** A guest sees only invited workspaces and no Settings. Resolve is disabled with its reason ("Only members can resolve."). A guest chip marks their entries. A page they may not see is the same 404 as a page that does not exist.
- **STA-6 Long content (in force: spec; screens, shared states).** Text wraps and never cuts a heading mid-word. Row text clamps at two lines; the full text is on the page.
- **STA-7 Live update arriving (in force: spec; WEB-11).** Nothing moves under the pointer or the reading position. New rows wait behind "{n} new"; counts and chips change in place; never a toast.
- **STA-8 Size and reflow (in force: owner, 2026-10-29).** Every state is checked at four settings: 100 % and 150 % (the owner's earlier pair), 200 % text size (WCAG 1.4.4), and reflow at 320 CSS px wide with no horizontal scrolling (WCAG 1.4.10). A state at 320 CSS px keeps all content and all actions.
  - **Exceptions, as WCAG allows:** genuinely two-dimensional content may scroll in both directions: the drawing and arranging canvas, the Before and After slider and Side by Side (WEB-35), and the customer's own page. Everything around them, the toolbar, the toasts and every state of this section, must still reflow.
  - A text-size check changes the text size only. The page zoom check at 400 % covers reflow.

#### Keys and focus: who owns what

Three conflicts needed a direct answer. The owner's answers follow. Where a Mac or spec rule is bent, the bend is in Exceptions (EX-W10 to EX-W12).

- **KEF-1 (in force: owner, 2026-10-29). Focus after Back and after a new page.** WEB-2 and LOD-13 each own a case.
  - **History pop** (Back or Forward, the browser's own): focus returns to the row or control that was focused when the person left, if it is on screen when the page is ready. This is WEB-2. If that row is gone or still loading, focus goes to the page heading and does not jump to the row later (LOD-13).
  - **Everything else** (a link, ⌘K, Esc to a list, a redirect, a first visit, a reload): focus goes to the page heading (LOD-13, `motion.md`).
  - A load finishing never moves focus, in either case.
- **KEF-2 (in force: owner, 2026-10-29). Who owns ⌘Z (Ctrl+Z).** The owner is chosen by where focus is, first match wins.
  1. **A text field has focus:** the browser's text undo.
  2. **A drawing, moving or arranging surface has focus or is the active tool** (the canvas, its mark list, the change list): that surface's history (EDT-5). ⇧⌘Z redoes it.
  3. **Anywhere else:** the Undo toast in the note slot, if one shows (TOA-9).
  4. **No toast:** nothing. There is no list history on the web.

  A toast on screen never takes ⌘Z from a canvas or a text field. To reach the toast's ⌘Z, leave the surface first (Esc or Tab), or press the toast's Undo button.

- **KEF-3 (in force: owner, 2026-10-29). Esc on a detail page.** WEB-3's steps (menu or popover, then drawing or arranging, then the composer, then pick mode) come first. One press closes one thing. When nothing is left to close:
  - **A list lies behind** (the person opened this page from its list in this tab): Esc is a history pop, and KEF-1 restores the row.
  - **No list behind** (a mail link, a bookmark, a pasted link, a new tab): Esc goes to the page type's list destination below. It is a normal navigation, so Back returns to the detail page, and focus goes to the page heading (KEF-1).
  - The app marks an object page "opened from its list" in the history entry when it is opened from the list. The tech plan chooses how.
- **KEF-4 (in force: owner, 2026-10-29). The list destination per page type.** Back, the Esc rule and the page's own back link all use this table. It is the one source.

| Page type                              | Esc and Back with no list behind goes to                    |
| -------------------------------------- | ----------------------------------------------------------- |
| a comment `/[org]/[ws]/comments/[n]`   | `/[org]/[ws]/comments`, default filters                     |
| a decision `/[org]/[ws]/decisions/[n]` | `/[org]/[ws]/decisions`                                     |
| a session `/[org]/[ws]/sessions/[id]`  | `/[org]/[ws]/sessions`                                      |
| a list page (Comments, Decisions, …)   | `/[org]/inbox`                                              |
| the Inbox and My Work                  | nowhere: Esc does nothing here                              |
| a settings page                        | the first settings page of its scope (`…/settings/general`) |
| an account page `/account/…`           | `/account/profile`                                          |
| an operator detail page                | its operator list, e.g. `/operator/organisations`           |
| a blog post `/blog/[slug]`             | `/blog`                                                     |

### 6. Enforcement map

Rules that only a person remembers get broken. Each rule below is backed by a component the screen must use or by a check that fails.

#### The components that are the only way

All live in `heydiff-kit/ui/src/<kebab-name>/`. The contract (props, timings, accessibility) is in [states-contract.md](states-contract.md).

| Component          | The only way to show                                                     | Rules                 | Exists today                                                                       |
| ------------------ | ------------------------------------------------------------------------ | --------------------- | ---------------------------------------------------------------------------------- |
| `Skeleton`         | a loading layout, after 400 ms, static                                   | LOD-1 to 4, 9, 12–14  | in the inventory (new variant of HeroUI); the delay and minimum time are not built |
| `Spinner`          | a small wait beside a control, and inside a busy button                  | LOD-1, 6, 12          | no                                                                                 |
| `ProgressBar`      | determinate and indeterminate progress                                   | LOD-3, 5, 11          | no                                                                                 |
| `RefreshIndicator` | a refresh of content already on screen, without dimming it               | LOD-8, 11, 12         | no; new                                                                            |
| `Button` `busy`    | the busy state of a pressed button, and its disabled reason              | LOD-6, STA-2          | Button is in the inventory; `busy` is not built                                    |
| `Toast`            | every toast, with `toast.result()`, `toast.undo()` and `toast.problem()` | TOA-1 to 14           | Toast is in the inventory; the API is not built                                    |
| `RecentlyRemoved`  | the lasting handle for Delete Comment, Discard and Dismiss               | TOA-13                | no; new                                                                            |
| `EmptyState`       | every empty list and the 404                                             | EMP-1 to 10           | missing, planned                                                                   |
| `ErrorState`       | a section, refresh or page load error                                    | ERR-1, 3, 4, 7, LOD-8 | no                                                                                 |
| `InlineError`      | field errors                                                             | ERR-1, 2, 9, 10       | no                                                                                 |
| `FailedSubmission` | a failed or unconfirmed write, as its own item                           | ERR-2, 3, 5, 13, 14   | no; new                                                                            |
| `OfflineBanner`    | the one offline banner (an Alert variant)                                | STA-4, ERR-10         | Alert is in the inventory; the variant is not built                                |

#### The checks

| Check                                                                                                                                                                                                                                                                                                                                                                                                                         | Holds                    | Exists                                        |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------ | --------------------------------------------- |
| A lint rule (a grit rule in `lint/`) and a `dependency-cruiser` rule: no `animate-spin`, no `<progress>`, no `role="alert"` or toast library outside `heydiff-kit/ui`                                                                                                                                                                                                                                                         | LOD-1 to 6, TOA, ERR-10  | no; to build with the kit components          |
| `test/states/segments.test.ts`: every folder with a `page.tsx` under `src/app/[locale]/(app)`, `(operator)` and `account` has its own `loading.tsx`; its nearest `error.tsx` is in it or in an ancestor inside its group (ERR-7); `not-found.tsx` and `global-error.tsx` exist                                                                                                                                                | LOD-10, ERR-7            | no; to build with the first real screen       |
| `test/states/coverage.test.ts`: for every page in `docs/ux/sitemap.json` and each of its `states`, an E2E test title in `e2e/` carries `@state:<page id>:<state>`, unless the page lists the state as not applicable; the test body must call the helpers its state kind requires (PRE-3). The same test requires every page of the app and operator areas to list `loading` and `error`, and every list page to list `empty` | PRE-3, principles 1, all | no; to build with the first real screen       |
| An E2E helper `e2e/support/states.ts`: delay a response (loading), fail it (error), answer it late (late success), drop the answer after the request leaves (no confirmation), go offline, sign in as a guest, empty the data. It also exports `expectTransition`, `expectKept`, `expectRecovered` and `expectFocus` (PRE-3). Every state test runs axe in that state                                                         | LOD, ERR, STA, EMP, KEF  | no                                            |
| Kit component tests, listed in states-contract.md: the 400 ms delay, the 300 ms minimum, no dimming, the two toast slots, recovery after a replaced toast, ⌘Z owner, failed-submission rules, reduced motion                                                                                                                                                                                                                  | LOD, TOA, ERR-13, 14     | no; to build with each component              |
| Microcopy check `test/i18n/microcopy.test.ts`: every key exists; a new check adds: every list has its empty keys and every `*.errors.*` key has the event, consequence, action shape or an exception                                                                                                                                                                                                                          | EMP-10, ERR-1            | the existence check exists; the rest does not |
| `cct:ux-rules-validate` against this section at each milestone, and `cct:ux-assessment-run` on every UI PR                                                                                                                                                                                                                                                                                                                               | everything               | yes (skills)                                  |

#### How a new screen proves it

A screen's feature PR is complete only when all of this is true. `scripts/verify_gate.py` runs the checks above.

1. Its page in `docs/ux/sitemap.json` lists every state it has, and its state table in the spec covers loading, empty, partial, error, offline and disabled-with-reason where they apply.
2. Every string of those states is a `microcopy.md` key, with the empty and error shapes of EMP-10 and ERR-1.
3. The route folder has its own `loading.tsx`, and `error.tsx` sits there or in an ancestor inside its group (LOD-10, ERR-7).
4. It uses only the kit components of the table above. Lint and dependency checks are green.
5. An E2E test per state, titled `@state:<page id>:<state>`, passes with axe clean, at 100 %, 150 % and 200 % text size, at 320 CSS px (STA-8) and on the phone. The title is not the proof: the test also asserts what PRE-3 requires.
6. A failed write on the screen keeps its input as its own item; an E2E test types, fails the request, types something new, retries, and checks nothing was lost or doubled (ERR-2, ERR-13, ERR-14).
7. Every Undo on the screen has its lasting handle, and an E2E test uses the handle after the toast is gone (TOA-13).
8. At the milestone, `cct:ux-rules-validate` reports no departure from this section, or each departure is a recorded exception.

#### Exceptions

- **No top loading bar** (departs from the design system's `loading.md`; conformance D29). The wait shows where you look, at the region.
- **Resolve and Decide show a visible change and also a toast** (departs from "never for something visible"; owner-decisions 6). The toast is a shortcut to the Undo; the item keeps the lasting handle.
- **Copy keeps its toast** (EX-9): the clipboard cannot show it changed.

#### Rules still proposed

These rules wait for the owner's confirmation at F14. Until then they are `proposed` (PRE-2). LOD-4, LOD-5, LOD-9, LOD-10, LOD-14; TOA-5, TOA-8, TOA-12, the web parts of TOA-6 and TOA-10; EMP-2 to EMP-4, EMP-6, EMP-9, EMP-10; ERR-6, ERR-9; STA-1, STA-3, the hide rule of STA-2; the optimistic list of LOD-7. Every other rule in this section is in force.

### 7. Worked examples

Each example says what stays visible, what survives, where focus goes and how recovery works.

#### Example A. Two quick destructive actions

Ana resolves comment #12, then deletes comment #14 four seconds later, then copies a link to #12 two seconds after that.

1. **Resolve #12.** The chip turns Resolved at once. An Undo toast shows in the note slot.
2. **Delete #14.** #14 leaves the list. Its Undo toast replaces the first in the note slot (TOA-7). The first toast only leaves the screen.
3. **Copy link.** "Copied link to #12." replaces the second toast. Both Undo toasts are gone from view.

- **Stays visible:** #12 reads Resolved. #14 is gone from the list. The Result toast shows for 5 s.
- **What survives:** both actions are still reversible. #12 has Reopen on itself and an activity line "Ana resolved this". #14 is in Recently removed with Restore for 30 days. A reload changes nothing (TOA-13).
- **Focus:** it stays on the control Ana used. After Resolve it stays on the same button, now Reopen. After Delete it moves to the next row, or to the list heading when none is left. No toast takes focus.
- **Recovery:** while the Undo toast showed, ⌘Z outside a text field and outside a drawing surface undid its action (KEF-2). After it left, Ana uses Reopen on #12 and Restore in Recently removed for #14. Nothing needed the toast, and copying the link removed no way back.

#### Example B. A reply fails while another reply is being written

Ben sends reply A on a comment. He starts reply B in the same composer. A's request gets no answer.

1. **Send A.** The reply shows in the thread with a quiet pending mark from 400 ms, and at 10 s "Sending…". The composer is empty at once, and Ben types B.
2. **At 30 s** there is no answer. A becomes "Not confirmed. HeyDiff didn’t answer, so the reply may have been sent. Check again or try again." in the thread (ERR-5). The server may have saved it.

- **Stays visible:** the thread with item A at its place, with its full text. The composer with B, and the caret where it was. No toast.
- **What survives:** B is not touched, and A's text is kept in its own item (ERR-13). Both survive a reload.
- **Focus:** it stays in the composer, at the caret. The item's message is a polite live region. Nothing takes focus.
- **Recovery, four ways:**
  - **Late success.** If the answer or the live stream brings A with its key, the item becomes the saved reply, the error goes, and one line says "Reply sent." There is no duplicate (ERR-14).
  - **Try Again** sends the same key. If A was saved, the server returns it. After success, focus goes to the saved item only if it was on the button.
  - **Edit** opens A's own field. Try Again then sends a new key with `replaces`, and the thread holds one reply.
  - **Move to the composer** is disabled with "Finish or send your current reply first." while B has text. When B is sent or empty, it works, and then it keeps anything already there.

#### Example C. A refresh fails with content already visible

Mia has the Inbox open with 8 rows. The browser comes back online and the Inbox refetches. The request never answers.

1. **0 to 400 ms.** Nothing visible. The region is `aria-busy`.
2. **400 ms.** A thin bar runs along the region's top edge. **1 s:** "Refreshing…" shows beside the heading. **10 s:** "Still refreshing…".
3. **At 30 s** (or earlier if the retries run out, ERR-4) the bar goes and the error shows above the rows: "Couldn’t refresh the Inbox. Showing what loaded at 10:42. Try again."

- **Stays visible:** all 8 rows, at full colour and full contrast the whole time (LOD-8). The shell, heading and filter bar. The error beside them.
- **What survives:** the rows, the scroll position, the selected row and any open composer. Nothing is dimmed, replaced or cleared.
- **Focus:** unchanged. If Mia was on row 5, she is still on row 5. The error is a polite status; it does not take focus. Try Again follows the filter bar in Tab order.
- **Recovery:** Try Again is busy while it runs, with a new 30 s budget, and the bar shows again. If the browser goes offline, the offline banner takes over and nothing retries until it is back. When it works, the error goes silently and only changed rows change.

#### Example D. Esc from a directly opened detail page

Kai opens a mail link to `/kestrel/web/comments/118` in a new tab. There is no history behind it and no list.

1. **Esc with nothing else open.** The page has no open menu, no drawing, and no composer text in focus.
2. **Kai presses Esc.** HeyDiff goes to `/kestrel/web/comments`, the list destination of a comment page (KEF-3, KEF-4). It pushes a history entry.

- **Stays visible:** the shell. The list appears with its default filters and its own loading states. The Esc did not close the tab or leave HeyDiff.
- **What survives:** the draft in #118's composer, if any (WEB-17). If the composer was open, the first Esc only closed it and kept the draft. A second Esc then went to the list: one press never closes two things (WEB-3).
- **Focus:** the page heading of the list. This is a new page, not a history pop, so LOD-13 applies and WEB-2 does not (KEF-1).
- **Recovery:** the browser's Back returns to #118, because Esc pushed rather than replaced. Had Kai come from the list in this tab, Esc would have been a history pop and focus would have gone back to row #118 if it was still on screen.

## Flows

The step-by-step wireflows W1 to W12 with their state tables live in the change folder `changes/2026-10-27-online-release-1/spec/interaction.md` until the milestone closes. Each is set in one of the audience's scenes (see [setup.md](setup.md)).

| Flow                                            | What it shows                                                   | Scene            |
| ----------------------------------------------- | --------------------------------------------------------------- | ---------------- |
| W1 Place a comment                              | pick, compose, send; draft kept when parked (WEB-17)            | review a build   |
| W2 Pick several elements                        | Shift-click, one comment on several anchors                     | review a build   |
| W3 Draw, W4 Move and align                      | the Mac editor's tools on the live page; moves as a change list | review a build   |
| W5 Filter what shows on the page                | eye menu, count dot, URL filters (WEB-1, WEB-34)                | review a build   |
| W6 Side panel                                   | list beside the page, Open in HeyDiff                           | review a build   |
| W7 Devices                                      | device size, honest labels (WEB-36)                             | review a build   |
| W8 Sessions                                     | start, end, share                                               | review a build   |
| W9 Decision                                     | start, vote, decide, Undo 8 s (WEB-5)                           | decide together  |
| W10 Agent revision, W11 Reply and resolve       | claim, revision, Before and After, reply reopens                | hand to an agent |
| W12 Reply from the phone                        | one column, 44 px targets (WEB-10)                              | answer on the go |
| Failed reply (examples B and C of States and feedback) | optimistic, fail, keep as its own item, Try Again          | all              |

## Exceptions

Deliberate departures. Each is a decision recorded in the spec's `owner-decisions.md`.

- **EX-W1. The focus ring is neutral, 2 px, on keyboard focus only** (departs from ACC-2's blue ring). WCAG 2.4.7 still holds (owner-decisions 12).
- **EX-W2. ⌘1 to ⌘9 are not bound** (departs from KEY-4). Chrome uses them for tabs.
- **EX-W3. Access and mail ask first** (bends FBK-4). Revoke, Remove from Organisation and Send Invitations cannot be taken back quietly.
- **EX-W4. Resolve, Decide, Cancel Decision and Change Status show a visible change and also an Undo toast** (bends FBK-1, WEB-4). The toast is a shortcut to the Undo; the lasting handle is on the item or in Recently removed (TOA-13; owner-decisions 6).
- **EX-W5. The consent page, the signed-in extension popup and the Desktop-only message have no Filled button** (bends WEB-20). Their next move is elsewhere or the choices are equal.
- **EX-W6. No loading bar at the top of the page** (departs from the design system's `loading.md`; conformance D29). Waits show where you look.
- **EX-W7. Single keys on the customer's page work only while the toolbar shows** (bends WEB-8's key rule). The page's own keys must not be taken.
- **EX-W8. Copy keeps its toast** (EX-9 on the Mac). The clipboard cannot show it changed.
- **EX-W9. Two toast slots, not one** (bends WEB-4's "one at a time"; owner, 2026-10-29). A note slot and a problem slot (TOA-7), so a Result never hides a Problem and a new toast never removes a way back.
- **EX-W10. ⌘Z is owned by focus** (bends EDT-5 and WEB-4's toast Undo; owner, 2026-10-29). Text field, then drawing surface, then toast (KEF-2).
- **EX-W11. Esc on a directly opened detail page goes to its list** (bends WEB-3's "history pop"; owner, 2026-10-29). It pops only when a list lies behind (KEF-3, KEF-4).
- **EX-W12. Focus after Back depends on the kind of move** (bends the single reading of WEB-2 and LOD-13; owner, 2026-10-29). A history pop restores the row; any other move focuses the heading (KEF-1).

## Enforcement map

| Rule                      | Enforced by                                                                                         | Exists?      | To build                                           |
| ------------------------- | --------------------------------------------------------------------------------------------------- | ------------ | -------------------------------------------------- |
| WRD-1, WRD-4, glossary    | `test/docs/glossary.test.ts` (unknown product word fails); `no-literal-jsx-text.grit`               | yes          |                                                    |
| every microcopy string    | `test/i18n/microcopy.test.ts`                                                                       | yes          |                                                    |
| WEB-1, WEB-2              | filters through `nuqs`; an E2E test that Back restores filters, scroll and the focused row          | no           | E2E per list screen                                |
| KEF-1 to 4, PRE-3         | an E2E test per rule: Back after a list, ⌘Z with focus in a field, on the canvas and elsewhere, Esc on a directly opened page; each asserts the focus | no | E2E helpers `expectFocus`, `expectTransition` |
| WEB-4, WEB-5, TOA-1 to 14 | `Toast` and `toast.*` in `heydiff-kit/ui`; lint forbids other toast libraries                       | no           | see States and feedback, section 6                 |
| WEB-8, KEY-6              | one key table feeds `?`, ⌘K and tooltips                                                            | no           | key table module and a test that the three read it |
| WEB-9, ACC-2, EX-W1       | the `focus` token in the kit; an axe pass per screen                                                | no           | kit token, axe step in E2E                         |
| WEB-12, EMP-1 to 10       | `EmptyState` in the kit; state coverage test                                                        | no           | section 6                                          |
| WEB-13, LOD-1 to 14       | `Skeleton`, `Spinner`, `ProgressBar`, `RefreshIndicator`, `Button busy`; segment test                                 | no           | section 6                                          |
| WEB-14, ERR-1 to 14       | `ErrorState`, `InlineError`, `FailedSubmission`; segment test; E2E that keeps input, retries once and finds one item                         | no           | section 6                                          |
| WEB-15, STA-2             | `aria-disabled` plus reason prop on `Button` (the reason is required)                               | no           | kit prop and type                                  |
| WEB-18, STA-4             | `OfflineBanner`; an E2E test with the browser offline                                               | no           | section 6                                          |
| WEB-20                    | `Button` kind prop; a lint or test that a region holds at most one Filled button                    | no           | kit, test                                          |
| WEB-29, ACC-5             | duration tokens only (lint on literal `ms` and `cubic-bezier`); a reduced-motion E2E pass           | no           | lint rule, E2E                                     |
| States on every screen    | `test/states/coverage.test.ts` from `sitemap.json` states                                           | no           | with the first real screen                         |
| Routes match the sitemap  | `test/docs/sitemap.test.ts` (every built page is in `sitemap.json`; the spec routes are all listed) | yes          |                                                    |
| All                       | `cct:ux-rules-validate` at each milestone; `cct:ux-assessment-run` on every UI PR                              | yes (skills) |                                                    |

A rule with nothing behind it is "not enforced", so it stays visible. The conformance pass reads this map.
