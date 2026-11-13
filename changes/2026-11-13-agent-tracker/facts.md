---
linear: none
type: facts
change: 2026-11-13-agent-tracker
design: docs/designs/agent-tracker.md
author: Calvin Dudek
status: draft
reviewed_by: null
approved_at: null
created: 2026-11-13
---

# Facts: Agent tracker, milestone 1

## Goal

<One paragraph, at most three sentences. What the user can do when this ships,
and why it is one change.>

## Acceptance criteria

Each fact is one EARS sentence: one outcome that a test or a person can check. Cite the asks it
answers and the rule IDs it touches, such as `(A1, A3; rules SEC-2)`. For UI, name the screen or state. Name the E2E test tag that
will prove it: `@F1`, beside the change tag `@<change id>` in the test title, so the feature
run selects the change's tests with `--grep @<change id>`. A fact that needs "and" is two
facts. Group facts by theme; keep each fact to one line; put the proof in the Verification block,
not in the sentence.

The six EARS patterns, the optional Gherkin block and `[NEEDS CLARIFICATION: ...]`
are documented once, in `cct:product-workitem-write` →
`references/requirements-grammar.md`. Read it before writing this section.

Replace every adjective with a number. "Fast" is not a fact; "answers in under
200 ms at p95" is.

**A change you can describe in one sentence gets one plain fact, no EARS, no
themes.** Over-specifying small work is the failure this whole chain is meant to
avoid. The test is ambiguity, not size: a one-line change whose correct answer is
unclear still needs the full shape.

### <Theme 1, e.g. Series and webinar behavior>

- [ ] **F1** (A1; rules <ID>) When <trigger>, the system shall <response>. Screen/state: <name>. Tag: `@F1`.
- [ ] **F2** (A2, A3; rules none) If <error condition>, then the system shall <response>. Screen/state: <name>.
- [ ] **N1** (A4) The system shall <non-functional property, with a number>.

<details>
<summary>Verification</summary>

- F1 — tag `@F1`: `<test file> › <test name>`
- F2 — tag `@F2`: `<test file> › <test name>`
- N1 — manual: <who checks, and how>

</details>

### <Theme 2, e.g. Settings and navigation>

- [ ] **F3** (A1, A5; rules none) While <state>, the system shall <response>. Screen/state: <name>.

<details>
<summary>Scenario — optional, only where F3 is ambiguous on its own</summary>

```gherkin
Scenario: <name> — proves F3
  Given <context with concrete data>
  When  <action>
  Then  <observable outcome, with a number where one exists>
```

</details>

<details>
<summary>Verification</summary>

- F3 — tag `@F3`: `<test file> › <test name>`

</details>

## Verification

What proves the whole change, beyond the per-fact checks.

- **Automated:** `python3 -m unittest discover -s tests && scripts/run-plugin-tests.sh` exits 0.
- **Manual:** <screens, devices, themes, who reviews>

## Out of scope

- <what this change does not do, on purpose> — <where it lives instead, if anywhere>
- A5 — <why this ask is not answered in this change>

## Assumptions

Defaults taken instead of asking, one line each: the default and why it is safe.

- <assumption>

## Deferred

Clarify questions left over after the budget of five (`references/quality-passes.md`), each
with the default taken. `none` when there are none.

## Open questions

At most three markers, only where a wrong guess changes scope, safety or money. Every
`[NEEDS CLARIFICATION: ...]` must be answered and deleted before `plan.md` is
approved — an agent that meets one and guesses ships the guess silently.

- [ ] [NEEDS CLARIFICATION: <question>]
