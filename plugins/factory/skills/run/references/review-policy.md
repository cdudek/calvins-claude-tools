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

## Security findings
- Each Important security finding names the rule it breaks: the milestone's `rule`, or one sentence of your own when the plan has none.
- Group findings by rule and lead with the shared cause: "a moved comment keeps its old team's readers (rule: guests read only their own comments)", then its instances. One cause is one fix.

## Reviewing a check
A check (a script, hook or gate) is reviewed against the threat model in its header, never against an attacker it does not claim to stop.
- A finding outside the stated model is a Nit, listed for the check's known-limits section. It never fails the change.
- One review round per change to a check. What a later round finds goes to the known limits, unless it breaks the stated model.

## What fails
- The verifier and the security review fail only on Important findings.
- Nits never fail a run. They go in the report under their own heading.
- A fix for an Important finding stays inside the task's own files and its `allowTestEdits`. Anything else is a `gap`: the coordinator's gap lane handles it inside the milestone's `mayTouch` (up to `gapRounds` rounds), or it ends `BLOCKED: owner approves plan revision for <finding>`.
