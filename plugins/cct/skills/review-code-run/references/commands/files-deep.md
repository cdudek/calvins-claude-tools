---
description: Focused review of specific files (code-as-is) — single full-spectrum reviewer + per-finding validation, persisted to $STATE_DIR
---

The user input is: $ARGUMENTS

Mode **files**, lane **deep**. Set `LANE=deep`, then compose the shared references:

1. **Mode** — follow `../references/mode-files.md`: validate the file list, read project rules, compute `$STATE_DIR`, write commentary-only `$STATE_DIR/INPUT.md` (if any).
2. **Lane** — follow `../references/lane-deep.md`: one full-spectrum reviewer over the whole file set → `$STATE_DIR/findings.json`.
3. **Tail** — follow `../references/pipeline-tail.md`: validate → synthesize → report (File Summary header).

There is no PR to post to — no posting step.
