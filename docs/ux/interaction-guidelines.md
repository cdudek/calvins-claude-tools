---
type: ux-guidelines
updated: 2026-11-13
---

# Agent tracker interaction guidelines: editing, navigation, dialogs, and feedback

Only the owner accepts a rule. Every rule below is `unresolved` until a decision accepts it; the change's spec proposes defaults and cites the area.

## Principles

None accepted yet.

## Rules

### Editing
- **Status:** unresolved
- **Note:** the tracker edits nothing the user owns. The one change it makes is marking an item seen.

### Side panels and detail pages
- **Status:** unresolved

### Dialogs, menus and popovers
- **Status:** unresolved

### Saving and unsaved work
- **Status:** unresolved
- **Note:** no user-entered work exists; view state (compact or details) saves itself.

### Confirmation and undo
- **Status:** unresolved

### Feedback and notifications
- **Status:** unresolved

### Progress and long operations
- **Status:** unresolved

### Navigation and return
- **Status:** unresolved

### Lists and selection
- **Status:** unresolved

### Forms and validation
- **Status:** not applicable. The tracker has no forms.

### Keyboard and focus
- **Status:** unresolved

### Search and filters
- **Status:** unresolved

### Undo across the app
- **Status:** unresolved

### Copy and paste
- **Status:** unresolved

### Drag and drop
- **Status:** not applicable. Nothing can be dragged in or out.

### Media playback
- **Status:** not applicable. The product has no media.

### Platform conventions
- **Status:** unresolved

### Local work and external writes
- **Status:** unresolved
- **Note:** the tracker writes outside its own folder only after the owner's press (hard rule: acts only on your press). See "Acts that write outside the tracker" below.

### Connection to external systems
- **Status:** unresolved
- **Note:** reads `claude agents --json`, git, gh and bd; any can be missing or fail.

### Remembered state
- **Status:** unresolved

### First run and help
- **Status:** unresolved

### Motion
- **Status:** unresolved

## Acts that write outside the tracker

Proposed defaults for Clear and Remove worktree. They apply to any later control that changes Claude Code's list or git state. Unresolved until the owner accepts them.

- **Confirm first:** a press never writes at once. It opens a confirm that says what will happen and what is kept. The one exception is an offer that already shows its reason and its two buttons.
- **Focus on the safe button:** when a confirm or an offer opens, focus is on Cancel or Keep, never on the act.
- **Never start the ring on a destructive button:** a page opens with the ring on a harmless control (Copy resume command or the Home crumb), never on Clear, Clear session or Remove worktree.
- **Result lines stay:** the lines that say what was done or refused stay until the owner leaves the page, and survive the 5-second re-read. A fresh visit shows the state as it now is.
- **Focus after the act:** after a Clear, focus goes to Keep worktree when an offer is drawn, else to Copy resume command, else to the Home crumb. It never goes to Reopen tasks.
- **Refuse on doubt:** re-read the facts at the press. If a session runs again or a read fails, change nothing and say so.
- **Name the next step:** an error line ends with an action ("Check it in a terminal.").

## Flows

Listed in `docs/ux/setup.md` under "Flows for this product"; drawn once rules are accepted.

## Exceptions

`docs/ux/exceptions.md`.

## Enforcement map

| Rule | Enforced by | Exists? | To build |
|---|---|---|---|
