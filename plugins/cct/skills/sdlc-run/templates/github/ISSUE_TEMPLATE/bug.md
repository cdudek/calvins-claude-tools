---
name: Bug
about: Something behaves differently from what it should
labels: bug
---

## Bug summary

<one sentence: what is broken, where, for whom>

## Steps to reproduce

1.
2.
3.

## Expected behavior

<what should happen>

## Actual behavior

<what happens instead. Exact error text, not a paraphrase>

## Environment

- **Browser / runtime:**
- **Device:**
- **URL:**
- **Environment:** production / staging
- **First seen:** <date, or the release that introduced it>

## Impact

<who is affected and how badly. All users, one segment, one account? Is work blocked? Workaround?>

## The rule that broke (EARS)

- **F1** If <the trigger that produces the bug>, then the system shall <the correct response>.

## Acceptance criteria

```gherkin
Scenario: <the reported case> — proves F1
  Given <the exact state that reproduces it>
  When  <the action>
  Then  <the correct observable outcome>
```

- [ ] No regression in <the related feature most likely to break>

## Tests needed

- [ ] A test reproducing this case, committed failing first
