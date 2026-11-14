---
type: ux-brief-write
mode: sdlc
change: 2026-11-14-tracker-session-cleanup
size: L
created: 2026-11-14
---

# Brief

This change is milestone agent-tracker-4 of the agent tracker. It builds on milestone 1's spec, `changes/2026-11-13-agent-tracker/spec/`, and on what was built after it. It adds no page. It fixes how a session's state and age read, and it adds three things to the pane: a Clear button on the Session page, a worktree offer inside Clear, and `/tracker tidy` with a quiet entry line on Home.

**Where this spec stands against milestone 1.** The pane was rebuilt after milestone 1 to follow the owner's mockups of 2026-11-14 ("Session detail", Home with "Your tasks not done"). Where milestone 1's `screens.md` and the built code differ, this spec describes the built code (`core/session-model.ts`, `core/pane-model.ts`) and says so. The owner's approved mockups win over anything new here, so nothing below redraws a built page. New controls are plain Buttons in the Session page's existing action row.

Job stories keep the numbers the intent gave them (J1 to J6). Milestone 1's job stories are written `M1-J<n>`.

## Owner Asks

The words are the asks in `intent.md`, copied exactly. Earlier briefs about the same screens: `docs/ux/owner-words.md` (the band, the pane, and the "observe only" decision of 2026-11-13) and the screenshot that came with A4 and A5, `changes/2026-11-14-tracker-session-cleanup/asks/2026-11-14/find-this-track-session-page.png`.

| Ask | Source | Words | Answered by |
|---|---|---|---|
| A1 | owner, chat, 2026-11-14 | "can we check which worktrees and open sessions we no longer need e.g. something that might happend over a month ago" | J5, `/tracker tidy`, the Tidy line on Home |
| A2 | owner, chat, 2026-11-14 | "if you look at the agent tracker as well" | J1 to J5 (the tracker side; the by-hand cleanup is in the handover) |
| A3 | owner, chat, 2026-11-14 | "I also want to close this sessions. is this something I can do?" | J3, the Clear button on the Session page |
| A4 | owner, chat, 2026-11-14 | "I wonder if there's also a way to, maybe from the panel, close a session and delete a work tree or ask to do that. Or maybe there's something more meta: as a supervisor I can launch a supervisor agent that launches subagents for the specific sessions and the sessions in question can be resolved gracefully (the ones that are not running, at least)." | J3, J4, J5, J6; Clear, the worktree offer, `/tracker tidy` |
| A5 | owner, chat, 2026-11-14 | "Something is running and it's more about sessions that are old. Once I see this, like the Spotify sessions (which I don't know when I ever touched) or an SES email session, I don't think that's relevant anymore. For some weird reason your task is not done. It's breathing there, popping up new and old ones but they are actually old. Not 100% sure here" | J1, J2; the state fix and the age line |
| A6 | owner, dialog, 2026-11-14 | "Fix the cause (Recommended), Clear button, Supervisor /tracker tidy" | all three: J1 and J2 (the cause), J3 and J4 (Clear), J5 (tidy) |

## Job Stories

Scenes from `docs/ux/setup.md`: S1 mid-prompt, S2 triage, S3 review. J5 is housekeeping, a rare job that happens in the S3 mood (the end of a day or week, reading what is left); no new scene is added.

| Job | Audience scene | Asks answered | Visible success |
|---|---|---|---|
| J1 When a background session has exited but Claude Code still lists it as blocked, I want the tracker to count it as ended, not as needing me, so I can trust that every needs-you row is real. | S2 triage | A5, A6 | The three sessions that showed as waiting on 2026-11-14 read "○ ended" and are absent from NEEDS YOU, the band count and the needs-you tasks. A spot check against `claude agents --json` finds no needs-you row without a `pid`. |
| J2 When I open the page of an old session, I want to see when it started and when it last did anything, so I can judge at a glance whether it still matters. | S3 review | A5, A6 | The page of a session idle 63 days reads "started 12 Sep 16:13  last activity 63d ago" and "○ ended 63d ago", never "since 16:13". |
| J3 When a session has ended but its asks still sit in "Your tasks not done", I want to clear the session and its open tasks from its page after one confirm, so I can stop the list from bringing back old work. | S3 review | A3, A4, A6 | Clear on an ended session's page, then one confirm that says what will happen. The result lines say what changed, in plain words, and Reopen tasks undoes the closing while the owner is on the page. The session's tasks leave Home. |
| J4 When a cleared session's worktree is clean and merged, I want to remove that worktree from the same page after one confirm, so I can clean up without opening a terminal. | S3 review | A4 | After Clear, the page offers "Remove worktree" with the reason it is safe; one press removes it; the branch stays. When it is not safe, a dim line says why. |
| J5 When many sessions and worktrees have gone stale, I want to start one tidy pass that checks each and asks me once per batch, so I can resolve them together without losing work. | S3 review | A1, A4, A6 | `/tracker tidy` ends with a report: what was cleared, what was kept and why. The Tidy line on Home is gone or shorter: it counts only what tidy can act on. Items that need a look are named in the report. |
| J6 When a session is still running, I want Clear and tidy to leave it alone, so I never stop work in progress by accident. | S2 triage | A4 | A running or live-waiting session's page has no Clear, only a line that says what to do instead. Tidy never collects a running session; its report names any worktree it skipped because a session is running in it. |

## Appetite

Size: L

## No-Gos

| No-go | Source | Reason |
|---|---|---|
| N1 Clearing, stopping or removing a session that still has a process (a `pid` in `claude agents --json`). | intent.md Constraints: "a running session is never stopped or removed"; A4 "the ones that are not running, at least" | Work in progress is never lost by accident (J6). |
| N2 Forcing anything: no `--force`, no `-D`, no discarding uncommitted changes or unpushed commits. | intent.md Constraints; owner's worktree rule | Removal never loses commits or changes. Ignored files (such as `.env`) go with a removed worktree; the offer lists them. |
| N3 Deleting a branch. | intent.md Constraints: "keeps the branch" | A worktree can be made again from its branch. |
| N4 Acting without the owner's press or command. The tracker never clears, removes or tidies on its own. | intent.md Constraints; owner, 2026-11-13: "ok never mind lets remove this intervention rules" | This change adds acting only on the owner's explicit action. |
| N5 Removing a worktree that is the main checkout, or that another live session is using. | J6; follows from N1 | A worktree under a running session is work in progress. Not in the intent: added here and recorded in Decisions Taken Here. |
| N6 A local path or an internal name in any word of the shipped plugin. | CLAUDE.md public repo rule; the task brief | Public repo. A worktree is shown by its folder name, never its path. |
| N7 Publishing tidy's output anywhere but the local transcript. | CLAUDE.md "Never publish to claude.ai" | Pages and reports stay local. |
| N8 A new button on the band, a hotkey shown anywhere, or a new section above "Your tasks not done" on Home. | owner rules, restated for this change: band buttons are spaced and show no hotkeys; open asks ("Your tasks not done") lead the dashboard; dashboards stay calm | The band and Home stay as the owner approved them. |
| N9 Actions on the Board (the web page). | design file: the Board is one local file and runs no commands | It can show a session as ended; it cannot clear one. |

## Visible Success

On the owner's next look, the needs-you rows are only sessions that are alive and waiting; the page of an old session says how old it really is; and from an ended session's page Clear and one confirm leave Claude Code's list and Home's task list without it, with the conversation still resumable. When its worktree is clean, pushed and merged, one more press removes it. `/tracker tidy` does the same for everything idle for 30 days or more that passes every check, asking once per batch, and ends with a plain report. The band looks exactly as before. Nothing running is ever touched.

## Ask Map

| Ask | Status | Where answered | Reason if set aside |
|---|---|---|---|
| A1 | answered | J5; `/tracker tidy`; Home, Tidy line | |
| A2 | answered | J1 to J5; the whole change | |
| A3 | answered | J3; Session page, Clear | The screenshot of A3 shows the band's "Your tasks not done"; the band gets no control (N8). The owner reaches Clear from Home's task row, so the path is band, Pane, task row, Clear. |
| A4 | answered | J3, J4, J5, J6; Clear, worktree offer, tidy | "ask to do that": the supervisor asks once per batch; "from the panel": the Session page |
| A5 | answered | J1, J2; state rule, age line | |
| A6 | answered | all three options | |

## Decided

Four questions were answered by the owner in a dialog on 2026-11-14. The answers are quoted as selected.

| Question | Owner's answer | Source | What the spec does |
|---|---|---|---|
| Should Clear ask for a confirm before it runs? | "Always confirm" | owner, dialog, 2026-11-14 | Pressing Clear opens one confirm every time Clear would write something. It says what will happen; focus lands on Cancel; "Clear session" runs it. Reopen tasks stays as the undo. |
| `claude rm` also deletes a worktree the session itself created, if safe. Is that allowed inside Clear? | "Allow, name it (Recommended)" | owner, dialog, 2026-11-14 | The confirm names it before the press ("If it made the worktree login, Claude Code also removes it, when that is safe.") and the result names it after. |
| `git worktree remove` deletes ignored files too. How does the offer treat them? | "List them in the offer (Recommended)" | owner, dialog, 2026-11-14 | The offer lists the ignored files it would delete: up to 3 names, then "and N more". The offer is never refused because of them. |
| Which word does the button use? | "Keep "Clear" (Recommended)" | owner, dialog, 2026-11-14 | The button on the Session page stays "Clear". |

## Open Questions

| Question | Recommended answer | Why it matters |
|---|---|---|
| After a worktree is removed, the copied resume command points at a folder that is gone. | The page says so and draws no resume button; the conversation file is kept, and resuming needs the worktree made again from the branch. Stage 3 confirms resuming works from a made-again folder. | The brief says the conversation is "resumable". |
| Should `/tracker tidy` take a number of days? | No: fixed at 30 days (A1: "over a month ago"). Add an argument when 30 proves wrong. | Fewer words to learn; the band-and-pane vocabulary stays small. |
| Which model do tidy's check subagents use? | The mod's rule (haiku) is for the mod's own calls. Tidy's subagents are the owner's Claude session spawning agents; recommend haiku for the read-only checks and the session's own model for the supervisor that acts. | The "cheap model" hard rule in `docs/ux/setup.md` reads "every model call pins haiku". |
| Where does tidy run? | In the session where the owner typed `/tracker tidy`. | The supervisor asks the owner questions, so it must be a session the owner is looking at. |
| Should "Copy resume command" return to ended sessions only? | Yes. Milestone 1 said so (F005); the built page shows it on every session; Clear sits beside it. | Resuming a live session starts a second process on it. |
| Should a forgotten task of an ended session age out sooner than 7 days? | No. It is real unfinished work; Clear is the answer. Revisit after a week of use. | A5 calls the list "breathing"; the state fix alone removes the 63-day rows, because tasks older than 7 days never list. |
