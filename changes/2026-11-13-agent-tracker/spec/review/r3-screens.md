# Reviewer 3: screen critique (loop pass, text only)

Reviewer: `cct:ux-usability-reviewer`, review mode, 2026-11-13. Persisted by the supervisor (review mode cannot write). Counts: Critical 0, High 10, Medium 19, Low 9.

## Severity 3

1. interaction.md: "arrows scroll" in the pane, but the elements matrix says session rows move by "Tab and arrows". Pick one; with Tab only, a long Home is a long Tab walk.
2. screens.md Home puts the Partial and Stale line in a footer; interaction.md puts Stale at the top of the pane.
3. interaction.md J11 has Enter on "session on the PR's branch" opening Session; screens.md makes the PR row a Box with a Link and Text, so that session has no control.
4. interaction.md J2 says Asks is "first after the header"; screens.md puts Running now before Asks.
5. interaction.md says redraw only when data changes, "never more often"; screens.md shows times that must tick ("6m", "goal 14m", "updated 3s ago"). State a timed redraw.
6. Session: Milestone and Usage come after an unbounded Asks list, scrolled by arrows only; J3 and J4 land there and are buried. Put a short Usage and Milestone block above Asks, or cap the Asks.
7. Session at 100 %: the ask row spends 3 + 9 + 13 cells on number, kind and status; in a 24 to 54 dock that leaves 10 to 29 cells for the ask text. Use the two-line row in every dock.
8. Repo PR row at 100 % is a one-line row of about 80 cells against a dock of 54 at most; at 150 % the failing-checks state sits in the dim line, the fact J11 exists for.
9. Ended sessions are off Home, but J2 and S3 assume a Home row; after a run the session is usually ended, so the S3 path is Repos line, Repo, Ended, Session (4 moves). Add an "Ended today" line or section.
10. Two-line Home rows put wait time and reason in the dim line; needs-you rows should keep them in normal colour.

## Severity 2

- Band drop order differs between 100 % (Work first) and 150 % (goal age first). Use one order.
- Stale at 75 columns is not in the drop order; Stale with no earlier good read has no defined view.
- Details needs-you column shows only the oldest session; details height and the cut rule for the needs-you line between 80 and 114 columns are unspecified.
- Counts are inert, though J6 is "dig from a count". Make "● 2 need you" open Home.
- No duration format above minutes (hours, days). "Running for" is ambiguous between turn and session.
- Home repeats a repo heading under both Running and Done; Done has no cap or age cutoff.
- Needs-you rows have no branch or worktree and no title fallback; the fallback when `waitingFor` is absent is undefined.
- At a 24-column dock the Running dim line and repo headings overflow; the drop rule exists only at 150 %. The Repos line's wrap and focus order are unspecified.
- Alone shows "the work segment and a dim note", losing Needs you (J10). Does Home list this session when alone?
- Session has no pending state while classification runs; "Not classified: ran without the tracker" is false for a failed model call.
- Ask rows: no text-length cap; status reads "replied" on all but the last row; a time column is listed but never placed.
- Session and Repo have no Loading or Stale state; interaction.md mentions "bd" with no UI or string.
- The band's PR count scope ("repos with sessions") does not match Home headings (live) or the Repos line (7 days).
- The band view is machine-wide, so Details in one session changes band height in every other session mid-typing (S1 layout shift).
- Widths assume no hotkey hint on buttons; there is no on-screen cue for `ctrl+x tab` or the letter keys.
- S3's "done" is not shown anywhere; asks with "replied" give no outcome.
- Repo lists Worktrees before Open PRs, pushing the J11 list down.
- "feature 2 of 4" (brief, interaction) against "2/4" (screens).

## Severity 1

- The ✓ glyph means both a done session and passing checks.
- "↓ mergeable" is an unusual glyph.
- Copy has no job story.
- The PR row sample repeats the PR title as "(session)".
- The Milestone line's Words sample holds a literal "…".
- The details header repeats the milestone in the branch.
- `/tracker band off` is undiscoverable.
- The band state diagram misses the Alone transitions.
- Back and Home duplicate each other on a Session opened from Home.
