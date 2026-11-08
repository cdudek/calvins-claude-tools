---
type: interaction-guidelines
status: accepted
accepted: 2026-10-26 by Calvin Dudek, at the plan gate of change 2026-10-26-interaction-guide-polish
created: 2026-10-26
build: v0.21.1
change: 2026-10-26-interaction-guide-polish
---

# How Snapmark behaves

This guide says how Snapmark should feel and behave, in one place. A builder, human or agent, checks a screen against it. Every rule can be answered yes or no.

The owner accepted every rule and exception on 2026-10-26, and the rules added by change 2026-10-26-picked-designs at its plan gate the same day. A new rule starts as `(proposed)` and is not a promise until the owner accepts it.

How to read a rule: the first line is the rule, what must be true. Under it:

- **Why:** the Law of UX behind it, by name.
- **Today:** where it shows in v0.21.1, or "not yet" and what is missing.

The older, longer proposal for v0.9.0 is kept at `docs/ux/audits/2026-09-28/interaction-guidelines-proposal.md`. Accepted decisions live in `docs/designs/`. Where this guide and an accepted decision disagree, the decision wins.

## 1. How Snapmark should feel

1. **Quiet and fast.** One chord does the common thing, with no question it could answer itself. Example: ⌃⇧4 captures the last area at once, with no picker and no dialog.
2. **Never in the way of the screen.** Snapmark is never in its own capture and never moves you to another Space. Example: the capture bar closes and waits 200 ms before the shot is taken.
3. **A Mac app.** It uses macOS's keys, words and windows, so nothing has to be learned twice. Example: ⌃⇧3, ⌃⇧4 and ⌃⇧5 mirror macOS's ⇧⌘3, ⇧⌘4 and ⇧⌘5.
4. **The agent reads what you mean.** Every mark and note says in words what it means. Example: a Cross reaches the agent as "remove this", not as red pixels to decode.
5. **Nothing is lost.** Every way out can be undone or recovered, so Snapmark rarely asks first. Example: ⌘W discards a screenshot to Discarded, where it stays for 7 days.
6. **It explains itself where you look.** Every icon tells its name and key on hover. Example: hovering the Box tool shows "Box (2 or ⌘2) · press again for Ellipse".

## 2. Rules

### Capture

- **CAP-1 (accepted).** ⌃⇧1 to ⌃⇧5 work from any app, Space or full-screen app, and never switch Spaces.
  - **Why:** Flow. A review keeps its rhythm only if capturing never pulls you out of the app.
  - **Today:** `src/keys.ts:6-13`; bar shown on every Space at `src/main.ts:446`.
- **CAP-2 (accepted).** No Snapmark window, bar, picker or counter ever appears in a capture.
  - **Why:** Mental Model. A screenshot must show the screen as you saw it before you pressed the key.
  - **Today:** the bar closes, then waits 200 ms (capture bar ADR); content protection at `src/main.ts:352`.
- **CAP-3 (accepted).** In the capture bar, keys 1–6 pick a mode in bar order and match the global digits: 1 New Area, 2 Window, 3 Full Screen, 4 Last Area, 5 Scrolling, 6 Record. Each mode shows its name and key under its icon. ↩ or ⌘↩ captures, Esc closes, ← → still move.
  - **Why:** Fitts's Law. A key needs no aiming, so a frequent choice costs no trip to the pointer.
  - **Today:** ← → ↩ Esc at `src/bar.ts:46-54`. Not yet: this order, Full Screen and the labels (2026-10-26-picked-designs, milestone 1); Record joins as 6 in milestone 3.
- **CAP-4 (accepted).** Clicking a mode only chooses it. Only Capture or ↩ takes the shot.
  - **Why:** Jakob's Law. macOS's own ⇧⌘5 bar works this way.
  - **Today:** `src/bar.ts:39`.
- **CAP-5 (accepted).** The Capture button names what it will do: "Capture", or "Capture One-Shot" when One-Shot is chosen.
  - **Why:** Cognitive Load. You read the outcome on the button instead of remembering the Options.
  - **Today:** `src/bar.ts:26`.
- **CAP-6 (accepted).** An option a mode cannot use is greyed, never hidden. Timer and Show Mouse Pointer grey for Window and Scrolling.
  - **Why:** Mental Model. A greyed item says the option exists and why it is off now.
  - **Today:** capture bar ADR, decision 5; `src/main.ts:308`.
- **CAP-7 (accepted).** The bar's Options apply only to captures started from the bar. The global keys never change.
  - **Why:** Mental Model. One key keeps one meaning, so a forgotten One-Shot never steals a capture.
  - **Today:** capture bar ADR, decision 4.
- **CAP-8 (accepted).** The area picker shows a hint and the live size. A click or a sliver starts over. Esc cancels.
  - **Why:** Postel's Law. It accepts a slip and never sends a broken capture on.
  - **Today:** `src/area.html:66-69`.
- **CAP-9 (accepted).** Capture Scrolling scrolls the area by itself and falls back to your own scrolling, with the reason, when it cannot. It says what it does, counts as it grabs, and ends on ↩, ⌃⇧5 or the menu bar icon (Done), or Esc or ⓧ (Cancel).
  - **Why:** Goal-Gradient Effect. A visible count shows how close you are to done.
  - **Today:** `src/scroll.html:61-63`; the height limit notice at `src/main.ts:460`. Not yet: auto-scroll and ⓧ (2026-10-26-picked-designs, milestone 4).
- **CAP-10 (accepted).** A Timer, and the countdown before a recording, shows the seconds left in an overlay on the area and beside the menu bar icon. Esc, ⌃⇧5 or a click on the icon cancels it. While a capture runs, ⌃⇧1–⌃⇧4 and ⌃⇧N do nothing, and ⌃⇧5 means Done or Cancel.
  - **Why:** Doherty Threshold. Each second answers at once, so you never wonder if it is still running.
  - **Today:** the menu bar digits at `src/main.ts:205-236`. Not yet: the overlay (2026-10-26-picked-designs, milestone 1).
- **CAP-12 (accepted).** Esc is taken from every app while the bar or a countdown is open, and only then. A recording takes no plain key.
  - **Why:** Mental Model. Esc closes what you just opened, even after a click took the focus elsewhere.
  - **Today:** not yet: the countdown holds a global Esc (`src/main.ts:205-236`); the bar does not (2026-10-26-picked-designs, milestone 1).
- **CAP-13 (accepted).** The capture bar is a key, non-activating panel: its keys never reach the app behind.
  - **Why:** Flow. The app you review stays in front and never receives a key meant for the bar.
  - **Today:** not yet: the bar is non-activating but not key (`src/main.ts:343`), so Esc reached the app behind (2026-10-26-picked-designs, milestone 1).

### Editing

- **EDT-1 (accepted).** A box, ellipse or arrow starts where the pointer goes down and grows with the drag.
  - **Why:** Jakob's Law. Every drawing app the owner uses works this way.
  - **Today:** the editor canvas, since v0.9.0.
- **EDT-2 (accepted).** After a tool key, the next shape shows as a ghost under the pointer before you click.
  - **Why:** Doherty Threshold. You see the result of the key at once, without drawing first.
  - **Today:** `src/editor.ts:310` (`drawGhost`).
- **EDT-3 (accepted).** Drawing tools always draw, even on top of marks. Only Select moves, resizes or deletes.
  - **Why:** Mental Model. One tool, one job, so a stroke never grabs a mark by surprise.
  - **Today:** `src/editor.ts:295`.
- **EDT-4 (accepted).** Select (C) works like Preview. Click selects, drag moves, ⌫ deletes, arrows nudge 1 pt (⇧ 10), ⌘A selects all.
  - **Why:** Jakob's Law. These are the keys the owner already uses in Preview and Finder.
  - **Today:** `src/keys.ts:45-49`; `src/editor.ts:1143-1163`.
- **EDT-5 (accepted).** ⌘Z undoes every change to marks and notes, and ⇧⌘Z redoes it. The toolbar has both buttons.
  - **Why:** Paradox of the Active User. People learn by trying, so trying must be safe.
  - **Today:** `src/editor.html:676-690`.
- **EDT-6 (accepted).** A key with two tools swaps tools when pressed again. Its icon shows the current tool, stacked to show there is another.
  - **Why:** Hick's Law. Seven keys are faster to choose from than twelve.
  - **Today:** `src/editor.ts:348-372`.
- **EDT-7 (accepted).** Remove marks are always coral red (#e5484d). Highlight marks are always yellow (#facc15), whatever colour is picked.
  - **Why:** Law of Similarity. One colour keeps one meaning across every screenshot and session.
  - **Today:** `src/tools.ts:20-21` and `src/editor.ts:55`.
- **EDT-8 (accepted).** Buttons and chrome use Snapmark's own palette. Only marks use the picked colour.
  - **Why:** Von Restorff Effect. Marks stand out only if the interface does not compete with them.
  - **Today:** colour tokens in `src/editor.html`; owner's words, 2026-10-25.

### Notes

- **NTE-1 (accepted).** The editor's top box is headed "General comment". Its placeholder reads "About the whole screenshot…".
  - **Why:** Cognitive Load. You see at once which box covers the whole screenshot and which covers a mark.
  - **Today:** not yet: no heading; the placeholder "Add a comment…" is its only label (`src/editor.ts:1317`).
- **NTE-2 (accepted).** Placing a Reference (1) puts the cursor in its note at once.
  - **Why:** Flow. Point, then type, with no click in between.
  - **Today:** `src/editor.ts:615`.
- **NTE-3 (accepted).** Each reference note's placeholder asks about its number: "What about 1?".
  - **Why:** Cognitive Load. A question prompts the answer the agent needs, so you never stare at a blank box.
  - **Today:** not yet: "Note for 1" (`src/editor.ts:989`).
- **NTE-4 (accepted).** Reference notes have 12 pt between them. Each starts with its number in a diamond of the mark's colour.
  - **Why:** Law of Proximity. Space between notes shows where one ends and the next begins.
  - **Today:** the diamond at `src/editor.html:592`. Not yet: `#refs` has no gap, so notes touch.
- **NTE-5 (accepted).** Notes grow to fit their text, the column scrolls, and Discard and Add to session stay in view.
  - **Why:** Working Memory. You reread a whole note instead of holding the hidden part in mind.
  - **Today:** `src/editor.html:487-503`.
- **NTE-6 (accepted).** The general comment and reference notes render Markdown as you type. Cards stay plain text.
  - **Why:** Jakob's Law. It writes like Notion, which the owner asked for.
  - **Today:** ADR "Markdown rendered as you type", 2026-09-25.
- **NTE-7 (accepted).** A card is a yellow speech bubble whose tail and line point at what it is about. You type on the card.
  - **Why:** Law of Uniform Connectedness. The line ties the words to their target.
  - **Today:** `src/tools.ts` (Card).
- **NTE-8 (accepted).** The References heading shows only once there is a reference.
  - **Why:** Occam's Razor. An empty heading adds a thing to read and nothing to do.
  - **Today:** `src/editor.html:727` (`hidden`).

### Recording

- **REC-1 (accepted).** A recording keeps the first, every changed and the settled last frame, at most 24, plus marked frames; the GIF keeps real timing.
  - **Why:** Cognitive Load. The agent reads what changed, not dozens of near-identical frames.
  - **Today:** not yet: `src/keyframes.ts` (2026-10-26-picked-designs, milestone 3); ADR "Recording with key frames".
- **REC-2 (accepted).** A mark belongs to the frame where it starts and is clipped to it.
  - **Why:** Law of Common Region. A frame's border holds its marks, so each mark is read with its moment.
  - **Today:** not yet: the recording editor (2026-10-26-picked-designs, milestone 3).

### Keys

- **KEY-1 (accepted).** Global keys are ⌃⇧ plus macOS's screenshot digits: ⌃⇧1 Capture New Area…, ⌃⇧2 Capture One-Shot…, ⌃⇧3 Capture Full Screen (every display, at once), ⌃⇧4 Capture Last Area, ⌃⇧5 capture bar. ⌃⇧N starts a new session and forgets the area.
  - **Why:** Jakob's Law. The digits are the ones the owner's fingers already know.
  - **Today:** `src/keys.ts:6-13`; ADR "Keys follow macOS".
- **KEY-2 (accepted).** In every Snapmark window, Mac keys keep their Mac meaning: ⌘W, ⌘S, ⌘C, ⌘Z, ⌘, for Settings, ⌘/ for Keyboard Shortcuts.
  - **Why:** Jakob's Law. A key that means the same everywhere is never learned twice.
  - **Today:** `src/keys.ts:35-68`; app menu at `src/menu.ts:166-179`.
- **KEY-3 (accepted).** Single-key tools (C, 1–7) are on by default and can be switched off in Settings. They never fire while typing.
  - **Why:** Flow. One finger picks a tool mid-review, without a chord.
  - **Today:** `src/editor.ts:52` and `:1166`; `src/settings.html:205`.
- **KEY-4 (accepted).** ⌘1–⌘7 always pick a tool, even while typing a note.
  - **Why:** Mental Model. One route that works everywhere is the one people trust.
  - **Today:** `src/editor.ts:1130`.
- **KEY-5 (accepted).** Esc steps back one level: out of the text, then the selection, then back to Select, then the editor closes.
  - **Why:** Mental Model. Esc always means "one step back", never "lose everything".
  - **Today:** `src/editor.ts:1153-1162`; ADR "Esc on Select closes the editor".
- **KEY-6 (accepted).** Every key is listed in the Keyboard Shortcuts window. The list and the keys come from one source.
  - **Why:** Paradox of the Active User. People look keys up only when stuck, so the list must be right.
  - **Today:** `src/keys.ts:13`; `src/shortcuts.html`.
- **KEY-7 (accepted).** New editor keys use ⌘ chords, never a plain ⌥ letter, which types a character.
  - **Why:** Jakob's Law. On a Mac, ⌥ plus a letter types a character, so ⌥A is "å", not a command.
  - **Today:** ⇧⌘O, ⇧⌘P and ⇧⌘F (2026-10-26-picked-designs, milestones 2 and 3).

### Feedback

- **FBK-1 (accepted).** A routine success shows itself in the changed thing, with no message. Adding closes the editor and the menu count goes up.
  - **Why:** Selective Attention. A message for every success trains people to ignore messages.
  - **Today:** the editor closes on Add to session; the menu shows the count.
- **FBK-2 (accepted).** A macOS notification appears only for results you cannot see: copied, exported, a new session, a failure.
  - **Why:** Selective Attention. A notice is worth reading only when nothing else shows the result.
  - **Today:** `src/main.ts:172` and `:721`.
- **FBK-3 (accepted).** An error says what happened, what it means, and what to do next.
  - **Why:** Peak-End Rule. A failure is the moment people remember, so it must leave a way forward.
  - **Today:** partly: "Couldn't save x.png: <reason>." names the event, not the next step (`src/main.ts:738`).
- **FBK-4 (accepted).** Removing acts at once and can be undone or recovered. Use ⌘Z or Discarded, not an "Are you sure?" question.
  - **Why:** Paradox of the Active User. People act first, so the fix must come after, not before.
  - **Today:** ⌘⌫ then ⌘Z in the session window (`src/keys.ts:66-68`); ⌘W to Discarded.
- **FBK-5 (accepted).** Ask first only before what cannot be undone. The button names the action; Cancel is the default.
  - **Why:** Cognitive Bias. People press the default without reading, so the default must be safe.
  - **Today:** "Move to Trash" / "Cancel" with Cancel as default (`src/main.ts:153-160`).
- **FBK-6 (accepted).** Anything over a second shows progress where you look. Anything under 400 ms shows nothing.
  - **Why:** Doherty Threshold. Under 400 ms feels instant; longer needs a sign that work is happening.
  - **Today:** the scrolling count; "Downloading Snapmark …" (`src/main.ts:945`).
- **FBK-7 (accepted).** A notification is never the only copy of something you need. The file, path or text stays reachable.
  - **Why:** Working Memory. A message that disappears cannot be read twice.
  - **Today:** copied paths are on the clipboard; exports open in Finder.

### Windows

- **WIN-1 (accepted).** Every icon-only control has a tooltip with its name and key, e.g. "Undo (⌘Z)", "Close (Esc)".
  - **Why:** Paradox of the Active User. People hover to find out; they do not read a manual.
  - **Today:** editor tools (`src/tools.ts:148`), Undo and Redo (`src/editor.html:676-690`), session window (`src/viewer.html:518-524`). Not yet: the capture bar's titles have no keys (`src/bar.html:105-139`).
- **WIN-2 (accepted).** A panel that never shows native tooltips names its controls on the panel itself. The capture bar shows each mode's name and key under its icon, and Capture its ↩ keycap. It draws no hover label.
  - **Why:** Selective Attention. The name and key show right where the eye already is, on the control.
  - **Today:** the drawn hover label `src/tip.html`, retired by 2026-10-26-picked-designs (milestone 1, Q3).
- **WIN-3 (accepted).** The capture bar opens at the bottom centre of the display with the pointer, over full-screen apps. Focus is on the chosen mode.
  - **Why:** Jakob's Law. macOS's own bar opens in the same place.
  - **Today:** `src/main.ts:336-358`; `src/bar.ts:18`.
- **WIN-4 (accepted).** Esc closes or steps back in the front Snapmark window only. One press never closes two things. Only the capture bar and a countdown take Esc from every app (CAP-12, EX-7).
  - **Why:** Mental Model. One press, one step, so Esc is always safe to press.
  - **Today:** bar at `src/bar.ts:49`; session window "All Screenshots (Esc)" at `src/viewer.html:518`; editor per KEY-5.
- **WIN-5 (accepted).** The editor has tools on top in key order, the image in the middle, notes on the right. Discard and Add to session sit bottom right, Add as the primary button.
  - **Why:** Serial Position Effect. The last thing you see is the thing you do last.
  - **Today:** `src/editor.html:661-745`.
- **WIN-6 (accepted).** The session window has Document and Screenshots tabs. ← → flip screenshots, ↩ renames, ⌘O opens Edit Again.
  - **Why:** Jakob's Law. It uses Finder's keys for the same jobs.
  - **Today:** `src/viewer.html:493-524`; `src/keys.ts:62-69`.
- **WIN-7 (accepted).** Settings is one window with General, Capture and Shortcuts tabs. A change applies at once, with no Save button.
  - **Why:** Jakob's Law. macOS's own settings work this way.
  - **Today:** `src/settings.html:133-211`.
- **WIN-8 (accepted).** Keyboard Shortcuts is its own window, opened by ⌘/ from any Snapmark window. It can stay open beside the editor.
  - **Why:** Working Memory. A list kept in view beats a list kept in your head.
  - **Today:** `src/shortcuts.html`; capture bar ADR, decision 8.
- **WIN-9 (accepted).** The menu bar menu stays short. Current session actions first, then sessions, then Settings… and Quit. Each item names its object.
  - **Why:** Hick's Law. Fewer, clearer items are quicker to choose from.
  - **Today:** `src/menu.ts:107-157`.

### Words

- **WRD-1 (accepted).** Menus, buttons, tabs and window titles use title case, as macOS does. Headings, labels, placeholders and messages use sentence case.
  - **Why:** Jakob's Law. The capitals match every other Mac app.
  - **Today:** `src/menu.ts` and Settings follow it. Not yet: the editor's "Add to session" button (`src/editor.html:743`).
- **WRD-2 (accepted).** A tooltip is "Name (key)". A short hint may follow after a colon or a "·". A label on the control itself shows the key as a keycap instead, e.g. "Window `2`" (WIN-2).
  - **Why:** Cognitive Load. The same shape everywhere is read at a glance.
  - **Today:** `src/tools.ts:148`; "Previous (←)" at `src/viewer.html:519`.
- **WRD-3 (accepted).** A placeholder asks or gives an example. It never replaces the label, because it vanishes when you type.
  - **Why:** Working Memory. The heading stays when the placeholder is gone.
  - **Today:** not yet: the general comment's placeholder is its only label (NTE-1).
- **WRD-4 (accepted).** One word per thing, everywhere: session, screenshot, mark, reference, card, Discarded.
  - **Why:** Law of Similarity. The same word signals the same thing on every screen.
  - **Today:** mostly; see `docs/ux/glossary-proposal.md`.
- **WRD-5 (accepted).** Use macOS's words: Settings, Trash, Finder, Quit. "…" ends a label only when more input follows.
  - **Why:** Jakob's Law. The owner already knows what these words do.
  - **Today:** "Settings…" and "Quit Snapmark" at `src/menu.ts:156-157`.
- **WRD-6 (accepted).** Keys use Mac symbols in Mac order: ⌃ ⌥ ⇧ ⌘, then ↩, ⌫, Esc and the arrows.
  - **Why:** Jakob's Law. These are the symbols macOS menus show.
  - **Today:** `src/keys.ts`.
- **WRD-7 (accepted).** Messages have no exclamation marks, no "please", no "oops". Outcomes are past tense and give the number.
  - **Why:** Cognitive Load. Plain words say the result with nothing extra to read.
  - **Today:** "Moved 3 old sessions to the Trash." (`src/main.ts:167`).
- **WRD-8 (accepted).** Screens show a session's readable name, e.g. "2026-10-24 · Ledgerly Q4 review". The folder keeps its date stamp.
  - **Why:** Mental Model. You know a session by its name, the Finder by its date.
  - **Today:** ADR "Session folders keep their date stamp".

### Accessibility

- **ACC-1 (accepted).** Every control has a name a screen reader reads. An icon-only button has an `aria-label`; a control with a key also has `aria-keyshortcuts`.
  - **Why:** Postel's Law. Snapmark accepts every way of working: pointer, keyboard and VoiceOver.
  - **Today:** bar and editor buttons are named (`src/bar.html:105-139`, `src/editor.html`). Not yet: `aria-keyshortcuts` anywhere.
- **ACC-2 (accepted).** Everything the pointer can do, the keyboard can do, except EX-6. Focus always shows as a 2 pt blue ring.
  - **Why:** Postel's Law. A keyboard user meets no dead end.
  - **Today:** `:focus-visible` rings in every window (`src/bar.html:50-53`).
- **ACC-3 (accepted).** Text reaches 4.5:1 against its background, and controls and focus rings 3:1, in light and dark.
  - **Why:** Selective Attention. What cannot be seen cannot be attended to.
  - **Today:** the bar's chosen mode, 3.5:1 or more (`src/bar.html:65-70`).
- **ACC-4 (accepted).** Click targets are at least 24 × 24 pt; the capture bar's are 40 × 40 pt.
  - **Why:** Fitts's Law. Small, far targets are slow and easy to miss.
  - **Today:** `src/bar.html:63`; editor tools 36 pt.
- **ACC-5 (accepted).** With Reduce Motion on, nothing slides or zooms; changes simply appear.
  - **Why:** Cognitive Load. Motion that cannot be turned off costs attention.
  - **Today:** not yet: no window reads `prefers-reduced-motion`.
- **ACC-6 (accepted).** Every status line in a capture panel, and every inline error, is a polite live region.
  - **Why:** Selective Attention. A screen reader hears the change without the focus moving to it.
  - **Today:** not yet: the scrolling count and the hex error are not announced (2026-10-26-picked-designs, milestones 1 to 4).

## 3. Exceptions

Deliberate departures from the rules above. Each one is accepted, like the rules.

- **EX-1 (accepted). Remove and Highlight ignore the picked colour** (bends EDT-8). Red and yellow carry a meaning the agent reads (EDT-7).
- **EX-2 (accepted). Single-key tools** (bends KEY-2). On Mac, plain letters type. On a canvas they pick tools, as the owner asked. They can be switched off and never fire in text.
- **EX-3 (accepted). Esc on Select closes the editor** (bends WIN-4's "always safe"). The screenshot goes to Discarded, so the close can be undone.
- **EX-4 (accepted). Redactions cannot be moved, resized or pasted** (bends EDT-4). Moving one would uncover what it hides.
- **EX-5 (accepted). References have a fixed size** (bends EDT-4). An even size keeps every number readable across a session.
- **EX-6 (accepted). Pen strokes are pointer only** (no keyboard route). A freehand path cannot be typed.
- **EX-7 (accepted). The capture bar and a countdown take Esc from every app** (bends WIN-4). Esc must close the bar even after a click on another app (A1). Only Esc is taken; digits, Tab and arrows stay with the app in front (CAP-12, CAP-13).
- **EX-8 (accepted). Quit with unsaved marks, and Move to Trash, ask first** (bends FBK-4). After them, there is nothing left to undo.
- **EX-9 (accepted). Copy keeps its notification** (bends FBK-1). The clipboard cannot show that it changed.
- **EX-10 (accepted). ⌃⇧2 uses macOS's own capture overlay, not the area picker** (CAP-8 does not apply). It is the system's own, and accessible as it is. Space in it still picks a window.
- **EX-11 (accepted). Global keys use ⌃⇧, not ⇧⌘** (bends principle 3, "A Mac app"). macOS keeps ⇧⌘3, ⇧⌘4 and ⇧⌘5 for itself.

## Enforcement

| Rule         | Enforced by                                                   | Exists? |
| ------------ | ------------------------------------------------------------- | ------- |
| KEY-6, KEY-1 | `src/keys.ts` feeds the shortcuts window; `test/keys.test.ts` | yes     |
| WIN-1, WRD-2 | `tipFor` in `src/tools.ts` builds every tool tooltip          | yes     |
| EDT-7, EX-1  | `color` on a group in `src/tools.ts`                          | yes     |
| WIN-2, CAP-3 | a test that every bar control shows a label and a key         | no      |
| NTE-1, NTE-3 | a test on the editor's heading and placeholders               | no      |
| All          | `cct:ux-rules-validate` against this file, on every UI PR        | yes     |
