---
description: Per-dimension agent-orchestrated PR review — select dimensions, one reviewer per dimension, merge, validate-all, synthesize, then optional posting
---

The user input is: $ARGUMENTS

Mode **pr**, lane **max**. Set `LANE=max`, then compose the shared references:

1. **Mode** — follow `../references/mode-pr.md`: parse `<pr_number>`, enter the worktree (or review in place), gather PR context + references, compute `$STATE_DIR`, write `$STATE_DIR/pr.diff`, resolve references → `$STATE_DIR/INPUT.md`.
2. **Lane** — follow `../references/lane-max.md`: select dimensions → one reviewer per dimension → merge → `$STATE_DIR/findings.json`.
3. **Tail** — follow `../references/pipeline-tail.md`: validate → synthesize → report (PR Summary header).
4. **Post** — follow `../references/mode-pr.md` → **Posting** (on user request only).
