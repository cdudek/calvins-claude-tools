---
name: review-feedback-run
description: "Coordinates handling of code feedback from a GitHub PR (worktree, CI failures, merge base, push, per-thread resolve), from findings in the conversation, from free text or from a fix set: it delegates diagnosis and disposition to cct:review-feedback-analyze, then drives test-first remediation (a failing test, then the minimal fix, through the agents cct:test-behavior-writer and cct:review-fix-implementer), verifies, and finalizes the PR. Use when someone says 'address the review feedback', 'fix the review comments', 'resume this PR', 'the PR is failing CI', 'resolve the review threads', 'rebase and fix this PR'. Skip for: opening a new PR, owned by cct:git-pr-run; diagnosis without any change, owned by cct:review-feedback-analyze."
allowed-tools: "Bash(gh *) Bash(wt *) Bash(git *) Bash(bash */review-feedback-run/scripts/*) Bash(bash */github-manage/scripts/*) Read Write Edit Grep Glob Agent EnterWorktree ExitWorktree mcp__claude_ai_Linear__save_issue mcp__linear__save_issue mcp__claude_ai_Linear__list_teams mcp__linear__list_teams mcp__claude_ai_Linear__list_issue_labels mcp__linear__list_issue_labels"
user_invocable: true
metadata:
  version: 1.1.0
  author: mpapis
---

# Address Feedback

Verification and every push follow the [local-first contract](../sdlc-run/references/local-first.md); read it before running checks or preparing a push.

Investigates and addresses code feedback from any source — PR reviews + CI, conversation context, or free text. Triages into an actionable summary, then executes fixes using Phase RED/GREEN.

Each subcommand selects the references it needs. The `pr` subcommand additionally handles worktree entry, CI failure classification, staleness (merge base, since the PR already exists), PR finalize (push + body update), and per-thread resolve/comment actions on GitHub (with confidence proposals + user override). The `chat`, `message`, and `fix-set` subcommands always run in-place in the current directory. The `fix-set` subcommand is **autonomous** — it consumes a pre-triaged fix set from a review-code-run run (`$STATE_DIR/fix-set.json`), so it skips the user-selection gate and never files Linear tickets (deferred items become DISCUSS).


## Scannable PR text (required)

- **Order:** `## What` → `## Why` → `## Proof` → `## Before merge` (only while something is open) → the repo's Decision4 section (only with `boundary-map.yaml`) → `## Decision record` (only at Migrate/Answer).
- **Bullets:** Every section is a list; start each bullet with a bold label (`- **Source plan:** 0 adds, 8 updates, 38 destroys.`). Keep one idea per bullet, at most two lines, and no paragraph longer than two sentences. Keep checklist syntax and bold-label the item.
- **Proof:** Name the check and result (`- **Unit tests:** 1,320 passed.`). Put links on the label or result, never a bare URL in prose. Preserve claims and human checklist attestations when restructuring an existing body.
- **Decision4:** When the repo has a boundary map, read it and copy the exact readable section from its PR template. Select its highest applicable class in bold with one colour circle and a sentence explaining recovery; use bold-labelled Recovery steps (numbered for multiple steps), optional Work preserved, Responsible for recovery (a named person at Answer), and Classification change. Keep the Recovery levels legend collapsed. Never author old plain `Decision-Class:` lines.
- **Decision record:** At Migrate/Answer use `## Decision record` with bold-labelled bullets: Chose, Over, Because, Commits us to. Never use “Repair, choice story:” headings; Repair needs no decision record.
- **Milestone and review text:** The same layout covers milestone-close PRs, issue bodies and PR comments. Put addressed feedback under What, its rationale under Why and its check results under Proof. A short thread reply can be one bold-labelled bullet; include only applicable sections.
- **Validation:** Validate the proposed body before pushing and the actual body after creation or edits through the repo's Decision4 gate when installed. Use `--body-file`; scannable formatting applies even without Decision4.

Read the full [body example](../sdlc-run/references/pr-body.md) before writing a PR, milestone-close body, issue or review reply.

## Routing

The user input is: $ARGUMENTS

Read the first word as the subcommand and route to its file, passing the rest on as arguments.

| Subcommand | Does |
|---|---|
| `chat` | No arguments expected — reads findings from the current conversation context → `references/commands/chat.md` |
| `fix-set` | The user input is: $ARGUMENTS → `references/commands/fix-set.md` |
| `message` | The user input is: $ARGUMENTS → `references/commands/message.md` |
| `pr` | The user input is: $ARGUMENTS → `references/commands/pr.md` |

No subcommand, or one that is not in the table: say
`Usage: /cct:review-feedback-run <chat | fix-set | message | pr>`
and ask which one they meant. Never guess — the subcommands do different things.

## Triage Action Verbs

Universal action verbs and PR-specific verbs (FLAKY → Linear, MERGE) are defined in `../role-review-vocabulary/SKILL.md` (see Action Verbs and Triage Classification Rules sections).

**MERGE on stale branches:** the `pr` subcommand always operates on an existing PR, so when the branch is behind base it uses a merge commit (standard — avoids force-pushing a branch with an open PR).

## Commands

| Command | Description | Arguments | Worktree | CI / staleness | Push + threads |
|---------|-------------|-----------|----------|----------------|----------------|
| `/address-feedback pr` | Gather PR feedback + CI + staleness, investigate, triage, execute, propose thread actions, finalize, apply thread actions | `<pr_number>` | enters | yes | yes |
| `/address-feedback chat` | Parse conversation context findings, triage, execute | none | in-place | no | no |
| `/address-feedback message` | Free text input as feedback, investigate, triage, execute | `<text>` | in-place | no | no |
| `/address-feedback fix-set` | Autonomously address a pre-triaged fix set from a review-code-run run — no user gate, no Linear | `<state_dir>` | in-place | no | no |
