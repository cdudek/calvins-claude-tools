# Report sections

Top-level runs render these, in this order. Nested runs render none of them (`pipeline-tail.md` → Nested). Skip a section that has nothing in it.

Write every sentence you add in plain English (`reviewer-rules.md` → Write in plain English): short sentences, one idea each, no idioms. Keep a reviewer's quoted words as they are.

## Verdict

First line of the report: `ship`, `fix-first`, or `rework`. Then 2-3 sentences on why. Name the finding that decided it, by `F<id>`.

| Verdict | When |
|---|---|
| `ship` | No confirmed finding blocks, and no acceptance criterion is `missing` or `partial`. Unverifiable and demoted findings never block on their own. |
| `fix-first` | A confirmed finding blocks, or an acceptance criterion is unmet, but the change's shape is right. |
| `rework` | The approach is wrong: confirmed findings cluster on the design, or an "Area warranting closer review" covers the change's core. |

**What blocks.** Three things, and any one of them is enough:

1. A confirmed `critical` or `warning`.
2. A confirmed finding of **any** severity with `reversibility: entrenches` — severity ranks urgency, reversibility decides whether it can wait. "Defer to a follow-up ticket" is the move that makes an entrenching shortcut expensive, so the floor refuses it.
3. An acceptance criterion at `missing` or `partial` in `ac-coverage.json`. A change that does not do what the ticket asked is not ready, however clean its code is. Name the criterion by its `AC-<n>`, the same way a finding is named by its `F<id>`.

`not-verifiable` never blocks — nobody can settle it by reading code, so refusing the change on it would ask the author for something they cannot deliver. The report names it instead.

`$AC_MODE: none` does not block **except for `audit-failed`**, which does. The other four
reasons say there was nothing to grade; `audit-failed` says the grading could not be trusted.
That difference matters because the second one is reachable from the ticket text: criteria that
push the auditor into rewording or splitting a row fail the Collect checks, and if a failed
audit passed through like an absent one, sabotaging the grading would buy exactly what forging
a `covered` row buys. It floors at `fix-first`, and `ac-check.md` leaves no `ac-coverage.json`,
so a re-run clears it.

`synthesize.md` derives the verdict. This table is its rubric.

## Acceptance criteria

Renders directly after the verdict, before the summary header. **This section is never skipped** — not when the audit ran, and not when it did not. A review that says nothing about acceptance criteria reads as a review that checked them.

`$AC_MODE` is `ac` → one row per criterion, from `ac-coverage.json`, in its order:

```markdown
## Acceptance criteria — 2 of 3 covered (SUPPLY-577)

| AC | Status | Evidence | Note |
|----|--------|----------|------|
| AC-1 | ✅ covered | `app/models/review.rb:42` | The scope filters on `published_at`. |
| AC-2 | ❌ missing | — | No CSV writer exists. |
| AC-3 | ➖ not-verifiable | — | Needs a rendered page; reading code cannot settle it. |
```

Markers: `✅ covered`, `⚠️ partial`, `❌ missing`, `➖ not-verifiable`. The heading counts only `covered` against the total, so `partial` reads as unmet — which is what the verdict rule treats it as.

`$AC_MODE` is `none` → one line, no table, worded from `$AC_REASON`:

| `$AC_REASON` | Line |
|---|---|
| `no-reference` | `Acceptance criteria: not checked — no ticket reference in the PR title, body, branch or commits.` |
| `unresolved` | `Acceptance criteria: not checked — <ref> was found but could not be resolved. Re-run when the tracker answers.` |
| `no-criteria` | `Acceptance criteria: not checked — <ref> resolved but states none.` |
| `not-applicable` | `Acceptance criteria: not applicable — files mode reviews code as it is.` |
| `audit-failed` | `Acceptance criteria: not checked — the audit pass failed. Re-run to retry it.` |

The five reasons stay distinct because they ask for different things. `unresolved` and `audit-failed` ask for a re-run. `no-criteria` asks someone to write criteria on the ticket. `no-reference` asks for a ticket link. `not-applicable` asks for nothing.

## Summary header

**PR Summary** (2-3 sentences), **Change Summary** (branch, base, commits, files), or **File Summary** (files with line counts). The mode file supplies it.

## Findings

Group by file. Order by severity. Render each in the detailed form from `finding-format.md`. Label each with its `findings.json` `id` as `F<id>`. Never number by position. Never renumber.

No real issues → say so.

### Minor — one line each

A confirmed finding at `suggestion` or `nit` whose `reversibility` is `cheap` does **not** get a
detailed block. It gets one line, in a list at the end of this section:

```markdown
### Minor

- F14 `app/models/review.rb:88` 🟡 [complexity] The method takes six positional arguments.
- F21 `spec/reviews_spec.rb:12` 🔵 [test-quality] The spec name repeats the class name.
```

These are the findings that do not block the verdict and that the fix loop does not fix
(`../scripts/fix-handoff.sh` → Routing). Rendering them as full blocks puts them beside a SQL
injection at the same visual weight, and a reader who cannot tell the two apart treats the whole
report as a task list.

Nothing is dropped. Same `F<id>`, same `file:line`, same severity and dimension — a reader who
wants one in full has its id and can look it up in `findings.json`. A `suggestion` carrying
`reversibility: entrenches` is **not** minor: it blocks the verdict, so it renders in full above.

## Split decisions

Render only when `$CODEX_STATUS` starts with `ok` and there is at least one dispute.

A split decision is a finding the two models disagree on:

1. `source: codex`, verdict `rejected` — Codex claimed it, a Claude validator could not confirm it.
2. `source: claude`, verdict `rejected`, at the same `file:line` as a rejected `source: codex` finding — both pointed at one place, neither survived.

Table columns: ID (`F<id>`), Location, Found by, Claim, Verdict, Counter-evidence (the validator's `justification`).

**Evidence decides.** Not the more confident wording. Not a split of the difference. If the code settles it, say which side and why. If not, say it is unresolved.

A `source: both` finding is agreement, not a dispute. It renders in Findings with its raised confidence.

## Cross-File Patterns

Duplicated logic, inconsistent error handling, circular dependencies across the reviewed files.

## Areas Warranting Closer Review

Smoke-signal clusters from `synthesize.md`. Omit when none.

## Demoted and rejected findings

Confirmed findings with a `suppressed_reason`, and findings with verdict `rejected` (except rejected `source: codex`, which go to Split decisions).

| ID | Location | Marker | Title | Reason |
|----|----------|--------|-------|--------|
| F12 | `app/x.rb:31` | (rejected) | N+1 query | Already batched via dataloader on line 15 |
| F18 | `app/y.rb:8` | (style) | Variable naming | No correctness impact |

Marker is `(rejected)`, `(style)`, or `(out-of-scope)`. Reason is the validator's `justification`, at most 100 chars. Omit the section when empty.
