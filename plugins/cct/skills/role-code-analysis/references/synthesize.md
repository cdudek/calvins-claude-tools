# Synthesize

After findings are validated, assemble them into a coherent report.

## Steps

1. **Group by code area** — group findings by function or tightly coupled code block (~50-100 LOC scope).
2. **Smoke signal check** — if 3+ rejected/low-confidence (<80) findings from different categories point at the same area, escalate as "area of concern" at confidence 70
3. **Drop** isolated rejected findings that didn't form a smoke-signal cluster. Both the deep and agent-orchestrated `max` pipelines validate every finding, so disposition is by validator verdict — keep confirmed (top-level), drop rejected, route confirmed `suppressed_reason:` findings to the demoted appendix. There is no unvalidated block.
4. **Resolve contradictions** — if two confirmed findings contradict, re-read the code to determine the winner. **Evidence decides — never authority, and never a split of the difference.** This holds whichever source raised each side: do not resolve a contradiction by preferring the more confident wording, the higher `confidence` score, or a particular model. If the code does not settle it, keep both and say plainly that it is unresolved.
5. **Deduplicate** — collapse near-duplicate confirmed findings using semantic similarity, not string matching. Preserve `source` when you collapse: two findings that merge across the Claude/Codex boundary become `source: both` on the same terms as `../../review-code-run/references/merge.md` → Provenance. Do not raise `confidence` again here — merge already applied the agreement bonus, and applying it twice would inflate the score.
6. **Group co-dependent findings** — findings that must be fixed together should be presented together
7. **Rendering (validate-all)** — both the deep and agent-orchestrated `max` pipelines validate every finding (`validate-findings.md` → Dispatch policy). Render confirmed findings top-level; include unverifiable findings inline (flagged); exclude rejected from synthesis. A confirmed or unverifiable finding whose validator returned `fix_valid: false` — the bug is real but the proposed fix is unsound — still renders top-level, with **⚠ fix needs revision** appended after its suggested fix. Confirmed or unverifiable findings carrying `suppressed_reason: style | out-of-scope` (demote-don't-delete) render in a trailing **"Demoted and rejected findings"** section. Rejected findings (verdict=rejected, no suppressed_reason) also render in that trailing section. **Unverifiable inline flagging**: when rendering an unverifiable finding in the main list, add `(?)` suffix to the severity emoji and `(unverifiable)` suffix to the category: `🟠(?) **[correctness](unverifiable)** ...`
8. **Final ranking** — order by severity; smoke-signal findings go at the end as "Areas warranting closer review". Re-ordering, grouping and appendix-splitting are **presentation only**: every finding keeps the `F<id>` of its persisted `id` in every section it appears in (`../../role-review-vocabulary/SKILL.md` → Finding Format). Never number findings by position.
9. **Derive the verdict** — apply `../../review-code-run/references/report-sections.md` → Verdict. Read **two** inputs, not one.
   - The **confirmed** findings: any at `critical`/`warning`, or any at any severity with `reversibility: entrenches`, floors the verdict at `fix-first`.
   - `$STATE_DIR/ac-coverage.json`, when it exists: any criterion at `missing` or `partial` floors the verdict at `fix-first` too. A change that does not do what the ticket asked is not ready, however clean its code is. `not-verifiable` never floors it. An absent file floors it only when `$AC_REASON` is `audit-failed` — the grading could not be trusted, and that state is reachable from the ticket text, so passing it through would make sabotaging the audit as good as passing it. The other four `none` reasons say there was nothing to grade, and never floor.

   A design-level cluster or a smoke-signal area over the change's core makes it `rework`; otherwise `ship`. State what forced the floor — a finding by `F<id>`, a criterion by `AC-<n>` — so the verdict is auditable rather than asserted. Unverifiable and demoted findings never block; say so when they are the only thing left.
10. **Suppression disclosure** — on the final summary line, state the acceptance-criteria result first (`AC 2/3 covered`, or `AC not checked — <reason>`), then how many findings were demoted (validator-confirmed `suppressed_reason:`), how many were unverifiable, and how many were rejected, broken down when available (e.g. "34 confirmed, 5 unverifiable, 9 rejected — 3 demoted style, 2 out-of-scope"). Silent truncation reads as "nothing there"; disclose the counts. On a Codex co-review, the caller also appends the co-review state to this line (`../../review-code-run/references/pipeline-tail.md` → step 3).

## Demoted and rejected section (trailing appendix)

Render after "Areas warranting closer review". Use a single table for both demoted (confirmed/unverifiable with `suppressed_reason`) and rejected (verdict=rejected) findings:

```
## Demoted and rejected findings

| ID | Location | Marker | Title | Reason |
|----|----------|--------|-------|--------|
| F12 | `app/x.rb:31` | (rejected) | N+1 query in index action | Query is already batched via dataloader on line 15 |
| F18 | `app/y.rb:8` | (style) | Inconsistent variable naming | Purely stylistic, no correctness impact |
| F22 | `lib/cache.rb:44` | (out-of-scope) | Refactor cache module | Code not touched by this change |
```

- **ID column**: the finding's persisted `id` as `F<id>` — the same identifier the main list uses. This appendix is a filter over the one findings list, never a separate numbering.
- **Location column**: `file:line`, so a row stays reconcilable independently of the id scheme
- **Marker column**: `(rejected)` for verdict=rejected; `(style)` or `(out-of-scope)` for demoted findings
- **Cross-model exception**: a rejected finding whose `source` is `codex` does **not** belong in this appendix — it renders in the report's **Split decisions** section instead (`../../review-code-run/references/report-sections.md`), because a cross-model disagreement is information the reader wants even when the claim did not survive. A rejected `source: claude` finding is a plain rejection and stays here — **unless** a rejected `source: codex` finding shares its exact `file:line`; that co-located pair is `report-sections.md`'s second Split-decisions shape (two models converging on a location while disagreeing on the defect), so both findings render there instead of here.
- **Reason column**: validator's `justification` field (for all rows), trimmed to ≤100 chars
- Omit this section entirely if no findings are demoted or rejected

## PATTERN collapsing

Findings marked as PATTERN (from generalize-sweep) should be collapsed into a single entry listing all affected locations, not presented as N separate findings.
