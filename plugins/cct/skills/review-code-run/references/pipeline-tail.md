# Pipeline tail — validate, synthesize, report

Runs after a lane wrote `$STATE_DIR/findings.json`. Same for every mode and lane.

## 1. Validate every finding

```sh
bash "${CLAUDE_SKILL_DIR}/scripts/validate-prep.sh" "$STATE_DIR/findings.json"
```

For each entry in the queue, skip it if `$STATE_DIR/verdict-<id>.json` exists. Else spawn a validator per `validate-agent.md`. Run up to ~5 concurrent, heaviest first. Write each verdict to `$STATE_DIR/verdict-<id>.json` as it returns. Validate every finding. Never a subset. Never pause to ask.

Then:
```sh
bash "${CLAUDE_SKILL_DIR}/scripts/verdicts-collect.sh" "$STATE_DIR"
```
It writes `$STATE_DIR/verdicts.json` and prints three counts.

### Executable claims

A finding with `executable_claim: true` says what a **matcher** does — a `case` pattern, a glob, a regex. Test that before its validator runs. The orchestrator runs the probe. The validator never does.

Write all three inputs as files, with quoted heredocs. Nothing from a finding goes on a command line. `<revid>` is the part after `rev-` in `$STATE_DIR`.

```sh
cat > "$STATE_DIR/probe-<id>.kind" <<'PROBE_KIND_<id>_<revid>_EOF'
<probe_kind>
PROBE_KIND_<id>_<revid>_EOF
cat > "$STATE_DIR/probe-<id>.pattern" <<'PROBE_PATTERN_<id>_<revid>_EOF'
<probe_pattern>
PROBE_PATTERN_<id>_<revid>_EOF
cat > "$STATE_DIR/probe-<id>.input" <<'PROBE_INPUT_<id>_<revid>_EOF'
<probe_input>
PROBE_INPUT_<id>_<revid>_EOF
bash "${CLAUDE_SKILL_DIR}/scripts/probe-pattern.sh" \
  "$STATE_DIR/probe-<id>.kind" "$STATE_DIR/probe-<id>.pattern" "$STATE_DIR/probe-<id>.input"
```

Rules:
- Keep the single quotes on the delimiter. `<<EOF` without quotes expands `$(...)`.
- Keep `<revid>` in the delimiter. The values come from code the author of that code controls. A delimiter built from the small `id` alone is guessable: a comment line `PROBE_PATTERN_7_EOF` ends the heredoc early, and what follows it runs in your shell. `<revid>` is the hash of the revision that contains the text, so the text cannot simply name its own hash; a determined attacker can still grind a later commit toward a chosen 12-character prefix. The delimiter stops accidental and casual collisions. The skip rule below is the backstop for the rest.
- `probe_kind` gets a file too. The script checks it, but only after your shell has already parsed the command line.
- If a value contains a line equal to its delimiter, **skip the probe** for that finding. A probe is optional; guessing is not.
- **Probe twice.** Once with `probe_input`. Once with a control input that should give the opposite answer. Same answer both times → the probe is not measuring anything. Say so on the `Probe:` line.
- The probe **never runs the artifact under review.** A claim that needs the whole program to run is not an `executable_claim`. It stays `unverifiable` when reading cannot settle it.

Put the observed `- matched:` lines, or the `- reason:`, on the validator's `Probe:` line. A probe that contradicts the claim rejects it. A probe that failed or did not discriminate changes nothing.

## Nested vs top-level

You are **nested** if `Agent()` spawned this session. `review-code-runner` is always nested. Otherwise you are **top-level**.

Validation and every file on disk are the same in both cases. Only the report differs.

## 2. Synthesize (top-level only)

Follow `../../role-code-analysis/references/synthesize.md` with `findings.json`, `verdicts.json` and `ac-coverage.json` (when it exists). Nested runs skip this step — nothing downstream reads the prose.

## 3. Report

**Top-level.** Render per `report-sections.md`, findings per `finding-format.md`. Order: Verdict → Acceptance criteria → Summary header → Findings → Split decisions → Cross-File Patterns → Areas Warranting Closer Review → Demoted and rejected. End with the disclosure line: the AC result, the three counts from `verdicts-collect.sh`, then `$CODEX_STATUS` as `codex-lane.md` set it.

Acceptance criteria is the one section you render even when it is empty — with `$AC_MODE: none` it is a single line naming `$AC_REASON`. Every other section may be skipped when it has nothing in it.

**Nested.** One line per finding:
```
F<id> <file>:<line> <severity> <dimension> <verdict>
```
Then one line with the three counts, plus `$CODEX_STATUS` when a Codex pass ran, plus the AC result as `AC=<covered>/<total>` or `AC=none:<reason>`. No snippets, no sections, no appendix. Do not re-read `findings.json` to format it.

**Do not add a second bare control token.** `$CODEX_STATUS` goes inside the counts line, as text. Step 4's line must stay the last line.

## 4. Report the state dir

The last line of your output, alone, exactly:
```
STATE_DIR=<absolute path>
```
`review-fix-run` matches the last non-empty line against `^STATE_DIR=(.+)$`. Emit it even when `findings.json` is empty.
