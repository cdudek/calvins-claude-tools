# factory-status

A Claude Code mod that shows where the factory run in your repo stands, inside the session. It only reads: it runs the repo's `.factory/factory-status.py` and never writes anything.

## What it shows

- **Status line:** one line under the prompt, such as `M3a (4/20) · T2/6 building · gap 0/3 · 38m`. It updates at session start, at each turn end and every 20 seconds, and disappears when no run is active.
- **Pane:** `/factory-status` opens a "Factory" pane with the milestones (id, state), the current milestone's tasks (id, state) and the needs-you text if the run waits on you. It never opens unasked.

If the repo has no `.factory/factory-status.py`, the mod does nothing.

## Install

```bash
claude plugin marketplace add cdudek/calvins-claude-tools
claude plugin install factory-status@cct
```

Restart Claude Code afterwards so the mod loads. In a terminal session the same works as `/plugin install factory-status@cct`.

## Needs

- **factory 0.8.0 or later:** it copies `.factory/factory-status.py` into each repo.
- **python3** on your PATH.
- Early access: the mod API is not stable and this build targets Claude Code 2.1.327.
