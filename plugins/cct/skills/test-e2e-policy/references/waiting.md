# Waiting

**This file is the single source for how a spec synchronises with the app.** The lint preset
enforces the bans at the end; everything else is judgement this file explains.

## The one-sentence version

Never wait for time; wait for the thing you need. Let actions auto-wait, assert outcomes with
retrying assertions, start an event wait before the action that causes it, and control
clocks and networks instead of waiting for them.

"Waiting is old school" is half right. Blind waiting is: `waitForTimeout`, `networkidle`,
`waitForNavigation`, sleeps, raised timeouts. Waiting **for a fact about the app** is how
every modern Playwright suite synchronises. The tools below are ordered by how often you
should reach for them.

## Contents

1. Actions already wait
2. Assertions are the synchronisation
3. Values outside the page: `expect.poll`
4. Blocks that must repeat: `toPass`
5. Events: start the wait, then act
6. Time: `page.clock`
7. Network: decide the answer instead of waiting for it
8. Readiness the app must publish: hydration, busy, open
9. Screenshots
10. Banned, and what to use instead
11. Finding and failing flakes

## 1. Actions already wait

`click`, `check` and `tap` wait until the locator matches exactly one element that is
visible, stable (not animating), not covered by another element, and enabled. `fill` waits
for visible, enabled and editable. Nothing before an action needs a wait.

```ts
await page.getByRole('button', { name: t('webinar.save') }).click()   // no wait before it
```

Actions do **not** wait for the backend to finish or for React to hydrate. That is what
sections 2 and 8 are for. `force: true` switches the checks off and hides the real bug,
usually an overlay covering the control. It is banned.

## 2. Assertions are the synchronisation

A web-first assertion retries until it passes or the expect timeout runs out. Assert the
outcome the person would see, and the test waits exactly as long as the app needs.

```ts
await page.getByRole('button', { name: t('webinar.save') }).click()
await expect(page.getByRole('status')).toHaveText(t('webinar.saved'))
await expect(page).toHaveURL(/\/webinars\/[0-9a-f-]+$/)
await expect(page.getByTestId('lead-row')).toHaveCount(3)
await expect(page.getByRole('button', { name: t('lead.redeem') })).toBeDisabled()
await expect(page.getByRole('main')).toMatchAriaSnapshot(`
  - heading "${t('webinars.title')}" [level=1]
  - button "${t('webinars.new')}"
`)
```

- **Instant reads do not retry.** `isVisible()`, `textContent()`, `count()`,
  `getAttribute()` sample once. `expect(await x.isVisible()).toBe(true)` is a race.
- **`toMatchAriaSnapshot`** (Playwright 1.49+) asserts structure through the accessibility
  tree and retries. It matches a subset by default; it suits "this region shows these
  controls" better than five separate assertions. Names inside it still come from `t()`.
- **A slow step gets a named timeout, not a global one.** The default expect timeout is
  5 seconds. When one step is legitimately slow (an export, a sync), configure it once and
  say why:

  ```ts
  // The CSV is generated server side; 15s covers 5,000 rows on CI.
  const slow = expect.configure({ timeout: 15_000 })
  await slow(page.getByRole('status')).toHaveText(t('export.ready'))
  ```

  A per-call `timeout:` with no comment is a note that the app is slow, written in the
  wrong place.

## 3. Values outside the page: `expect.poll`

When the fact lives outside the browser (an API, a database row, an outbox entry, a mail),
poll it. Always give it a timeout and intervals.

```ts
await expect
  .poll(async () => (await db.outbox.findByLead(leadId))?.status, {
    timeout: 10_000,
    intervals: [250, 500, 1_000],
  })
  .toBe('sent')
```

## 4. Blocks that must repeat: `toPass`

When several steps must be retried together (reload, then assert), wrap them in `toPass`.

```ts
await expect(async () => {
  await page.reload()
  await expect(page.getByTestId('budget-left')).toHaveText('€ 1.250,00')
}).toPass({ timeout: 20_000, intervals: [1_000, 2_000] })
```

- `toPass` has **no timeout by default** and ignores the expect timeout. Always set one.
- Never wrap a single locator assertion; it already retries.
- Never put an action that creates or changes data inside the block. A retried "create"
  creates twice.

## 5. Events: start the wait, then act

Downloads, popups, and a response whose status or payload is the thing under test: start
the wait **before** the action, then await it after.

```ts
const download = page.waitForEvent('download')
await page.getByRole('button', { name: t('leads.export') }).click()
const file = await download
expect(await readFile(await file.path(), 'utf8')).toContain(t('leads.csv.header'))

const response = page.waitForResponse(
  (r) => r.url().includes('/api/redeem') && r.request().method() === 'POST',
)
await page.getByRole('button', { name: t('lead.redeem') }).click()
expect((await response).status()).toBe(200)
```

Clicking first and then calling `waitForResponse` misses a fast response and hangs. And
prefer the visible outcome (section 2) unless the response itself is what you are testing.

## 6. Time: `page.clock`

Countdowns, debounce, session expiry, scheduled sends and polling UIs are tested by
controlling the browser's clock (Playwright 1.45+), never by sleeping through them.

```ts
await page.clock.install({ time: new Date('2026-10-10T09:00:00+02:00') })  // before goto
await page.goto(`/webinars/${id}`)
await page.clock.pauseAt(new Date('2026-10-10T09:59:00+02:00'))  // time stops; nothing drifts
await page.clock.fastForward('00:50')       // mm:ss; jump, due timers fire once
await page.clock.runFor(10_000)             // run timers tick by tick
await expect(page.getByRole('status')).toHaveText(t('webinar.live'))
```

`install` must come first; on its own it lets time keep running, so `pauseAt` it when the
test needs exact control. `setFixedTime` freezes `Date` while timers keep running;
`pauseAt` and `resume` give step control. The server's clock is not affected: a rule the
server enforces by time needs a seeded timestamp, not a browser clock.

## 7. Network: decide the answer instead of waiting for it

You own the app; you do not own third parties. Route what you do not own, and force the
states you cannot otherwise reach (strategy.md section 2.6).

```ts
// third parties never decide whether a test passes
await page.route(/googletagmanager|hotjar|intercom/, (r) => r.abort())

// an error state, deterministically
await page.route('**/api/leads*', (r) => r.fulfill({ status: 500, json: { error: 'boom' } }))

// a loading state you can assert, then release
let release!: () => void
const held = new Promise<void>((resolve) => (release = resolve))
await page.route('**/api/leads*', async (r) => { await held; await r.continue() })
await page.goto('/leads')
await expect(page.getByRole('table')).toHaveAttribute('aria-busy', 'true')
release()
await expect(page.getByRole('table')).not.toHaveAttribute('aria-busy', 'true')
```

`routeFromHAR` replays recorded responses; `routeWebSocket` (1.48+) scripts a socket.
Never route your own API in a journey test that claims the wiring works: that is a component
test in a slower costume. Use it for the loading and error cells of the state matrix.

## 8. Readiness the app must publish

Some readiness is invisible to Playwright, and the fix is a small contract in the app.

- **Hydration.** In a server-rendered React or Next.js app the button is visible and enabled
  before its click handler is attached. A click in that gap is lost, auto-waiting passes,
  and the test flakes on slow runners. Playwright has no hydration API. Publish one: the
  root layout sets `data-hydrated="true"` on `<html>` in an effect, and the persona fixture
  asserts it after every `goto`.

  ```ts
  await page.goto(path)
  await expect(page.locator('html')).toHaveAttribute('data-hydrated', 'true')
  ```

  Put it in the fixture once, never in each spec. It is the locator policy's second
  escape (section 5): a `data-*` marker the app publishes as a contract for tests.
- **Busy.** A region that loads sets `aria-busy="true"` while it loads. Screen readers need
  it anyway; the test asserts it clears.
- **Open, checked, selected.** Assert the ARIA state (`aria-expanded`, `aria-checked`,
  `aria-selected`) or a component library's published `data-state`, not an animation.

## 9. Screenshots

`toHaveScreenshot` already takes shots until two in a row match. Make them stable by
configuration, not by waiting:

```ts
await expect(page).toHaveScreenshot({
  animations: 'disabled',
  caret: 'hide',
  stylePath: 'e2e/screenshot.css',   // hides timestamps, avatars, anything volatile
  mask: [page.getByTestId('relative-time')],
})
```

Playwright already waits for web fonts before it takes a screenshot; nothing to add.

## 10. Banned, and what to use instead

| Banned | Why | Instead |
|---|---|---|
| `page.waitForTimeout(n)` | Too short on CI, too long everywhere else | The assertion for the state you wanted |
| `waitForLoadState('networkidle')` | Discouraged by Playwright; "nothing happened for 500 ms" is not a fact about your app | An assertion on the content |
| `page.waitForNavigation()` | Deprecated | `await expect(page).toHaveURL(...)` |
| `page.waitForSelector(...)`, `locator.waitFor()` | A wait with no assertion; passes on the wrong state | `await expect(locator).toBeVisible()` or `.toBeHidden()` |
| `page.waitForFunction(...)` | Arbitrary JS polling, invisible in the trace | A locator assertion, or `expect.poll` |
| `expect(await x.isVisible()).toBe(true)` | Samples once | `await expect(x).toBeVisible()` |
| `{ force: true }` | Hides the overlay that is the bug | Close or wait out the overlay by assertion |
| Raising a timeout to go green | Moves the race, does not remove it | Find what you were really waiting for. A timeout on `expect.poll`, `toPass` or `expect.configure` is allowed when a comment says why the step is slow |
| More `retries` | Turns a race into a flaky pass | Section 11 |

The lint preset (`test-e2e-setup/templates/eslint.config.e2e.mjs`) fails `waitForTimeout`, `networkidle`,
`waitForSelector`, `force: true`, per-action timeouts and a `toPass` without a timeout, and
warns on a magic timeout that repeats.

## 11. Finding and failing flakes

- Reproduce: `npx playwright test path/to.spec.ts --repeat-each=20 --workers=4`. Several
  workers expose shared-data races that one worker hides. Read the summary line: any
  `flaky` or `failed` count above zero is a reproduction; open that run's trace with
  `npx playwright show-report`.
- Fail on flakes in CI: `failOnFlakyTests: !!process.env.CI` in the config (1.52+). A test
  that only passes on retry then fails the run instead of hiding in a green one.
- Run what changed first: `--only-changed=origin/main` (1.46+) for a fast local loop; the
  PR gate still runs the whole tier.
- Name steps so traces read: `test.step('redeem the lead', async () => { ... })`, and
  `locator.describe('budget left')` (1.53+) names a locator in the trace.
- Then fix with `cct:test-flake-fix`; quarantine rules are in strategy.md section 7.
