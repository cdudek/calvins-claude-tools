# E2E personas

Copy this to `e2e/personas.md` and fill it in. The `test-e2e-planner` agent reads this file
instead of re-deriving personas from the auth fixture on every run, and the generator uses
the helper named here rather than hand-rolling a login.

A persona is an **application role** — who is signed in and what they may see. It is not a
buyer persona or an ICP; that material answers which journeys are worth covering, and never
reaches a spec.

## How a spec authenticates

<!-- Name the one helper or fixture. Never a login form, never a hand-rolled session. -->

```ts
// e.g. import { test } from './fixtures/auth'
// test('…', async ({ operatorPage }) => { … })
```

<!-- Say what the helper does under the hood in one sentence, so a reader knows what it
     costs and what it bypasses. e.g. "Writes the session row directly and sets the cookie;
     the real login is Google OAuth and is not drivable." -->

## The personas

| Persona | Fixture / helper | May see | May change | Notes |
|---|---|---|---|---|
| `<name>` | `<fixture>` | | | |
| `<name>` | `<fixture>` | | | |

## Combinations that do not work

<!-- List any pair that cannot appear in one test, and why. This is the section that saves
     the most time — it is invisible from the code and costs an hour to rediscover.
     e.g. "operatorPage and partnerPage are the same page on the same context and both write
     the same cookie name; requesting both in one test silently leaves whichever ran last." -->

## Data each persona needs

<!-- Which factory or seed creates the world this persona acts in, and whether it is shared.
     Name the file. If the suite runs against a shared seeded database, say so here and state
     the hygiene rule: every mutation self-cleaning in `finally`, or non-destructive. -->

## Locale

<!-- Which locale the suite runs in by default, and whether any spec runs in others.
     The copy helper (`e2e/i18n.ts`) resolves strings for whichever is chosen — no spec
     should contain a user-visible string either way. -->
