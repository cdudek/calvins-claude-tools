# Quality passes — rules, clarify, checklist, analyze, challenge, converge, class

Seven small mechanisms (3.8.0, challenge 3.9.0) that keep the facts honest before the build and
the build honest after it. Ideas from github/spec-kit (MIT) and, for challenge, reflection and
the audit, Habitat-Thinking/ai-literacy-superpowers (Apache-2.0); the wording is ours. Each is
read-only except for the one file it names.

## Rules

`sdlc.json` `rules` lists the repo files that hold standing rules. Default, files that exist:
`CLAUDE.md`, `PRODUCT.md`, `DESIGN.md`, `docs/rules.md`, `<designsDir>/INDEX.md`,
`boundary-map.yaml`, `docs/architecture-policy.md`. A list in `sdlc.json` replaces the default.

- **A rule ID** is the ID the file gives (`SEC-2`, `D4`); a file without IDs is cited as
  `<file>#<heading>`.
- **Stage 1** reads the files; `intent.md` → Constraints → "Rules that apply" lists the IDs or
  names that touch the asks.
- **Stage 3**: each fact cites the rule IDs it touches, after its asks: `(A1, A3; rules SEC-2)`.
- **Stage 4**: `plan.md` → `## Rules check` is run before the design and again after it. A plan
  step that breaks a rule goes into `## Justified violations` (Violation | Why needed | Simpler
  alternative rejected because). A rule marked MUST that is broken without a row is CRITICAL in
  the analyze pass, and `verify_gate.py approve` refuses a row with an empty cell.

## Clarify (Stages 1 and 3)

Scan the asks and facts against nine areas: scope, data, UX states, non-functional, integrations,
edge cases, constraints, terminology, completion signals.

- At most **5 questions** per change, one at a time (`AskUserQuestion`), highest impact on the
  build or the tests first. Each carries a recommended answer and the reason.
- **Skip** a question whose answer would change neither the build nor a test.
- Put each answer into the facts at once and replace the sentence it overturns.
- A gap you could fill with a sensible default is not a question: fill it and list it under
  `## Assumptions` in `facts.md`. At most **3** `[NEEDS CLARIFICATION]` markers stay open, only
  where a wrong guess changes scope, safety or money; none may remain at the gate.
- Questions left over are listed under `## Deferred` in `facts.md` with the default taken.

## Requirements checklist (`checklist.md`)

Owned by the reviewer (the agent in a fresh context, never the one that wrote the facts). Each
item tests how a fact is **written**, never whether the software works: "Is the empty state of
the list defined?", not "Check the list renders". Items start `- [ ]`, are tagged **Gap**,
**Ambiguity**, **Conflict** or **Assumption**, and cite the fact (`F3`). The reviewer ticks an
item only after the facts answer it. `verify_gate.py approve` refuses while any item is open.

## Analyze (before gate 2)

Read-only. Reads intent, facts, plan, `spec/` and the rule files; writes only `analyze.md` and
edits nothing else. Six passes: **duplication**; **ambiguity** (vague adjectives, placeholders
such as TODO or `<…>`); **underspecification** (a fact with no screen or state, a verb with no
object); **rules alignment**; **coverage** (ask → fact → E2E tag → plan row, and back: an
unmapped item either way is a finding); **inconsistency** (terminology drift, a number that
differs between files).

Severity: **CRITICAL** a broken MUST rule, a missing ask, a fact no test can prove; **HIGH** a
conflict or an untestable fact; **MEDIUM** drift or a vague term; **LOW** wording. At most 50
findings, stable IDs `X1…`. `analyze.md` is one coverage table (ask | facts | tags | plan row)
and one findings table: `| ID | Severity | Pass | Where | Finding | Status |`, Status `open` or
`fixed`. The agent fixes in the source file and marks `fixed`; the pass itself never edits.
`verify_gate.py approve` refuses an `open` CRITICAL.

## Challenge (before gate 2, after analyze)

Analyze asks "do the documents agree with each other?". Challenge asks "is this the right
change?". A reviewer in a fresh context (never the agent that wrote the plan) reads `intent.md`,
`facts.md` and `plan.md` and argues against them, read-only, five lenses:

1. **Existence**: which ask would still be met if this change were not built, or built by editing
   something that exists?
2. **Simpler alternative**: the smallest change that meets every ask, and why the plan is not it.
3. **Failure assumptions**: each thing the plan assumes true (a service up, data clean, a user
   who reads the banner), and what happens when it is not.
4. **Implicit choices**: decisions the plan makes without saying so (a default, an ordering, a
   dependency, a name that becomes a contract).
5. **Who else is affected**: other teams, callers, data consumers, support, the next change.

Writes only `challenge.md`: `| ID | Severity | Lens | Where | Challenge | Status |`, severity as in
analyze, ids `H1…`, at most 20 findings, Status `open`, `answered` (the plan or facts now say
why; name the line) or `accepted` (the engineer decided to carry it; the reason is in the
row). The pass never edits the plan. `verify_gate.py approve` refuses an `open` CRITICAL, and
nothing else in it; a change with no `challenge.md` (in flight before 3.9.0) is not blocked.
Size S and `none` may skip it with a printed line.

## Converge (milestone close)

After validation, before the fix round. Append-only: it adds to `findings.md`, never edits it.

1. Re-read every fact and ask of the milestone against the built diff and `validation.md`. A
   ticked box in `facts.md` or `plan.md` is **not evidence**; only code, a test result or a
   capture is.
2. Per item, one verdict: `missing`, `partial`, `contradicts` (the build does the opposite) or
   `unrequested` (built, no ask or fact). Append each as `- [ ] **C<n>** <verdict>: <F or A id>
   — <source ref: file:line, test name or shot>` under `## Converge` in `findings.md`.
3. The one fix round closes the items. Run the pass again; items it adds are fixed in the same
   round if small, else they start the next milestone. A pass that adds nothing writes
   `Converged: round <n>` and the milestone may close.

`verify_gate.py milestone` fails `not-converged` while the section has no `Converged:` line.

## Class (Decision4 v1)

Source: https://github.com/Habitat-Thinking/decision4. One question per decision: if this turns
out wrong, what does it take to put right?

| Class | Putting it right takes |
|---|---|
| Undo | a revert |
| Repair | real work, inside the team |
| Migrate | coordinated change with other people |
| Answer | an explanation to someone outside the team; nothing unmakes it |

`intent.md` records the change's `class` (frontmatter, with the reason in Constraints). Unsure:
take the higher. The engineer approves the class with the plan at gate 2 and `approve` copies it
into `lock.json`. The `/goal` closes only work **up to that class**. A decision above it is not
built: write it to `questions.md` with the options and what it would take, skip the item, go on.
Raising the class during the build is always allowed and recorded; lowering it needs the
engineer's words in `decisions.json` `protectedEdit`.

## Decision record in a PR

Follow [Decision4 PR writing](decision4-pr.md) for the class-specific Decision record: Repair choice story; Migrate options or forced constraint; Answer labelled evidence and challenges, with no recommendation. Omit it at Undo.