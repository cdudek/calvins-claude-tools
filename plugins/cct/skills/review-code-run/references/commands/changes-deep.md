---
description: Deep review of local branch changes (committed-only) — single full-spectrum reviewer + per-finding validation, persisted to $STATE_DIR
---

The user input is: $ARGUMENTS

Mode **changes**, lane **deep**. Set `LANE=deep`, then compose the shared references:

1. **Mode** — follow `../references/mode-changes.md`: parse `[base_branch]`, enforce committed-only, compute `$STATE_DIR`, write `$STATE_DIR/changes.diff` (three-dot), resolve references → `$STATE_DIR/INPUT.md`.
2. **Lane** — follow `../references/lane-deep.md`: one full-spectrum reviewer → `$STATE_DIR/findings.json`.
3. **Tail** — follow `../references/pipeline-tail.md`: validate → synthesize → report (Change Summary header).

There is no PR to post to — no posting step.
