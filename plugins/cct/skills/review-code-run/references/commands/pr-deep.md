---
description: Thorough worktree-based PR review — single full-spectrum reviewer + per-finding validation, persisted to $STATE_DIR
---

The user input is: $ARGUMENTS

Mode **pr**, lane **deep**. Set `LANE=deep`, then compose the shared references:

1. **Mode** — follow `../references/mode-pr.md`: parse `<pr_number>`, enter the worktree (or review in place), gather PR context + references, compute `$STATE_DIR`, write `$STATE_DIR/pr.diff`, resolve references → `$STATE_DIR/INPUT.md`.
2. **Lane** — follow `../references/lane-deep.md`: one full-spectrum reviewer → `$STATE_DIR/findings.json`.
3. **Tail** — follow `../references/pipeline-tail.md`: validate → synthesize → report (PR Summary header).
4. **Post** — follow `../references/mode-pr.md` → **Posting** (on user request only).
