# Iteration commit boundaries and resuming after a limit stop

Read in step 7 when the auto-commit's staging is in question, and in step 2 / Safety when a
subagent was killed by a usage or session limit. Sibling paths written `../<skill>/…` below are relative to the **skill folder** (`plugins/cct/skills/review-fix-run/`), one level up from this file.

## Why the auto-commit stages everything

`git add -A`, matching the pre-loop baseline commit — **not** a hand-built file list. Phase RED stages its new tests, but the fix stage may leave an untracked file unstaged (`../review-feedback-run/references/policies.md` → Commit / post: it deliberately leaves the tree dirty for this step). Anything left uncommitted here survives into the next iteration, where a `changes` review halts on the dirty tree (`../review-code-run/references/policies.md` → Changes Reviews) and the run ends as `ABORTED` — a clean tree at every iteration boundary is what step 1's committed-only review depends on.

## A usage/session-limit stop is resumable, not a failure

Step 2's parse rule, in full:

- **Usage/session-limit termination** (the subagent was killed by the harness mid-run — the surfaced result is a limit/quota message, not a review token) → **RESUMABLE, not a failure.** Re-run the loop when the limit window permits (immediately if it has reset, otherwise after reset); `review-code-runner` relaunches against the same `rev-<revid>` dir (HEAD is unchanged — no commit happens until step 7 → same revid) and resumes from the on-disk checkpoints (`findings.json` / `dim-*.json` skip-if-exists). Do **not** treat this as `ABORTED:` or as the unparseable-result STOP below.

And the Safety guarantee it rests on:

- **A usage/session-limit stop is resumable at any stage, not a failure.** No commit happens until an iteration finishes (step 7), so a subagent killed mid-iteration leaves HEAD unchanged → the same `rev-<revid>` dir on re-run. Review and validation resume from their per-`rev` checkpoints (`findings.json` / `dim-*.json` skip-if-exists; per-verdict checkpointing for the validation pass); the address stage re-applies the same `fix-set.json`. Re-running the loop when the limit window permits picks up where it stopped — step 2 encodes this for `review-code-runner`.
