---
type: sitemap
status: "As built" checked against the audit; "Proposed" is a proposal, nothing accepted
created: 2026-09-28
build: main at v0.9.0
source: UX audit 2026-09-28, evaluators e1–e8 (finding IDs are the evaluators' own, renumbered at the merge)
---

# Snapmark sitemap

Snapmark has no pages or routes. It has surfaces, reached from the menu bar icon, three global keys and
each other. This file shows how they are reached today (v0.9.0) and how the proposed interaction
guidelines would arrange them.

## As built (v0.9.0)

Sources: the menu data rendered for four states (agent 1), agent 2's every-way-in-and-out and
where-things-open tables, agent 4's key × screen map, and the other evaluators' findings. Items marked
_(native)_ are macOS's own; _(silent)_ gives the reviewer no sign.

```
ENTRY POINTS
├── Menu bar icon (corner and dot; tooltip "Snapmark"; click or right-click opens the same menu;
│   keyboard: only macOS's ⌃F8, mentioned nowhere)
├── ⌃⇧4  Capture Screenshot     (works in every app; "(shortcut unavailable)" if another app owns it)
├── ⌃⇧5  Capture Options        ──► CAPTURE BAR (brought forward if open; nothing while a capture runs)
├── ⌃⇧3  Capture Last Area
├── ⌃⇧N  New Session
└── Relaunching Snapmark from Applications or Spotlight: nothing happens (F217)

MENU (rebuilt on every open; rows appear and disappear with state: 12 to 17 top-level rows)
├── [Restart to Update to <v>]              only when an update waits ──► all windows close, no question (F212)
├── Capture Screenshot  ⌃⇧4
│     └──► macOS capture overlay (native): drag a region, or Space + click a window ──► Editor
│                                          Esc or a failed capture ──► nothing (silent; the two look alike, F028)
├── Capture Last Area   ⌃⇧3   sub-line "1280 × 720" or "First time: drag the area"
│     ├── no area yet, or its display is gone ──► Area picker (display under the pointer, over full-screen apps)
│     │        drag ≥ 8 × 8, release ──► captured at once ──► Editor · click or sliver ──► starts over · Esc ──► nothing
│     └── area set ──► captured at once (with any Snapmark window that is over it, F033/F066) ──► Editor
├── Capture Options…  ⌃⇧5      ──► CAPTURE BAR (was: Capture Options ▸ four items)
├── [Reopen Last Discarded]                  only when Discarded holds something
│     ├── a closed capture ──► Editor with its marks ("Add to session"); its old session becomes current (F010)
│     └── a removed screenshot ──► back at the end of its session + notification ──► Session window
├── [Reopen Discarded…]                      ──► folder panel on the hidden .discarded folder (native) ──► as above
├── ──
├── "Current Session: 28 Sep 09.14 · 7 screenshots" | "No Session Yet"      (grey header, not clickable)
├── Open Session              ──► Session window (current session only); missing: notification that opens the menu
├── Copy Prompt for AI        ──► clipboard (path + key to the marks) + notification
├── Copy session.md Path      ──► clipboard (bare path) + notification "Path to 28 Sep 09.14 copied."
├── Rename Session…           ──► AppleScript dialog "Rename session" (native); errors only after it closes
├── Show Session in Finder    ──► Finder, the folder opened (not revealed)
├── [Export Session ▸ PDF · ZIP]   hidden while empty ──► Finder with the file selected (replaces the last one)
│                                                       failure: notification with the raw error (silent otherwise)
├── ──
├── Switch Session ▸  up to 10 sessions by last use, the current one always among them, ✓ current (click = make current); greyed with no session
│                     · Older Sessions… (only above 10) ──► folder panel (native), "Session folders start with their date."; wrong pick: notification afterwards
├── New Session  ⌃⇧N   ──► notification "New session: 2026-09-28 22.15" (or "… is still empty, so new captures keep going there.")
├── ──
├── Settings…  ⌘,              ──► SETTINGS WINDOW (was: Settings ▸ six items)
└── Quit Snapmark ⌘Q   ──► with unsaved editors: sheet "N screenshots are not in a session yet." [Review] [Quit anyway]

EDITOR  (one per capture; title "Snapmark"; opens centred, exactly on top of any open editor; Dock icon shows;
         from a full-screen app it stays on that Space while the Mac slides to the desktop, F026 / F026)
├── Title row: traffic lights · app icon + "Snapmark" (drags the window; the window title stays "Snapmark — <session>")
├── Toolbar: C Select · ⌘1 Reference/Card · ⌘2 Box/Ellipse · ⌘3 Arrow · ⌘4 Pen · ⌘5 Cross/Remove area ·
│            ⌘6 Highlighter/Spotlight · ⌘7 Cut & move/Redact (captions follow Settings ▸ Shortcuts ▸ Pick tools with single keys: C or Esc) ·
│            colour swatch · Undo (icon) · Redo (icon) · Copy or Save (icon) · "<session> · n screenshots ⌄"
├── Copy or Save ──► native menu: Copy Image ⇧⌘C · Save As… ⇧⌘S
├── session label ⌄ ──► native menu: the 10 recent sessions (this editor's ticked) · New Session
│         a pick ──► the editor saves there, and it becomes the current session (plain text in Edit Again and one-shot)
├── Canvas (fitted, no zoom)
├── Side panel: comment ("Add a comment…") · References (after the first) · [Discard ⌘W] [Add to session ⌘↵ | Save changes ⌘↵]
├── ⌘↵ ──► entry added (or replaced, Edit Again) ──► window closes (silent; no route to the session)
│         session folder gone ──► nothing; button dead (silent, F049)
├── ⌘W · Discard · Esc past Select · close button · ⌘R (stock Reload) · Quit anyway · Restart to Update
│         ──► Discarded, 7 days (silent); an unchanged Edit Again is filed too (F077/F078)
└── Mac menu bar: Snapmark (About, Settings… ⌘,, Keyboard Shortcuts ⌘/, Services, Hide, Quit) · File ▸ Close Window ⌘W · Edit ▸ Undo (not the marks) ·
    View ▸ Reload ⌘R, Force Reload, Toggle Developer Tools, zoom, Toggle Full Screen ⌃⌘F · Window · no Help

SESSION WINDOW  (title "<folder name> — Snapmark"; 900 × 900; one per session, brought forward if open;
                 follows outside changes to session.md; reopens on the new name after Rename)
├── Header: name · [Document | Screenshots] · Open in Markdown App ──► the default .md app
├── Document: session.md rendered and editable, saved as you type (silent; outside writes can drop typing, F126/F127)
│             (the empty-session hint never shows, F132)
└── Screenshots: one at a time · ← → · "n of N" (position) · Edit Again ──► Editor ("Save changes")
                 · Remove from Session ──► Discarded (silent)

CAPTURE BAR       bottom centre of the pointer's display, every Space, full screen too; Close · Capture Window ·
                  Choose New Area · Capture Last Area · Capture Scrolling · Options ▾ (Save to · Timer · Show Mouse Pointer) ·
                  Capture | Capture One-Shot
                  ↩ ──► bar closes ──► the mode (Timer: seconds beside the menu bar icon, Esc cancels) ──► Editor
                  (session or one-shot) · Esc ──► nothing
SETTINGS WINDOW   title names the tab; one window, brought forward if open; reads its data again when it comes forward
                  General: Open Snapmark at login · Sessions folder Change… ──► folder panel · Clear Sessions Older Than 60 Days… ·
                  Snapmark <version> Check for Updates… ──► notification
                  Capture: Save to · Timer · Show mouse pointer (the capture bar's options)
                  Shortcuts: Pick tools with single keys · the four global keys · Show All Shortcuts ──► KEYBOARD SHORTCUTS WINDOW
AREA PICKER       see-through, display under the pointer, every Space; hint "Drag over the area to capture.
                  ⌃⇧3 captures it again each time. Esc cancels."
KEYBOARD SHORTCUTS WINDOW   "Keyboard Shortcuts", src/shortcuts.html, 980 × 680, read-only, no Dock icon; ⌘/ from any
                  Snapmark window or Settings ▸ Shortcuts ▸ Show All Shortcuts; one window; Esc or ⌘W closes it;
                  two columns: "Other keys" by where they work (Anywhere, Capture bar, Snapmark windows, Editor,
                  Session window) · "Editor tools" (13 rows, keys of the current mode)
NOTIFICATIONS (native)   the only channel for copies, New Session, failures; clicking only "… is no longer in …" does something
NATIVE PANELS AND DIALOGS   Sessions Folder…, Older Sessions…, Reopen Discarded… (folder panels, "Open"); Rename (AppleScript);
                  Quit sheet
FINDER            session folder = session.md · img/NNN.png · img/NNN/ (parts of a tall screenshot) · .edit/ (clean
                  originals, also of redacted images, F192) ·
                  <name>.pdf · <name>.zip ; sessions folder/.discarded/
FIRST LAUNCH      no window, no hint; Screen Recording asked at the first capture, which is wallpaper until Snapmark restarts
```

### Named or reachable two ways

- The editor: ⌃⇧4, ⌃⇧3, ⌃⇧5, Choose New Area…, Reopen Last Discarded, Reopen Discarded…, Edit Again.
- The session window: Open Session; restoring a removed screenshot.
- "Discard" (editor) and "Remove from Session" (session window) end in one store; "Reopen" brings back both
  with different results (F223).
- "Capture Screenshot" (menu) = "Capture region" (Keyboard Shortcuts, README) (F224).
- One session: "28 Sep 09.14" (menu, most notifications) and "2026-09-28 09.14" (editor, session window,
  session.md, the New Session notification) (F201/F222, F222).
- ⌘W in the editor: "Discard" (button, key list) and "Close Window" (Mac menu bar) (F110).

### Dead ends and no way back

| Where                                  | What is missing                                                | Findings              |
| -------------------------------------- | -------------------------------------------------------------- | --------------------- |
| Editor                                 | no route to its session; destination cannot be changed         | F061/F101, F101       |
| After Add to session                   | no sign of where the screenshot went                           | F062, F062            |
| Session window                         | no hand-off, export, rename, Finder                            | F133, F133            |
| Any non-current session                | reachable only by making it current                            | F008                  |
| Sessions in a previous sessions folder | unreachable                                                    | F175, F175            |
| Sessions                               | cannot be deleted                                              | F225, F008/F225       |
| A taken global key                     | cannot be changed                                              | F021, F021/F158/F173  |
| Discarded, beyond the last item        | folder panel on a hidden folder                                | F174, F174            |
| Keyboard Shortcuts                     | one path (Settings); none from the editor; lost behind windows | F003/F065, F164, F065 |
| Full-screen capture                    | reviewer on the desktop, editor on another Space               | F026, F026            |
| The saved area                         | cannot be seen, adjusted or cleared                            | F035, F036            |
| First launch                           | no window, no hint                                             | F209, F209            |

## Proposed

**A proposal, not decided.** The structure the proposed interaction guidelines imply. Items that depend
on an open decision are marked _(decision)_; the options are in the guidelines.

```
ENTRY POINTS
├── Menu bar icon (shows a brief tick and the count after each Add to session; a key opens it (decision))
├── Global keys: capture only, on neighbouring keys, changeable (chosen 2026-10-25: ⌃⇧3, ⌃⇧4, ⌃⇧5 mirror macOS's ⇧⌘3, ⇧⌘4, ⇧⌘5)
│     ├── Capture Screenshot
│     └── Capture Last Area
├── ⌘/ in any Snapmark window ──► Keyboard Shortcuts
├── Drop an image on the menu bar icon, or paste ──► Editor on that image
└── Relaunching Snapmark ──► opens its menu

FIRST LAUNCH ──► the menu opens once: "Snapmark lives here. <keys> capture."
FIRST CAPTURE without Screen Recording ──► small window: [Open System Settings] [Quit & Reopen] (no wallpaper capture)

MENU (fixed rows in a fixed order; unavailable rows greyed, never hidden; about 11 rows)
├── Capture Screenshot                <key>
├── Capture Last Area                 <key>    sub-line "1280 × 720 · Built-in Display, top left"
├── Choose Area…                      ──► Area picker with the current area drawn, adjustable, then [Capture] (Return)
├── ──
├── "Checkout review · 7 screenshots"          (header)
├── Copy for AI                       ──► clipboard + notification (decision: one line with the path, the key living in
│                                          session.md · prompt with a "Path Only" setting that renames the item · ⌥ alternate)
├── Open Session                      ──► Session window
├── ──
├── New Session…                      ──► asks for a name, date and time filled in (decision: no global key)
├── Switch Session ▸                  sessions with count and date ──► opens that session's window (current unchanged)
│                                     · Older Sessions… (any folder, only above 10)
├── Reopen Last Discarded             (greyed when nothing; says what comes back)
├── ──
├── Settings ▸  Open at Login · Sessions Folder… (offers to move sessions) · Check for Updates…
├── Keyboard Shortcuts   ⌘/
├── Quit Snapmark        ⌘Q
└── [Undo New Session / Restart to Update (0.9.1) / "28 Sep 14:32 is missing · Locate…"]   state lines, at the bottom

EDITOR  (opens over the app and Space the capture came from, offset from any open editor, on the last tool and colour;
         title "Screenshot → 28 Sep 14:32 — Snapmark" or "Screenshot 004 · 28 Sep 14:32 — Snapmark")
├── Toolbar: tools (strong active state; ⇧ + key for the sibling (decision)) · colour (recolours the selection) ·
│            Undo/Redo naming their step · zoom · ?
├── Canvas: zoom and pan; keyboard cursor (arrows, Enter, Tab through marks); click-pairs for every drag;
│           ⌘C ⌘V ⌘D on marks; drop an image ──► new editor
├── Side panel: Comment (labelled) · References · Cards · Moves · [Remove: …, Keep: …] rows, each linked to its mark
│   └── footer: "→ Checkout review ▾" (Open Session · other sessions · New Session…) · [Discard ⌘W] [Add to Session ⌘↵]
├── ⌘↵ ──► added ──► focus back to the app it came from; tick and count on the menu bar icon
│         failure ──► footer line with [Try Again] [Add to Another Session…]; the editor stays
├── ⌘W / Discard ──► Discarded, said once; nothing filed when unchanged
│   Edit Again with changes ──► "Discard your changes to screenshot 004?" [Keep Editing] [Discard Changes]
├── Esc ──► steps back to Select and stops
└── Mac menu bar: Snapmark (About, Settings… ⌘,, Keyboard Shortcuts ⌘/, Hide, Quit) · Edit (the editor's undo) · Window · Help

SESSION WINDOW  (any session; title "Checkout review — Snapmark"; remembers tab, size and last entry)
├── Header: name (click to rename, inline check) · "Saved" · [Document | Screenshots | Discarded] ·
│           [Copy for AI] (primary) · ⋯ (Export ▸ PDF · ZIP, Show in Finder, Open in Markdown App, Capture into This
│           Session, Delete Session…)
├── Document: session.md with the key to the marks on top; each entry with Edit Again and Remove beside it;
│             ⌘F find; conflicts ask [Keep Mine] [Load Theirs]; empty session: "No screenshots yet. Press <key> to capture one."
├── Screenshots: "Screenshot 004 · 3 of 12", the picture with its comment and notes; ← →; Edit Again;
│                Remove from Session (quiet, far right) ──► "Removed · Undo · In Discarded for 7 days"
└── Discarded: thumbnails, time, session; Restore per item (current session unchanged)

AREA PICKER       every display; opens with the current area drawn; drag or click-pairs or keys; [Capture] (Return); Esc
KEYBOARD SHORTCUTS WINDOW   "Anywhere" first, then "In the editor", "In the session window", "In the area picker";
                  global keys changeable here; Esc closes; built from the one key registry
NOTIFICATIONS     only for what happens out of sight (copies, a key taken at launch, background update), each with an
                  in-app twin in the menu
FINDER            session folder = session.md · img/ · exports with a date in their name; clear originals of redacted
                  images kept outside the shared folder (decision)
```

### What changes, in short

| Today                                             | Proposed                                           | Guideline                                     |
| ------------------------------------------------- | -------------------------------------------------- | --------------------------------------------- |
| 12–17 top-level rows that move with state         | about 11 fixed rows, greyed when unavailable       | Dialogs, menus and popovers                   |
| two copy items                                    | one hand-off item that says what it copies         | Dialogs, menus and popovers; The session file |
| New Session on ⌃⇧2 between the captures           | capture-only global keys, changeable               | Keyboard and focus                            |
| session actions in the menu, current session only | session actions in the session window, any session | Navigation and return                         |
| Discarded as a folder panel                       | Discarded as a tab with Restore                    | Lists and selection; Confirmation and undo    |
| editor stranded on a full-screen Space            | editor over the Space it came from, focus returned | Navigation and return                         |
| Esc's last step discards                          | Esc stops at Select; ⌘W discards                   | Keyboard and focus                            |
| silent Add to session, Discard, Remove, failures  | a sign on the icon, Undo bars, failures in place   | Feedback and notifications                    |
| Keyboard Shortcuts under Settings                 | ⌘/ from every window, top level in the menu        | First run and help                            |
| stock Electron app menu                           | Snapmark's own app menu                            | Platform conventions                          |
