# review-feedback-run — internal contract

Loads when editing files in this skill. The skill follows one model: **source → gate → shared execution tail**. Keep the producer/consumer pairs below in sync — they pass data by convention, not enforced code (the cross-skill rules are in `../CLAUDE.md`).

## Architecture

| Layer | Files | Responsibility |
|---|---|---|
| Source | `commands/{pr,chat,message,fix-set}.md` | Collect feedback items (PR gather + worktree / conversation / free text / `fix-set.json`), set `GATE`, then run the tail. `pr` also brackets the tail with merge-base, flaky tickets, and thread/finalize steps. |
| Gate | `references/policies.md` | The single `GATE=interactive\|autonomous` knob — triage wait, Linear, commit/post, DEFER rule source (implementation in execute-phases.md → Deferred Work), untrusted-input, error handling. Also owns the `DISCUSS_ITEMS` handoff contract (schema, rendering). |
| Tail | `references/execution-tail.md` | Investigate → triage (gated) → execute → verify → report. Investigate and verify are inlined; execute delegates to `references/execute-phases.md`; triage delegates to `references/triage-table.md` under `GATE=interactive` only (autonomous skips the table). |

Change the tail's step set → check all four commands still compose correctly. Change `GATE` semantics or `DISCUSS_ITEMS` handoff (field names, format, consumer rendering) → edit `references/policies.md` only (commands and the tail reference it, never restate it). The Architecture table's Gate row covers both `GATE` knob semantics and the `DISCUSS_ITEMS` handoff.

## Subagent input contract

`references/execute-phases.md` spawns two dedicated agents (`../../agents/{test-behavior-writer,review-fix-implementer}.md`). The tail's Investigate step produces two descriptions per finding; `references/execute-phases.md` is the intermediary that routes them into the spawn prompts (the tail never spawns agents directly):

- **Behavior** (what should happen, no implementation detail) → `test-behavior-writer` only. Never pass it the Diagnosis or a fix suggestion — the test must stay honest.
- **Diagnosis** (why it's broken, what to change) → `review-fix-implementer`, with the feedback text; for `ADD TEST` items also the Phase RED test path + failure output (omitted for `FIX` and `REFACTOR` items — mechanical changes need no failing test).

Change a description's name or split → update `references/execution-tail.md` (Investigate), `references/execute-phases.md`, `references/triage-table.md` (its Behavior/Diagnosis column headers), and both agent files together.

## fix-set.json

`fix-set` consumes `<state_dir>/fix-set.json` — the projection `{id,file,line,severity,dimension,body,reversibility,idiomatic_fix?}` written by `../../agents/review-fixset-triager.md`. Change one side → change the other (see `../CLAUDE.md`).

`reversibility` and `idiomatic_fix` do **not** change what gets applied — the fix stage still makes the minimal change that resolves the item. They are carried so the run can say what the reviewer knew: an `entrenches` item is one where deferring is what makes the fix expensive, and an `idiomatic_fix` names a framework-native shape the minimal patch leaves behind. Surface both in the report (`references/execution-tail.md`); silently dropping them is what this projection was widened to stop.

## Phase fan-out cap

`references/execute-phases.md` spawns one agent **per item** in both phases, and
they are the pipeline's most expensive (full context load + a test-suite run each),
so both are capped at **~5 concurrent** — the same pool size review-code-run uses for its
far cheaper read-only validators (`../review-code-run/references/validate-agent.md` →
Concurrency). `scripts/test_fanout_caps.py` fails the build if either phase loses
its cap or the two numbers drift apart. Raise one → raise both, deliberately.

## Script paths

Reference scripts from skill-context files (`commands/*.md`, `references/*.md`) as `${CLAUDE_SKILL_DIR}/scripts/<name>.sh`; `github-manage` scripts as `${CLAUDE_SKILL_DIR}/../github-manage/scripts/<name>.sh`. Don't use `${CLAUDE_PLUGIN_ROOT}` here — that form is for agent-context files.
