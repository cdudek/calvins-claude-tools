# Review policy

Used by the verifier, the security review and the Codex plan review. It decides what fails a milestone.

## Important
A finding is Important only if it does one of these:
- It breaks behaviour: a requirement or scenario fails, or a neighbouring flow breaks.
- It leaks data: someone can see or change what they must not.
- It breaks a policy: a rule in the plan, the spec, an ADR or the repo's own docs.

Every Important finding carries evidence: the command, the revision and what it showed. Findings are numbered `finding-<n>` per report, and a report names one after an explainer: "guest can read other trips (finding-2)".

## Nit
Everything else that is true but small. Report at most five Nits, the five that matter most. Drop the rest.

## Do not report
- Style that the linter or formatter owns.
- Naming taste.
- Speculative performance with no measurement.
- Anything you did not run or read.

## What fails
- The verifier and the security review fail only on Important findings.
- Nits never fail a run. They go in the report under their own heading.
- A fix for an Important finding stays inside the task's own files and its `allowTestEdits`. Anything else is a `gap`: the coordinator's gap lane handles it inside the milestone's `mayTouch`, or it ends `BLOCKED: owner approves plan revision for <finding>`.
