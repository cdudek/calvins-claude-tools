---
name: role-review-vocabulary
description: "Shared vocabulary for code review — severity levels, categories, confidence thresholds, finding format, action verbs, and triage rules. Not a slash command — auto-installed as a dependency."
user_invocable: false
metadata:
  version: 1.0.0
  author: mpapis
---

# Role: Review Vocabulary

Shared vocabulary for code review and feedback workflows. Provides canonical definitions for severity levels, categories, finding format, action verbs, and triage classification rules.

## Severity Levels

| Emoji | Severity | Description |
|-------|----------|-------------|
| 🔴 | **Critical** | Security holes, data loss risks, broken functionality |
| 🟠 | **Warning** | Bugs, logic errors, missing edge cases |
| 🟡 | **Suggestion** | Performance, maintainability, better approaches |
| 🔵 | **Nit** | Style, naming, minor improvements |

## Finding Format

```
<ref>. <emoji> **[category]** `file_path:line` — description
```

**`<ref>` is an identity, not a position.** When the finding comes from a persisted findings file — `review-code-run`'s `$STATE_DIR/findings.json` and everything derived from it (`verdicts.json`, `fix-set.json`, `discuss.json`) — `<ref>` is that finding's `id` field, rendered `F<id>`. Print it unchanged at every stage, in every section, and in every bucket listing, however the list is re-ordered, filtered, split or merged: sorting by severity, grouping by file and bucketing by disposition must **never** renumber. Always print `file:line` next to it so a report stays reconcilable even if the id scheme changes later.

Plain sequential numbering (`1.`, `2.`, …) is only for finding lists that have no persisted id: ad-hoc reports (`pr-quick`, `review-dependency-run`, `review-security-run`, `cct:ux-assessment-run`, `review-ux`), interactive selection tables not derived from a findings file, and **pre-identity** reviewer output — `review-code-reviewer` and `ux-usability-reviewer` emit no `id` because ids are minted downstream, so numbering their return is correct. A single report must never mix the two schemes.

Categories: `security`, `bug`, `performance`, `testing`, `convention`, `rules`, `completeness`, `clarity`

Use specific sub-tags when presenting findings: `[security]`, `[logic/sort]`, `[API misuse]`, `[null safety]`, `[test coverage]`, `[convention]`, `[completeness]`, `[design/coupling]`, `[complexity]`, `[dead code]`, etc.

## Reversibility

A second axis, orthogonal to severity. **Severity ranks urgency; reversibility decides whether it can wait.**

| Value | Meaning |
|---|---|
| `cheap` | Undoing it later costs about what fixing it now costs. |
| `entrenches` | Shipping it makes the fix more expensive later: a data migration, a public API or schema contract, or a non-native pattern other code will copy. |

A producer always emits one of the two. `unstated` exists only downstream: the merge mints it when a producer failed to judge, and the verdict floor never fires on it — so an omitted `entrenches` is a lost block.

`entrenches` at `suggestion` severity is a real and common combination, not a contradiction — a one-line shortcut can be trivial today and costly once rows and callers accumulate on top of it. Consumers that gate on blocking (`../review-code-run/references/report-sections.md` → Verdict) treat a confirmed `entrenches` finding as a blocker at any severity, because "defer to a follow-up ticket" is the move that makes it expensive.

Judge the cost of **undoing**, never the cost of doing. If the two feel identical, the value is `cheap`.

A **producer** emits only `cheap` or `entrenches`. Consumers may additionally see `unstated`, minted downstream when no source supplied the field (`../review-code-run/references/merge.md`, `../review-code-run/scripts/posting-findings.sh`). `unstated` means unknown — never treat it as `cheap`, which would silently waive the blocking rule above.

## Confidence Scoring

Each finding should have a confidence score (0-100). Confidence governs *rendering*, not inclusion: no finding is dropped for low confidence (see **Threshold** below).

- **90-100**: Verified against code, certain
- **70-89**: High confidence, verified pattern
- **50-69**: Likely issue, needs human confirmation

**Threshold:** 50 — the generation floor. Findings below 50 are never dropped. The deep and agent-orchestrated `max` pipelines validate **every** finding regardless of band (the validator verdict is the disposition); only `pr-quick`, which has no validate step, renders sub-50 findings in a trailing "Unvalidated observations" block.

The `85` bypass cutoff once used by the deep modes is retired — deep and `max` now both validate every finding with no confidence gate (see `../role-code-analysis/references/validate-findings.md` → "Calibration — superseded by validate-all" and `review-code-run/CLAUDE.md` → "Confidence-threshold gate — retired"). The `50` floor is a static generation default; the offline-recalibration apparatus has been retired. Do not retune per-run.

## Action Verbs

### Universal Actions

| Action | Meaning | Phase |
|--------|---------|-------|
| `ADD TEST` | Write or improve tests — new tests, additional cases, better coverage; if test fails, fix follows in Phase GREEN. **Any change targeting a test file is ADD TEST, not FIX.** | RED → GREEN |
| `FIX` | Mechanical change — toolchain is the test (lint, typo, import, format) | GREEN only |
| `INVESTIGATE` | Uncertain; resolved during Phase RED by writing a characterization test | RED → resolves to ADD TEST, FIX, DISCUSS, or SKIP |
| `REFACTOR` | Behavior-preserving restructuring; run existing tests before and after | GREEN only |
| `SKIP` | No action needed | — |
| `DISCUSS` | Needs user input before proceeding; **fallback when uncertain at any point** | — |
| `DEFER → Linear` | Reviewer asks to defer work for later; create a Linear ticket, don't fix now | — |

### PR-Specific Actions

| Action | Meaning | Phase |
|--------|---------|-------|
| `FLAKY → Linear` | CI failure also fails on base; file a ticket, don't fix | — |
| `MERGE` | Branch is behind base and PR already exists — use merge commit (standard) | before all other actions |

## Triage Classification Rules

- Mechanical on production code (lint, typo, import, format) → `FIX`
- Behavioral findings → `ADD TEST`
- Any change targeting test files (new tests, additional cases, coverage improvements) → `ADD TEST`
- Uncertain whether behavioral → `INVESTIGATE`
- Reviewer asks to defer → `DEFER → Linear`
- Inconclusive/architectural → `DISCUSS`
