# Lane: deep — one full-spectrum reviewer

Makes `$STATE_DIR/findings.json`. Used by `pr-deep`, `changes-deep`, `files-deep`.
The mode file already set `$STATE_DIR`, `$ROOT`, `$TARGET_BRANCH`, the surface (`$DIFF` or a file list), `$INPUT_MD` and `$EXTRA_TAGS`. Use them. Do not gather context again.

First run:
```sh
bash "${CLAUDE_SKILL_DIR}/scripts/state-codex-check.sh" "$STATE_DIR" "$CODEX"
```
It removes a cached merge that disagrees with `$CODEX` (`- reset: yes`). The script deletes the files itself; you read nothing from its output before the next line. The reviewer output on disk stays, so only the merge runs again.

**Then, if `$STATE_DIR/findings.json` exists, skip this file.** Go to `pipeline-tail.md`.

## 1. Review

Spawn **one** reviewer per `review-subagent.md`, with `AXIS=full-spectrum` and the brief from that file. Pass the whole surface, `$ROOT`, `$TARGET_BRANCH`, `$INPUT_MD`, `$EXTRA_TAGS`. Skip the spawn when `$STATE_DIR/dim-full-spectrum.json` exists.

In the **same message** — or alone, when the spawn was skipped — run the Codex pass. Follow `codex-lane.md`. Run it every time you reach this step. Its own gate returns at once when the pass is turned off or already done, and it is the only thing that sets `$CODEX_STATUS`.

In that same message, run the acceptance-criteria audit. Follow `ac-check.md`. Its own gate returns at once when `$AC_MODE` is not `ac` or `ac-coverage.json` already exists.

Never trim the surface for size. On a diff over 500 lines, say in the report that `max` covers more dimensions. Do not narrow the scan.

## 2. Write the reviewer output

Wait for the calls to return. `$CODEX_STATUS` must be set before you continue, and the AC audit must have settled — `ac-coverage.json` exists, or `$AC_MODE` is not `ac`.

Write the reviewer's output to `$STATE_DIR/dim-full-spectrum.json`, unless it exists:

```json
{"result": "<findings text>"}
```

Never write an empty file. An empty file blocks the merge on every later resume.

## 3. Merge

Skip if `$STATE_DIR/findings.json` exists.

Follow `merge.md`. Always — also when Codex is off, unavailable, failed, or found nothing. With one source it collapses nothing and stamps `source: "claude"` on every finding.

There is no second way to write `findings.json`. `merge.md` owns ids, collapse and `source`.
