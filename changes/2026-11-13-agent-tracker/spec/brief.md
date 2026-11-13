---
type: ux-brief-write
mode: sdlc
change: 2026-11-13-agent-tracker
size: L
created: 2026-11-13
---

# Brief

This change is milestone 1 of the agent tracker: the band above the prompt and the pane, inside Claude Code. The web page (milestone 2) and the insights (milestone 3) are designed only as far as milestone 1 must leave room for them.

## Owner Asks

The words are the asks in `intent.md`, copied exactly. Earlier briefs about the same screens: the decisions in `docs/designs/agent-tracker.md` (owner, 2026-11-13) and the two ponytail screenshots in `asks/2026-11-13/`. The terminal mockups the owner reviewed were local files and are not in the repo; what they settled is in the design file's Decisions.

| Ask | Source | Words | Answered by |
|---|---|---|---|
| A1 | owner, chat, 2026-11-13 | "I want more cloud mods. When can we do it? What can we do? What can we do visually? Should we have a TUI ..." (excerpt; full brief in `asks/2026-11-13/owner-brief.md`) | J1, J2, J3, J4, J11 |
| A2 | owner, chat, 2026-11-13 | "we should always use a cheap model for that, can we specify that?" | no-go N4 (no interface) |
| A3 | owner, chat, 2026-11-13 | "can we also include something like the \"you should know\" mod as well as decisions that were made without me. Does this make sense?" | J8, milestone 3; milestone 1 leaves the band column slot |
| A4 | owner, chat, 2026-11-13 | "there should also be a feature to compact it" | J5 |
| A5 | owner, chat, 2026-11-13 | "also I think I'd rather have a webpage then a tui" and "like what ponytail has" | milestone 2; milestone 1 has no Board button |
| A6 | owner, chat, 2026-11-13 | "ponytail also has this little menu. if you click on compact you ge tthis one liner, and when you click on board you get the web page. we could have something similar for us." | J5, J6 |
| A7 | owner, chat, 2026-11-13 | "I also wonder if it could actually show the repo or project name, and description of what is currently developed. and whether a goal is running or something is running on the current session?" | J7 |
| A8 | owner, chat, 2026-11-13 | "How does the work I asked for per repository work? Can I explore it, dig into one, and navigate inside this app? I suppose I can but what does the detail page look like? What are milestones and this type of milestone, and do milestones have subtasks?" | J3, J6 |
| A9 | owner, chat, 2026-11-13 | "I like the agent. The triage queue has the cleanest interface in my opinion yet but I am not sure." | J1 (pane Home is the triage queue) |
| A10 | owner, chat, 2026-11-13 | "it doesnt do this automatically does it? so it can also work without sdlc-run?" | J9 |
| A11 | owner, dialog, 2026-11-13 | "1 and 2" | the band and pane (this milestone); the web page (milestone 2) |
| A12 | owner, dialog, 2026-11-13 | "Fully standalone" | J9, no-go N5 |

## Job Stories

Scenes from `docs/ux/setup.md`: S1 mid-prompt, S2 triage, S3 review.

| Job | Audience scene | Asks answered | Visible success |
|---|---|---|---|
| J1 When I run sessions across several repos and worktrees, I want to see every session and which ones wait for me, so I can answer the blocked one first. | S2 triage | A1, A9 | The band names the session that has waited longest and for how long; the pane's Home lists waiting sessions first. |
| J2 When I type a prompt in a session, I want each ask kept in order as a task or a question, so I can see what I asked for, chronologically. | S3 review | A1, A2 | The pane's Session page lists the asks numbered in order, each marked task or question. |
| J3 When a long loop with a plan runs, I want to see the breakdown of milestones and features and where they stand, so I know how far the work is. | S3 review | A1, A8 | In an sdlc-run repo the band header shows the milestone and "feature 2 of 4"; the Session page lists the features with their state. |
| J4 When I want to know how a session is doing, I want to see tokens, tool errors and retries per session, so I can spot where it struggles. | S3 review | A1 | Each session row shows tokens; errors and retries show when above zero. |
| J5 When I open the prompt of any session, I want a compact line that counts what needs me, so I can stay aware without leaving my work. | S1 mid-prompt | A4, A6 | One line above the prompt: "● 2 need you" and the oldest waiting session. |
| J6 When I want details, I want to switch the band to details or open the pane, so I can dig from a count to one item. | S1 mid-prompt, S2 triage | A6, A8, A9 | One click on Details shows columns; one click on Pane opens the list; one more opens a session. |
| J7 When I look at a session, I want to see its repo, project, what is being developed, and whether a goal or other work runs, so I can tell sessions apart at a glance. | S1 mid-prompt | A7 | The band header reads like "calvins-claude-tools · agent-tracker-1 · feature 2 of 4 · goal 14m · 2 subagents". |
| J8 When an agent finishes a turn, I want to see what I should know and what it decided without me, so I can overrule a call before it spreads. | S3 review | A3 | Milestone 3. Milestone 1 shows nothing for it and reserves its band column. |
| J9 When I use a repo without sdlc-run, I want the same view from sessions, git, gh and bd alone, so I do not depend on one process. | S1, S2, S3 | A10, A12 | A repo with no `changes/` folder shows sessions, branch and PRs; the header uses the session title instead of a milestone. |
| J10 When I forget to check on sessions that waited, I want pushed attention, not a list I must poll, so I do not lose time to a blocked agent. | S1 mid-prompt | none (assumed) | The band in every session updates by itself and the count turns to the warning colour. |
| J11 When I want one place for open PRs, I want to see each PR's state next to its session, so I know what is left to merge. | S3 review | A1 | The pane's Repo page lists PRs with checks, review and mergeable state, and the session on that branch. |

## Appetite

Size: L

## No-Gos

| No-go | Source | Reason |
|---|---|---|
| N1 Writing to a session or an agent: no hidden notes, no automatic continue, no queued answers. | intent.md Constraints; owner: "ok never mind lets remove this intervention rules" | The tracker observes; it never steers. |
| N2 A terminal UI as its own program. | A5 | The owner chose a web page instead (milestone 2). |
| N3 Any server, port or hosted page. | design file, Web page decision; repo rule "never publish to claude.ai" | The page is one local file. |
| N4 Any model but `haiku`. | A2 | Cost. Not visible on screen. |
| N5 Depending on another memory or workspace tool. | A12 | Standalone. |
| N6 Closing, removing or archiving anything (a task, a worktree, a session). | design file step 7: "only the owner closes a task"; research note on force-removed worktrees | Observe only; a proposal at most. |
| N7 Internal names, people or local paths in committed fixtures or screenshots. | CLAUDE.md public repo rule | Public repo. |

## Visible Success

In any Claude Code session the owner sees one line above the prompt: how many sessions need them, which one has waited longest, and what runs in this session. One click shows the details; `/tracker` opens a pane where waiting sessions come first, each repo's sessions and PRs follow, and any session opens to its asks in order. The running count matches `claude agents --json` on every spot check.

## Ask Map

| Ask | Status | Where answered | Reason if set aside |
|---|---|---|---|
| A1 | answered | J1, J2, J3, J4, J11; band and pane | |
| A2 | answered | no-go N4; facts, not screens | |
| A3 | deferred | J8, milestone 3 | Collecting the items needs milestone 3's model pass; milestone 1 reserves the band column and the Home section. |
| A4 | answered | J5, band compact view | |
| A5 | deferred | milestone 2 | The page is its own milestone; milestone 1 shows no Board button until it exists. |
| A6 | answered | J5, J6, band buttons | Board button waits for milestone 2. |
| A7 | answered | J7, band header row | |
| A8 | answered | J3, J6, pane pages | |
| A9 | answered | J1, pane Home as the triage queue | |
| A10 | answered | J9 | |
| A11 | answered | band and pane now, web page milestone 2 | |
| A12 | answered | J9, no-go N5 | |

## Open Questions

| Question | Recommended answer | Why it matters |
|---|---|---|
| Show the Board button in milestone 1, before the page exists? | No: add it in milestone 2. | A button that does nothing breaks trust in every other button. |
| Show the "you should know" and "decided without you" columns in milestone 1? | No: they appear in milestone 3, when something fills them. | Empty columns cost band width on every prompt. |
