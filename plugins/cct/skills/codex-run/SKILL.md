---
name: codex-run
description: |
  Run the OpenAI Codex CLI headlessly inside Claude Code against a prompt and a target, with a chosen
  model and reasoning level. A general Codex-exec wrapper — use it to get a non-Claude model to review,
  refactor, explain, or propose edits. Use when the user asks to "run codex", "codex review", "codex
  refactor", "codex edit", "run Codex CLI", or wants a "second opinion" from Codex on some code. For a
  full PR-review pipeline with Claude and Codex reviewing together, use the pr-review skill instead;
  this skill runs one Codex pass and reconciles nothing.
allowed-tools: "Bash(codex *) Bash(git *) Read Write Grep Glob AskUserQuestion"
user_invocable: true
metadata:
  version: 1.0.0
  author: hejhugo
---

# Run Codex CLI (Headless)

Run the OpenAI Codex CLI in non-interactive mode via `codex exec`, from inside Claude Code. This skill does one thing: it hands a prompt and a target to Codex with the model, reasoning effort, and sandbox you choose, then returns Codex's output.

It does **not** run a competing Claude analysis or reconcile two models. If you want a full review pipeline that does — Claude reviewers and Codex on the same surface, merged, then validated per finding — that is `pr-review`, which co-reviews with Codex whenever the CLI is available (`--codex` to require it, `--no-codex` to skip it). Keeping this skill to a single Codex run is deliberate — no task-type branching, no duplicated review flow.

## Prerequisites

| Requirement | How to check | If missing |
| --- | --- | --- |
| Codex CLI on PATH | `codex --version` | Stop. Tell the user: install with `npm install -g @openai/codex`, then re-run. |
| Authenticated | `codex login status` succeeds, **or** `[ -n "$OPENAI_API_KEY" ]` | Stop. Tell the user: run `codex login` (ChatGPT account) or export `OPENAI_API_KEY`, then re-run. |

Check these yourself in Step 0 — do not ask the user to confirm them.

## Parameters

All have defaults, so the skill runs without interrogating the user. Take any that the user supplied in their request; only ask (Step 1) for what is genuinely missing.

| Parameter | Default | Notes |
| --- | --- | --- |
| `model` | `gpt-5.5` | Passed as `-c model="<model>"`. |
| `reasoning` | `high` | Passed as `-c model_reasoning_effort="<level>"`. One of `low`, `medium`, `high`, `xhigh`. |
| `sandbox` | `read-only` | Codex reads but cannot write/create/delete (OS-enforced). Only widen if the user explicitly wants Codex to edit files. |
| `prompt` | — | What Codex should do. Required. |
| `target` | current branch diff vs `develop` | The files/dirs/diff to act on. |

## Step 0 — Preflight

Run the two Prerequisites checks above. Only continue if both pass.

## Step 1 — Resolve parameters

Fill each parameter from the user's request, falling back to the defaults in the table.

- If the user gave no `prompt` (e.g. bare "run codex"), use AskUserQuestion to ask what Codex should do and offer the common starting points: review the code, suggest refactorings, or make a specific edit. Whatever they pick becomes plain instructions in the `prompt` — there is no separate code path per choice.
- If the user gave no `target`, default to the current branch diff:
  1. `git branch --show-current` for the branch name.
  2. Base branch defaults to `develop`. If the current branch **is** `develop` or `main`, ask which branch to compare against.
  3. Confirm `git diff <base>...HEAD` is non-empty; if empty, ask the user for an alternative target.
- Only ask about `model`, `reasoning`, or `sandbox` if the user signalled they care. Otherwise use the defaults silently and state which you used.

## Step 2 — Run Codex

```bash
codex exec \
  -c model="<model>" \
  -c model_reasoning_effort="<reasoning>" \
  --sandbox <sandbox> \
  --ephemeral \
  "<prompt>"
```

- `--ephemeral` — session is not saved to disk; Claude Code owns the session.
- Map a user's "extra high" to `xhigh`.
- The `target` is named inside `<prompt>` — e.g. "review `path/to/dir`" or "run `git diff <base>...HEAD` and review it". Codex reads those paths itself under the sandbox; do not pass the target as a separate flag.

**Never inline a large diff into the prompt argument.** A big branch diff passed as `"<prompt>"` blows the shell arg limit (`argument list too long`). Instead either:
- (a) tell Codex to produce the diff itself — e.g. "run `git diff <base>...HEAD` and review it"; Codex can read the repo under `--sandbox read-only`; or
- (b) write the full prompt (instructions + diff) to a temp file and pipe it on stdin: `codex exec <flags> < prompt.txt`.

## Step 3 — Return the output

Codex writes to stdout. Capture it and present it to the user as-is, lightly structured if it helps (e.g. group findings by severity when Codex returned a review). Do not add a parallel Claude pass or a comparison table.

If Codex proposed code changes (it could not apply them under `--sandbox read-only`), present them as a clear change list or diff and offer to apply them yourself.

## Follow-up

Offer the obvious next steps only: apply a specific proposal, re-run Codex on a different target, or hand off to `pr-review` if the user now wants the full pipeline — Claude reviewers plus Codex on the same surface, merged and then validated finding by finding.
