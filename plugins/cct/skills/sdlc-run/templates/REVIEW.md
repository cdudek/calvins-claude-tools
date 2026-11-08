# Review instructions

Read by `cct:review-code-run` at every milestone close (the only code review; nothing reviews
in CI), and by anyone reviewing by hand. The human reviewer's job is intent and risk — does the change do what
`changes/<date>-<slug>/plan.md` says, and is the blast radius acceptable. The
mechanical passes below are Claude's job, and they run identically on every PR.

The review (`cct:review-code-run` with one `review-fix-run` round) runs once per milestone,
on the milestone diff, not on each feature PR.

## Passes

Read the diff once; tag every finding with one of these three passes. Open a file only
when the diff alone cannot settle a finding — never walk the repo, the budget is ~$1:

- **Bugs** — logic errors, broken edge cases, subtle regressions, a guard that no longer
  short-circuits, a summary that counts skips as successes.
- **Security** — credentials or PII in logs or error messages, a secret outside the
  secret store, a client without a timeout, a swallowed exception, a new network
  egress, a widened permission in a workflow, an auth check that trusts client input.
- **Compliance** — the change matches the change folder when the PR names one. Check every
  fact, the plan's files list, and for UI changes: `spec/screens.md` labels, controls and
  layout; `spec/interaction.md` state tables and Back behaviour; `spec/ia.md` navigation
  moves; `spec/conformance.md` component decisions and deliberate inconsistencies. A departure
  with no `## Revisions` line is **Important**. It also follows `CLAUDE.md` and does not make a
  repo rule false without updating it.

## Decision4 recovery

Read the PR template's writing-rules HTML comment and the repo's `boundary-map.yaml`.
Check the readable section headed `## How hard is it to undo this PR after merging?`:
one selected class at the highest whole-diff floor, a specific recovery sentence,
ordered Recovery steps (optional for Undo), Work preserved only with evidence,
Responsible for recovery (a named person for Answer), and Classification change
(`None` or from -> to, by whom and why). Read legacy Decision-Class, Put-right,
Answerer and Class-Change as aliases; comments supply no values. The checker proves
minimum fields, not truthful recovery or backup claims. A lowering needs authorization.

## Design questions

While reading, also ask these four (from the CUPID properties). They add no fourth pass: a yes
is filed under Bugs when it breaks behaviour, and is a Nit otherwise.

- **Hidden dependencies**: does the code need something the caller cannot see, such as call
  order, a global or env var, a file, or a prior write?
- **Surprising side effects**: does a function with a read-sounding name write, send, cache or
  mutate its argument?
- **Domain vocabulary**: do names match the words in `intent.md` and the product's glossary, or
  do two names mean one thing here?
- **Composability**: could a caller use this part alone, or is it only usable inside this flow?

## What Important means here

Reserve **Important** for a finding that would break behaviour, write to the wrong
system, leak data, or breach a rule a guardrail test does not already catch. Style,
naming, and "I would have done it differently" are **Nits**.

## Cap the nits

Report at most five nits per review; summarise the rest as a count.

## Do not report

- Anything CI already enforces: formatting, lint rules, type checks, the guardrail tests.
  If it would fail there, it is not a finding here.
- Generated files: lockfiles, image-tag bumps, `changes/**/interview*.json`,
  `changes/**/facts-*.json`, `changes/**/*annotations*.json`, `CODEOWNERS`.
- Comment density or prose style in code comments — this repo explains its scars on
  purpose.

## Output

Inline comments on the exact lines for every Important finding and for the nits you keep.
One top-level comment with the tally in this exact shape on its own line, so the merge
gate can read it:

    IMPORTANT: <n>  NITS: <m>  SHA: <head sha>
