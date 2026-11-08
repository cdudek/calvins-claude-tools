# review-code-run skill — tests & internals

## Manual smoke — `tests/dogfood-prompts/`

The `references/*.md` files are consulted instructions, so their *behavior* is
not unit-testable. `tests/dogfood-prompts/README.md` carries structural checks
(grep the file for its required keys/rows). Run them by hand after editing the
referenced file.

Their *contracts* are testable where a past bug proved they drift, or where a
new one crosses enough files to drift on its own. Four guards live in
`scripts/`, all auto-discovered by CI
(`.github/workflows/validate-plugins.yml` → the
`plugins/*/skills/*/scripts/test_*.py` glob):

- `test_review_pr_contracts.py` — an input a rule needs but no file supplies:
  `$TARGET_BRANCH` reaching the reviewer (the dead-code gate), `pr-quick`
  minting `side` before posting, and `gh pr diff` staying scoped to quick mode.
  Plus the posted-comment contract: the three posting exclusions (`nit`,
  `unverifiable`, demoted) checked **behaviourally** by running
  `posting-findings.sh` against a fixture, `finding-format.md` § Section C
  keeping the layout it owns, every composer and forwarder pointing at that one
  section, and `pr-quick` restating the exclusions it cannot inherit — it writes
  no `findings.json`, so the script that owns them never runs for it.
- `test_finding_id_contract.py` — two separate, opposite guarantees:
  (a) the `F<id>` finding-identity contract holds across every file in the
  script's `ID_CONTRACT_FILES` — `role-review-vocabulary/SKILL.md`,
  `references/finding-format.md`, `references/report-sections.md`,
  `role-code-analysis/references/synthesize.md`,
  `agents/review-fixset-triager.md`, `review-fix-run/SKILL.md`,
  `review-feedback-run/references/execution-tail.md` and
  `agents/review-feedback-runner.md` — so a revert to positional numbering fails
  the build; and (b) `references/validate-agent.md` keeps the **numeric** `#<id>`
  wire form and never adopts `F<id>`, because the validator echoes that id back
  as the number `verdicts-collect.sh` joins on. Do not merge the two lists —
  (b) is the inverse of (a), and the file list is asserted against the docs.
- `test_codex_contract.py` — the Codex co-review's producer/consumer seams, which
  span a JSON Schema, three shell scripts and eight prose files: the schema
  matching the canonical field set, `--sandbox read-only` surviving in
  `codex-review.sh`, `merge-prep.sh` reading `codex-findings.json`, the `$CODEX`
  gate keeping its three values with `auto` degrading and `on` stopping, and the
  nested tail never emitting a second bare control token after `STATE_DIR=`.
  Its **sanitize-chain** guards are deliberately behavioural — they run
  `codex-scan-secrets.sh` and `codex-review.sh` against fixture trees, because
  every exclusion in the scan is implicit (a pattern is excluded by being absent
  from the `find` expression), so only behaviour can pin it. A quiet failure here
  discloses a secret rather than losing a finding, which is why this is the one
  area where a presence assertion is not good enough.

- `test_review_quality_contract.py` — the review-quality rules and the
  executable-claim probe. Three of its guards are behavioural: the fix-set
  blocking floor (`fix-handoff.sh` against a fixture carrying every severity),
  the AC gate's five modes (`ac-gate.sh` against five `INPUT.md` fixtures), and
  the probe itself. The prose guards cover: `failure_scenario` staying required across producer,
  merge, validator and the Codex schema; `reversibility` staying a separate axis
  from `severity`; the report's verdict existing and being floored by
  `entrenches` at any severity; and the probe staying with the **orchestrator**
  while `review-finding-validator` keeps `tools: Read`; the acceptance-criteria floor
  living in both `report-sections.md` and `synthesize.md`; every `none` reason
  having its own disclosure line, because a silent skip is the one failure this
  feature cannot survive; and `dimension` coming from the merge block header
  rather than the reviewer's own field. Its probe guards run
  `probe-pattern.sh` for real, including a check that a command substitution in a
  pattern executes nothing.

All four were mutation-checked when written — `test_review_pr_contracts.py`, `test_finding_id_contract.py`, `test_codex_contract.py` and `test_review_quality_contract.py`: reverting each rule the guard covers
was confirmed to fail the suite. Keep that property when editing them — a
presence-only `assert "x" in text` passes on a partial revert.

## Command structure — modes × lanes × shared tail

The six commands are thin shells (`commands/<mode>-<lane>.md`) that set `LANE` and compose shared references along **two axes**:

- **3 mode references** (`references/mode-{pr,changes,files}.md`) — collect the review surface: worktree/root, context, references, the diff (or none), and `INPUT.md`. They set the **mode→lane handoff** (`$STATE_DIR`, `$ROOT`, the diff/file-list surface, `$INPUT_MD`, summary; pr also posting inputs + a `## Posting` tail). `$STATE_DIR` is named per `references/state-dir.md`.
- **2 lane references** (`references/lane-{deep,max}.md`) — run the review over that surface → `$STATE_DIR/findings.json`. Deep = one full-spectrum `review-code-reviewer`; max = `review-dimensions-selector` → one `review-code-reviewer` per dimension → merge. A Codex co-review adds a source to either lane. Both lanes always end in `merge.md` — with one source it collapses nothing and stamps `source: claude` — so exactly one path writes `findings.json`. (An earlier version let deep serialize its single reviewer by hand when Codex contributed nothing; that path minted no `id`s, and every `verdict-<id>.json` then collided on `verdict-null.json`.)
- **1 shared tail** (`references/pipeline-tail.md`) — `review-finding-validator` per finding → `verdicts.json` → synthesize → report. Identical for all six but for the summary header label and whether a `$DIFF` is present (files mode has none). The synthesize+report half is **top-level only**: a nested run (always, under `review-code-runner` / `review-fix-run`) skips it for a compact per-finding list. Validation and the on-disk artifacts are identical either way.
- **1 optional co-review reference** (`references/codex-lane.md`) — runs the OpenAI Codex CLI read-only over the same surface, concurrently with the Claude reviewers, and writes `$STATE_DIR/codex-findings.json`. Gated by `$CODEX` (`auto` / `on` / `off`, parsed in `SKILL.md` § Routing). Orthogonal to both axes: it attaches to either lane and every mode, adds no reviewer to the 15-cap, and changes nothing below merge.

So a command runs `mode-<mode>` → `lane-<lane>` (which launches `codex-lane` in the same message as its reviewers, when `$CODEX` is not `off`) → `pipeline-tail` → (pr only) `mode-pr` § Posting. All six spawn the same dedicated leaf agents — `review-dimensions-selector` (max only), `review-code-reviewer`, `review-finding-validator` — and persist the same artifacts to `$STATE_DIR`. They differ only in mode (data collection) and lane (axis breadth).

## Lanes

**Deep** (`pr-deep`, `changes-deep`, `files-deep`): one `review-code-reviewer` with the **full-spectrum axis** (sonnet, or opus when the review surface ≥ 120k tokens). No dimension selection. One `review-finding-validator` per finding (haiku).

**Max** (`pr-max`, `changes-max`, `files-max`): `review-dimensions-selector` picks axes, then one `review-code-reviewer` per dimension launches in a single parallel batch. Selector and reviewers run on **sonnet below a 120k-token surface, opus at/above it** (Opus's 1M window holds what Sonnet's 200k can't). Merge step inline (orchestrator reads `merge-prep.sh` output). One `review-finding-validator` per finding (haiku — reads only the cited file + neighbours, so it stays under 200k regardless of PR size). State checkpointed in `$STATE_DIR` — resumes across relaunches within the same revision.

The recall lever is review **breadth** (max's dimension fan-out); model tier is chosen for **capacity** — opus only when the surface won't fit Sonnet's 200k window — not for marginal per-reviewer quality.

## Nested-consumer contract — `$STATE_DIR`

**Every** mode (deep and max) writes the same structured artifacts into `$STATE_DIR` — the per-revision dir `$STATE_BASE/rev-<revid>` (keyed by mode+repo+target+revision; see `references/state-dir.md`) — and **reports that absolute path on the final output line** so a nesting caller can pick them up. A new commit / changed file set ⇒ a new `$STATE_DIR`, so checkpoint resume never serves stale artifacts:

- `INPUT.md` *(optional)* — human framing: resolved Linear ticket/AC + linked refs + any user commentary. Read by `review-dimensions-selector`, `review-code-reviewer`, and (in the fix loop) `review-feedback-run`.
- `findings.json` — `{"findings":[{id,file,line,severity,confidence,dimension,source,self_proving,evidence,body,failure_scenario,reversibility,validation_effort,idiomatic_fix?,executable_claim?,probe_kind?,probe_pattern?,probe_input?,suppressed_reason?}]}` (includes demoted findings carrying `suppressed_reason: style|out-of-scope`). `references/merge.md` owns this shape — keep the two in sync, since this restatement is what a nested consumer reads first.
- `verdicts.json` — `[{id,verdict:"confirmed"|"unverifiable"|"rejected",...}]` from the validate-all pass.
- `ac.json` — the acceptance-criteria gate, written by `scripts/ac-gate.sh` from `INPUT.md`: `{mode:"ac",source,criteria:[{id,text}]}`, or `{mode:"none",reason,detail?}` with `reason` one of `no-reference` / `unresolved` / `no-criteria` / `not-applicable` / `audit-failed`. Always present for `pr` and `changes` modes; `files` mode writes `not-applicable`.
- `ac-coverage.json` *(only when `ac.json` says `mode: ac` and the audit succeeded)* — `{ac:[{id,text,status:"covered"|"partial"|"missing"|"not-verifiable",evidence:[{file,line,quote}],note}]}`, one row per criterion, from the `review-criteria-auditor` agent. `evidence` is an **array**, and `quote` is the cited line copied character for character — `scripts/ac-verify-evidence.sh` opens each file and checks the text is there, which is the only reason a `covered` row is falsifiable at all. Absent means the audit did not run or failed — never that the criteria are met.
- `codex-findings.json` *(optional)* — the Codex co-review's own findings, in the **pre-identity** shape (no `id` — merge mints those): the canonical fields plus `source: "codex"`, written by `scripts/codex-review.sh` under `scripts/codex-findings-schema.json`. Absent when Codex was `off`, unavailable, or failed — including a failure anywhere in the sanitize chain. A pass that ran and found nothing writes the file **with an empty `findings` array**, because the lane treats its presence as the resume signal (`references/codex-lane.md` → Gate check 2); "no findings" and "no file" are different states. It is an **input to merge, not an output of the run** — a nested consumer reads `findings.json`, where the Codex findings already live with ids assigned.

Provenance is part of the contract: every finding in `findings.json` carries `source` (`claude` | `codex` | `both`), and `both` also carries a raised `confidence` (`references/merge.md` → Provenance). A Claude-only run stamps `claude` uniformly, so a consumer never has to branch on an absent field.

`review-fix-run` consumes this contract via its `review-fixset-triager` agent: `scripts/fix-handoff.sh <findings.json> <verdicts.json>` joins finding→verdict and buckets into `fix_now` / `recheck` / `discuss` / `drop`. The runner re-validates the `recheck` (unverifiable) bucket at higher effort, then writes `fix-set.json` into `$STATE_DIR` and merges DISCUSS items into `$STATE_BASE/discuss.json` (a cross-iteration accumulator one level up, so it outlives rev-dir pruning) for the fix stage. The human-readable report (confirmed top-level, unverifiable inline-flagged, demoted+rejected appendix) is for direct invocation; nested consumers read the JSON, not the prose.

## Codex co-review — why it is a source, not a pipeline

Codex enters as one more **source of findings** and stops there. It shares the surface, the reviewer rules and the dimension catalogue with the Claude reviewers, and its findings go through the same merge, the same per-finding validators, the same synthesis, the same posting and the same fix loop.

Two consequences worth keeping:

- **No cross-examination rounds.** `pipeline-tail.md` already spawns an independent `review-finding-validator` per finding, so a Codex claim is verified against the real code by a Claude agent (and vice versa). A rebuttal exchange between the two models would re-derive verdicts the validators already produce, at the cost of a second Codex call. Do not add one.
- **Independence is structural, not procedural.** The Codex pass launches in the same message as the Claude reviewers, so there is no point in the flow at which either could see the other's output. That is what makes `source: both` mean something — anchored agreement would prove nothing.

The `--codex` / `--no-codex` flags and the `auto` default live in `SKILL.md` § Routing; the degradation policy lives in `references/policies.md` → Codex co-review; the mechanics live in `references/codex-lane.md`.

## Executable claims — why the orchestrator probes

`pipeline-tail.md` once told the validator to "run the artifact against the exact claimed input". `review-finding-validator` has `tools: Read`, so that rule could not be followed by the agent it addressed — a rule nobody can execute is worse than a narrower one that holds.

The resolution narrowed the rule rather than widening a permission:

- **The orchestrator runs the probe**, through `scripts/probe-pattern.sh`, and passes the observed result to the validator on the `Probe:` line. It already holds `Bash`, and its Bash allowlist admits no ad-hoc commands — only `gh *`, `git *` and `bash */review-code-run/scripts/*` — which is why the probe is a script rather than an ad-hoc command.
- **`review-finding-validator` keeps `tools: Read`.** Its entire input is attacker-controllable text from the diff. Giving it a shell to satisfy a doc would trade a documentation gap for an execution risk.
- **The probe never runs the artifact under review.** Reproducing a claim about a repo script would mean executing code a reviewer just read as untrusted data. `probe-pattern.sh` evaluates self-contained matchers only — a `case` pattern, a glob, a regex. A claim needing the surrounding program is not an `executable_claim`, and `unverifiable` is the honest verdict.
- **Probe twice**, with a control input that should disagree. A probe that cannot report the opposite result is not measuring the matcher.

One non-obvious detail lives in the script: `|` is split before matching. In a real `case` arm the bar separates alternatives, but only when written literally in the source — arriving through a variable it degrades to an ordinary glob character, so an unsplit probe of `develop|main` answers "no match" for `main`. That is true of the probe and false of the code under review, which is the one outcome a probe must never produce.

## Staggered launch ramp — retired

`lane-max.md` used to launch reviewer 0 in the background, sleep 10 seconds, then launch the rest, so later reviewers could read reviewer 0's prompt-cache prefix. That was 830 words of instructions for a saving the text itself called best-effort ("a cost miss, never a failure", "the 10 is a heuristic"). It also forced two launch paths, because background completions never re-enter a nested session, and a wrong top-level/nested guess stranded the pipeline before merge. Every lane now uses one path: all reviewers in one message, synchronous, no `run_in_background`. The prompt-cache saving is forgone. If it is ever measured to matter, add it back as a script-driven step, not as prose.

## Confidence-threshold gate — retired

All modes validate **every** finding via Agent sub-agents (one per finding) — the independent validator verdict is the disposition: **do not re-add a confidence gate** (confidence is a weak correctness sorter — the `<50` band has confirmed *higher* than `50–69`). The old static 50/85 gate survives only as a documented escape hatch in `role-code-analysis/references/validate-findings.md` → "Calibration — superseded by validate-all".
