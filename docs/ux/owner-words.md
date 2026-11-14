---
type: owner-words
updated: 2026-11-13
---

# The owner's words about the interface

Verbatim, dated, grouped by topic. Quote from here; never cite a request by number. The full first brief is in `changes/2026-11-13-agent-tracker/asks/2026-11-13/owner-brief.md`.

## What the tracker is for

- 2026-11-13, chat: "In a nutshell what I want is to understand what is happening across different projects, repositories, and work trees. I want to understand who is working, what agent is working on what, and which agent needs attention."
- 2026-11-13, chat: "I want to see where we are from everywhere, ideally in a dashboard."
- 2026-11-13, chat: "I want to understand which repository is what, what has been done, what work has been finished, what's unfinished, and whether there are open PRs and where they stand."
- 2026-11-13, chat: "Also how many tokens were used, what it struggled with, and how many retries it has. It was kind of like a monitoring tool and task tracker that I have locally."

## Asks: tasks and questions

- 2026-11-13, chat: "Every time I add a task I want to differentiate whether there is a task or a question that I ask. If there is a task I want to have it added chronologically in a list."
- 2026-11-13, chat: "It might be the case that a task gets made redundant by a decision further down the line so we need to evaluate that as well."
- 2026-11-13, chat: "we should always use a cheap model for that, can we specify that?"

## Progress and structure

- 2026-11-13, chat: "If I have a long-running loop with a plan, I want to understand what the breakdown of those things is."
- 2026-11-13, chat: "How does the work I asked for per repository work? Can I explore it, dig into one, and navigate inside this app? I suppose I can but what does the detail page look like? What are milestones and this type of milestone, and do milestones have subtasks?"
- 2026-11-13, chat: "Things may or may not be connected to Linear so there might be Linear tickets or Linear projects and we need to structure this. It might be that we use BEADS as an issue tracker or GitHub projects."

## Surfaces

- 2026-11-13, chat: "Should we have a TUI, like a TypeScript user interface?"
- 2026-11-13, chat: "also I think I'd rather have a webpage then a tui" and "like what ponytail has"
- 2026-11-13, dialog: "1 and 2" (a pane mod and a standalone UI; the standalone UI later became the web page)
- 2026-11-13, chat: "I like the agent. The triage queue has the cleanest interface in my opinion yet but I am not sure."

## The band

- 2026-11-13, chat: "there should also be a feature to compact it"
- 2026-11-13, chat: "ponytail also has this little menu. if you click on compact you ge tthis one liner, and when you click on board you get the web page. we could have something similar for us." Screenshots: `changes/2026-11-13-agent-tracker/asks/2026-11-13/ponytail-band-details.png`, `ponytail-band-compact.png`.
- 2026-11-13, chat: "I also wonder if it could actually show the repo or project name, and description of what is currently developed. and whether a goal is running or something is running on the current session?"

## Things to know and decisions taken without the owner

- 2026-11-13, chat: "can we also include something like the \"you should know\" mod as well as decisions that were made without me. Does this make sense?"

## Independence and limits

- 2026-11-13, chat: "it doesnt do this automatically does it? so it can also work without sdlc-run?"
- 2026-11-13, dialog: "Fully standalone"
- 2026-11-13, chat: "ok never mind lets remove this intervention rules" (the tracker observes; it never steers the agent)
