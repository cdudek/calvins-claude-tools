---
description: Per-dimension agent-orchestrated review of a file set or directory (code-as-is) — select dimensions, one reviewer per dimension, merge, validate-all, synthesize
---

The user input is: $ARGUMENTS

Mode **files**, lane **max**. Set `LANE=max`, then compose the shared references:

1. **Mode** — follow `../references/mode-files.md`: validate the file list, read project rules, compute `$STATE_DIR`, write commentary-only `$STATE_DIR/INPUT.md` (if any).
2. **Lane** — follow `../references/lane-max.md`: select dimensions → one reviewer per dimension over the whole file set → merge → `$STATE_DIR/findings.json`.
3. **Tail** — follow `../references/pipeline-tail.md`: validate → synthesize → report (File Summary header).

There is no PR to post to — no posting step.
