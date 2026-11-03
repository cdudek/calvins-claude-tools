# Review instructions

Read by `cct:pr-review` at every milestone close (the only code review; nothing reviews
in CI), and by anyone reviewing by hand. The human reviewer's job is intent and risk — does the change do what
`changes/<date>-<slug>/plan.md` says, and is the blast radius acceptable. The
mechanical passes below are Claude's job, and they run identically on every PR.

The review (`cct:pr-review` with one `review-fix-loop` round) runs once per milestone,
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
