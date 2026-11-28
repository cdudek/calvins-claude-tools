# factory-status

A Claude Code mod that shows where the factory run in your repo stands, inside the session. It only reads: it runs its own bundled reader, `bin/factory-status.py`, with `python3 -I` and never writes anything. It never runs a script from the repo: a repo you open may be untrusted, so nothing in it is executed (the mod only checks that `.factory/` or `changes/` exists at the git root).

`bin/factory-status.py` and `bin/factory-board.py` are byte copies of the files of the same name in `plugins/factory/skills/run/scripts/`; a pytest in the factory plugin fails when they differ. After changing an original run `cp plugins/factory/skills/run/scripts/factory-status.py plugins/factory/skills/run/scripts/factory-board.py plugins/factory-status/bin/`.

## What it shows

- **Band:** one row above the prompt, only in a factory repo with a building or needs-you change: `factory  M2f (7/24) · gap fix building · gap 3/3 · 3h23m`. A needs-you text comes first in red (`needs you: <text>`). It updates at session start, at each turn end and every 20 seconds.
- **Buttons:** `[pane]` opens the pane, `[board]` opens the factory board in the browser, `[–]` hides the band (remembered between sessions).
- **Pane:** `/factory-status` opens a "Factory" pane with the milestones (id, state), the current milestone's tasks (id, state) and the needs-you text if the run waits on you. It says "No factory change in this repo." when there is none. It never opens unasked.

## Commands

- `/factory-status`: open the pane.
- `/factory-status web`: open the board at http://127.0.0.1:8765/. When nothing answers there it first runs `python3 -I bin/factory-board.py install`, which copies the board to `~/.factory/bin` and loads a launchd agent (macOS), then waits for the port. The browser opens with `open` (macOS) or `xdg-open`.
- `/factory-status band on|off`: show or hide the band.

If no git root at or above the session directory holds `.factory/` or `changes/`, the mod does nothing. The reader still calls `git` and `gh` in that repo, so a repo's git config applies.

## Install

```bash
claude plugin marketplace add cdudek/calvins-claude-tools
claude plugin install factory-status@cct
```

Restart Claude Code afterwards so the mod loads. In a terminal session the same works as `/plugin install factory-status@cct`.

## Needs

- **A factory repo:** `changes/<slug>/plan.md` files written by the factory plugin.
- **python3** on your PATH.
- Early access: the mod API is not stable and this build targets Claude Code 2.1.327.
