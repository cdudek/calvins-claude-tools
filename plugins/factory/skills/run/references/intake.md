# Intake (station 0)

- Ask what the person brings (idea, journey or screen, bug) and size it: bug, small feature, milestone or project.
- Check the target branch has a merge gate: branch protection or a ruleset, required CI, no agent bypass. If it is unreadable or absent, tell the person that PRs are then never auto-merged, and record `"merge": "owner"` in the plan.
- Where Actions minutes cost the owner money (the person says so at intake), a multi-milestone change always sets `"integration"`. Milestone PRs merge into it on their own; the human merge decision applies only to the one release PR into `base`. A single-milestone change or a bug there may target `base` directly. There is no plan PR there either: see station 2.
- Check the repo has fast commands (lint, typecheck, unit). If one is missing, ask. Run `python3 scripts/discover-tests.py <repo>` and put its proposed `tests` block in the plan for the owner's one approval (rules: `test-strategy.md`; schema: `plan-standard.md`). Its NOTES list what to ask the owner.
- Once per repo, link `specs/` and `specs/adr/` from the README.
- The plugin's scripts reach `<repo>/.factory/` by themselves: a SessionStart hook copies `check-plan.py`, `goal-brief.py`, `task-step.py`, `test-integrity.sh` and `kickoff.md` there whenever the repo has `changes/*/plan.md` or `.factory/` and the copies differ. Never read and rewrite them by hand. Commit `.factory/` on the first change branch.
- Run the scripts from `.factory/`, never by the plugin's install path.
- A repo with the pre-0.3.0 folder name: the hook prints the migration command and copies nothing until it has run (`references/files.md`, "Old repos").
