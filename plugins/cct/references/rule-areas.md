# Interaction guidelines: structure, rule areas, flows, enforcement

The interaction guidelines are the app's shared behaviour: which interaction to use, when, and
why. A user should learn an action once and predict how it works everywhere else. A catalogue of
components alone does not satisfy this.

## Three levels

- **Principles:** what the experience must achieve, and why. Examples: keep the user in context
  for small changes; protect their work; give feedback in proportion to the consequence.
- **Patterns:** when and how to edit, save, open, close, confirm, undo, report an outcome.
  Example: rename directly in the list; open a side panel for several related settings.
- **Components:** the field, panel, dialog or notification that implements a pattern.

## The rule areas

For each area: what happens today in every build audited, a recommended default, the justified
exceptions, and every affected screen. Never assume one presentation fits every task merely
because it looks consistent.

| Area | Questions the rule must answer |
|---|---|
| Editing | When does a small change (rename) happen directly in the list? When does editing need a side panel, dialog or dedicated page? How does editing start, commit and cancel? |
| Side panels and detail pages | When must the list stay visible for comparison or repeated editing? Is the panel blocking, or can the user keep working beside it? What happens when another item is selected, or the window narrows? |
| Dialogs, menus and popovers | Which actions justify interruption? Which need only a menu or a small contextual choice? Dismissal, button labels and order, initial focus, whether another surface can open on top. |
| Saving and unsaved work | What saves immediately and what needs Save or Apply? How are pending, saving, saved and failed shown? What happens on every exit and document switch? |
| Confirmation and undo | What happens immediately with Undo, and what needs confirming first? Exactly what is deleted or overwritten, whether recovery is possible, how multi-item actions behave. |
| Feedback and notifications | When is the changed object itself enough? When is a brief toast useful? When must a result, error or required action stay visible beside the affected item? Essential information never lives only in a disappearing message. |
| Progress and long operations | Progress on the control, on part of the screen, or in a persistent queue? Can the user keep working, cancel, retry, resume? What happens after partial success? |
| Navigation and return | When does opening an item change pages? What does Back restore: filters, selection, scroll position? Previous/next, deep links. |
| Lists and selection | Select, open, preview and edit kept distinct. Click, double-click, Enter, Space, row actions and multi-select, each with a keyboard equivalent. |
| Forms and validation | When errors are checked and shown; values preserved; what Enter, Escape, clicking outside and a failed save do. |
| Keyboard and focus | Where focus goes when a surface opens and closes; which surface gets Escape; when shortcuts are suspended; a keyboard route for every pointer action. |
| Search and filters | As-you-type or on Enter; one search field in one place; what is kept on return; how active filters show and clear; what "no results" says and offers. |
| Undo across the app | One undo everywhere, and how far back; which actions can never be undone and must say so first; Undo and Redo naming what they undo. |
| Copy and paste | Copy, cut and paste for the product's objects, within and between screens; pasting onto something that is already there. |
| Drag and drop | What can be dragged from where to where, including from the operating system; how a target shows accept or refuse; folders, many files, unreadable files; the keyboard and menu route for every drag. |
| Media playback | What plays on select, focus or hover; one at a time or layered; what stops or continues on screen change, dialog or new sound; how fast a preview starts; volume; the transport versus single previews. (Skip when the product has no media.) |
| Platform conventions | The menu bar or app chrome, standard keys (close, quit, settings, full screen), window close with unsaved work, right-click menus, text-field keys. Where the product follows or breaks the platform. |
| Local work and external writes | The difference between changing local data and writing to an external system (a device, a server, another app). Pending, disconnected, stale data, failed transfer. |
| Connection to external systems | Connected, disconnected mid-job, switched off, replaced by another model or version; read-only versus writable targets; stale data and refresh; what a running job does after reconnect. (Skip when there is none.) |
| Remembered state | What persists between sessions and screens: last screen, window size, detail level per view, columns, sort, filters, selection, scroll, collapsed panels. Per screen or global. |
| First run and help | The first launch; empty data; indexing or setup; where help lives: key hints, tooltips, empty states that teach, a shortcut list. How much can be learned without reading. |
| Motion | What animates, how long, and what happens with reduced motion on. Motion that explains a change versus motion that decorates. |

Areas that do not apply to a product are listed with "not applicable" and the reason.

## How each rule is written

```markdown
### <Rule name, plain language>
- **Status:** proposed · accepted (date, by whom) · deferred · rejected · unresolved
- **Situation:** when it applies.
- **Rule:** the behaviour, concretely: which surface, which keys, which words.
- **Why it helps:** the workflow benefit.
- **Tradeoff:** the main downside.
- **Exceptions:** each with its reason and the screens it covers.
- **Example:** a concrete one from this product, with an annotated screenshot or a labelled
  proposal.
- **Applies to:** every affected screen.
<details><summary>Supporting notes</summary>Findings it resolves · evidence · other products.</details>
```

Acceptance is never inferred from an existing implementation or an older document. Only the
owner accepts a rule.

## Complete flows

Rules are shown working together in complete flows, not only in isolated surfaces. Each flow
shows every step: what the user does (pointer and keyboard route) and what they see. The
project's `docs/ux/setup.md` lists its flows; these are the minimum:

- rename an item from a list
- edit a document and leave with unsaved work
- compare and edit several items
- delete an item and recover it where possible
- send or write to an external system: success, failure, partial completion
- search, open a result, come back to the same results
- drag files in from the operating system, including one that cannot be read
- lose the connection in the middle of a job and get it back
- the first launch up to the first useful result
- plus media playback while moving through a list and changing screen, when there is media

Set each flow in one of the audience's scenes (from the project's audience file) and say which.

## Enforcement map

For every accepted rule: the one shared component or the test that makes breaking it
impossible, whether it exists today, and what would have to be built. A rule with nothing
behind it is marked **not enforced**, so it is visible rather than forgotten. `ux:conformance`
reads this map.

| Rule | Enforced by | Exists? | To build |
|---|---|---|---|
