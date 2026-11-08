# Ecosystem: Playwright

Browser end-to-end tests. Flaky here means something different from a flaky unit test: the
failure is almost always **synchronisation or shared state**, not logic.

Before anything, read
`plugins/cct/skills/test-e2e-policy/references/locator-policy.md` — a repair that violates
the policy is not a repair.

## Commands

```bash
npx playwright test <spec>                      # one spec
npx playwright test <spec> --repeat-each=20     # calibrate the reproduction rate
npx playwright test <spec> --repeat-each=20 --workers=1   # rule out parallelism
npx playwright test <spec> --trace on           # trace on every run, not just retry
npx playwright show-trace test-results/**/trace.zip
npx playwright test --last-failed
npx playwright test <spec> --grep "@tag"
```

**Read `test-results/**/error-context.md` first.** It is the accessibility-tree snapshot at
the moment of failure and it usually names the cause outright — an element that is not there,
two elements where one was expected, a page still on the previous route.

## Reproduction

`--repeat-each` is the calibration tool. A spec that fails 1 in 20 locally and 1 in 3 in CI is
telling you the difference is machine speed, which points at a race rather than a wrong
assertion.

Three switches isolate the class quickly:

| Switch | If the failure disappears |
|---|---|
| `--workers=1` | Parallelism — shared data, shared session, or a shared port. |
| `--repeat-each=20` on a **fresh** database | Accumulating state; the spec is not re-runnable. |
| `--project=chromium` alone | Browser-specific, usually a timing or rendering difference. |

## Order dependency

Playwright has no `--bisect`. Use `--workers=1` plus `--grep` to narrow, or `--shard` to split
the suite and see which half carries the failure. `test.describe.serial` in the suite is a
strong hint that ordering was already a known problem.

A config with `workers: 1` and `fullyParallel: false` does not prove the suite is
order-independent — it **hides** ordering bugs rather than preventing them. Treat it as an
unanswered question, not a guarantee.

## The five causes, in the order they actually occur

| Cause | Signature | Fix |
|---|---|---|
| **Async wait** — ~45% of UI flakes | Passes with a sleep, fails without; fails more on slow CI | Web-first assertion on the settled state. Never `waitForTimeout`. |
| **Shared state** | Fails only on the second run, or only after another spec | Make the spec re-runnable — scope to data it created, never assert emptiness of accumulating rows |
| **Copy drift** | Fails right after a wording change; the string is in the catalogue | Replace the literal with `t('<key>')`. Do not retype the new wording. |
| **Positional locator** | Fails after a column or row was added | Replace `.nth()` / `.first()` with a test id; report it if the app lacks one |
| **Animation / repaint** | Only fails on `getComputedStyle` or screenshot assertions | Assert the post-animation state, or disable animations in the config |

## What is not a fix

- Adding `waitForTimeout`, or raising a per-call `timeout:`.
- Adding a retry to `playwright.config.ts` to cover one spec.
- Replacing a text assertion with `toBeVisible()` — a toast reading "Error" is visible too.
- `test.skip()` or `test.fixme()`. If the spec is right and still fails, that is the strongest
  available signal of a **product** defect: report it and leave it red.
- Editing application source to make the test pass.

## When it is a real bug

Google's data: when a stable test became flaky and the cause was traced to a code change, it
was a genuine production bug about **1 time in 6**. Treat a newly flaky spec as a suspect
regression until the trace says otherwise.
