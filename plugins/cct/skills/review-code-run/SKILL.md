---
name: review-code-run
description: "Coordinates a code review as independent evidence plus finding validation: PR modes (pr, pr-deep, pr-max), local changes (changes, changes-max) or specific files (files, files-max), with a second independent model (OpenAI Codex CLI) when it is installed. It delegates the review passes to the agents cct:review-code-runner, cct:review-code-reviewer and cct:review-dimensions-selector, acceptance-criteria grading to cct:review-criteria-auditor and every finding to cct:review-finding-validator, then merges and posts the report. Covers code correctness only. Use when someone says 'review this PR', 'run a code review on my changes', 'deep review of these files', 'check this PR for bugs', 'co-review with codex'. Skip for: security-focused differential review, owned by cct:review-security-run; UX critique of a PR's UI, owned by cct:ux-assessment-run; dependency bumps, owned by cct:review-dependency-run."
allowed-tools: "Bash(gh *) Bash(git *) Bash(bash */review-code-run/scripts/*) Read Grep Glob Agent EnterWorktree"
user_invocable: true
metadata:
  version: 2.1.0
  author: calvindudek
---

# Code Review Skill

## Prerequisites

| Requirement | Needed for | How to check | If missing |
| --- | --- | --- | --- |
| `gh` CLI, authenticated | every `pr*` mode | `gh auth status` | Stop. Tell the user: `gh auth login`. |
| `jq` | every mode | `command -v jq` | Stop. Tell the user: `brew install jq`. |
| `codex` CLI, authenticated | Codex co-review (optional) | `scripts/codex-available.sh` (`codex --version`, `codex login status` or `OPENAI_API_KEY`) | `auto` degrades to Claude-only and says so; `--codex` stops with the fix: `npm install -g @openai/codex`, then `codex login`. |
| `rsync` | Codex co-review | `command -v rsync` | Same as above — the sanitized mirror cannot be built without it. |
| `CODEX_MODEL`, `CODEX_MODELS`, `CODEX_REASONING` (env, optional) | Codex co-review | `jq -r '.models[].slug' ~/.codex/models_cache.json` | Model: `CODEX_MODEL` if set, used as-is. Otherwise the first `CODEX_MODELS` entry — slugs or globs, default `*-sol *-terra`, frontier models left off on purpose — that matches the account's `models_cache.json`; among one glob's matches the lowest `priority` (newest) wins, so a new model generation needs no edit. No match → the pass fails, lists the offered models and gives the `~/.claude/settings.json` `env` line to set; no readable cache → the first literal entry, or a failure if all are globs. `CODEX_REASONING` defaults to `high`. |

`references/codex-lane.md` runs the Codex checks; do not ask the user to confirm them.

## Routing

The user input is: $ARGUMENTS

**First, strip the Codex flags** — they may appear anywhere in `$ARGUMENTS`, and every mode
accepts them. Remove the matched token before parsing anything else, then set `$CODEX`:

| Token in `$ARGUMENTS` | `$CODEX` | Meaning |
|---|---|---|
| *(none)* | `auto` | Co-review with Codex when it is available; degrade to Claude-only when it is not. |
| `--codex` | `on` | Require Codex. Stop with the fix instruction when it is unavailable. |
| `--no-codex` | `off` | Claude-only, even when Codex is available. |

Both tokens together → report the conflict and stop. `references/codex-lane.md` owns
everything that happens next with this value; the modes and lanes only pass it through.

Then parse the first remaining word as the command name. Route to the matching command file, passing remaining args as $ARGUMENTS:

| Command | Arguments | Description |
|---------|-----------|-------------|
| `pr` | `<pr_number>` | Quick diff-only review → `references/commands/pr-quick.md` |
| `pr-deep` | `<pr_number>` | Thorough worktree-based review with multi-agent validation → `references/commands/pr-deep.md` |
| `pr-max` | `<pr_number>` | Per-dimension agent-orchestrated PR review (validate-all, diff-scoped) → `references/commands/pr-max.md` |
| `changes` | `[base_branch]` | Deep review of local branch changes → `references/commands/changes-deep.md` |
| `changes-deep` | `[base_branch]` | Explicit alias for `changes` → `references/commands/changes-deep.md` |
| `changes-max` | `[base_branch]` | Per-dimension agent-orchestrated version of `changes` (diff-scoped) → `references/commands/changes-max.md` |
| `files` | `<path> [path2] ...` | Focused review of specific files/dirs (code-as-is, not diffs) → `references/commands/files-deep.md` |
| `files-deep` | `<path> [path2] ...` | Explicit alias for `files` → `references/commands/files-deep.md` |
| `files-max` | `<path> [path2 ...]` | Per-dimension agent-orchestrated review of a file-set/dir (one reviewer per dimension, validate-all) → `references/commands/files-max.md` |

If `$ARGUMENTS` is empty or no command word is recognized, tell the user: "Usage: `/cct:review-code-run pr <pr_number>`, `/cct:review-code-run pr-deep <pr_number>`, `/cct:review-code-run pr-max <pr_number>`, `/cct:review-code-run changes [base_branch]`, `/cct:review-code-run changes-max [base_branch]`, `/cct:review-code-run files <path...>`, `/cct:review-code-run files-max <path...>` — any mode also takes `--codex` / `--no-codex`"

## Codex co-review

Every mode except `pr` (→ `references/commands/pr-quick.md`, which persists no `findings.json` and has no
merge step, so it has nowhere to put a second source) can run a second, independent reviewer:
the OpenAI Codex CLI, read-only, over the same surface, at the same time as the Claude
reviewers. It is **one more source of findings**, not a second pipeline — its findings merge
into the same `findings.json` and are validated by the same independent per-finding validators.
Read `references/codex-lane.md` before the lane — it owns all three `$CODEX` states, including
`off`.

## Policies & principles

Before executing the routed command, read `references/policies.md` — it carries the shared policies that apply to every mode: autonomy (validate-all, no cost/scope gates), GitHub posting (never automatic), worktree, error handling, the per-mode rules (changes / files), and large-PR routing, plus the review principles and the GitHub error reference.

## Common mistakes

Each row is a failure this skill's own history produced, not a hypothetical.

| Mistake | Do instead |
|---|---|
| A finding with no `failure_scenario` | If you cannot name inputs and a wrong outcome, you have not established a defect. Drop it. |
| Treating `reversibility` as a synonym for severity | Severity ranks urgency; reversibility decides whether it can wait. `entrenches` at `nit` is a real combination. |
| Deferring an `entrenches` finding to a follow-up ticket | The deferral is what makes the fix expensive. It is `fix-first` now. |
| Reading a matcher's behaviour instead of probing it | `probe-pattern.sh`, twice — the claimed input and a control that should disagree. |
| Giving the validator a shell so it can "run the artifact" | Its whole input is attacker-controllable diff text. The orchestrator probes; the validator judges. |
| Probing by running the script under review | That is arbitrary execution of untrusted code. Probe the matcher in isolation, or accept `unverifiable`. |
| A resolved thread read as an addressed concern | Declined ≠ resolved. Did the code change, or was a reason given the code supports? |
| Handing Codex `$ROOT` and asking it not to read secrets | Read-only stops writes. Withhold by absence — the sanitized mirror. |
| Showing one model the other's findings before both finish | Anchored agreement proves nothing, and agreement is the reason to run two models. |
| A guard that asserts a word is present | A presence check survives any rename of the thing it names. Assert the exact construct, or test the behaviour. |
| Posting to GitHub without being asked | Never automatic. Present findings; post only on an explicit request. |
| Reporting a check as passed without its output | Run it, paste what it said, or say plainly that it did not run. |

## Red flags — stop

- About to emit a finding you cannot write a failure scenario for
- About to file an `entrenches` shortcut as a nit, or as a follow-up ticket
- About to claim a matcher's runtime behaviour from reading alone
- About to widen a permission — a validator's tools, a Bash allowlist — to satisfy a rule that cannot be followed. Narrow the rule instead
- About to add a fallback that sends the unsanitized review root when the mirror step fails
- About to resolve a cross-model disagreement by picking the more confident wording
- About to write `assert "<word>" in text` as a contract guard
- About to report a verdict of `ship` while a confirmed `entrenches` finding stands
- About to say a check passed when you did not run it, or ran it in an environment where it could not fail
