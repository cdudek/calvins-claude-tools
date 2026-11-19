# Convergence: make UI review rounds end

Visual review rounds do not converge when "any defect fails" has no size, spacing is judged by
eye, and the design system is still growing. This file is the rule set. The layers and
tolerances live in `../../ux-build-validate/references/build.md` (Measurements) and the shared
`visual-pass.md` (section 5); this file adds the round rules, the design-system audit and the
capture rule.

## Six layers, written tolerances

A screen passes when all six layers pass. A repo may tighten a tolerance in its config. It never
loosens one without a decision record.

| Layer | Pass rule (default) |
|---|---|
| Structure | Same headings in the same order, same landmarks, nothing lost at 320 px. |
| Copy | Same words after normalising quotes and spaces. Sample data and ruled lines are excluded. |
| Tokens | Same design token for colour, type, weight, radius and background. Sizes within 0.5 px. |
| Geometry | Gaps use a spacing token and are within 2 px of the reference. Anchors within 4 px on desktop, 2 px on a phone. Order and alignment exact. |
| Rules and access | The repo's UI rules and WCAG 2.2 AA: zero violations. |
| Review | Only High and Medium defects fail. Low is listed, not blocking. |

**A pixel diff is advisory only.** Sample data in a design is meant to differ from the real data,
so a diff of the two fails for the wrong reason. Use it to find where to look, never as a verdict.

## Severity decides

High blocks a task or fails contrast. Medium is noticed at a glance: the wrong component, a
missing element, a misalignment over 4 px. Low is only visible when measuring, and it does not
fail.

**How this fits the kit's one scale.** These are the visual-review readings of the existing
levels in `finding-format.md`, not a second scale: High is P1, Medium is P2, Low is P3.
Critical (P0) is unchanged: lost work or data, or a blocked core job. A failed contrast ratio is
a WCAG failure, which that file already makes at least High. The build gate already says "no
P0-P2 remains", so Low never blocked and nothing about the gate changes. What is new is the
examples that tell a reviewer which level a visual defect gets.

## One defect list per screen, frozen

The first review of a screen writes its defect list. After that the list is frozen. A later
review ticks items off and may add only a High item or a regression, meaning something that
passed before and fails now. A new Medium or Low item found later is not added; that is what
kept rounds from ending.

## Budget: one fix round at milestone close, two per screen while building

There are two budgets, for two different moments, and they do not add up.

- **One fix round at milestone close**, for every finding source together (code review, visual,
  converge). The close's visual and build QA are report-only; the supervisor owns the one round
  and passes it the joined findings.
- **Two fix rounds per screen per design-system release** for visual work outside the close, the
  build loop of a screen under construction. After two rounds on one screen in one release, stop.
  What is left goes to the owner as a side-by-side list (reference next to build, one row per open
  item) to accept or send back. A new design-system release starts a new budget.

### What the close leaves: one disposition

After the one round, each residual finding gets one durable disposition, a row in `findings.md`
under `## Dispositions`: `| item | disposition | owner | reason | quote |`. `fixed` is the ticked
box. `accepted` or `deferred` needs a named owner (the one authorised to take it), a reason of a
few words and a quote: the engineer's own words, verbatim, at least eight words, which must equal one whole
sentence of one genuine user message of the session transcript, and that sentence names the item
id (the transcript is read only from Claude Code's folder for the repo, never from a path anyone
names, never through a link, and only files you own; hooks refuse any Write, Edit or shell write
into `~/.claude/projects`); words only the
agent wrote never count, nor do tool results, hook or command wrappers, reminders or attachments. The table is not locked at approval, because it
is written after it; the quote is the binding. A deferral names the milestone that builds it.

**Threat model.** This protects against a careless or over-eager agent settling a finding without
the owner. It does not stop someone with a shell who edits files by hand; that is out of scope. The Bash guard matches a normalised command text (quotes, `//`, `/./`, `~` and `$HOME` resolved), so it is a speed bump for a careless agent, not a sandbox: a variable, an encoded string or a script file gets past it. The owner quote stays the binding, because it must equal a sentence the engineer wrote in the transcript and the gate checks that. `blocked` is terminal: the gate stops with
`findings-blocked`. A `partly` or `not met` fact in `validation.md` is never cleared this way;
that needs a scope change with a new approval, or the milestone is held. `verify_gate.py
milestone` reads this table.

## Design-system audit and freeze (over about 20 screens)

For a UI change with more than about 20 screens, stage 2 adds a component audit before any
build. Walk every reference screen and compare each part with the design system. Collect every
gap in one list, ship one design-system release that closes them all, then freeze the release:
no further additions until the milestone is captured.

A screen that is done in the app and waits only on a missing design-system part gets the status
`waits-on-design-system` (a reference row in `marks.json`; `differs` names the missing parts).
It is not a failure and needs no accepted words. When the release ships, the row is checked again
and set to `match` or `differs`.

## Capture: one owner, one manifest, one pinned commit

One assessment (`cct:ux-assessment-run`) owns every capture of a milestone, in
`verify/shots/manifest.json`, keyed by build SHA, reference revision, screen, state, width and
zoom. Responsive, accessibility, build QA and the reviewer read those captures; none takes its
own. After a fix, only the affected cells are captured again, from the new build. A stale `qa.md`
is invalidated by its inputs (its recorded build against HEAD, the reference bytes), never reused
because the file exists. `marks.py check` enforces it: a capture or `qa.md` whose build differs
from HEAD in any file outside the changes folder, a changed reference, a shot missing from the
manifest, or one cell captured twice is a problem.

Capture all visual evidence from one build per milestone version, from a worktree pinned to one
commit. Never capture from the live milestone branch: merges moved the branch in the middle of a
capture and ruined a batch. Builders change code; the capture happens once, after they are done.
Capture each screen in one batch, twice, to prove it is stable. A screen whose two captures differ
is unstable and is fixed or ruled before it is judged.
