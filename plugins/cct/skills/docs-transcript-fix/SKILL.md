---
name: docs-transcript-fix
description: "Corrects speech-to-text transcription errors using dictionary rules then AI analysis, and keeps a personal correction database that grows with each fix. Use when the user says 'fix this transcript', 'clean up meeting notes', 'fix transcription errors', 'ASR cleanup'. Skip for: auditing documentation (use cct:docs-audit)."
allowed-tools: "Read Grep Glob Edit Write Bash(uv *) Bash(sqlite3 *) Bash(diff *) Bash(sed *)"
user_invocable: true
metadata:
  version: 1.0.0
  author: daymade
---

# Transcript Fixer

Two-phase correction pipeline: deterministic dictionary rules (instant, free) followed by AI-powered error detection. Corrections accumulate in `~/.transcript-fixer/corrections.db`, improving accuracy over time.

## Prerequisites

| Dependency | Required | How to obtain |
|------------|----------|---------------|
| `uv` | Yes | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |

All scripts use PEP 723 inline metadata — `uv run` auto-installs dependencies.

## Quick Start

```bash
# First time: Initialize database
uv run scripts/fix_transcription.py --init

# Single file
uv run scripts/fix_transcription.py --input meeting.md --stage 1

# Batch: multiple files in parallel
for f in /path/to/*.txt; do
  uv run scripts/fix_transcription.py --input "$f" --stage 1
done
```

## Core Workflow

1. **Initialize** (once): `uv run scripts/fix_transcription.py --init`
2. **Add domain corrections**: `--add "wrong" "correct" --domain <domain>`
3. **Phase 1 — Dictionary**: `--input file.md --stage 1` (instant, free)
4. **Phase 2 — AI Correction**: Claude reads output and fixes errors natively
5. **Save stable patterns**: `--add "wrong" "correct"` after each session

After Stage 1, Claude reads the output and fixes remaining ASR errors:
1. Read **entire** transcript before proposing corrections
2. Identify ASR errors — compile corrections across files
3. Apply fixes with sed in batch, verify each with diff
4. Finalize: rename `_stage1.md` → `.md`, delete original `.txt`
5. Save stable patterns to dictionary for future reuse

## Dictionary Addition After Fixing

| Pattern type | Example | Action |
|-------------|---------|--------|
| Non-word → correct term | cloucode → Claude Code | Add |
| Person/company name error | Getsentry → Sentry | Add |
| Common word → context word |争 → 蒸 | Skip (false positive risk) |

## Utility Scripts

- `fix_transcription.py` — Core CLI (dictionary, add, audit, learning)
- `fix_transcript_timestamps.py` — Timestamp normalization
- `generate_word_diff.py` — Word-level diff HTML
- `split_transcript_sections.py` — Split by marker phrases

## References

See @references/ for detailed guides:
- `false_positive_guide.md` — Read before adding rules
- `iteration_workflow.md` — Complete session checklist
- `quick_reference.md` — CLI reference
- `troubleshooting.md` — Common issues

## Sources

| Origin | Author | License |
|--------|--------|---------|
| [daymade/claude-code-skills](https://github.com/daymade/claude-code-skills) — `transcript-fixer` | daymade | MIT |
