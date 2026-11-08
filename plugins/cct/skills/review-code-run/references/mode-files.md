# Mode: files

Collects the review surface for `files-deep` and `files-max`. Reviews the code as it is now. No diff, no git history, no ticket. `$ROOT` = the current dir. `$TARGET_BRANCH` = `none`.

`$ARGUMENTS` = one or more paths.

## 1. Check the paths

```sh
bash "${CLAUDE_SKILL_DIR}/scripts/files-exist.sh" <paths>
```
A `- missing:` row → report it and stop. No valid path left → show the usage line and stop.

Read `CLAUDE.md` and `agents.md` from the repo root if present. Read nothing else about history or tickets.

Show:
```
## File Review: {count} files
- {file} ({lines} lines)
```

## 2. State

Write `$FILES` — one path per line: every `- file:` row, plus every file under each `- dir:` row — to `$STATE_DIR`-independent scratch, e.g. `"${TMPDIR:-/tmp}/review-files-$$.txt"`. Then:
```sh
bash "${CLAUDE_SKILL_DIR}/scripts/state-dir.sh" files "$LANE" - <that file>
```
Read `$STATE_BASE` and `$STATE_DIR` from its output. Then copy the list to `$STATE_DIR/files.txt`.

If the user passed a note, write it verbatim to `$STATE_DIR/INPUT.md` under `## User commentary`. Else no `INPUT.md`.

## 3. No acceptance-criteria audit

```sh
bash "${CLAUDE_SKILL_DIR}/scripts/ac-gate.sh" "$STATE_DIR" --not-applicable
```

`$AC_MODE` = `none`, `$AC_REASON` = `not-applicable`. Files mode reviews code as it is, so there is no ticket to grade against and nothing anyone could add to make one appear. The flag keeps that distinct from a PR whose ticket is simply missing — the report words the two differently (`report-sections.md` → Acceptance criteria).

The lane gets the whole file list, no diff. `$EXTRA_TAGS` = "add `domain:` and `surface:` tags per `dimensions.md`".

## Report header

**File Summary**: files with line counts. No posting.
