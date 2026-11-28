# factory-status

A Claude Code mod that shows where the factory run in your repo stands, inside the session. It only reads: it runs its own bundled reader, `bin/factory-status.py`, with `python3 -I` and never writes anything. It never runs a script from the repo: a repo you open may be untrusted, so nothing in it is executed (the mod only checks that `.factory/` or `changes/` exists at the git root).

`bin/factory-status.py` is a byte copy of `plugins/factory/skills/run/scripts/factory-status.py`; a pytest in the factory plugin fails when they differ. After changing the original run `cp plugins/factory/skills/run/scripts/factory-status.py plugins/factory-status/bin/`.

## What it shows

- **Status line:** one line under the prompt, such as `M3a (4/20) · T2/6 building · gap 0/3 · 38m`. It updates at session start, at each turn end and every 20 seconds, and disappears when no run is active.
- **Pane:** `/factory-status` opens a "Factory" pane with the milestones (id, state), the current milestone's tasks (id, state) and the needs-you text if the run waits on you. It never opens unasked.

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
