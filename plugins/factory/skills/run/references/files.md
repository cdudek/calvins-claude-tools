# Files and where they live

```
specs/<YYYY-MM>/<YYYY-MM-DD>__<feature>.md  living spec (requirements as req-<n>, journeys); date = when it was created
specs/adr/NNNN-<words>.md             architecture decisions, numbered; superseded ones stay
changes/<slug>/intent.md              problem, outcome-1.., constraint-1.. (references/intent-template.md)
changes/<slug>/delta.md               ADDED / MODIFIED / REMOVED requirements req-<n>, each citing [outcome-<n>] or [constraint-<n>]
changes/<slug>/plan.md                plan, progress log at the bottom
changes/<slug>/kickoff-<M>.md         run briefing per milestone, written by goal-brief.py
changes/<slug>/evidence/<M>/          screenshots, verifier and UX reports, gallery.md
.factory/                             the plugin's scripts, copied here at session start (commit it); .factory/state/ is git-ignored
~/.factory/scenarios/<repo>/<slug>/   holdout scenarios, verifier only
```

All of it except the scenarios lives in the app's own repository, versioned with the code. A multi-app change writes one delta per repo.

## Lifecycle
- The intent stays in the change folder after shipping.
- When the change merges, the delta goes into `specs/<YYYY-MM>/<YYYY-MM-DD>__<feature>.md` in the same PR.
- A decision that is expensive to reverse gets an ADR per `references/spec-standard.md`. It is drafted as `proposed` and set to `accepted` before the approval commit is recorded. It is never deleted; a later ADR supersedes it.

## Old repos
- A repo set up before version 0.3.0 still has the old folder name and plans with the old fence. The session-start message gives the one command, `migrate-name.py <repo>`; `migrate-name.py --home` moves the old home folder.
- Plans approved before the rename need a new approval revision: `check-plan.py --approved` compares the plan through its json block.
