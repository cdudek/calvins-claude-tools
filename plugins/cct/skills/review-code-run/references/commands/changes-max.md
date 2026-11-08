---
description: Per-dimension agent-orchestrated review of local branch changes (committed-only) — select dimensions, one reviewer per dimension, merge, validate-all, synthesize
---

The user input is: $ARGUMENTS

Mode **changes**, lane **max**. Set `LANE=max`, then compose the shared references:

1. **Mode** — follow `../references/mode-changes.md`: parse `[base_branch]`, enforce committed-only, compute `$STATE_DIR`, write `$STATE_DIR/changes.diff` (three-dot), resolve references → `$STATE_DIR/INPUT.md`.
2. **Lane** — follow `../references/lane-max.md`: select dimensions → one reviewer per dimension → merge → `$STATE_DIR/findings.json`.
3. **Tail** — follow `../references/pipeline-tail.md`: validate → synthesize → report (Change Summary header).

There is no PR to post to — no posting step.
