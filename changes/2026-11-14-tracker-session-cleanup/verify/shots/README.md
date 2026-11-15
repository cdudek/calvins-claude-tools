# Render check frames (N1)

**What these are:** text frames of the Session page and Home at 120, 80, 54 and 40 columns and a 24-column dock. They are not terminal screenshots.

**How they were made:** the plugin test kit gives the drawn element tree, not cells. `tests/fixtures/frame.ts` lays that tree out (stacked columns, wrapping rows, word-wrapped text) and prints the lines. It models Ink's layout and is not the engine's own render.

**Scenes:** `session-offer-*` (after Clear, with the worktree offer and its ignored files), `session-confirm-*` (the Clear confirm with 7 open tasks), `session-error-*` (git refused the removal), `home-*` (unchanged by this change).

**What is asserted:** `tests/worktree.test.ts`, the `N1` tests: every button label whole on one line, no line wider than the window, rows within the bounds measured here.

**Rows used:**

| Scene | 120 | 80 | 54 | 40 | 24 |
|---|---|---|---|---|---|
| Session, offer | 15 | 15 | 19 | 24 | 37 |
| Session, confirm | 16 | 19 | 25 | 30 | 46 |
| Session, error | 11 | 11 | 14 | 17 | 26 |
| Home | 24 | 31 | 31 | 38 | 48 |
