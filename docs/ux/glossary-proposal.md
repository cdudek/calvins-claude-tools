---
type: ux-glossary-proposal
updated: 2026-11-13
---

# Glossary proposal

One word per meaning, one meaning per word. Filled in by an audit; the change's `spec/ia.md` alias table proposes terms before anything is built.

| Term | Meaning | Band | Pane | Web page | Docs | Finding |
|---|---|---|---|---|---|---|
| Clear | Takes an ended session off Claude Code's list and closes its open tasks, after a confirm. The conversation is kept. | none | Session page button, confirm | none | setup.md, ADR |  |
| Remove | Removes a merged, clean worktree after the owner presses Remove worktree. The branch stays. Not used for sessions. | none | Session page offer | none | setup.md, ADR |  |
| Tidy | The skill `git-cleanup-run`: clears many stale sessions and worktrees, one question per batch. Not a tracker feature: the tracker has no Tidy. | none | none | none | README, ADR |  |
| idle | How long since a session's last activity ("idle 41d", the skill's 30-day rule). Also Claude Code's status for an interactive session that waits for nothing, which counts as done. | count | state word | none | design |  |
| ended | A session whose row in Claude Code's list has no process, or that Claude Code reports done. | none | Session header, Home | none | design |  |
| last activity | The newest of a session's last prompt, last turn end and last transcript line. Reads "last activity unknown" when none is known. | none | Session facts line | none | design |  |
| started | When the session started, in local time ("started 12 Sep 16:13"). Never "since". | none | Session facts line | none | design |  |
