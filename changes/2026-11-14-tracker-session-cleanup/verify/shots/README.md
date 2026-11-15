# Render check frames (N1)

**What these are:** text frames of the Session page and Home at 120, 80, 54 and 40 columns and a 24-column dock. They are not terminal screenshots.

**How they were made:** the plugin test kit gives the drawn element tree, not cells. `tests/fixtures/frame.ts` lays that tree out (stacked columns, wrapping rows, word-wrapped text) and prints the lines. It models Ink's layout and is not the engine's own render.

**Scenes:** `session-offer-*` (after Clear, with the worktree offer and its ignored files), `session-confirm-*` (the Clear confirm with 7 open tasks), `session-error-*` (git refused the removal), `home-*` (unchanged by this change).

**What is asserted:** `tests/worktree.test.ts`, the `N1` tests: every button label whole on one line, no line wider than the window, rows within the bounds measured here.

**Looked for a real render, found none:** `claude plugin --help` lists configure, details, disable, enable, eval, init, install, list, marketplace, prune, restore-set-aside, tag, test, uninstall, update and validate, with no render, preview or snapshot. `claude plugin test` has no options. The test kit's `ui` handle has `drawn`, `find`, `findAll`, `press`, `resize` and the like: `drawn()` returns the element tree, and `resize` fails with "the drawing holds no Client". A real terminal screenshot needs an interactive `claude` run on real sessions, which this build does not do.

**What these frames cannot answer (for the owner at the gate):** dim contrast on a light and a dark theme (R2-22), whether the plain Buttons read as buttons and not text (R2-05), and the comparison with the owner's mockups. Also not answered: how many rows the real window has. The pane does not scroll.

**Rows used:**

| Scene | 120 | 80 | 54 | 40 | 24 |
|---|---|---|---|---|---|
| Session, offer | 15 | 15 | 19 | 24 | 37 |
| Session, confirm | 16 | 19 | 25 | 30 | 46 |
| Session, error | 11 | 11 | 14 | 17 | 26 |
| Home | 24 | 31 | 31 | 38 | 48 |
