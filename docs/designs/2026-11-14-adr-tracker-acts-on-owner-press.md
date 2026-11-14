---
title: The tracker acts on the owner's press; cleanup is a skill the owner triggers
type: adr
status: accepted
created: 2026-11-14
tags: [agent-tracker, safety, cleanup]
---

# The tracker acts on the owner's press; cleanup is a skill the owner triggers

## Decision

- **Chose:** the tracker acts, but only when the owner presses a button on a Session page. Cleanup of many stale sessions and worktrees is a script the owner starts through the skill `git-cleanup-run`, and the script acts only on the ids the owner picks in the skill's question.
- **Over:** staying observe-only, and a supervisor inside the tracker (a Tidy line on Home, a `/tracker tidy` command, a model that launches subagents and removes things).
- **Because:** the owner asked for it, and a script can check safety where a model cannot be trusted to.
- **Commits us to:** a confirm before anything that cannot be undone, the five checks of a removable worktree, no force, branches kept, a tracker free of cleanup, and the owner merging the PR.

## Context

On 2026-11-13 the owner made the tracker observe only: "ok never mind lets remove this intervention rules". Its setup file carried the hard rule "Observe only".

On 2026-11-14 the owner found dead background sessions listed as waiting, and asked for a way to close them:

- "I also want to close this sessions. is this something I can do?"
- "I wonder if there's also a way to, maybe from the panel, close a session and delete a work tree or ask to do that. Or maybe there's something more meta: as a supervisor I can launch a supervisor agent that launches subagents for the specific sessions and the sessions in question can be resolved gracefully (the ones that are not running, at least)."

In a dialog the owner chose "Fix the cause (Recommended), Clear button, Supervisor /tracker tidy". The change then built the first two. Later the same day the owner rejected the supervisor inside the tracker and chose a skill: "I think you are right it shouldnt be part of the tracker, but there should be another skill in the same plugin that I can trigger". The dialog answers were "Code acts, Claude reports (Recommended)" and "agent-tracker, git-cleanup-run (Recommended)".

## Options

- **Observe only (the 2026-11-13 rule).** Safe and simple. It leaves the owner clearing sessions and worktrees by hand in a terminal, which they did for 72 worktrees and 6 sessions. It cannot answer the ask.
- **Act on the owner's press, and a skill for batches (chosen).** Each write follows a press or an answer. It adds two writes to a public plugin: `claude rm` and `git worktree remove`. It needs the checks below.
- **A supervisor inside the tracker (rejected by the owner, 2026-11-14).** One tidy pass from Home. It puts a model between the owner and the writes and gives the tracker standing power. The owner said it should not be part of the tracker.

## What the tracker and the skill do

- **Clear:** on an ended session's page, Clear opens a confirm with focus on Cancel. Clear session runs `claude rm` for a session that has a job id and no process, and closes the session's open tasks. The conversation is kept.
- **Remove worktree:** after a Clear, or when only a worktree is left, the page offers to remove the session's worktree. Remove worktree runs `git worktree remove` without force from the main checkout. The branch stays.
- **The skill:** `git-cleanup-run` lists ended sessions and linked worktrees idle 30 days or more, with the result of every check. Haiku subagents only read and summarise. The skill asks the owner once per batch. The script's `act` takes the chosen ids, re-checks each and acts only on those that still pass.

## The five checks

A worktree is removable only when all five hold, each computed by code, in the tracker and again in the script:

1. It is a linked worktree, not the main checkout.
2. It has no modified, staged or untracked files.
3. It has no commits that are not pushed.
4. Its branch is merged into the default branch, or its pull request is merged or closed.
5. No live session has its folder at or under the worktree.

Ignored files do not refuse a removal. The offer names them first, and secret-looking names are always listed.

## Consequences

- **Never force:** no `--force`, `-f`, `-D`, `--force-remove-worktree` or `--discard-unpushed` anywhere. A test greps both source trees.
- **Never stop a session:** no `claude stop`, and no `claude rm` for a session whose latest read shows a process.
- **Branches kept:** neither the tracker nor the script deletes a branch.
- **Nothing on its own:** every tracker write follows a press. Every script write follows `act` with ids the owner chose. No model runs `claude rm` or a worktree removal.
- **The tracker stays free of cleanup:** it has no tidy line, no `/tracker tidy`, no `$.prompt.submit` and no `$.tool.register`. The band and the web Board gain no control.
- **Public docs name the writes:** the README, the plugin description and the marketplace description say the tracker acts on a press, so a user who installs it is told.
- **Model calls:** the mod adds none. The skill's subagents use `haiku` and only read.
- **The owner merges the PR:** this change is Repair, so auto-merge is never armed.

## Decision record

- **Chose:** acting on the owner's press in the tracker, and cleanup by a script the owner triggers through the skill `git-cleanup-run`.
- **Over:** staying observe-only (the owner's decision of 2026-11-13), and a supervisor inside the tracker (rejected by the owner on 2026-11-14).
- **Because:** the owner asked to close sessions and remove worktrees from the panel, and chose a skill with a script that acts and a model that only reports.
- **Commits us to:** the confirm, the five checks, no force, branches kept, and a tracker without cleanup. It also commits us to keeping the README, the plugin description and the marketplace description honest about the two writes.
- **How to undo:** the tracker's two writes are behind buttons. To go back to observe-only, remove Clear and the offer from the Session page and delete the skill folder. A cleared session does not return to Claude Code's list. Its conversation file stays. A removed worktree can be made again from its kept branch.
- **Responsible for recovery:** the plugin owner.
