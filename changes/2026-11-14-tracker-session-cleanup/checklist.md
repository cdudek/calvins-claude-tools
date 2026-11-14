---
type: checklist
change: 2026-11-14-tracker-session-cleanup
reviewer: fresh-context agent
created: 2026-11-14
---

# Requirements checklist: Tracker shows only live sessions and clears dead ones

Items test how `facts.md` is written, not whether the software works. Ticked only after the facts answer them.

## Gap

- [x] **Gap** (F5, F7, spec ia Open Questions) Last activity is shown and measured, but no fact says where the time comes from.
  Answered: F71 (newest of last prompt, turn end and transcript's last line; none known reads "last activity unknown").
- [x] **Gap** (F1, F9, spec ia "Ended session") No fact keeps this session's own id from being ended, nor says a background `done` row is ended even with a `pid`.
  Answered: F72 (own id never ended; background `done` stays ended); F1 reworded.
- [x] **Gap** (F8, F10, F15, F29, F32) "Open task" is used for Clear's work but never defined, and tasks over 7 days never list.
  Answered: F8 reworded (an open task is a task Home lists for the session, F15).
- [x] **Gap** (spec interaction "Cleared") No fact says where focus goes after a Clear; F13, F18 and F40 cover only the first draw, the confirm and the offer.
  Answered: F73 (Keep worktree, else Copy resume command, else Home crumb; never Reopen tasks).
- [x] **Gap** (F28, F61) Clear's error lines cut the reason at 60 cells, but tidy's report line for a failed item has no reason or cut.
  Answered: F61 reworded (reason after the item, cut at 60 cells); Assumption added.
- [x] **Gap** (F57, F59, F65) The supervisor is a model session, yet only the mod runs checks and `claude rm`; no fact says how the supervisor reaches them.
  Answered: F59 reworded (only through the mod's checked functions, never `claude rm` or git itself); Assumption "Supervisor's actions" leaves the mechanism to `plan.md`.
- [x] **Gap** (F57, rule MODEL-1) F57 cites MODEL-1 but names no model for the gathering subagents or the supervisor.
  Answered: F57 reworded (subagents `haiku` and read only; supervisor the session's own model, no change before the batch answer); Assumption added.

## Ambiguity

- [x] **Ambiguity** (F31, F66) "Reopen tasks" does not say whether it survives a pane re-open, nor whether a tidy pass can reopen what it closed.
  Answered: F31 reworded (lives only while the owner stays on the page; tidy offers no reopen); Assumption added.
- [x] **Ambiguity** (F48) "Its folder's last change" could mean the folder entry or anything inside, and a cleared session's worktree has no stated rule.
  Answered: F48 reworded (the folder's own modified time; every session that used it, cleared or not; no second rule); Assumption added.
- [x] **Ambiguity** (F49) "Last verdict" of an ask does not say where the verdict is stored.
  Answered: F49 reworded (the last stored verdict in the tracker's ask record).
- [x] **Ambiguity** (F58) "Clear all 5" and "Skip these 5" do not say what the number counts once a batch splits at 25.
  Answered: F58 reworded (the number is the size of that batch).

## Conflict

- [x] **Conflict** (F1, spec ia "Ended session" and Decisions) ia.md limited the no-`pid` rule to `blocked` or `done` rows; F1 and the supervisor decision say every row.
  Answered: F1 stands (decision of 2026-11-14); ia.md reworded to match; Assumption "Rows with no `pid`".
- [x] **Conflict** (F52, F55, spec screens Tidy words) F52 drops the closing periods and F55 and screens.md keep them, so one string has two spellings.
  Answered: F52 reworded to the screens.md strings, with the periods.

## Assumption

- [x] **Assumption** (F1, F4, F11) The ended rule rests on every live row carrying a `pid`, which is not stated as an assumption.
  Answered: Assumption "Rows with no `pid`" (every live row checked on 2026-11-14 carried one; the F4 guard stays).
- [x] **Assumption** (F25, F43, F46) The facts rely on what `claude rm` does (keeps the conversation, may remove a worktree the session made) without recording it.
  Answered: Assumption "`claude rm`" (with the owner's "Allow, name it").
- [x] **Assumption** (F53) The hand-off by `$.prompt.submit({ text })` is unverified and has no fallback.
  Answered: Assumption "Hand-off" (checked against a fixture at build; fallback a plugin skill recorded in `plan.md`).
- [x] **Assumption** (F35 condition 4) "Merged into the default branch" does not say how the default branch is found.
  Answered: Assumption "Default branch" (origin HEAD, then `main`, then `master`; else the PR alone, F38).
