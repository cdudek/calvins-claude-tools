---
type: component-contract
status: proposed
created: 2026-10-29
updated: 2026-10-29
---

# States and feedback: component contract for `heydiff-kit/ui`

For the kit UI builder. It says what each state component is called, what it takes, how it behaves, how long it waits, where focus goes and what a screen reader hears. The reasons and examples are in [interaction-guidelines.md, "States and feedback"](interaction-guidelines.md#states-and-feedback). Rule IDs (LOD, TOA, EMP, ERR, STA, PRE, KEF) point there.

**Status.** The file is `proposed` as a whole until the owner reads it at the milestone 1 PR (F14). Each behaviour below says which rule it builds. Where that rule is in force (owner, 2026-10-29, or spec), the behaviour is not optional. Where the rule is `proposed`, the value is a default and lives in a token. On a conflict, PRE-1 decides: the owner's decisions, then the ruleset, then the older rules.

A screen never builds these by hand. Lint and the dependency check fail a raw `animate-spin`, `<progress>` or toast library outside `heydiff-kit/ui`.

## Tokens

Durations and curves are the motion tokens of `motion.md`. This file adds state tokens, in the same token file. Change a value there, never in a screen.

```css
:root {
  --state-delay: 400ms; /* nothing shows before this (LOD-1) */
  --state-refresh-label: 1000ms; /* "Refreshing…" text and the bar's label (LOD-8) */
  --state-min-visible: 300ms; /* once shown, stays at least this long (LOD-4) */
  --state-slow: 10000ms; /* "Still loading…" appears (LOD-11) */
  --state-budget: 30000ms; /* the one waiting budget per operation (LOD-11) */
  --state-retry-floor: 5000ms; /* no read retry starts with less budget left (ERR-4) */
  --toast-result: 5000ms; /* TOA-5 */
  --toast-undo: 8000ms; /* TOA-4 */
  --toast-resume-min: 3000ms; /* time left after a pause (TOA-5) */
}
```

The 30 s budget counts from the first request and includes every retry. For an upload or a long job it counts time without progress.

## Skeleton

Path `heydiff-kit/ui/src/skeleton/Skeleton.tsx`. Built from HeroUI Skeleton. For types K and N (LOD-2, LOD-9).

| Prop      | Type                                                 | Notes                                                             |
| --------- | ---------------------------------------------------- | ----------------------------------------------------------------- |
| `variant` | `'rows' \| 'entries' \| 'card' \| 'text' \| 'thumb'` | The layouts of our screens. `rows` and `entries` take `count`.    |
| `count`   | `number`                                             | Inbox 8 rows, a thread 3 entries.                                 |
| `label`   | `string` (required)                                  | The status sentence, from a message key: "Loading the comments…". |
| `busy`    | `boolean`                                            | Wrapper form: `<Skeleton busy={isPending}>…children…</Skeleton>`. |

- Renders nothing visible for `--state-delay`, then the static blocks. No shimmer, no pulse, no animation at all.
- Once visible, stays at least `--state-min-visible`, even if `busy` turns false sooner.
- Blocks take the final height and width of the real content, so nothing shifts (LOD-14).
- From `--state-slow` it adds the text `common.loading.slow` ("Still loading…") inside the region. At `--state-budget` the caller shows `ErrorState`; the component does not time out by itself.
- Accessibility: the wrapper sets `aria-busy="true"`; the blocks are `aria-hidden`; a visually hidden polite status line (`role="status"`) holds `label` and is inserted when the blocks appear, not before. It never moves focus.
- Also exports page skeletons used by `loading.tsx`: `InboxSkeleton`, `ListPageSkeleton`, `DetailPageSkeleton`, built from the same variants.
- A skeleton never replaces rows that are on screen for the same query. A refresh uses `RefreshIndicator`.

## RefreshIndicator

Path `heydiff-kit/ui/src/refresh-indicator/RefreshIndicator.tsx`. New. For type R: content already on screen refreshes (LOD-8).

| Prop     | Type                | Notes                                                              |
| -------- | ------------------- | ------------------------------------------------------------------ |
| `active` | `boolean`           | True while the refresh runs.                                       |
| `label`  | `string` (required) | "Refreshing…". From a message key.                                 |
| `slow`   | `boolean`           | Derived from time; switches the label to `common.refreshing.slow`. |

- Wrapper form: `<RefreshIndicator active={isFetching} label=…>{rows}</RefreshIndicator>`. It sets `aria-busy="true"` on the wrapper at once.
- Nothing visible for `--state-delay`. Then a 2 px indeterminate bar along the region's top edge, inside the region, never at the top of the page. Stays at least `--state-min-visible`.
- From `--state-refresh-label` the text "Refreshing…" shows beside the region's heading. It is also the polite status line (`role="status"`), inserted then, not before. At `--state-slow` it reads "Still refreshing…".
- It **never changes the children**: no opacity, no filter, no overlay, no pointer-events change. Text keeps its colour and its 4.5:1 contrast (LOD-8, ACC-3). A test fails if a computed style on a child changes while active.
- It never moves focus.
- Reduced motion: a static full-width bar at 40 % opacity, with the same text.

## Spinner

Path `heydiff-kit/ui/src/spinner/Spinner.tsx`. For a small wait beside a control (type X) and inside a busy Button. Never alone as a page loader.

| Prop    | Type                | Notes                                                        |
| ------- | ------------------- | ------------------------------------------------------------ |
| `size`  | `'sm' \| 'md'`      | 16 px and 20 px.                                             |
| `label` | `string` (required) | Visible text beside it, or the status sentence if icon only. |

- Same 400 ms delay and 300 ms minimum as Skeleton, **except inside a busy Button**, where it shows at once with the button (LOD-6).
- Under reduced motion it is a static three-dot mark.
- Colour is `text-2`, never the accent.

## ProgressBar

Path `heydiff-kit/ui/src/progress-bar/ProgressBar.tsx`. Built from HeroUI Progress. For type U (determinate or indeterminate) and type X in a region.

| Prop       | Type                  | Notes                                                               |
| ---------- | --------------------- | ------------------------------------------------------------------- |
| `value`    | `number \| undefined` | 0 to 100. Undefined means indeterminate.                            |
| `label`    | `string` (required)   | Always visible text: "Uploading {file}…". Never a bar alone.        |
| `onCancel` | `() => void`          | Optional. Shows a Text button "Cancel". Always given for an upload. |

- `role="progressbar"`, `aria-valuenow` when determinate, `aria-valuemin` and `aria-valuemax`, `aria-label` from `label`.
- Appears at 1 s (the caller starts it at 1 s; `--state-delay` does not apply), sits in the region of the thing that waits, never at the top of the page.
- Determinate: width follows the value with `--motion-quick` and `--ease-standard`. Indeterminate: a short bar sliding; under reduced motion a static full-width bar at 40 % opacity with the label.
- For an upload the 30 s budget is time without progress: the caller resets it on every value change. A bar that stalls for `--state-budget` ends as an item error (ERR-5).
- Announces the start through its label once; never announces every percent.

## Button `busy`

Path `heydiff-kit/ui/src/button/Button.tsx`. Props on the existing Button. For type B and the start of type U (LOD-6).

| Prop             | Type      | Notes                                                                   |
| ---------------- | --------- | ----------------------------------------------------------------------- |
| `busy`           | `boolean` | Turns on the busy state at once, no delay. Exempt from `--state-delay`. |
| `busyLabel`      | `string`  | The announcement: "Sending the comment…". Required with `busy`.         |
| `busySlowLabel`  | `string`  | Optional. Replaces `busyLabel` at `--state-slow`: "Still sending…".     |
| `disabledReason` | `string`  | Required when the button is `isDisabled`. See below.                    |

- The pressed state (`:active`, `data-pressed`) shows at once on every press. It is never delayed.
- Busy: a Spinner replaces the icon, or sits before the label when there is no icon, and shows at once. Label and width stay. Presses and Enter are ignored. `aria-busy="true"`. The button keeps focus.
- `busyLabel` goes to the polite status line once when `busy` becomes true. `busySlowLabel` goes once at `--state-slow`.
- At `--state-budget` the caller ends the operation (ERR-5). The button leaves busy, and the item or region shows "Not confirmed". The button is not left spinning.
- Disabled with a reason (STA-2): the button stays visible and focusable, sets `aria-disabled="true"`, ignores presses, shows the reason in its Tooltip and `aria-describedby`. On touch, the reason shows beside the button. A disabled button without `disabledReason` is a type error.
- No ripple and no state layer while disabled or busy (`motion.md`).

## Toast

Path `heydiff-kit/ui/src/toast/Toast.tsx`. One `ToastRegion` per page (or per shadow root in the extension), mounted before any toast. It holds two slots (TOA-7): the **note slot** for Result and Undo, the **problem slot** for Problem.

API, called from event handlers and server action results only:

```ts
type Recovery = {
  /** Where the way back lives after the toast is gone (TOA-13). */
  kind: 'item' | 'removed' | 'history';
  /** The id of that handle, registered with registerRecovery(). */
  ref: string;
};

toast.result(message: string): void;                                          // 5 s
toast.undo(message: string, o: { onUndo: () => void; recovery: Recovery }): void; // 8 s
toast.problem(message: string, retry?: () => void): void;                     // until closed
registerRecovery(ref: string): void;  // the item or RecentlyRemoved view calls it on mount
```

`message` is a message-key result (a sentence ending in a full stop). The kit does not accept a bare string literal in JSX. `toast.undo` without `recovery` is a type error. In development it also throws when `recovery.ref` was never registered.

| Behaviour          | Rule                                                                                                                                                                                                                                                          |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Note slot          | One at a time. A new Result or Undo replaces the one showing (exit `--motion-quick`). A replaced Undo toast only leaves the screen; its `recovery` handle stays valid and `onUndo` stays reachable through it.                                                |
| Problem slot       | One at a time, nearer the edge than the note slot. Never replaced and never hidden by a Result or Undo. A second Problem waits behind it and the first shows "1 of 2".                                                                                        |
| Problem leaves     | Close, a successful Try Again, or `toast.dismissProblem(id)` when its cause is gone. Never by a timer.                                                                                                                                                        |
| Dedupe             | The same text within 2 s refreshes the timer; it does not stack.                                                                                                                                                                                              |
| Timer              | `--toast-result` and `--toast-undo` start when visible. Pause while the pointer or focus is inside. After a pause it restarts with at least `--toast-resume-min` left.                                                                                        |
| Untimed equivalent | The timer is never the only chance (TOA-14). The `recovery` handle has no timer.                                                                                                                                                                              |
| Actions            | Undo or Try Again, one at most, a Text button last in the row. No links.                                                                                                                                                                                      |
| Close              | A Close icon button only on a Problem toast. Esc closes a toast that has focus.                                                                                                                                                                               |
| Keys               | ⌘Z (Ctrl+Z elsewhere) runs `onUndo` of the Undo toast in the note slot, and only as the last owner in KEF-2: not when focus is in a text field, not when a drawing, moving or arranging surface has focus or is the active tool. The toast never takes focus. |
| Place              | Web desktop: bottom centre of the main column, 24 px above the edge. Phone: 16 px gutter, 12 px above the fixed bottom bar. Extension: 12 px above the toolbar or the docked composer, inside the shadow root.                                                |
| After a dialog     | A toast raised by a dialog's action waits until the dialog has closed.                                                                                                                                                                                        |
| Motion             | `--motion-shift-far` up plus opacity, `--motion-standard`, `--ease-emphasised`; exit opacity, `--motion-quick`. Reduced motion: opacity only.                                                                                                                 |

Accessibility: the region is `role="status"` with `aria-live="polite"` and `aria-atomic="true"`. A Problem toast is `role="alert"`. An Undo toast's announcement ends with "Press ⌘Z to undo." (`extension.toasts.undoHint`). No toast ever carries the only copy of something (TOA-11), and no Undo toast is the only way back (TOA-13).

### The ⌘Z owner

The Toast listens at the document, and a surface claims the key first. A surface that owns history (the canvas, its mark list, the change list) marks itself `data-undo-owner`. The Toast handler does nothing when `document.activeElement` is a text field or lies inside a `data-undo-owner` element, or when the surface is the active tool. A test per case (below).

## RecentlyRemoved

Path `heydiff-kit/ui/src/recently-removed/RecentlyRemoved.tsx`. New. The lasting handle for Delete Comment, Discard and Dismiss (TOA-13). Rendered as the `?view=removed` view of a list.

| Prop        | Type                                                                                      | Notes                                    |
| ----------- | ----------------------------------------------------------------------------------------- | ---------------------------------------- |
| `items`     | `{ id: string; label: string; removedAt: Date; kind: 'comment' \| 'draft' \| 'inbox' }[]` | Newest first, kept 30 days.              |
| `onRestore` | `(id: string) => Promise<void>`                                                           | Restore puts the item back where it was. |

- Each row has its text or label, the time, and a Restore button (busy while it runs).
- After Restore the status line (polite) says where it went: "Restored to Comments." Focus goes to the restored item if the page shows it, otherwise stays on the list heading.
- A discarded draft keeps its text, drawing and choices. A restore into a place that already has a newer draft never overwrites it (ERR-2): it restores as a separate item.
- An empty view uses `EmptyState` kind `nothing-yet`: "Nothing was removed."
- It calls `registerRecovery('removed')` on mount, and the app registers it once at start so a toast never points at a missing view.

## FailedSubmission

Path `heydiff-kit/ui/src/failed-submission/FailedSubmission.tsx`. New. A failed or unconfirmed write, as its own item (ERR-2, ERR-5, ERR-13, ERR-14). Replaces `InlineError`'s old item form.

| Prop               | Type                                   | Notes                                                                                                                                 |
| ------------------ | -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| `status`           | `'failed' \| 'unconfirmed' \| 'saved'` | `failed`: confirmed failure. `unconfirmed`: no answer. `saved`: reconciled; renders the item.                                         |
| `message`          | `string`                               | Event, consequence, action, from `*.errors.*`. "Not confirmed…" for `unconfirmed`.                                                    |
| `text`             | `ReactNode`                            | The full payload, shown read-only.                                                                                                    |
| `onRetry`          | `(edited: boolean) => void`            | `edited` is true after Edit. The caller makes a new key and sends `replaces` when it is true (ERR-14).                                |
| `onEdit`           | `(text: string) => void`               | Opens the item's own field in place. Never touches the composer.                                                                      |
| `onDiscard`        | `() => void`                           | Moves the payload to Recently removed.                                                                                                |
| `onMoveToComposer` | `() => void \| undefined`              | Optional.                                                                                                                             |
| `composerEmpty`    | `boolean`                              | Required with `onMoveToComposer`. When false, the button is disabled with `disabledReason` "Finish or send your current reply first." |

- Sits at the position where the item was sent, marked "Not sent" or "Not confirmed". Each failure is its own item; two failures render two.
- A polite live region (`role="status"`) says the message once when it appears. It never takes focus.
- Try Again is busy while it runs. **Move to the composer** re-checks `composerEmpty` when the move applies. If text has arrived, it does nothing and keeps both texts.
- `status` turns to `saved` when the caller reports a late success or a retry's success (ERR-14). The error text goes, one polite line says "Reply sent.", and no second item exists.
- Focus: nothing moves on failure. After a successful Try Again, or after a late success, focus goes to the saved item only if focus was inside the failed item. After Discard, focus goes to the next item, or to the composer when none is left.
- The payload is persisted in the draft store (WEB-17) so a reload, an offline spell and an expired session keep it.

## EmptyState

Path `heydiff-kit/ui/src/empty-state/EmptyState.tsx`. Composed; also the 404.

| Prop             | Type                                                                      | Notes                                                              |
| ---------------- | ------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| `kind`           | `'first-use' \| 'nothing-yet' \| 'filtered' \| 'all-done' \| 'not-found'` | Sets the layout and which parts may show.                          |
| `title`          | `string`                                                                  | One short sentence, sentence case. Absent in the compact form.     |
| `text`           | `string`                                                                  | One sentence.                                                      |
| `action`         | `{ label: string; onPress: () => void } \| undefined`                     | At most one, Filled. `all-done` and the compact form reject it.    |
| `compact`        | `boolean`                                                                 | One plain line for a small section.                                |
| `onClearFilters` | `() => void`                                                              | Required when `kind="filtered"`; renders the Clear Filters button. |

- Fills the list area, centred; the header and filter bar stay outside it.
- No illustration; an optional neutral 24 px icon.
- The title is a heading; its level is a prop (`headingLevel`), set by the page.
- `kind="not-found"` has one fixed text, "This page doesn’t exist, or you don’t have access.", and never says which.
- When a filter change makes a list empty, the caller's list status line (polite) says the text. The component announces nothing on first render.
- The caller renders it only after the checks of EMP-8: never over content, never while loading, never after a failed load with nothing on screen.

## ErrorState

Path `heydiff-kit/ui/src/error-state/ErrorState.tsx`. For a section or a page whose load failed, and for a refresh that failed over readable content.

| Prop        | Type                                           | Notes                                                                                                                                        |
| ----------- | ---------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `level`     | `'section' \| 'page'`                          | Section fills the region; page fills the shell body.                                                                                         |
| `placement` | `'replace' \| 'beside'`                        | `replace` (default): stands where the content would be. `beside`: sits above kept content, which it never hides (LOD-8). Section level only. |
| `message`   | `string`                                       | Event, consequence, action, from a `*.errors.*` key. For `beside`: names the load time.                                                      |
| `loadedAt`  | `Date \| undefined`                            | Required with `placement="beside"`. Fills "Showing what loaded at {time}."                                                                   |
| `onRetry`   | `() => void \| undefined`                      | Shows Try Again (Tonal). Omit for a refusal by a rule (ERR-3).                                                                               |
| `reference` | `string \| undefined`                          | Page level only: "Reference: {id}".                                                                                                          |
| `secondary` | `{ label: string; href: string } \| undefined` | Page level: Go to Inbox.                                                                                                                     |

- Try Again is busy while it retries, and keeps its place. A retry has a new 30 s budget (LOD-11).
- A page `ErrorState` moves focus to its heading on mount. A section one, `replace` or `beside`, does not move focus; its text is a polite live region.
- `beside` renders as a strip above the content, in normal flow, never an overlay. The content under it is unchanged: same colour, same contrast, same scroll, same focus.
- After a filter or sort change that failed, the message says which results show: "Couldn’t apply the filter. These are the earlier results." (LOD-8).
- Used by `error.tsx` (calls `reset`), by section error boundaries and by failed `Suspense` regions. The boundary rule is ERR-7: the nearest ancestor `error.tsx` counts.

## InlineError

Path `heydiff-kit/ui/src/inline-error/InlineError.tsx`. For a field only. An item's failure is a `FailedSubmission`.

| Prop      | Type     | Notes                                                      |
| --------- | -------- | ---------------------------------------------------------- |
| `message` | `string` | Event, consequence, action. A field error is one sentence. |
| `id`      | `string` | The field points at it with `aria-describedby`.            |

- Text plus a danger-text icon, never colour alone. Sits directly under the field.
- A polite live region (`role="status"`). It stays until the cause is fixed.
- A field sets `aria-invalid="true"` while an `InlineError` shows. Checked on blur after the first edit and on submit; on submit, focus moves to the first invalid field.
- The component never clears the input it belongs to.

## OfflineBanner

Path `heydiff-kit/ui/src/alert/OfflineBanner.tsx`. A variant of Alert, one per page.

- Full width of the main column, above the content, `role="alert"`, announced once when it appears.
- Words: "Offline. You can read what’s loaded. Replying and resolving are off until you’re back. Your drafts are kept." (`common.offline.banner`).
- Listens to the browser's `online` and `offline` events. On `online` it leaves and the page makes one refetch.
- Writes elsewhere on the page use `Button` with `disabledReason`, naming what is off ("Offline. Replying is off until you’re back.").
- A `FailedSubmission` stays on the page while offline. Its Try Again is `aria-disabled` with the reason until the browser is back.

## Next.js files the kit's users must add

| File                                 | Where                                                                   | Content                                                                                  |
| ------------------------------------ | ----------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| `loading.tsx`                        | every folder with a `page.tsx` under `(app)`, `(operator)`, `account`   | the page skeleton of that screen (its shape is its own)                                  |
| `error.tsx`                          | `(app)`, `(operator)`, `account`, and any folder whose recovery differs | `ErrorState level="page"` with `reset`. A route below one needs none (ERR-7).            |
| `not-found.tsx`                      | the locale root and each shell group                                    | `EmptyState kind="not-found"` inside the shell                                           |
| `global-error.tsx`                   | `src/app`                                                               | its own `html` and `body`, static English text: "Something went wrong. Reload the page." |
| `<Suspense fallback={<…Skeleton/>}>` | around each independently slow server component                         | the matching skeleton; the shell and heading stay outside                                |

## What the kit's own tests prove

Every test asserts behaviour, not only that a state renders (PRE-3). Timing tests use fake timers.

- **Skeleton:** nothing before 400 ms; visible after; stays 300 ms; `aria-busy` and the status line; "Still loading…" at 10 s; never moves focus.
- **RefreshIndicator:** nothing before 400 ms; the bar after; "Refreshing…" and the status line only from 1 s; "Still refreshing…" at 10 s; children's computed opacity, colour and `pointer-events` never change; contrast of the child text is unchanged; reduced motion renders the static form.
- **Spinner and ProgressBar:** the same delay; the progressbar attributes; the bar's budget resets on progress and fails after 30 s without it; reduced motion renders the static forms.
- **Button:** the pressed state shows at once; `busy` shows at once (no 400 ms), ignores presses, keeps its label and width, announces once; `busySlowLabel` at 10 s; `isDisabled` without `disabledReason` does not compile.
- **Toast:**
  - 5 s and 8 s; Problem until closed; pause on hover and focus; restart with at least 3 s left; dedupe.
  - A new Result replaces a Result; a new Undo replaces an Undo; **the replaced Undo's `recovery` handle still works** (no way back is lost).
  - A Result and an Undo never hide a Problem; a second Problem queues and shows "1 of 2".
  - `toast.undo` without `recovery` does not compile; an unregistered `ref` throws in development.
  - ⌘Z: runs the Undo toast outside text fields and surfaces; does nothing, and is not default-prevented, with focus in a text field; does nothing with focus inside a `data-undo-owner` surface; does nothing when no Undo toast is showing.
  - No focus steal; roles; the Undo announcement ends "Press ⌘Z to undo."; reduced motion fades in place.
- **RecentlyRemoved:** newest first; Restore is busy, then puts the item back and says where; a discarded draft restores with its content; a restore never overwrites a newer draft; empty state.
- **FailedSubmission:**
  - Two failures render two items; the composer's content is never changed by a failure.
  - Move to the composer is disabled with its reason while `composerEmpty` is false, and does nothing if text arrived during the move.
  - `unconfirmed` and `failed` show different words; `saved` removes the error and leaves one item.
  - A late success after Try Again was pressed leaves one item. An edited retry passes `edited: true`.
  - Focus: no move on failure; after success, on the saved item only if focus was inside; after Discard, on the next item or the composer.
  - A reload keeps the item.
- **EmptyState:** each `kind` shows only the parts it may; `all-done` rejects an action.
- **ErrorState:** Try Again busy with a fresh budget; `placement="beside"` keeps the content's text, colour and focus, and requires `loadedAt`; a page error moves focus to its heading, a section error does not; the filter-change message names the earlier results.
- **InlineError:** the input is never cleared; live region; `aria-invalid`.
- **Every component** under reduced motion (`prefers-reduced-motion: reduce`), at 200 % text size and at 320 CSS px with no horizontal scroll (STA-8).
