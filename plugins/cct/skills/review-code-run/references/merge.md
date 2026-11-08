# Merge review sources

Makes `$STATE_DIR/findings.json` from every review source in `$STATE_DIR`. Used by all max lanes, and by a deep lane when Codex returned findings.

**Skip if `$STATE_DIR/findings.json` exists.**

## Input

```sh
bash "${CLAUDE_SKILL_DIR}/scripts/merge-prep.sh" "$STATE_DIR"
```

It prints one `-#-#- BEGIN/END DIMENSION REVIEW: <name> -#-#-` block per Claude reviewer, and one `-#-#- BEGIN/END CODEX FINDINGS -#-#-` block when Codex returned findings. The Codex block is already JSON with `source: "codex"`.

Work from this output only. Do not read code. Do not open the diff. Do not call tools.

## Rules

1. **Collapse only obvious duplicates.** Same defect, same symbol or contract, even across dimensions or across models. In doubt, keep them apart — a duplicate only costs one cheap validator. Never collapse on file or area alone.
2. **Drop nothing.** Every finding gets a validator. The validator decides.
3. **Assign `id`** as 1..N after sorting by (`file`, `line`, `dimension`). The fixed order means a resumed merge gives the same ids, so earlier `verdict-<id>.json` files still match.
4. **Take `dimension` from the block header.** Every Claude finding sits inside a `-#-#- BEGIN DIMENSION REVIEW: <name> -#-#-` block. That `<name>` is the axis, and it is the value you write — whatever the finding's own `dimension` field says. Strip any decoration the reviewer added: `full-spectrum (test-quality)` is `full-spectrum`. A collapse across two Claude blocks keeps the more specific of the two axis names.

   The header is generated, not written by a model: `merge-prep.sh` builds it from the `dim-<name>.json` filename, which the lane took from `dimensions-capped.json`. So it cannot drift, and the reviewer cannot get it wrong. Reviewers do reach for the wrong vocabulary — `bug`, `logic`, `clarity`, `conventions` and `testing` are **categories** from `role-review-vocabulary`, not axes — and those values reached `findings.json` before this rule existed.

   Two things this rule does **not** do. It does not clamp the name to the catalogue in `dimensions.md`: a dimension the selector discovered (`shell-quoting-exit-status`, `subprocess-lifecycle-management`) is a legitimate axis and its block header already carries it. And it does not touch the `CODEX FINDINGS` block, which has no axis — keep a Codex finding's own `dimension` and map it to the closest catalogue name.

## Fields

| Field | Value |
|---|---|
| `file`, `line`, `severity`, `confidence`, `evidence`, `body` | from the source finding |
| `dimension` | **from the enclosing block header**, not from the finding's own field — see below |
| `source` | `claude`, `codex`, or `both` — see below |
| `self_proving` | `true` only when the quoted evidence alone shows the defect |
| `failure_scenario` | carry through verbatim. Missing → `unstated`. Never invent one. |
| `reversibility` | carry through. When collapsing, take `entrenches` if **any** source said so. Missing → `unstated`. Never guess `cheap`; it waives the verdict floor. |
| `idiomatic_fix` | carry through when present; else omit |
| `executable_claim`, `probe_kind`, `probe_pattern`, `probe_input` | carry through together or not at all |
| `suppressed_reason` | carry through when present; else omit |
| `validation_effort` | 0-6 from the source. 6 = cross-file tracing, 3 = one neighbour read, 0 = self-proving. Do not change it. |

## Provenance — `source`

| Value | When |
|---|---|
| `claude` | from a `DIMENSION REVIEW` block only |
| `codex` | from the `CODEX FINDINGS` block only |
| `both` | a Claude finding and a Codex finding collapsed under rule 1 |

**`both` raises confidence: `confidence = min(100, max(claude_confidence, codex_confidence) + 15)`.** Two models that never saw each other agreed. Take the higher score, add 15, cap at 100.

This is free: the validator queue sorts by `validation_effort`, never by `confidence`. Keep `validation_effort` as it was.

`both` is evidence, not a verdict. The finding still gets its validator.

## Output

```json
{"findings":[{"id":N,"file":"...","line":"...","severity":"...","confidence":N,"dimension":"...","source":"claude|codex|both","self_proving":bool,"evidence":"...","body":"...","failure_scenario":"...","reversibility":"cheap|entrenches|unstated","validation_effort":N,"idiomatic_fix":"..."?,"executable_claim":bool?,"probe_kind":"..."?,"probe_pattern":"..."?,"probe_input":"..."?,"suppressed_reason":"style|out-of-scope"?}]}
```

Fields marked `?` are omitted when absent. Reply with the JSON only.
