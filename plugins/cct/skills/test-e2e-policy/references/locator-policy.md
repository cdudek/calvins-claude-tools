# The locator policy

**This file is the single source for how an e2e test binds to the page.** The three
agents (`test-e2e-planner`, `test-e2e-generator`, `test-e2e-healer`) read it before they write anything, and
`cct:test-e2e-policy` restates nothing from it. If a rule lives in two places, one of them
is already wrong.

Framework-agnostic where it can be. The examples are `@playwright/test` because that is what
this standard ships; the decision table applies to any driver.

## The one-sentence version

Bind to the **role** for anything a person clicks, bind to a **test id** for anything a
person reads out of a grid, and never write a user-visible string into a spec.

## 1. The decision table

Pick by what the element *is*, not by what the app is.

| The element | Bind with | Why |
|---|---|---|
| Button, link, heading, dialog, tab, menu item, form field | `getByRole(role, { name })` | It has an accessible name because a screen reader needs one. The test rides a contract the app already owes its users. |
| A value inside a grid, table cell, row, card, list item — anything repeated | `getByTestId` | Role + name is ambiguous the moment there are two rows. Scoping to the row still needs the row, and the row has no name. |
| Something with no role and no name (a layout wrapper, a chart canvas, a progress strip) | `getByTestId` | There is nothing else to hold. |
| A third-party widget you do not control | `getByTestId` on your own wrapper | Never bind to someone else's DOM. |
| Anything else | — | Raw CSS and XPath are banned. See §5. |

**When the table says `getByTestId` and the element has no test id, the application owes
one.** Adding it to the app is the fix, not a workaround, and a person makes that change
(or the feature's own PR does): the agents report a missing test id, they never add one. A spec that reaches an element by
counting is a spec that will break when a row is inserted.

## 2. Never write a user-visible string into a spec

This is the rule that matters most and the one every suite gets wrong.

A `name:` is copy. `getByRole('button', { name: 'Save changes' })` is exactly as coupled to
the marketing team's next edit as `getByText('Save changes')` is. Moving from text to role
does not fix copy coupling — it only fixes *structure* coupling.

**Resolve every user-visible string through the project's own copy catalogue.**

```ts
// e2e/i18n.ts — see test-e2e-setup/templates/i18n-fixture.ts for the shipped version
import { t } from './i18n'

await page.getByRole('button', { name: t('settings.save') }).click()
await expect(page.getByTestId('toast')).toHaveText(t('settings.saved'))
```

Rules for the helper:

- **It throws on a missing key.** A renamed or deleted key must fail loudly at that line, not
  silently match nothing and time out 10 seconds later somewhere else.
- **It reads the same catalogue the application reads.** Not a copy, not a fixture — the real
  file. A second copy is a second source of truth within a month.
- **It takes a locale.** The same spec then runs in every locale the product ships.

What this buys, plainly: the coupling moves from **copy** to **key names**. That is a win only
because engineers own key names and other people own copy. It is not a win in a product with
no catalogue — see §2.1.

### 2.1 When the project has no copy catalogue

Some products are single-locale and never will be otherwise (an internal tool, a desktop app).
Inlining copy there is defensible, and pretending otherwise adds a layer for nothing.

The test is not "does it have i18n today" but **"could the words change without the behaviour
changing?"** If yes, the strings belong in one file the spec imports — even if that file is
just `e2e/copy.ts`. One place to look when a rename lands beats fifty.

A product that treats exact wording as product surface (where the copy *is* the feature) is
the one real exception. Say so in the spec, in a comment, once.

## 3. Positional selection is a missing test id

`.first()`, `.last()`, `.nth(n)`, `:nth-child`, `td:nth-of-type(5)` — every one of these binds
the test to the order of the DOM.

```ts
// No. Insert a column and this silently asserts a different column.
await expect(row.locator('td').nth(5)).toHaveText('1')

// Yes.
await expect(row.getByTestId('lead-count')).toHaveText('1')
```

Two legitimate uses survive:

- **Scoping then acting**, where the container itself is uniquely named:
  `page.getByRole('row', { name: t('table.rowFor', { name: partner.name }) }).getByRole('button')`
- **Asserting a count**: `await expect(rows).toHaveCount(3)` — that is the assertion, not a
  selector.

Everything else means the app owes the test an identifier.

## 4. Waiting

See `waiting.md`.

## 5. Raw CSS and XPath are banned

Banned: class chains (`.border-main.bg-surface-elevation-1`), utility classes of any kind, id
+ tag + attribute triples, structural selectors (`div:has(> table)`, `tbody tr:last-child`),
and every XPath, especially `locator('..')`.

Three escapes, each of which must be a named constant or carry a comment:

1. `iframe` — has no ARIA role you can select by.
2. A `data-*` marker the application deliberately publishes as a contract (`[data-row]`,
   `[data-step]`). If the app declares it for the tests, it is a test id by another name —
   prefer `getByTestId` and configure `testIdAttribute` so both spellings resolve.
3. Bare landmark tags (`main`, `nav`) where the page genuinely has one. `getByRole('main')`
   is better and costs nothing.

## 6. Personas

A spec authenticates as a **declared** persona, never by driving a login form and never by a
hand-rolled session.

The project declares its personas once in `e2e/personas.md` (see
`test-e2e-setup/templates/personas.md`). The planner reads that file; it does not re-derive personas by
reading `auth.ts` on every run.

A persona here is an **application role** — who is signed in and what they may see. It is not
a buyer persona. Buyer and ICP material answers *which journeys are worth
covering*; it never reaches a selector.

## 7. What belongs at e2e level at all

See `strategy.md` section 2.

## 8. Enforcement

None of the above is a note. `test-e2e-setup/templates/eslint.config.e2e.mjs` enforces §3, §5 and
`waiting.md` §10 mechanically, and `test-e2e-setup/templates/eslint-rules/no-catalogue-copy.js` enforces §2 by loading the
project's own catalogue and failing any spec literal that matches a value in it.

Install both with `test-e2e-setup/scripts/install-lint.sh <repo-root>`. A rule that is not enforced is a rule
that lasts until the next deadline.
