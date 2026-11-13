---
type: checklist
change: 2026-11-13-agent-tracker
reviewer: fresh-context agent
created: 2026-11-13
---

# Requirements checklist: Agent tracker, milestone 1

Items test how `facts.md` is written, not whether the software works. Ticked only after the facts answer them.

## Gap

- [x] **Gap** (J12, F50) The Repo page shows PRs, worktrees and ended sessions but no milestone or feature list, so "follow it from repo to milestone to feature" has no fact.
  Answered: Out of scope: a milestone and feature view on the Repo page waits for milestone 2's web page (J12). F50 stays as is.
- [x] **Gap** (intent Proposed outcome, A7, F33) The intent says the band header names "the repo, the project and milestone", but no fact shows a project name.
  Answered: Out of scope: the project name in the band header (the milestone names the work). Out of scope line added.
- [x] **Gap** (spec Pane Home, Pane Session, Pane Repo controls; spec interaction Close) No fact defines Back, Home, Close, the breadcrumb, the hotkeys (`p`, `d`, `c`, `b`, `h`, `x`, `r`) or the two-step Escape.
  Answered: F88 (buttons and hotkeys per page), F89 (Back), F90 (Home), F91 (Close), F92 (two-step Escape), F113 (breadcrumbs), F23, F80, F112 (hotkeys).
- [x] **Gap** (spec interaction "Menu route") `/tracker details` and `/tracker compact` have no fact; only `/tracker band on|off`, `copy`, `session` and `repo` appear.
  Answered: F79 (`/tracker details` and `/tracker compact`).
- [x] **Gap** (spec screens, Band details Copy failed toast; Session Copied toast) No fact covers the copy-failed toast, or the "Resume command copied" toast; F36 and F49 give only the success path.
  Answered: F86 (Copy failed toast), F112 (Resume command copied toast), F36 reworded.
- [x] **Gap** (spec screens, Pane Session header, Usage) No fact states the Session header (state line with time in state, repo button, branch, PR link "#42") or the Usage fields "started" and "last activity".
  Answered: F103 (header), F104 (state line), F105 (branch and PR link "#42"), F106 (Usage, started and last activity).
- [x] **Gap** (spec screens, Pane Home Lists) No fact defines Running, Done and Ended today row contents (branch, duration, tokens, errors and retries when above 0), only the Needs you row (F40).
  Answered: F93 (Running row), F94 (Done row), F95 (Ended today row), F40 reworded (errors and retries), F96 (empty sections hidden).
- [x] **Gap** (spec screens, Pane Home Sections) No fact says Running and Done rows are grouped under repo headings, nor that a heading is a button reading "web-app · 2 PRs · 1 failing".
  Answered: F97 (repo heading button "web-app · 2 PRs · 1 failing"), F93 and F94 (grouped under repo headings).
- [x] **Gap** (spec screens, Pane Home Layout) No fact covers the pane's narrow layout: two-line rows below 70 columns, what drops below 40, "Only the title is cut".
  Answered: F99 (two-line rows below 70 columns, only the title cut), F100 (below 40 columns drops).
- [x] **Gap** (spec screens, Band details Layout and Interaction Narrow) F35 stops at "below 80 columns"; the fold into two rows of two below 60 `bodyColumns` and the 150 % header cuts (F33) have no fact.
  Answered: F83 (fold below 60 `bodyColumns`), F84 (header cut order at 150 percent), F33 reworded (branch left out), F35 kept.
- [x] **Gap** (spec screens, Band details Words) F35 gives four columns but not each column's line: oldest waiting, longest running, latest done, "1 failing · 2 mergeable".
  Answered: F81 (needs you, running, done lines), F82 (PRs "4 open" and "1 failing · 2 mergeable").
- [x] **Gap** (spec screens, Pane Repo Lists) No fact covers the Worktrees section rows, its sort (main checkout first, then most recent session), "No worktrees found.", "No open PRs." or "No repos yet.".
  Answered: F117 (Worktrees rows and sort), F118 ("No worktrees found."), F119 ("No open PRs."), F98 ("No repos yet.").
- [x] **Gap** (spec screens, Pane Repo Words) F59 gives one not-found string, but the Repo page has its own "No repo named ... has had a session."
  Answered: F121 (Repo not found string); F59 reworded to the session string only.
- [x] **Gap** (spec screens, Band compact Words) The "1 needs you" and "0 need you" (dim) forms of the count have no fact; F25 gives only the plural.
  Answered: F76 ("1 needs you"), F77 ("0 need you" dim).
- [x] **Gap** (spec screens, Pane Home Words "Durations") The duration format "6m", "2h 10m", "3d" and the "updated 2m ago" line have no fact.
  Answered: F125 (duration format), F101 ("updated just now" and "updated 2m ago").
- [x] **Gap** (spec interaction Refresh) No fact says the band and an open pane redraw once a minute so durations stay true; F30 covers only state changes.
  Answered: F126 (redraw once a minute).
- [x] **Gap** (spec screens preamble) "Colour never carries meaning alone: every glyph has a word or a count" is a rule with no fact or test.
  Answered: F124 (a word or a count beside every glyph).
- [x] **Gap** (F2, F3, F5, F6) Statuses and states `claude agents --json` can return beyond `busy`, `working`, `waiting`, `blocked`, `idle` and `done` (any other value) map to no session state.
  Answered: F66 (unknown status or state shows as running, raw value in the state line, never needs you).

## Ambiguity

- [x] **Ambiguity** (F7, F14, spec Repo Worktrees) The repo is "the folder of the git top-level path", but a worktree's top level is the worktree folder, so two testers could name the repo of a `.worktrees/login` session differently.
  Answered: F7 reworded (folder of the main worktree, the parent of `git rev-parse --git-common-dir`).
- [x] **Ambiguity** (F9, F10, F27, F48) "Branch belongs to an sdlc-run milestone" is undefined, and a repo with a `changes/` folder but a non-milestone branch falls between F9 and F10.
  Answered: F9 and F10 reworded (a `milestone.md` whose `branch:` equals the session's branch; a `changes/` folder alone is not a milestone).
- [x] **Ambiguity** (F9, F48, Assumptions "Feature complete") F48 lists the states "complete" and "merged" while the Assumptions count `done` or `merged` as complete; which stored state shows as which word is not written.
  Answered: F71 (complete is `done` or `merged`), F48 reworded ("complete" for `done`, "merged" for `merged`).
- [x] **Ambiguity** (F12) What counts as an ask in a transcript (tool results, sidechains, slash commands), and whether backfill covers only live sessions or also ended ones for Repos and Ended, is not written.
  Answered: F12 reworded (live or ended, active in 7 days), F70 (what counts as an ask).
- [x] **Ambiguity** (F13) "Read it by search, not whole" does not say what is searched for or what the result must contain.
  Answered: F13 reworded (a grep over the file; returns the fields of F12).
- [x] **Ambiguity** (F14) How often git and gh are polled, and for which repos (every repo, or those with a session in 7 days), is not written; the band's "PRs" count (spec: repos with sessions) has no stated scope.
  Answered: F67 (own repo, every 2 minutes), F14 reworded, F78 (band PR count over repos with a session in 7 days).
- [x] **Ambiguity** (F15, F57, F61) F15 says the kind is "task" or "question" but not who decides it or when; only F57 and F61 imply a `haiku` call.
  Answered: F15 reworded (the session's own mod, at `prompt.submit`, with `haiku`).
- [x] **Ambiguity** (F16) The derived ask statuses "in progress", "needs you" and "replied" have no stated rule for which session state or event produces each.
  Answered: F72, F73, F74, F75 (the rule for each ask status); F16 reworded.
- [x] **Ambiguity** (F28) "Below 40 columns" does not say terminal columns or `bodyColumns` (columns minus 5); the spec says `bodyColumns`.
  Answered: F28 reworded (`bodyColumns` below 40).
- [x] **Ambiguity** (F32, spec Band Alone) F32 keeps the needs-you segment and adds a note, but does not say that the Running and PR segments are replaced and the Work segment stays.
  Answered: F32 reworded (Running and PR segments replaced; needs you and Work stay).
- [x] **Ambiguity** (F29, F22) Whether `/tracker band off` hides the band in this session or every session, and whether it persists, is not written.
  Answered: F29 reworded (every session, kept in the settings file).
- [x] **Ambiguity** (F36) "Copy the state as Markdown" does not say which content (counts, every row, the header) the Markdown holds.
  Answered: F85 (Markdown content), F36 reworded.
- [x] **Ambiguity** (F40, F45) When this is the only live session and it waits, F40 lists it under Needs you while F45 shows "Only this session is running"; whether both show is not written.
  Answered: F102 (alone and waiting: listed as "this session"); F44 and F45 reworded.
- [x] **Ambiguity** (F43) The freeze is written, but not when the order is re-sorted (keyboard leaves the pane, next open); only the spec says it.
  Answered: F43 reworded (re-sorts when the keyboard leaves the pane or it reopens).
- [x] **Ambiguity** (F46, F59) How `/tracker session <text>` matches (title substring, id prefix) and what happens with several matches is not written.
  Answered: F122 (title substring, else id prefix, most recent on several; same for repo names).
- [x] **Ambiguity** (F49) `cd <folder> && claude --resume <id>` does not say whether a folder with spaces is quoted.
  Answered: F49 reworded (folder single-quoted).
- [x] **Ambiguity** (F51) "Then newest" does not say newest by creation or by update.
  Answered: F51 reworded (newest by creation time).
- [x] **Ambiguity** (F63, F36, F49) "Shall write only under `~/.claude/agent-tracker/`" collides with the clipboard writes of Copy; whether the clipboard counts is not written.
  Answered: F63 reworded (the clipboard is not a file).

## Conflict

- [x] **Conflict** (F5, F19) F5 marks every `idle` session done while F19 shows an `idle` session flagged by the question check as needs you; F5 states no exception.
  Answered: F5 reworded (idle is done unless the question-check flag is set).
- [x] **Conflict** (F52, spec Pane Home Stale) F52 gives the band string "session list unavailable · counts from 2m ago" for the band and Home, but Home's own string is "Session list unavailable. Showing what was read 2m ago. ...", and the band shortens to "stale 2m" below 60 columns.
  Answered: F52 reworded to the band string with "stale 2m" below 60 `bodyColumns`; F123 (Home's own Stale string).
- [x] **Conflict** (F1, F30) F1 polls every 5 seconds yet F30 requires every band to show a new count within 5 seconds, which a change just after a poll breaks.
  Answered: F30 reworded (by the next poll and its redraw).
- [x] **Conflict** (F34, F11, Assumptions "Background tasks") The spec header and Running now show background tasks, wake-ups and "background task · npm test · 2m", but the facts keep only subagents and background sessions.
  Answered: F11 reworded (subagents and background sessions); wake-ups added to Out of scope. spec/screens.md still names wake-ups and was not edited.
- [x] **Conflict** (spec screens Pane Session Sections, spec interaction Pane Session Live) screens.md orders Running now, Usage, Milestone, Asks; interaction.md orders Running now, Asks, Milestone, Usage; F46 follows screens.md, and the spec disagrees with itself.
  Answered: spec/interaction.md Live row now matches screens.md (Running now, Usage, Milestone, Asks); F46 unchanged.
- [x] **Conflict** (Open questions, intent Open questions 1, F3, F4) The intent leaves open whether `blocked` and `waiting` mean a permission prompt, while the facts say "None" and F3 maps both to needs you.
  Answered: Open questions now says the checked 2.1.323 mapping in `spec/ia.md` answers it.
- [x] **Conflict** (CLAUDE.md "One Claude Code plugin (`cct`) in `plugins/cct/`", Verification, Assumptions "Test layout") The facts test and place files under `plugins/agent-tracker/`, which the repo rules do not allow for.
  Answered: New Assumption: the design file says CLAUDE.md's "one plugin" line is updated when the mod lands; `plan.md` names `plugins/agent-tracker/`.

## Assumption

- [x] **Assumption** (F3, F4, F17, F18, F37) The facts rest on Claude Code 2.1.323 mod API fields (`waitingFor`, `turn.complete`, `bodyColumns`, `Svg`, `$.agent.list()`) and on managed machines skipping classic hooks, none of which is stated as an assumption.
  Answered: New Assumption: Mod API (2.1.323 engine types, checked 2026-11-13) and the managed-machine skip of `classic.*` hooks.
- [x] **Assumption** (F1, F8, F14, F30) Every session with the mod runs its own collector, but no fact says whether the polls of `claude agents --json`, git and gh are shared or repeated per session.
  Answered: F1, F67, F68, F69 and an Assumption (each session polls and scans for itself and writes its own file; the pane merges).
- [x] **Assumption** (F4, Assumptions "Reason text") "asks permission" depends on a `waitingFor` value whose content is "checked in the build", so F4 cannot be tested from the facts.
  Answered: F4 reworded and its Assumption: "asks permission" is tested against a `waitingFor` fixture recorded from a real session.
