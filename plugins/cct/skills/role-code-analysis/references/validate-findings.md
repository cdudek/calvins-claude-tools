# Validate Findings

Each finding must be independently verified before presenting to the user.

## Principle

The verifier receives only the claim and the code location — not the original reasoning that produced the finding. This prevents confirmation bias. The verifier reads the code independently and returns: the finding's `id` (echoed verbatim), confirmed / rejected, confidence (0-100), brief justification. The echoed `id` gives the orchestrator deterministic `finding → verdict` linkage; the verifier is **not** told the finding's generation confidence, so the linkage leaks nothing that would bias it.

## Key rule

Use a different prompt frame for validation than for generation. Research shows that asking the same model to justify its own finding increases false positives. Reframe the question: instead of "is this finding correct?" ask "does this code have the claimed problem?"

## Proof-first pre-check

Every finding carries an `evidence:` field — a verbatim quote of the code at its `file:line` that proves the claim (if you cannot quote code that literally shows the problem, it is not a finding). The validator's **first** step is cheap and mechanical: re-read the cited `file:line` and confirm the quoted code is actually there. If the quote is absent or materially differs from the source → **reject immediately** (the finding was not grounded; no further reasoning needed). Only when the quote checks out does the validator assess whether that code has the claimed problem. This makes most rejections cost a single read instead of a full re-derivation.

A finding's evidence is **self-proving** when the quoted code, read on its own, demonstrates the problem with no further inference (e.g. a literal SQL string interpolating `params[...]`; a method signature whose caller passes the wrong arity). It is **not** self-proving when confirming the issue still requires tracing data flow, checking a value at runtime, or reading other files.

## Default approach: Subagent per finding

Launch a separate `Agent` for each finding. The subagent sees only the claim and the code location — no other findings, no original reasoning. This provides the strongest independence guarantee and prevents findings from contaminating each other's validation.

Research (Chain-of-Verification, Meta AI) confirms that fully factored verification — where each claim is verified independently — reduces hallucinations by 50-70% compared to joint/batch approaches.

**Exception:** Inline validation is acceptable when the agent is already isolated on a single finding's code context (e.g., during per-item investigation in review-feedback-run). Must still use a different prompt frame.

## Verification code

Any code written to verify a finding must follow the anti-theater rules (global rule `anti-theater.md`). Prove the check can detect failure before trusting it to confirm success.

## Executable claims must be reproduced, not estimated

When a finding asserts the **runtime behaviour of a matcher** — a bash `case`/glob pattern, a `settings.json` permission pattern, a regex — reading it is not enough. It is a fact, and facts get observed.

**Who runs the probe.** Not the validator, and not the reviewer: both are read-only agents whose whole input is attacker-controllable text from the diff. The **orchestrator** runs it, through `../../review-code-run/scripts/probe-pattern.sh`, and passes the observed result down (`../../review-code-run/references/pipeline-tail.md` → Executable claims). A reviewer marks the finding `executable_claim: true` and supplies `probe_kind` / `probe_pattern` / `probe_input`; it never executes anything itself.

**What is in scope.** Self-contained matchers only, evaluated in isolation. A claim about what a whole script does is **out of scope**: reproducing it would mean running code that was just read as untrusted data, which is arbitrary execution rather than a probe. Such a claim stays a reasoned one, and `unverifiable` is the honest verdict when tracing cannot settle it. Do not instruct any agent here to "run the artifact" — none of them has, or should have, the tools.

**Prove the probe discriminates** (anti-theater). Probe **twice**: once with the claimed input, once with a control input that should produce the opposite result. If both come out the same, the probe is not measuring what you think and its outcome means nothing.

**Disposition.** An observed result that contradicts the claim **drops the finding** — a probe-falsified claim is wrong, and shipping it at any severity erodes trust. A probe that could not run leaves the claim exactly where it was. If the probe exposes a *different* real defect, raise that as its own finding with its own claim and evidence.

Example — a finding claims the allowlist pattern `Bash(bash */review-code-run/scripts/*)` fails to match a nested script path:

```bash
# every input is a FILE, the kind included — nothing from a finding reaches a command line
$ cat kind.txt; cat pattern.txt
glob
Bash(bash */review-code-run/scripts/*)
# claimed input
$ probe-pattern.sh kind.txt pattern.txt claimed-input.txt   # input: Bash(bash /x/review-code-run/scripts/a.sh)
- matched: yes
# control input — should NOT match, proving the probe discriminates
$ probe-pattern.sh kind.txt pattern.txt control-input.txt   # input: Bash(rm -rf /)
- matched: no
```

The claim said "fails to match"; the probe observed a match, and the control confirms the probe can also report a non-match. The finding is dropped.


## Confidence thresholds

- **90-100**: Verified against code, certain
- **70-89**: High confidence, verified pattern
- **50-69**: Likely issue, needs human confirmation
- **Below 50**: Low confidence — still validated like every other band (all modes validate every finding; see dispatch policy below). Confidence is a weak correctness signal (see the evidence under "Dispatch policy"), so a band is a render hint, never a reliability verdict.

**Probed matcher claims are binary.** A finding asserting the runtime behaviour of a **matcher** — one a probe can settle, see "Executable claims must be reproduced, not estimated" — may not ship in the 50–89 "likely" band on the strength of reading alone: either it was reproduced (≥ 90) or it is dropped. The "needs human confirmation" band is for judgement calls (design, risk, intent), not for facts a probe settles in seconds.

This does **not** extend to a claim about what a whole script or program does at runtime. That is out of probing scope on purpose — reproducing it would mean executing code read as untrusted data — so it is a reasoned claim like any other, and `unverifiable` is its honest verdict when tracing cannot settle it. Do not drop such a finding for want of a probe that must not exist.

## Dispatch policy

**Every mode that validates now validates *every* finding** — gating on the independent verdict, never on a confidence threshold. Skipping by confidence is unsafe: the would-be-skipped bands confirm at rates that don't track confidence (the `<50` band can confirm *higher* than the `50-69` band — a non-monotonic inversion), reproducing the consensus that LLM self-reported confidence is a poor predictor of code correctness ([Spiess et al.](https://arxiv.org/pdf/2402.02047), [Yang et al.](https://arxiv.org/pdf/2412.14737)).

### Agent-orchestrated `max` pipeline
`files-max` / `pr-max` / `changes-max` validate all findings via Agent sub-agents per `review-code-run/references/validate-agent.md` (same as deep modes): one Agent(model=haiku) per finding → keep confirmed, drop rejected, route confirmed `suppressed_reason:` findings to the demoted appendix (see `synthesize.md`).

### Deep modes — Agent sub-agents
`pr-deep` / `changes-deep` / `files-deep` validate all findings via Agent sub-agents per `review-code-run/references/validate-agent.md` (each command file's Validate step wires it): one Agent(model=haiku) per finding, proof-first + drill cap, same independence rules → keep confirmed, drop rejected. No confidence gate, no unvalidated band.

(`pr-quick` has no validate step — it lists findings directly.)

**Model & cost.** Validators run on **haiku**. Each validator reads only the cited file (and at most one neighbour for high-effort findings) — targeted reads rather than a full code bundle, so cost scales with finding count and cited-file size, not the full review surface.

<details><summary>Superseded: the confidence gate (old cost compromise)</summary>

All modes formerly gated by confidence to bound cost: `< 50` → unvalidated trailing block; `≥ 85` ∧ severity ∈ {suggestion, nit} ∧ self-proving evidence → bypass tagged `[unvalidated-high-conf]`; otherwise validate. Superseded by validate-all via Agent sub-agents. Reinstate only if validating-all on a large standalone run proves too costly under a budget cap.
</details>

## PATTERN finding shape

The meta/collapse step may emit a collapsed multi-location PATTERN finding: one claim with several `file:line` references. Validators receive **one PATTERN finding = one validator subagent**, not N. The validator confirms the *claim* holds at each cited location, returning a single confirmed/rejected verdict. If some locations don't match, it returns `partial_reject: [<locations>]` so `synthesize.md` can prune the cited list while keeping the finding.

## Calibration — superseded by validate-all

All modes validate **every** finding, so every confidence band already carries an independent verdict — there is no threshold left to tune. **The verdict is the disposition.** Do not rebuild offline confidence-recalibration apparatus or per-run threshold tuning — there is no gate left to calibrate, and the evidence under "Dispatch policy" shows generation confidence is too weak a signal to gate on.
