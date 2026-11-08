# Fix Discipline

Verification and every push follow the [local-first contract](../../sdlc-run/references/local-first.md); read it before running checks or preparing a push.

The problem-solving workflow this skill follows, and the protocol for each fix step.

**Constraint (applies throughout):** [Protect tests](../../role-code-analysis/references/protect-tests.md). Tests are sacrosanct; change them only as a last resort, and never to accommodate broken code. For a flaky test the fix usually is in the test or its fixtures, so keep it to the cause of the flakiness and leave assertions as they are.

Analysis steps (from `role-code-analysis`, the understand, diagnose and evaluate subset):

1. **Understand intent**: parse the problem, not the literal symptom ([understand-intent](../../role-code-analysis/references/understand-intent.md)).
2. **Root cause analysis**: find why the failure was possible ([root-cause-analysis](../../role-code-analysis/references/root-cause-analysis.md)).
3. **Evaluate approaches**: outline options for a non-trivial fix ([evaluate-approaches](../../role-code-analysis/references/evaluate-approaches.md)).

Fix steps, in order. Step 1 is a hard gate:

1. Reproduce (section 1)
2. Fix minimally (section 3)
3. Quick verify (section 2)
4. Prove causation (section 4)
5. Revert on failure (section 5)

## 1. Reproduce before fixing

Reproduce the failure before touching code. For flaky-specific calibration (seeds, rates, timing) see `references/reproduction.md`.

Run the test and **do not proceed to the fix until you have seen it fail.** This is a gate, not a suggestion.

- Read the output and confirm the failure matches the one you are fixing (not a setup error, not a different test).
- If a test you wrote to capture the correct behavior passes, investigate before continuing with a 3-step check:
  1. **Negate the key assertion.** If the negated test also passes, the test is tautological: rewrite it.
  2. **Sabotage the code under test** (for example a wrong return value). If the original test still passes, it does not reach the right code path: rewrite it.
  3. If negation and sabotage both cause failure, the code already handles this case. Report that and make no code fix.
- Derive expectations from the specification or existing patterns, never from the current broken behavior.

If you find yourself editing production code without a failing run in your history, stop and go back to the reproduction. If you cannot reproduce the failure, report it and ask for guidance. Do not guess at a fix.

## 2. Quick verify

The inner loop, run after every change:

1. Lint and format checks first: fastest feedback.
2. Run the specific tests related to the change.
3. Fix any lint or test failure before moving on.

After all fixes pass quick verification: run the full lint pass, then the full test file or relevant suite, then the stash-based check in section 4 if causation proof is needed (it is, for this skill).

Any script or command you write to verify a fix must be falsifiable: able to fail. Confirm it catches a known-bad case before trusting it.

## 3. Minimal fix

Apply the smallest change that makes the failing test pass reliably.

- Change only what is necessary to fix the identified root cause.
- Do not refactor, clean up or improve surrounding code, even where it is obvious.
- Do not add comments explaining what was broken; the commit message does that.
- One fix per concern. Every extra change is a potential regression; the fix should be reviewable in seconds.

## 4. Stash-based verification (mandatory)

This proves the fix addresses the actual failure.

1. **Stash the fix**: `git stash --include-untracked`. Untracked files (fixtures, factories, helpers) created by the fix are stashed too; plain `git stash` only captures tracked changes.
2. **Confirm the test fails without the fix.** Same test, same seed if one was used. It should fail. If it passes, try 2-3 more runs. If it consistently passes without the fix, the flakiness may be non-deterministic: report that, because the fix may be correct but unprovable by the stash test.
3. **Restore the fix**: `git stash pop`.
4. **Confirm the test passes with the fix.** If it fails, the fix is incomplete: return to diagnosis.
5. **Run the full test file** with the ecosystem's file-level command to catch regressions, and report any new failure.

Low reproduction rate: if the calibrated rate was under 80%, one cycle is not conclusive. Run the test N times with the fix stashed and count failures, run it N times with the fix applied and count failures, compare the rates and report both.

The protocol is falsifiable: step 2 expects failure and step 4 expects success. If both give the same result, the verification failed; say so and never treat step 2's outcome as predetermined.

## 5. Revert on failure

Keep proven work and discard failed experiments cleanly.

1. After each verified fix, stage the specific files: `git add <specific-files>`.
2. If an attempt fails, return to the last proven state: `git restore .` (staged changes are kept; only unstaged experiments are discarded).
3. Never layer attempt 2 on top of broken attempt 1. Restore to clean first.
4. When all fixes are done, leave the proven files staged and uncommitted; this skill never commits (see Policies in SKILL.md).
5. Full reset only when needed: `git restore --staged --worktree .`.
