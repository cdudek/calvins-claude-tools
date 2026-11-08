# Lane: max — one reviewer per dimension

Makes `$STATE_DIR/findings.json`. Used by `pr-max`, `changes-max`, `files-max`.
The mode file already set `$STATE_DIR`, `$ROOT`, `$TARGET_BRANCH`, the surface (`$DIFF` or a file list), `$INPUT_MD` and `$EXTRA_TAGS`. Use them. Do not gather context again.

First run:
```sh
bash "${CLAUDE_SKILL_DIR}/scripts/state-codex-check.sh" "$STATE_DIR" "$CODEX"
```
It removes a cached merge that disagrees with `$CODEX` (`- reset: yes`). The script deletes the files itself; you read nothing from its output before the next line. The reviewer output on disk stays, so only the merge runs again.

**Then, if `$STATE_DIR/findings.json` exists, skip this file.** Go to `pipeline-tail.md`.

## 1. Select dimensions

Skip if `$STATE_DIR/dimensions-capped.json` exists.

Follow `select-agent.md`. It writes `dimensions.json` and `dimensions-capped.json`.

## 2. Review

Take the dimensions from `dimensions-capped.json` in order. Skip any that already has `$STATE_DIR/dim-<name>.json`.

Launch every remaining reviewer **in one message**, as parallel `Agent()` calls, **without** `run_in_background`. Follow `review-subagent.md` for each one:

| Field | Value |
|---|---|
| `AXIS` | the dimension `name` |
| `AXIS_BRIEF` | the dimension `description` |
| Surface | the whole `$DIFF`, or the whole file list |
| Also pass | `$ROOT`, `$TARGET_BRANCH`, `$INPUT_MD`, `$EXTRA_TAGS` |

In the **same message**, run the Codex pass. Follow `codex-lane.md`. It is one `Bash` call, not one per dimension.

In the **same message** again, run the acceptance-criteria audit. Follow `ac-check.md`. Its own gate returns at once when `$AC_MODE` is not `ac` or `ac-coverage.json` already exists. One agent per review, never one per dimension.

The calls return together. For each reviewer, write its output to `$STATE_DIR/dim-<name>.json`:

```json
{"result": "<findings text>"}
```

Do not write a `dim-*.json` for Codex. `merge-prep.sh` reads `codex-findings.json` itself.

Never write an empty `dim-<name>.json`. An empty file blocks that dimension on every later resume.

Go to step 3 only when **all three** are true:
- every dimension in `dimensions-capped.json` has a `dim-<name>.json`;
- `$CODEX_STATUS` is set (`codex-lane.md` → Collect);
- the AC audit settled — `ac-coverage.json` exists, or `$AC_MODE` is not `ac` (`ac-check.md` sets it to `none` when the audit failed).

## 3. Merge

Skip if `$STATE_DIR/findings.json` exists.

Follow `merge.md`. Run `merge-prep.sh`, merge its output inline, write `findings.json`.

## Notes

- A reviewer that fails writes no `dim-*.json`. Re-run the command; only that reviewer relaunches.
- The harness may queue reviewers past its concurrency limit. That costs time, not results.
- Do not pause to ask about scope or cost. See `policies.md` → Autonomy.
