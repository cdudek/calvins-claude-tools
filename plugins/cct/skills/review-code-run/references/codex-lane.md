# Codex co-review

Runs one read-only Codex pass over the same surface the Claude reviewers get. Writes `$STATE_DIR/codex-findings.json`. Both lanes call this. `merge.md` folds the result in.

Codex is a second **source of findings**, not a second pipeline. Nothing below merge changes. There is no cross-examination round: `pipeline-tail.md` already validates every finding with an independent agent.

## 1. Gate

`$CODEX` comes from `SKILL.md` → Routing: `auto`, `on`, or `off`. Every mode except `pr-quick` runs this file. Check in this order:

1. **Turned off?** `$CODEX` is `off` → set `$CODEX_STATUS=off`. Stop here.
   This comes first. A revision reviewed earlier with `auto` may hold a `codex-findings.json`; `--no-codex` must not reuse it. The lane already ran `state-codex-check.sh`, which removed a merged `findings.json` that held Codex findings, so the merge runs again Claude-only.
2. **Already done?** `$STATE_DIR/codex-findings.json` exists → this revision had its pass. Set `$CODEX_STATUS=ok (<N> findings)` from its `findings` length. Go to merge. Skip the preflight.
3. **Usable?**
   ```sh
   bash "${CLAUDE_SKILL_DIR}/scripts/codex-available.sh"
   ```

Route on `- available:`:

| `$CODEX` | `available: yes` | `available: no` |
|---|---|---|
| `auto` | run the pass | degrade: set `$CODEX_STATUS=unavailable: <reason>`, continue Claude-only. Never ask the user. |
| `on` | run the pass | stop; report the `- reason:` as given. It has the fix command. |

Degradation is silent-but-disclosed: a missing CLI has one fix, so it is not a decision for the user.

**There is no secrets gate.** Secret-shaped files are withheld from Codex, not used to refuse the pass. `codex-review.sh` does that (below). `policies.md` → Codex co-review says what this does and does not protect.

## 2. Surface

| Mode | `<kind>` | `<surface path>` |
|---|---|---|
| pr, changes | `diff` | `$DIFF` |
| files | `files` | `$STATE_DIR/files.txt` — the `$FILES` list, one path per line |

## 3. Run

```sh
bash "${CLAUDE_SKILL_DIR}/scripts/codex-review.sh" \
  "$ROOT" "<kind>" "<surface path>" "$TARGET_BRANCH" "${INPUT_MD:--}" \
  "$STATE_DIR/codex-findings.json"
```

- Run it in the **same message** as the Claude reviewers, as a plain synchronous `Bash` call. Never `run_in_background`.
- Give the call a long timeout — up to the harness maximum. A large diff takes minutes.
- Pass `$TARGET_BRANCH` as-is. Pass `-` when there is no `INPUT.md`.

The script never hands `$ROOT` to Codex. It scans for secret-shaped file names and for every symlink, copies the tree without them, re-scans the copy, removes the sections of secret-shaped files from the diff, and runs Codex on the copy. Any failure in that chain → `status: failed`, no Codex call. The script header has the details.

## 4. Collect

| `- status:` | Do |
|---|---|
| `ok` | `$CODEX_STATUS=ok (<N> findings)` from `- findings:`. Append `; <M> files withheld` when `- withheld:` is above 0, and `; <K> diff sections withheld` when `- diff_withheld:` is above 0. |
| `failed` | `$CODEX_STATUS=failed: <reason>`. `$CODEX` is `on` → **stop** and report the reason: the user required Codex, and a Claude-only result is not what they asked for. `$CODEX` is `auto` → continue Claude-only. Do not retry in this run. |

Do not read `codex-findings.json` into context. `merge-prep.sh` does that.

## 5. Disclose

`pipeline-tail.md` prints `$CODEX_STATUS` in the report. A reader must see whether one model or two reviewed the code.
