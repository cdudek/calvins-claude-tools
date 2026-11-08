---
type: ux-setup
updated: 2026-09-28
---

# UX setup: Snapmark

Every `ux:` skill reads this file first. Keep it short and true.

## The product

- **What it is:** a macOS menu bar app that captures a screen region, lets you mark it up, and appends it with your notes to a Markdown session an AI agent can read.
- **Platform:** desktop — Electron 45, macOS only. Menu bar app; a Dock icon shows while an editor or session window is open.
- **Audience file:** none; the owner confirmed these scenes on 2026-09-25 ("I think this are the main use cases").
  1. **Reviewing an overnight build:** a complete UX/UI review of what an agent built overnight, with detailed feedback on many different elements, captured on the fly with shortcuts, then handed to Claude Code. The main scene.
  2. **Sharing with a person:** the same session as a PDF or ZIP for a teammate or stakeholder.
  3. **A quick verdict:** mark what should go and what should stay (red remove, green approve) on one screenshot.
- **Jobs to be done:** point at something on screen precisely; say what should change; collect it in one file per piece of work; hand it to an AI in a token-efficient way.
- **Products the audience already uses** (for pattern research, owner's answer 2026-09-25): macOS Screenshot (the built-in `⌘⇧4`/`⌘⇧5` markup), Figma, Ocra (as written), Xnapper.

## The rules it must follow

- **Design system:** [design-system-starter](https://github.com/cdudek/design-system-starter), pinned in `snapmark-app/design/tokens.lock.json` and built into `snapmark-app/src/tokens.css` by `npm run tokens`; Snapmark's rules are its `examples/snapmark.md`. App and menu bar icons in `snapmark-app/assets/`.
- **Glossary:** none yet — `docs/ux/glossary-proposal.md`.
- **Voice and writing rules:** none in the repo.
- **Hard rules** that override UX preferences (from the owner's words):
  - Everything must be doable on the fly with shortcuts.
  - The output is a Markdown document including the images, organised as sessions.
  - macOS first; Electron + TypeScript.
  - Remove marks are always red and approve marks always green.

## The owner's words

- **File:** `docs/ux/owner-words.md` — every request, verbatim, dated. Quote from it; never cite a request by number.

## Where the UX files live

| File                                                 | Path                                                                        |
| ---------------------------------------------------- | --------------------------------------------------------------------------- |
| Audits                                               | `docs/ux/audits/<YYYY-MM-DD>/` (briefing, evaluator notes, findings, shots) |
| Findings (latest)                                    | `docs/ux/audits/<YYYY-MM-DD>/findings.md`                                   |
| Decision lists (one per round, built by ux:decision) | `docs/ux/decisions-<YYYY-MM-DD>.md`                                         |
| Decision log (every answer, appended)                | `docs/ux/decisions.md`                                                      |
| Interaction guidelines                               | `docs/ux/interaction-guidelines.md`                                         |
| Target sitemap                                       | `docs/ux/sitemap.md`                                                        |
| Glossary proposal                                    | `docs/ux/glossary-proposal.md`                                              |
| Decision page (optional)                             | <none yet>                                                                  |

## Screens and states

| Screen                    | Route or entry                                                                                | States to capture                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| ------------------------- | --------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Menu bar menu             | the menu bar icon                                                                             | no session yet · current session empty · current session with screenshots · Switch Session list · Export submenu · something discarded (Reopen items shown) · Capture Last Area with and without an area · update waiting · development build (updates and Open at Login disabled) · the capture rows: Capture Last Area (`⌃⇧4`), Capture New Area… (`⌃⇧1`), Capture Full Screen (`⌃⇧3`), Capture One-Shot… (`⌃⇧2`), Capture Options… (`⌃⇧5`) · during a countdown (a click cancels)                                                                                                                             |
| Capture One-Shot          | `⌃⇧2` or the menu                                                                             | macOS's own `screencapture -i`: region · window (Space) · cancelled (Esc) · from a full-screen app's Space; the capture opens in a one-shot editor. Not Snapmark's UI, but part of the flow.                                                                                                                                                                                                                                                                                                                                                                                                                     |
| Capture bar               | `⌃⇧5` or menu → Capture Options…                                                              | one row: Close, the five modes, the destination ("To <session>" or "One-Shot", `⇧⌘O`, its pop-up `⇧⌘P`), Options and Capture · each mode chosen: New Area, Window, Full Screen, Last Area, Scrolling (1–5; Capture reads Start Scrolling) · a control's drawn tooltip, on hover and after Tab · the focus ring after Tab · Options menu (Timer None, 3, 5 or 10 Seconds; Show Mouse Pointer) · destination pop-up open · no session yet · One-Shot chosen (Capture One-Shot) · ↩ or ⌘↩ captures · Esc closes, also from another app · narrow (under 1000 pt) and 150 % · light and dark · over a full-screen app |
| Area picker               | `⌃⇧1`, `⌃⇧4` the first time or after New Session, or the capture bar's New Area               | dimmed screen with the hint · dragging with the size label · a click or sliver (starts over) · Esc · over a full-screen app                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| Capture Last Area         | `⌃⇧4` once an area is set                                                                     | captures at once · the area's display is gone (asks again)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| Capture Full Screen       | `⌃⇧3`, the menu, or the capture bar's Full Screen                                             | every display at once, one screenshot and one editor each, the pointer's display in front · one display                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| Countdown overlay         | a capture bar Timer (3, 5 or 10 Seconds)                                                      | the area outlined with the digit square · Full Screen (square in the middle of the display) · each digit · Reduce Motion · cancelled by Esc, `⌃⇧5` or a click on the menu bar icon · 150 % · never in the screenshot                                                                                                                                                                                                                                                                                                                                                                                             |
| Editor window             | opens after a capture, a reopened discard, or Edit Again                                      | empty · every tool of groups 1–7 and Select · reference added, note being typed · card being typed · card with a pointer line · mark selected with handles · cut piece mid-move · spotlight · redact · undo and redo · Edit Again ("Save Changes") · Session and One-Shot · the session pop-up open · the move error under the pop-up · One-Shot with notes ("Notes stay with Session. They are not copied.") · the hex error · minimum size (820 × 520) · light and dark · saving · opened from a full-screen app's Space                                                                                       |
| Session window            | menu → Open Session; opens at 90 % of the screen the first time, then at its last size        | Document tab (session.md rendered and editable) · Screenshots tab (one at a time, ← →, Edit Again, Remove from Session, Open in Markdown App) · empty session · session.md changed outside                                                                                                                                                                                                                                                                                                                                                                                                                       |
| Settings window           | menu → Settings…, or `⌘,` in a Snapmark window                                                | General · Capture · Shortcuts · login waiting for approval · development build (login and updates greyed) · `SNAPMARK_ROOT` set · a key taken by another app · light and dark                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| Keyboard Shortcuts window | `⌘/` in a Snapmark window, or Settings ▸ Shortcuts ▸ Show All Shortcuts                       | the list · single keys on and off · light and dark · below 760 pt (stacked)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| Notifications             | macOS notification centre                                                                     | new session (`⌃⇧N`) · session still empty · copied prompt or path · export failed · shortcut taken by another app · session missing · update check                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| Native dialogs            | Sessions Folder…, Older Sessions…, Reopen Discarded…, Rename Session…, Quit with unsaved work | each dialog                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `session.md`              | the session window, or the owner's Markdown app                                               | one entry · many entries · entry with notes, cards and a move                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| PDF and ZIP export        | menu → Export Session                                                                         | one entry · several entries · tall images across pages · Finder opens with the file selected                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| First run                 | installing the DMG, first launch, first capture                                               | Screen Recording permission not granted (wallpaper-only capture) · first capture with no session · auto-update to a new version                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |

App-wide parts: menu bar icon and menu, global shortcuts `⌃⇧1` (Capture New Area), `⌃⇧2` (Capture One-Shot), `⌃⇧3` (Capture Full Screen), `⌃⇧4` (Capture Last Area), `⌃⇧5` (the capture bar) and `⌃⇧N` (New Session), the Dock icon, macOS notifications, Finder reveal, auto-update, Discarded (kept 7 days).

## How to run it for an audit

- **Build and run:** `npm ci && npm run smoke`. It renders a mock app page, opens the real editor on it, uses every tool, saves, exports a PDF, and writes `editor.png` (the editor window) and `smoke/img/001.png` (the saved image) to a temp folder it prints as `root:`.
- **Scale check:** `npm run build && (cd snapmark-app && npx electron --force-device-scale-factor=1 dist/test/smoke.js)` for a non-Retina screen.
- **Test data:** the mock page inside `snapmark-app/test/smoke.ts`; `SNAPMARK_ROOT` points sessions at a temp folder. Never the owner's screen.
- **Screenshots go to:** `docs/ux/audits/<YYYY-MM-DD>/shots/`
- **Window sizes:** editor at its minimum 820 × 520, and 1440 and 1920 wide; Retina (2×) and 1×.
- **Builds to audit:** `main` (v0.9.0 and later). No open pull requests.
- **Not scriptable:** the menu bar menu, macOS's capture overlay, notifications, native dialogs and Spaces (full-screen apps). Evaluate those from the code and the owner's reports; say which in each finding. The area picker can be driven like the smoke test does (`pickArea()` plus input events to its window); its screenshot shows only Snapmark's own window.

## Safety

- **Never write to:** `~/Documents/Snapmark/` (the owner's real sessions), `~/Library/Application Support/snapmark/state.json` (the installed app's state), the owner's login items (the Open at login toggle), the owner's clipboard.
- **Read only:** the owner's sessions, if a real example is needed, and only with the owner's permission.
- **Never capture:** the owner's real screen. Use the mock page. Never press `⌃⇧1`, `⌃⇧2`, `⌃⇧3`, `⌃⇧4`, `⌃⇧5` or `⌃⇧N`, and never run `screencapture`.
- **Writes only against:** temp folders via `SNAPMARK_ROOT`, and `~/Library/Application Support/Electron/` (where the smoke test keeps its state, because it runs without the app's package name).

## Flows for this product

Beyond the minimum in `rule-areas.md`:

- Capture, mark, save, capture the next one (scene 1).
- Start a new session and switch back to an older one (scene 1).
- Hand a session to an agent: Copy prompt for AI, paste (scene 1).
- Share with a person: export PDF or ZIP (scene 2).
- Move sessions into iCloud Drive or Google Drive (scene 2).
- Mark what goes and what stays on one screenshot (scene 3).
- Cut an element and move it where it should go (scene 1).
- Place a card that points at an element, then move the card (scene 1).
- Fix a mistake: undo, select, delete (all scenes).
- First launch up to the first saved screenshot (all scenes).
