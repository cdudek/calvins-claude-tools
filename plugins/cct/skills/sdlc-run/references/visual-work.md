# Visual work: capture, inspect, record

Every rule about capturing a screen, looking at it and recording the verdict lives here. The
stages, [heavy work](heavy-work.md) and [convergence](convergence.md) point to this file; the round
budgets, the severity scale and the owner's answer stay in convergence. The layers and tolerances
live in `../../ux-build-validate/references/build.md` (Measurements) and the shared
`visual-pass.md` (section 5).

## Changes approved from 3.25.0: the app's own screenshots (lock `"visual": "app"`)

A design tool is direction, never a gate. The screens are built in the real app and the owner approves
screenshots of the real app; the approved shots become exact visual tests (the same renderer against
itself).

1. **Plan (Stage 2).** The UX plan writes `screens.json` in the change folder: one entry per screen and
   state, `{"id": "leads.list.empty", "route": "/preview/leads?state=empty", "viewport": [1440, 900],
   "fixture": "<scenario name>"}`, and names the one sample-data fixture the app seeds.
2. **Build (Stage 5).** Every entry gets a preview page in the app that renders that screen and state
   with the fixture (dev and test builds only; the repo decides how, for example a `/preview` route
   behind an environment flag). A milestone whose `screens.json` has an entry with no reachable
   preview is refused.
3. **Capture (Stage 6, one batch).** Every entry is shot at its viewport, twice; two different shots of
   one entry mean the page is unstable, which is a problem to fix. The latest shots are
   `verify/shots/<entry>.png`.
4. **Approval.** `python3 scripts/evidence.py gallery <change>` writes `verify/gallery.html`: one
   offline file, every shot grouped by screen, with its route and accept / send back. The owner
   downloads `answers.json` and the agent runs `evidence.py gallery <change> --import answers.json`:
   an accepted shot is copied to `screens/<entry>.png` (tracked) and its sha256 goes into
   `screens/approved.json` with the approver and the date; a send back removes the entry and prints
   `reopened: <entry>`. An answer for a shot that changed after the gallery was made is refused.
   Regenerating the gallery never touches an approval.
5. **Exact tests.** From then on the gate compares each entry's capture with its approved sha256
   (zero tolerance; `visual.threshold` in `sdlc.json`, default 0). A difference fails with the entry
   name and a diff image path, and needs a new approval.
6. **Status.** `screens: N of M approved · K changed since approval · L not captured`.

Retired for these changes: design-bundle pinning, `marks.py` rows against bundles and references, the
six-layer geometry tolerances and the design-system audit tied to board counts (the design-system pin
stays).

## Changes approved before 3.25.0

A change whose lock has no `"visual": "app"` keeps the process below unchanged. Read the lock, not the
version of the skill.

## Capture headless, never in the owner's browser

Capture real screenshots headless: `agent-browser` CLI first, or Playwright
headless through the repo's E2E setup. This is reproducible, works in CI, and never uses the
person's own browser session. Never use Claude in Chrome or any tool driving that browser.
Captures are heavy work and run through the queue (`python3 scripts/heavy.py run -- <command>`,
[heavy work](heavy-work.md)).

## The shared visual pass (milestone close, Stage 6 step 2)

- Capture every changed screen and control open, in the states and widths the plan names. Keep the
  fresh shots under `changes/<id>/verify/shots/`, with change-relative paths in `shot`.
- Require the shared visual pass from each UX run: open every image, including responsive
  and state captures, with the image-reading tool, and validate each issue against the repo's
  documents with the same three verdicts: `violates` with a quoted rule, `allowed by` with its
  decision or exception (remove from fixes), or `no convention` (keep it; propose
  `cct:ux-decision-log`). Require the review's visual ledger and one convention verdict per issue.
  Run the Laws of UX and conformance passes too. Include late feature captures before the final check.
- Never post the review's comments.
- A failed check means the review did not run; the gate and report must say FAIL or BLOCKED. An
  earlier PASS cannot clear it. Use the checker path and current run returned by
  `cct:ux-assessment-run`.

## Marked screens and referenced wireframes

For a marked screen or referenced wireframe, run `python3 scripts/marks.py init <id>`, then capture
every marked and referenced screen headless into `verify/shots/`, at the mark's width. Match the
screen, state and width, including populated fixtures and open controls; an admin screen cannot
prove a partner-screen fix.
Open each original/build pair with the image-reading tool and fill every `marks.json` row
against the owner's words as refined by its ADR. Reuse the shared visual pass and its ledger;
`marks.json` records the comparison, not a second inspection ledger. Missing states are coverage
gaps, not inferred passes. A `ruled-out` note needs its ADR, not a screenshot.
Supplied marks and reference images still require comparison, even when the UX skill is skipped.

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

## Evidence

- **Evidence is one file per screen.** `evidence.py record` writes `<dir>/<screen>.json` with the shot's
  hash and a hash of each text-catalogue key the screen shows. Parallel helpers never write the same
  file, and a ledger edit conflicts with nothing.
- **"Changed since capture" is checked per text key.** `evidence.py stale` names each screen whose own
  keys changed, so one new button label recaptures the screens that show it, not every screen.

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
