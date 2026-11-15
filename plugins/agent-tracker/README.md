# agent-tracker

A Claude Code mod. It draws a band above every prompt and opens a `/tracker` pane that show each session's repo, work and state, and which sessions need you. It acts only on your press and never on its own. It writes outside its folder in two ways, both from a button on an ended session's page and both after a confirm: `claude rm` takes the session off Claude Code's list (the conversation is kept), and `git worktree remove` removes a clean, pushed, merged worktree (never forced, and the branch is kept). It never stops a running session and never deletes a branch. The skill `/agent-tracker:git-cleanup-run` does the same for sessions and worktrees idle 30 days or more, and asks you once per batch.

Early access. The mod API is not stable and this build targets Claude Code 2.1.323.

## Install

```bash
claude plugin marketplace add cdudek/calvins-claude-tools
claude plugin install agent-tracker@cct
```

Restart Claude Code afterwards so the mod loads.

## What it keeps

- **Folder:** `~/.claude/agent-tracker/` is the only folder the mod keeps files in. Each session writes its own file in `sessions/`.
- **Outside it:** only the two writes above, after your press or your answer.
- **Clipboard:** Copy puts the state on the clipboard as Markdown. The clipboard is not a file.
- **Settings:** `settings.json` in that folder holds the chosen view and whether the band is hidden.

## Things to know

- **Model calls:** the mod makes three kinds, each pinned to the alias `haiku`: sorting an ask into task or question, checking whether a turn's last message asks you a question, and reading that message for "you should know" and "decided without you" lines. The reading also says how each open task of the session stands (done, partly, not started, or replaced by a later ask): the same call, no extra one. `haiku` is an alias, so it can move to a newer model. The skill's subagents also run on `haiku` and only read.
- **Question check:** it runs only in sessions that have the mod, and only when the last paragraph of the final message holds a question mark. A session without the mod stays done after a question.
- **Notes:** the lines read from a turn's last message (a message under 200 characters is skipped) are kept on that session's record, at most 50. In a repo that uses sdlc-run, open questions in `questions.md` and the plan's `## Revisions` are read as files. In those files, an item older than 24 hours counts as seen. Marking a line seen, Keep and Close on a task, and Clear and Reopen tasks (which close and reopen a session's open tasks) go to `settings.json`. The two writes above are the only others.
- **Automated runs:** a session whose transcript says `sdk-*` (or that `claude -p` started) is left out of every list and count and makes no model call.
- **Not checked:** a task with no verdict in a finished or idle session is not called forgotten. Once per session, the session holding the poller lease asks haiku about it (one call on the session's asks and what the agent wrote after the first), and never again.
- **Tasks not done:** the task asks that no verdict, merged change or Close has finished, in the band, on Home and on the Board. A task is forgotten when its session ended or has been quiet for more than 30 minutes, superseded when a later ask may have replaced it, in progress otherwise.
- **Hide the band:** `/tracker band off` hides it in every session. `/tracker band on` brings it back. The `[–]` button does the same.
- **Board:** `/tracker web` opens `~/.claude/agent-tracker/board.html`. The Board button in the band runs it.
