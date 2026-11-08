# E2E journeys

The claims this suite makes, grouped by the people who use the product. The `test-e2e-planner`
agent reads this file before it plans anything, and every PR that changes behaviour updates
it. A spec that serves no journey here is a harness or a candidate for deletion.

How to find, score, tier and keep it current: `cct:test-e2e-policy`,
`references/strategy.md` section 2.

**Scores** are 0 to 2 on: money, law, access or data, how many people, broke before, only a
browser can catch it. **T1** 8 or more, or a 2 on money, law or access: every PR. **T2** 4 to
7: milestone and nightly. **T3** under 4, or 0 on "only a browser": no e2e, covered lower
down. Keep T3 rows; they record a decision, not an omission.

**States**: lifecycle transitions as `a > b`, screen states from strategy.md section 2.5.
Mark covered ones `[x]` and uncovered ones `[ ]`.

## Budget

| Lane | Limit | Today |
|---|---|---|
| PR gate (T1), wall clock on CI | 10 min | |
| T1 spec files | | |
| T2 spec files | | |

## Audiences and personas

| Audience | Persona | Signs in with | May see | May change |
|---|---|---|---|---|
| | | | | |

## <Audience 1>

### <ID> <Journey in one line>

| Persona | Score | Tier | Owner |
|---|---|---|---|
| | money 0, law 0, access 0, traffic 0, broke 0, browser 0 = 0 | | |

- **States:** [ ] `draft > live` [ ] `live > closed` [ ] refused: viewer [ ] empty [ ] error
- **Specs:**
- **Proves:**
- **Does not prove:**

## <Audience 2>

## Quarantine

<!-- A person adds a row; the healer never does. Expiry at most 14 days out. On expiry the
     test is fixed or deleted, and the journey's "Does not prove" says what is uncovered. -->

| Test | Journey | Owner | Ticket | Since | Expires |
|---|---|---|---|---|---|

## Harnesses

<!-- Specs that are not journey tests (screenshot capture, state audits, proofs). Name the
     env flag or Playwright project that keeps each out of the gate. -->

| Spec | Purpose | Enabled by |
|---|---|---|

## Not journeys

<!-- Design-system, layout and accessibility checks. They protect the look and the rules,
     not a person's path. Keep them out of the T1 gate unless a journey depends on them. -->

| Spec | Protects |
|---|---|
