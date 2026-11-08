---
name: arch-decision-log
description: "Records an accepted technical decision as an ADR: context, decision, consequences, rejected alternatives, status and supersession. Writes the ADR file; does not decide. Use when the user says 'record an ADR', 'log this architecture decision', 'write the decision record', 'supersede that ADR'. Skip for: UX decisions (use cct:ux-decision-log), the plan that led to the decision (use cct:arch-plan-write), saving the ADR in Linear (use cct:linear-manage)."
allowed-tools: "Read Grep Glob Write Bash(git *) Bash(python3 scripts/design_index.py *)"
user_invocable: true
metadata:
  version: 1.0.0
  author: calvindudek
---

# Record a technical decision

Writes one ADR for a decision that has already been accepted. The owner decides; this skill
records the decision, the reasons and the rejected options, and links it to what it replaces.

A decision that is still open belongs in the plan or RFC (`cct:arch-plan-write`) as an open
question. Do not write an ADR for a deferred decision.

## Steps

1. **Collect** the decision, the owner's answer in their own words, and the alternatives that were
   weighed. If the decision, the decider or the reason is missing, ask once; never invent them.
2. **Find the home.** Read `<designsDir>/INDEX.md` (`designsDir` from `sdlc.json`, else
   `docs/designs`) and any existing ADRs on the topic. If a current ADR is replaced by this one,
   note its id for `supersedes`.
3. **Write one file per decision**: `<designsDir>/<YYYY-MM-DD>-adr-<slug>.md` (nest by
   `<year>/<year-month>/` when that folder already does). Never append a row to a log.
   Frontmatter: `title`, `type: adr`, `status: accepted`, `created`, `decided_by`,
   `tags: [architecture, <area>]`, and `supersedes: [<id>]` when it replaces one.
4. **Body** follows `${CLAUDE_PLUGIN_ROOT}/skills/linear-manage/references/adr-template.md`: Status, Context, Decision (starts with "We
   will"), Consequences (positive and negative), one subsection per alternative with "Rejected
   because", Related, and the Supersedes / Superseded by lines. No requirement language; if you
   find yourself writing "the system shall", the content belongs in an RFC or an issue.
5. **Supersession.** When this ADR replaces an earlier one, set the old file to
   `status: superseded` and `superseded_by: <this id>`. Without these links the pile of ADRs is
   not a decision log.
6. Run `python3 scripts/design_index.py write` when the repo has it, so the next reader opens
   `INDEX.md` and then one file.

## Boundaries

- Linear: the template in `${CLAUDE_PLUGIN_ROOT}/skills/linear-manage/references/adr-template.md` also fits a Linear document (title
  `ADR-<number>: <title>`). Creating it there is `cct:linear-manage`; pass it the finished text.
- A decision that changes or rules out a Snapmark note: put the ADR's repo-relative path in that
  mark's `decision` field in `marks.json`.
- UX decisions use the same file shape but are recorded by `cct:ux-decision-log`.
