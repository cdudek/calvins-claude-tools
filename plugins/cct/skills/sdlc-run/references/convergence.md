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

### What the close leaves: one owner answer

After the one round, each residual finding is settled only by the owner's answer to an
`AskUserQuestion` dialog. The question text starts `Change <change id>, finding <finding id>: ` and
the options are fixed: `Fix it now`, `Accept as is`, `Defer to milestone <n>` and `Block the close`.
The gate reads the structured tool results of the session transcript (never free text, an agent
message, a tool output from elsewhere or a subagent), matches question to change id and finding id
and takes the selected option as the decision: `Accept as is` and `Defer to milestone <n>` settle,
`Fix it now` keeps the item open, `Block the close` is terminal (`findings-blocked`; it also stands
against a ticked box until the owner answers again). The latest answer for a finding wins; an
answer older than the finding's first appearance in `findings.md` is ignored. The transcript is
read only from Claude Code's folders for this repo (its working tree and its main checkout), never
from a path anyone names, never through a link, and only files you own; hooks refuse any Write,
Edit or shell write into `~/.claude/projects`. The same reader settles an unresolved visual row in
`marks.json`. There is no table to fill and no quote to copy.

**Threat model.** This protects against a careless or over-eager agent settling a finding without
the owner. It does not stop someone with a shell who edits files by hand; that is out of scope. The
Bash guard matches a normalised command text (quotes, `//`, `/./`, `~` and `$HOME` resolved), so it
is a speed bump for a careless agent, not a sandbox: a variable, an encoded string or a script file
gets past it. A fact that is `partly` or `not met` in `validation.md` is never cleared this way;
that needs a scope change with a new approval, or the milestone is held. `verify_gate.py milestone`
and `sdlc_status.py` read the answers through one shared reader (`marks.owner_decisions`).

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

For a change approved from 3.21.0 (its `lock.json` has `"manifest": "required"`; older changes keep
the lenient behaviour) the rules are strict: the manifest must exist when the change holds visual
work; each `build` is a full 40-character commit sha, never `HEAD` or a branch; each entry carries
the sha256 `reference` digest; each entry lists the `sources` (repo files or folders) of its screen
and the manifest lists `shared` dependencies, so a fix to screen A leaves screen B's cell valid and a
change to a shared file invalidates every cell; and `<spec>/qa.md` must exist and record its own
`Build: <sha>` line, which is checked against HEAD (the manifest's `qa` metadata is ignored). Fail closed: an unreadable `lock.json` counts as strict; a change with visual rows needs `qa.md` even without a spec folder or a manifest; every declared `sources` and `shared` path must be a plain repo path (no absolute path, `.` or `..`) tracked at HEAD. `lock.json` is protected after approval by `chain-gate.sh`.

Capture all visual evidence from one build per milestone version, from a worktree pinned to one
commit. Never capture from the live milestone branch: merges moved the branch in the middle of a
capture and ruined a batch. Builders change code; the capture happens once, after they are done.
**Capture once; capture again only a screen marked unstable or whose first judgement fails.** A
screen is not captured twice up front. If two captures of a screen exist they must agree: a screen
whose two captures differ is unstable and is fixed or ruled before it is judged.

## One record per screen (changes approved from 3.23.0)

A change whose `lock.json` has `"screens": "required"` keeps one file per approved screen,
`<change>/screens/<file>.json`, committed with the change (not in the ignored `verify/` folder,
which holds generated gate output only), so parallel helpers never write the same file and a
worktree hand-off carries the records. The screen id is the one `marks.py` derives from the approved
inputs (a note or loose image is its row id, such as `ref:asks/home.png`; a design bundle is one id
per html page, such as `bundle:asks/export/home`); one shared rule turns an id into the file name.
A record holds the status (`match`, `fixed`, `open`, `waits-on-design-system`, `ruled-out`,
`accepted-by-owner`), the frozen defect list (id, severity, layer, text, the build) and a snapshot of
the first review, `rounds` (fix rounds used in the approved design-system release), the release it
was last reviewed against, the build sha, and the sha256 of each capture with its build, state,
viewport and zoom. The files are written with `scripts/evidence.py` (`screen`, `review`, `round`,
`status`, `sheet`), under a lock and by atomic rename, never by hand. `marks.json` and the shared
manifest stay for older changes.

A screen is done only when it was reviewed against the approved design-system release (a re-approved
release makes older reviews not done), has a full 40-character build sha and a capture of that build,
and has no open High or Medium defect. `accepted-by-owner` needs the owner's recorded answer.

`marks.py check` fails: a screen with no record; a status that its record does not earn; a defect
added after the first review that is not High and not marked as a regression; a first-review defect
removed or edited; more than two rounds in one design-system release (send the side-by-side list to
the owner); two captures of one build, state, viewport and zoom that differ; a capture whose bytes no
longer match its recorded sha256. The round budget belongs to the approved release in `lock.json`:
a new release starts a new budget. Commit the records before the close: uncommitted ones block it,
and a later commit that changes or deletes one voids the pass.

`sdlc_status.py` prints `screens: 62 of 271 done · 40 wait on you · 50 wait on the design system ·
119 open` (271 is the approved inventory; done is match, fixed, ruled-out and accepted-by-owner that
earned it; a screen with no record counts as open).

## One owner sheet, answered once per group

Screens still open after their two rounds go to the owner as one sheet, not one dialog per
finding: `evidence.py sheet <change>` writes `<change>/owner-sheet.md`, one row per screen
(reference image, build capture, open defects, a blank "accept / send back" column), grouped by the
screen's `group`. The owner answers it once per group; `evidence.py sheet <change> --import`
records the answers in the screen records: `accept` becomes `accepted-by-owner`, `send back` reopens
the screen with a new round budget. Regenerating the sheet keeps answers and refuses to drop one
that was not imported.
