# Fix Workflow

Shared steps for both `ticket` and `local` commands. Executed after the command-specific context gathering and worktree setup.

## Step 3: Detect Ecosystem

Follow SKILL.md ecosystem detection. Load the matching `references/ecosystem-*.md`.

## Step 4: Reproduce

Follow `references/reproduction.md` using the test file/line and seed (if available).
For e2e tests, first read `references/controlled-diagnosis.md` and establish its controls.

**Seed handling:** If a seed was provided (from ticket or argument), use it. If not, run the test once and capture the seed from the output using the ecosystem-specific seed regex. Record this seed — it will be used for all subsequent runs including verification.

## Step 5: Bisect (if order-dependent)

If the test passes in isolation but fails in the full suite, this is order-dependent.

Follow the bisect section in the loaded ecosystem reference. Only runners with bisect support (RSpec, Minitest, Pytest with plugin) can do this automatically. For Jest/Vitest, follow the manual workaround in their ecosystem reference.

## Step 6: Diagnose and Fix

Read the failing test and the code it exercises. Consult `references/flaky-patterns.md` for common patterns and fixes.

Apply the minimal fix (`references/fix-discipline.md` section 3). Keep changes focused:
- Fix only the flaky behavior
- Do not refactor the test
- Do not change unrelated assertions
- Do not add comments explaining what was flaky (the commit message handles that)

## Step 7: Verify

Follow `references/fix-discipline.md` section 4 (stash-based verification). This step is mandatory.

## Step 8: Report

Follow `references/report-format.md`.

Do not commit or push. Wait for the user's instructions.
