---
name: ux-assessment-run
description: "Coordinates specialist UX assessments and merges their verdicts into one findings document, at one of two scopes. scope=app audits the whole running app (every screen and state, every lens, three independent evaluators, an uncapped findings document, sitemap, glossary proposal and proposed guidelines); scope=change reviews one PR or branch (screenshots of every changed screen, always-run and shape-picked passes, merged by script and compared with the previous round). Delegates the verdicts to cct:ux-usability-audit, cct:ux-accessibility-audit, cct:ux-responsive-audit, cct:ux-rules-validate, cct:ux-usability-reviewer and cct:ux-sitemap-create. Use when the user says 'audit the whole app', 'run the ux assessment', 'ux review of this PR', 'review the ui changes of this branch', 'does it all fit together'. Skip for: a single-lens verdict, which belongs to cct:ux-usability-audit."
user_invocable: true
allowed-tools: "Bash(python3 */ux-assessment-run/scripts/*)"
metadata:
  version: 1.0.0
  author: calvindudek
---

# cct:ux-assessment-run

**Arguments:** `scope=app [extra builds: PR numbers or URLs] [focus]` or
`scope=change [pr-number | pr-url]` (defaults to the current branch's open PR).

This process coordinates; it does not judge. The verdicts come from the specialists it
dispatches: `cct:ux-usability-audit` (Nielsen, Shneiderman, the 30 Laws of UX, the dark-pattern
checklist), `cct:ux-accessibility-audit` (WCAG 2.2), `cct:ux-responsive-audit` (window sizes),
`cct:ux-rules-validate` (accepted guidelines, glossary, design system),
`cct:ux-usability-reviewer` (agent, independent critique of a diff or screens) and
`cct:ux-sitemap-create` (routes). It owns the briefing, the builds, the screenshots, the visual
pass, the merge and the report. It never changes the app, user data or a real device.

Shared files are in `references/`, two levels up from this skill's base directory:
`lenses.md`, `laws-of-ux.md`, `checklist.md`, `writing.md`, `finding-format.md`,
`rule-areas.md`, `conflicts.md`, `dispatch.md`, `visual-pass.md` and `findings.schema.json`.
Nielsen's ten and the dark-pattern checklist are this skill's own
`references/usability-heuristics.md`; the rendered-result categories and page-class rules are
its `references/visual-audit.md`. `$F` below is `${CLAUDE_SKILL_DIR}/scripts/findings.py`,
which validates, merges, renders and compares the passes' JSON; the visual ledger is checked by
`${CLAUDE_SKILL_DIR}/scripts/visual-check.py`. Do not type the findings document by hand.
Conflicts between rules are settled with `references/conflicts.md` (the precedence ladder); the
findings list every exception (`EX-<n>`) relied on. Every agent returns JSON in the shape of
`findings.schema.json`.

## Prerequisites

| Need | For | Without it |
|---|---|---|
| Python 3.10+ | Findings and visual checks | Report BLOCKED |
| Image-reading tool | Open the screenshots | Report BLOCKED for visual review |

## Shared steps (both scopes)

- **Setup.** Read `docs/ux/setup.md` if the repo has one. Missing: run `cct:ux-setup` first for
  `scope=app`; for `scope=change` the review still works without it, but there are then no
  known-safe fakes, so review from code unless the repo's e2e setup isolates user data.
- **Design documents.** Look for each one every time, before any reviewer starts: interaction
  guidelines, glossary, design system, decisions (`<designsDir>/INDEX.md`, default
  `docs/designs`, and the ADRs tagged `ux`; the old decision log only where it remains),
  exceptions register, product and audience (`PRODUCT.md`, `AUDIENCE.md`, `setup.md`). Take paths
  from `setup.md`, otherwise search `docs/ux/`, `docs/` and the repo root, and follow a router
  file such as `INTERACTION.md`. Record each as found (with path) or missing as `DOC-guidelines`,
  `DOC-glossary`, `DOC-design-system`, `DOC-decisions`, `DOC-exceptions`, `DOC-product` in
  `passes/documents.json` (dispatch.md section 5). A missing document is a finding on every run
  until it exists, never a reason to skip a pass: each pass runs against what exists and lists
  the checks it could not run under `did_not_run`. Hand the table to every reviewer.
- **Safety.** Never run against real user data or real devices. Only one agent may talk to a real
  device, and only to read: two apps talking to one device can corrupt its replies. Each extra
  build lives in its own worktree following the repo's worktree rules; never touch the main
  checkout.
- **Visual pass.** Follow `references/visual-pass.md`: open every screenshot with the
  image-reading tool, write `visual.json`, validate each issue against the repo's conventions
  with exactly one verdict, and write the retained findings to `passes/visual.json`. Then run
  `python3 "${CLAUDE_SKILL_DIR}/scripts/visual-check.py" "<run folder>" --repo "$PWD"`. Failure
  means the assessment did not run: repair it or report BLOCKED before any merge. Repeat after any
  new capture. Code-only output is BLOCKED for visual review; it cannot claim the screenshots
  comply.
- **Pass prompts.** Every dispatched pass gets the prompt shape of `dispatch.md` section 4: JSON
  only, every clean criterion in `passed`, every unchecked one in `did_not_run` with the reason,
  `finding-format.md`, its output path `passes/<pass>.json`, and `python3 "$F" validate <file>`
  run before it returns. Evidence rules apply: `seen`, `code` and `measured` need evidence,
  anything without it is filed as `assumption`, and codes belong in `id` and `location`, never in
  `summary` or `current`.
- **Laws pass.** Every check of every law in `laws-of-ux.md` on every screen and state in scope,
  each law marked pass, fail or not applicable with its evidence (a screenshot, a `file:line`, a
  count or a timing); a failed check is a finding with its check id (`L12.3`) as `id`. Delegate it
  to `cct:ux-usability-audit`; the file must pass
  `python3 "$F" validate <file> --expect L1-L30,B1-B14`.
- **Merge by script** (steps below, identical for both scopes): validate; a failing pass is sent
  back once with the errors, then goes under `did_not_run` and its file leaves `passes/`; the
  mandatory `visual` pass is never dropped. `python3 "$F" merge passes/*.json --skill
  cct:ux-assessment-run -o merged.json` removes exact duplicates only (same id, same place),
  lists every source, and never splits or drops. Settle every disagreement in the merge's `notes`
  with `conflicts.md` by correcting the pass file (its `impact`, or a `conflict` line and the
  exception in `exceptions_used`), then merge again. A pass that ran without its agent or skill
  sets `degraded`, and the rendered document prints a banner.

## scope=app: the whole-app audit

Findings first, decisions later. The audit documents; decisions follow in `cct:ux-decision-log`.

### 1. Write the briefing, and get it approved

Write `docs/ux/audits/<YYYY-MM-DD>/briefing.md`, the one brief every agent gets.

1. **Deliverables, in order:** findings; then the as-built and proposed sitemap; the glossary
   proposal; the proposed interaction guidelines with the enforcement map; and older UX documents
   marked `status: superseded` with a pointer (never deleted).
2. **The owner's words it answers:** quote every relevant request verbatim with its date.
3. **Scope:** every screen and state from `setup.md`, every build (main plus each PR in the
   arguments or in `setup.md`), the window sizes, the safety rules (what is read only, what may
   only be written against fakes).
4. **The checks.** C1 to C22 below, every lens in `lenses.md`, every point of `checklist.md`
   adapted to the platform, every rule area in `rule-areas.md`, every flow.
5. **The team** and **the finding format** (`finding-format.md`).

Show the briefing to the user and ask what is missing or wrong. Do not start agents until they
say go. A briefing change is cheap; a wasted audit is not.

### The checks

| # | Check | Produces |
|---|---|---|
| C1 | **Do the concepts fit together?** Every object and every action: where it appears, what it is called, how it looks and behaves on each screen. | One table per object and action, one row per screen; every differing row is a finding |
| C2 | **Hierarchy per screen:** its job, what users do most, whether visual weight matches. | Primary, secondary, tertiary as built and as they should be |
| C3 | **Sitemap against the object model:** run `cct:ux-sitemap-create as-built`; its checks SM-1 to SM-12 cover dead ends, orphans, one thing reachable or named two ways, no way back. | The as-built sitemap, checked against the glossary and product docs; its findings join the merge |
| C4 | **Jobs to be done:** every job, which screens, how many steps, where it breaks. | Job x screen: works, clumsy, broken, impossible |
| C5 | **List, detail, back, and unsaved work:** every way in and out, the back control, previous/next, unsaved work on every exit. | A table of every way in and out |
| C6 | **Page layout:** where navigation, header, toolbar, body and bottom bars sit on every screen. | A block diagram per screen; every departure is a finding |
| C7 | **Every control, instance by instance:** each control type (the project names them) in every place: look, size, label, keys. | One table per control type |
| C8 | **Tables and lists:** click, double-click, Enter, rename, row actions, multi-select, checkboxes, empty rows, cursor. | One row per list |
| C9 | **Where things open:** every popover, sheet, dialog, menu and page change: trigger, fit, stacking, buttons, Esc and Enter. | One row per surface |
| C10 | **Levels of detail:** what each dense view shows and what the user would want to show or hide. | Per view: shown today, could be switched |
| C11 | **Writing for the audience** (`writing.md`). | One finding per string or pattern |
| C12 | **One vocabulary:** term x place for every object, action and state; misspellings; outdated text. | The table; every clash a finding; the glossary proposal |
| C13 | **Visual design system:** fonts, sizes, colours, spacing, radii, icons, component look against the design system and siblings. | Findings with screenshots side by side |
| C14 | **Window sizes:** every main screen at every size in `setup.md`. | Screenshots and findings |
| C15 | **Every earlier request re-checked:** met, partly, not met, with what is on screen now. | One row per request, quoting it |
| C16 | **Every state:** empty, loading, error, not found, disconnected, and the product's own. | Screen x state table |
| C17 | **The keyboard:** every shortcut per screen; clashes; keys firing in text fields or dialogs; hints that lie; pointer-only actions. | Key x screen map and findings |
| C18 | **Pattern research:** for every decision-shaped finding, how the products in `setup.md` do it. | One line per product in supporting notes |
| C19 | **One interaction grammar:** today's behaviour in every rule area of `rule-areas.md`, across every build, and a proposed rule for each, with exceptions and flows. | Proposed interaction guidelines |
| C20 | **The rendered result:** the ten visual categories, typography specifics and performance-as-design in `references/visual-audit.md`, plus the AI-slop blacklist: would a designer at a respected studio ship this? | One finding per category, per screen |
| C21 | **Page-class rules:** classify each screen as marketing, app UI or hybrid and audit it against that class's hard rules in `references/visual-audit.md`. | One finding per breach |
| C22 | **Laws of UX, all thirty:** the laws pass above. | The coverage table per evaluator; one finding per failed check, citing its id |

### 2. The team

**Before spawning:** build every build once (main and each PR in its own worktree), so agents only
launch built apps and never rebuild the same folder at the same time. Write one `common.md` for
all agents: the briefing path, the builds and their folders, how to launch with the harness, the
safety rules, the inputs, where output goes. Keep agents' notes and screenshots outside the repo
(a scratch audit folder, `<scratch>`, under `${TMPDIR:-/tmp}/cct/audit/`) until the merge, so
independent evaluators cannot read them by accident.

Spawn all agents in one message so they run in parallel. Every agent gets `common.md`, its checks,
`finding-format.md` and its own output file `<scratch>/passes/a<n>.json`. Screenshots go to one
shared `shots/` folder, file names prefixed with the agent number. Every agent runs the app itself
with the test data and fakes from `setup.md`, and opens each image it judges with the
image-reading tool.

| Agent | Checks |
|---|---|
| 1 Concepts and structure | C1, C2, C3, C4, C18. Later, phase 2: C19 synthesis (run `cct:ux-guidelines-write draft`), flows, enforcement map, proposed sitemap (`cct:ux-sitemap-create proposed`) |
| 2 Navigation, layout, surfaces, states | C5, C6, C9, C16; C19 areas: navigation and return, side panels and detail pages, dialogs menus and popovers, feedback, progress and long operations, local work and external writes, connection to external systems, remembered state, first run and help, motion; checklist: navigation |
| 3 Controls, tables, detail, visual, sizes | C7, C8, C10, C13, C14 (window sizes through `cct:ux-responsive-audit`); C19 areas: editing, saving and unsaved work, confirmation and undo, lists and selection, forms and validation, search and filters, undo across the app, copy and paste, drag and drop, media playback; checklist: forms, responsive, performance |
| 4 Words, vocabulary, keys, earlier requests | C11, C12, C15, C17; C19 areas: keyboard and focus, platform conventions; the glossary proposal; checklist: content |
| 5 Accessibility | WCAG 2.2 through `cct:ux-accessibility-audit`; checklist: accessibility; the accessibility rules the guidelines must include |
| 6, 7 Heuristic evaluators | Every lens in `lenses.md` on the whole app, independently, through `cct:ux-usability-audit`, including C22 (each accounts for every law in its own file; the merge keeps every disagreement); they do not read earlier audits |
| 8 Heuristic evaluator: Codex | The same, run in the background with `codex exec -s workspace-write -C <its scratch folder> --skip-git-repo-check -o <scratch>/passes/a8.json "<prompt>"` from a script file, the prompt carrying the schema path and the JSON-only instruction. The prompt forbids reading other agents' notes and writing anywhere but its scratch folder. If the configured model needs a newer CLI than installed, run `npx -y @openai/codex@<latest> exec ...` instead. If Codex cannot launch the app, it evaluates the code and says so up front. |

Every rule area in `rule-areas.md` has exactly one owner in this table; check that before
spawning. Accepted-rule conformance checks are `cct:ux-rules-validate`'s job, not the agents'.

**Independence.** Evaluators 6, 7 and 8 do not see each other's notes, the other agents' findings
or the proposed guidelines until all three have submitted. Agent 1's C19 synthesis runs after every
other agent has finished, using their evidence, with wording and keyboard input from agent 4 and
accessibility input from agent 5.

If an agent or skill cannot load, record it under `did_not_run` in the audit's own
`<scratch>/passes/00-audit.json` (scope, method, and what did not run) and carry on.

### 3. Merge and write

- After the independent evaluators finish, run the visual pass (shared steps).
- Validate, then merge with `--skill cct:ux-assessment-run`, as in the shared steps.
- `python3 "$F" render <scratch>/merged.json -o docs/ux/audits/<YYYY-MM-DD>/findings.md
  --title "UX audit <YYYY-MM-DD>" --order location`: numbered F001 upward, grouped by place, with
  the method line of every agent, a degraded banner when one ran without its skill, totals by
  impact and by verification, then Passed, Not applicable and Did not run. Copy `merged.json`
  beside it as `findings.json`, so the next audit can be compared with this one.
- Send agent 1 into phase 2 with every agent's file: it runs `cct:ux-guidelines-write draft`,
  which writes the proposed rules into `docs/ux/interaction-guidelines.md` (every rule
  `status: proposed`), the flows and the enforcement map, and runs `cct:ux-sitemap-create
  proposed`, which writes `docs/ux/sitemap.md` and `sitemap.json`. Agent 4's glossary proposal goes
  to `docs/ux/glossary-proposal.md`.
- Mark older UX documents `status: superseded` with a pointer.

### 4. Report

Tell the user: the counts, the ten most severe findings in one line each, what did not run, and
where the files are. Offer `cct:ux-decision-log` as the next step. Never start implementing.

## scope=change: the review of one PR or branch

The same lenses and the same finding format as `scope=app`, scoped to one PR. Keep your own
commentary minimal: the deliverable is the consolidated findings.

### 1. Resolve the PR

- Arguments: a PR number or URL. Otherwise the current branch's open PR:
  `gh pr view --json number,url,title,headRefName,baseRefName`. None: stop and say so.
- `gh pr diff <n> --name-only`; keep interface files (components, screens, styles, strings,
  locales; adjust to the repo layout). None: stop, nothing to review.
- The PR's change has a spec folder (its change folder's `spec/`, or a `docs/ux/specs/` folder the
  PR or its ticket names; see the shared `references/spec-folder.md`): include
  `cct:ux-build-validate <change>` as the `spec` pass and run it when `qa.md` is missing there.
  Its findings join the merge, and the reviewers check against the spec instead of re-deriving the
  target from the diff.
- The PR adds, moves or removes a route: run `cct:ux-sitemap-create diff base:<base ref>` as the
  `sitemap` pass; its findings join the merge, including every moved address with no redirect.
- Make the run folder, outside the repo, and note the previous round of this PR first:

  ```bash
  base="${TMPDIR:-/tmp}/cct/review/<owner>-<repo>-<n>"
  prev=$(ls -1d "$base"/*/ 2>/dev/null | sort | tail -n 1)
  run="$base/$(date +%Y%m%d-%H%M%S)"; mkdir -p "$run/passes"
  ```

### 2. See it running

Build the PR's head in its own worktree with the test data and fakes from `setup.md`. Screenshot
every changed screen, and every changed dialog, menu, popover or select open, into `$run/shots/`,
then run the visual pass (shared steps) with `$run` as the run folder. If the app cannot be run,
say so in the report and review from code; that output is BLOCKED for visual review.

### 3. Pick the passes, then run them in parallel

Read `references/dispatch.md`. The always-run set (`documents`, `visual`, `conformance`, `laws`)
runs on every review; the matrix adds passes by the shape of the change, and a change you are
unsure about runs everything. Write `$run/passes/00-review.json` as dispatch.md section 5 says,
listing every pass not picked under `did_not_run` with `not dispatched: <row>`.

Dispatch the picked passes in one message, each with the prompt shape of dispatch.md section 4:
its pass name, the PR number, the interface file list, the screenshots folder, the documents
table, `finding-format.md`, the instruction to read the diff itself with `gh pr diff <n>`, and its
output path `$run/passes/<pass>.json`. The orchestrator owns `visual`; it is not dispatched again.
Every other pass opens any image it judges and sends new images and issues back to that ledger
before merge.

- `ux-usability-reviewer`: `cct:ux-usability-reviewer`; the prompt MUST begin with the line `MODE: review`.
  If the agent is not available, the pass runs anyway from `lenses.md` with `degraded` set.
- `heuristics`, `lenses`: `cct:ux-usability-audit`. `accessibility`: `cct:ux-accessibility-audit`.
  `responsive`: `cct:ux-responsive-audit`. Each runs what dispatch.md section 1 names for it.
- `laws`: the laws pass (shared steps), delegated to `cct:ux-usability-audit`.
- `conformance`: `cct:ux-rules-validate <n>` with the screenshots folder and the documents table.
- `e2e-coverage`: read-only, no server. One finding per new or substantially changed surface that
  no e2e spec exercises, with `cct:test-suite-run` named as the recommendation. It never writes tests.
- `sitemap`: route changes only; `cct:ux-sitemap-create diff base:<base ref>`, its checks
  (`SM-<n>`, `RC-<n>`) written as JSON findings.

### 4. Merge by script

Every step is a command; the markdown is its output.

1. Reconcile every pass's visual issues, run `visual-check.py` (shared steps), then
   `python3 "$F" validate "$run"/passes/*.json`. A missing or invalid `visual` findings file
   blocks the review; a failing pass is re-dispatched once, then goes under `did_not_run` in
   `00-review.json`.
2. `python3 "$F" merge "$run"/passes/*.json --skill cct:ux-assessment-run -o "$run/merged.json"`.
3. Read the merge's `notes`; settle every disagreement and rule conflict with
   `references/conflicts.md` (shared steps), then repeat steps 1 and 2.
4. `python3 "$F" render "$run/merged.json" -o "$run/findings.md" --title "UX review: PR <n>"`,
   adding `--previous "$prev/merged.json"` when the previous round's file exists. The header then
   carries Regressed, New, Persistent, Fixed (and Not re-checked) against that round.

### 5. Report

The report is `$run/findings.md` as rendered: the method line of every pass, a degraded banner when
a pass ran without its agent, the scope, totals by impact and by verification, the comparison with
the previous round, the findings in `finding-format.md`'s shape sorted Critical to Design choice,
then Passed, Not applicable, Did not run, the exceptions relied on, and the notes (where each found
design document lives). Missing design documents are findings with a `DOC-` id. Show it unchanged;
when it is long, give the path, the totals, the comparison line and the Critical and High findings
in one line each. Zero findings: the rendered text names every pass that looked; never shorten that
to "no issues".

### 6. Offer to post (never auto-post)

Ask: "Post these N findings as inline PR comments?" Only on an explicit yes:
- read the findings from `$run/merged.json`, never from the markdown;
- a finding whose `location` is `file:line` becomes an inline comment: summary, impact, current
  experience, recommendation, decision needed;
- screen-level findings go into the review summary, grouped by screen;
- follow the repo's punctuation and voice rules;
- print the PR URL afterwards.
