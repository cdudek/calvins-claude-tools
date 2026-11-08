---
name: ux-run
description: "Coordinates the whole UX process on a project: setup (cct:ux-setup), an approved briefing, the assessment (cct:ux-assessment-run), proposed interaction guidelines annotated by the owner, a decision page where the owner decides, recording every answer (cct:ux-decision-log), and approved delivery. Stops at every point only the owner can decide and resumes from where the project is. Use when the user says 'run the ux process', 'do the same ux process on this project', 'cct:ux-run', 'take this project through the full ux flow'. Skip for: designing one change, which belongs to cct:ux-design-run."
user_invocable: true
metadata:
  version: 1.0.0
  author: calvindudek
---

# cct:ux-run

**Arguments:** `[extra builds: PR numbers or URLs]  [from: setup | briefing | audit | guidelines | page | decide | build]`

One command for the process: **document everything, let the owner decide, then build only what
was decided.** It chains the other ux skills and adds the gates between them. It never changes
the app before the owner has decided and approved a plan.

Shared files are in `references/`, two levels up from this skill's base directory. Read
`decision-page.md` before step 6.

## Where the project is

Work out the current step from the repo, unless `from:` names one, and say which step you are
starting at:

| Found | Start at |
|---|---|
| no `docs/ux/setup.md` | 1 |
| no approved briefing for the latest audit | 2 |
| an approved briefing, no `findings.md` | 3 |
| findings, no proposed interaction guidelines | 4 |
| proposed guidelines not yet annotated by the owner | 5 |
| no decision page file named in `setup.md` | 6 |
| a decision page with unanswered items | 7 |
| answers recorded, changes not built | 8 |

## Steps

1. **Setup.** Run `cct:ux-setup`. Ask the owner only what the repo cannot tell you.

2. **Briefing: stop for the owner.** Write the briefing as `cct:ux-assessment-run` step 1 says: deliverables in
   order, every relevant request quoted with its date, the scope, the checks, the team, the
   finding format. Show it in full. When the owner asks "what is the brief based on", show which
   of their requests each part answers. **Do not start any agent until the owner says go.**

3. **Audit.** Run `cct:ux-assessment-run` with the approved briefing. Findings are **uncapped** and written as
   markdown **before** anything is written for deciding. Where two sources disagree (a behaviour
   seen two ways), run a small targeted check and settle it; never leave a contradiction in the
   findings.

4. **Guidelines.** Run `cct:ux-guidelines-write draft`: principles, a rule per rule area, concrete examples,
   complete flows, exceptions, the enforcement map. Every rule `status: proposed`.

5. **Owner's comments: stop for the owner.** Open the guidelines in Plannotator
   (`plannotator annotate <path>`, run in the background) and tell the owner it is open. When the
   annotations come back, write each one into the rule it is about, quoted with its date, and
   mark what it decides and what it leaves open. An assumption about what a comment means is
   written as one, and becomes a question on the page. Commit.

6. **Decision page.** Run `cct:ux-decision-log page`, following `references/decision-page.md` point by
   point. Shared rules first in rounds of five, then screen and word choices, then behaviour
   changes that belong to no rule, then routine fixes as one question. Read the whole page before
   handing it over. Write the local HTML file, verify that answers save and export, and put its path in
   `setup.md`. Give the owner the path and one line on how to answer and export.

7. **Decide: stop for the owner.** Read the answers from the exported `answers.json` (the path in `setup.md`) when the
   owner says they have answered (never before). For each answer, run `cct:ux-decision-log` recording and
   `cct:ux-guidelines-write record`. A rule becomes accepted only on the owner's own answer. A later
   message that reverses an earlier decision is recorded as a reversal, quoted, on the rule and
   the finding. Regenerate the page with decided items moved to "Already decided".

8. **Build: stop for the owner's approval of the plan.** Turn the accepted rules and applied fixes
   into changes the repo's own way (its SDLC, change folders and PR rules). Write the plan first
   and wait for the owner to approve it. A decision is not approval of a plan, and a comment is
   not approval either. Before building a new screen, flow or behaviour, run `cct:ux-design-run
   <change>` (when the repo runs `cct:sdlc-run` with a Design stage, that stage runs it).
   Then build, run `cct:ux-spec-validate build <change>` when a spec folder exists,
   `cct:ux-rules-validate` on each change and `cct:ux-assessment-run` on each PR.

## Never

- Change the app, user data or a real device before step 8's plan is approved.
- Cap a list, or merge findings to make a list shorter.
- Put a code, finding number or PR number in text the owner reads, outside supporting notes.
- Treat silence, an earlier message or your own summary as the owner's decision.
- Justify a recommendation only because it is already built or matches another product.
