# agent-tracker

A Claude Code mod. It draws a band above every prompt and opens a `/tracker` pane that show each session's repo, work and state, and which sessions need you. It only observes: it never writes to a session, git, gh or bd.

Early access. The mod API is not stable and this build targets Claude Code 2.1.323.

## Install

```bash
claude plugin marketplace add cdudek/calvins-claude-tools
claude plugin install agent-tracker@cct
```

Restart Claude Code afterwards so the mod loads.

## What it keeps

- **Folder:** `~/.claude/agent-tracker/` is the only folder the mod writes. Each session writes its own file in `sessions/`.
- **Clipboard:** Copy puts the state on the clipboard as Markdown. The clipboard is not a file.
- **Settings:** `settings.json` in that folder holds the chosen view and whether the band is hidden.

## Things to know

- **Model calls:** the mod makes three kinds, each pinned to the alias `haiku`: sorting an ask into task or question, checking whether a turn's last message asks you a question, and reading that message for "you should know" and "decided without you" lines. `haiku` is an alias, so it can move to a newer model.
- **Question check:** it runs only in sessions that have the mod, and only when the last paragraph of the final message holds a question mark. A session without the mod stays done after a question.
- **Notes:** the lines read from a turn's last message (a message under 200 characters is skipped) are kept on that session's record, at most 50. In a repo that uses sdlc-run, open questions in `questions.md` and the plan's `## Revisions` are read as files. Marking a line seen is the only thing the pane writes, and it goes to `settings.json`.
- **Hide the band:** `/tracker band off` hides it in every session. `/tracker band on` brings it back. The `[–]` button does the same.
- **Board:** `/tracker web` opens `~/.claude/agent-tracker/board.html`. The Board button in the band runs it.
