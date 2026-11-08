# How every finding is written

One format for `cct:ux-assessment-run`, `cct:ux-rules-validate` and `cct:ux-spec-validate`.
Every finding must be understandable without opening another document.

**This file is the human rendering. The contract is `findings.schema.json`** in this folder:
every pass returns its findings as JSON in that shape, and `skills/ux-assessment-run/scripts/findings.py`
merges the passes and renders this markdown from them. Write the fields; never type the report.
The table under "Fields" says which JSON field becomes which line.

```markdown
### F<nnn>: <brief title: the problem in plain language>
- **Impact:** Critical · High · Medium · Low · Design choice — one sentence: who is affected and
  what goes wrong. "Design choice" when there is no demonstrated problem.
- **Current experience:** two or three sentences, a concrete example, the exact words on screen.
- **Visual:** an annotated screenshot. For a layout or interaction change, also a mockup
  labelled "Proposal". For wording, the exact text before and after.
- **Recommendation:** the change, and how it helps the user's workflow.
- **Tradeoff:** the main downside. An alternative only when it is meaningfully different.
- **Decision needed:** one plain question, or "Routine fix: no individual decision needed".
- **Verified:** seen on screen · read in the code · measured · assumption, not checked · owner's preference.
- **Owner's words:** the earlier request, quoted with its date, or "no earlier request found".

<details><summary>Supporting notes</summary>

- Where: screen, control, build (main, or which PR)
- Broken: heuristic, law of UX, checklist point, WCAG criterion, project rule
- Code: file:line
- Screenshots: file names
- Earlier IDs: from older audits
- Other products: how they do it, one line each
- Seen by: which evaluators or lenses
- Guideline: the interaction rule this falls under, once one exists
- Rung: the rung the finding breaks; when a conflict was settled, the rung that won over the
  one that lost, and the exception if one applies (`Rung: R4 (IG-8) over R5 (L7.4), EX-3`; see
  `conflicts.md`)

</details>
```

## Fields

| Line above | JSON field |
|---|---|
| Title | `summary` (at most 240 characters, no codes) |
| Impact | `impact`, one of the five levels below |
| Current experience | `current` |
| Visual | `evidence` entries that are image paths |
| Recommendation, Tradeoff, Decision needed | `recommendation`, `tradeoff`, `decision_needed` |
| Verified | `verified`: `seen`, `code`, `measured`, `assumption`, `preference`. The first three need at least one `evidence` entry |
| Owner's words | `owner_words` |
| Where | `location`: `file:line`, or route + state + width, or a selector on a named route. It must be somewhere a person can open; two findings are merged only when `id` and `location` are identical |
| Broken | `id` (the stable rule or check id: `L7.2`, `WCAG-2.5.8`, `C3`, `IG-8`) and `lens` |
| Rung | `rung` (the rung of `conflicts.md` the finding breaks) and, when a conflict was settled, `conflict` |
| Code, Screenshots | the other `evidence` entries |
| Seen by | `sources`, written by the merge |
| Component | `component`, the shared part a repeated defect lives in |
| Earlier IDs, Other products, Guideline | `supporting_notes`, one line each, written as `Other products: ...` |

Beside the findings, every file carries `passed` (checked and clean), `not_applicable` and
`did_not_run` (each with its reason), `exceptions_used`, `notes`, a one-line `method`, and
`degraded` when a pass ran without its agent. "No issues found" without those lists is
indistinguishable from "nobody looked".

## Rules

- **No cap.** Never aim for a number. One problem per entry. Merge only when it is the same
  problem in the same place; then list every source.
- **Split bundles.** A finding about several places or several problems becomes one entry each.
- **Evidence is real.** "Seen on screen" needs a screenshot you looked at. "Read in the code"
  needs the line. Anything else is an assumption and says so.
- **No codes in the main text.** Requirement numbers, audit IDs and file paths live in the
  supporting notes only. The owner's earlier requests are quoted, never cited by number. If the
  quote cannot be found, say "no earlier request found".
- **Facts, assumptions and preferences stay apart.** A preference is labelled a preference.
- **"Already built" and "another product does it" are never the reason** for a recommendation.
  They can be evidence.
- **A change in behaviour is never a routine fix.** Routine fixes are only corrections with no
  real choice: a typo, a contrast value, a broken link, a missing label.
- **Conflicts are settled with `conflicts.md`.** The precedence ladder decides; the finding's
  severity follows the rung that is broken. In the Laws of UX coverage table a check covered by
  a recorded exception reads `pass (EX-n)`, never `n/a`, and the report lists every exception it
  relied on.
- **Earlier audits are something to re-check, not something to copy.** Nothing is skipped because
  an earlier audit mentioned it.
- **Visuals:** annotate screenshots (a box or arrow and a short label) with a script, not by
  hand-waving. Proposals are clearly labelled "Proposal" and never look like a screenshot of the
  real app.

## Impact levels

| Level | Meaning |
|---|---|
| Critical | Loses the user's work or data, or blocks a core job |
| High | A core job is broken, misleading or needlessly hard for most users |
| Medium | A job is clumsy, inconsistent, or broken for some users |
| Low | A small friction or polish issue |
| Design choice | No demonstrated problem; a direction to decide |

## One scale, mapped

These five levels are the kit's only severity scale. Every other scale a skill or a reference
uses is a name for one of them, never a second judgement.

| Level | Nielsen 0-4 | `cct:ux-accessibility-audit` | Build QA in `cct:ux-spec-validate` |
|---|---|---|---|
| Critical | 4, usability catastrophe | Critical | P0 |
| High | 3, major problem | Serious | P1 |
| Medium | 2, minor problem | Moderate | P2 |
| Low | 1, cosmetic problem | Minor | P3 |
| Design choice | 0, not a usability problem | none | none: taste, kept apart from mismatches |

- **A WCAG 2.2 A or AA failure is at least High**, and Critical when it blocks a task.
- **A legal non-compliance is Critical** (for example pre-ticked consent, or withdrawal harder
  than granting).
- **B2B escalation rule (ours):** a finding on a money, consent, access or mail action is raised
  one level, never above Critical.
- Nielsen rates frequency, impact and persistence
  (https://www.nngroup.com/articles/how-to-rate-the-severity-of-usability-problems/); say which
  factor drove the level when it is not obvious.
