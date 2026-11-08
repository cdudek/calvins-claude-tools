# How we write a requirement

> **This file is the canonical copy.** `plugins/cct/skills/sdlc-run/references/` holds a
> byte-identical mirror. `scripts/check-requirements-grammar.py` fails if they diverge.
> Edit this file, then copy it across.

One grammar, for every skill that asks someone to write a requirement. It exists in exactly two
places so each skill can read it from its own folder. Those two copies are kept byte-identical by a test. Do not make a third, and do
not restate the pattern table inside a template — a loose copy is a second grammar within a month.

Three rules, in order:

1. **EARS states the requirement.** Wherever system behaviour is specified.
2. **Gherkin proves it.** Optional, per requirement, never blanket.
3. **Neither**, when the document records a decision, a proposal, a finding, or work small
   enough to describe in one sentence.

---

## 1. EARS — the requirement

Easy Approach to Requirements Syntax. Alistair Mavin and colleagues at Rolls-Royce, first
published at RE'09 (<https://alistairmavin.com/ears/>). Six patterns, and `shall` is mandatory.

| Pattern | Template | Use for |
|---|---|---|
| Ubiquitous | `The <system> shall <response>.` | an always-on property, including non-functional ones |
| State-driven | `While <precondition>, the <system> shall <response>.` | behaviour active only in a state |
| Event-driven | `When <trigger>, the <system> shall <response>.` | a response to an event |
| Optional feature | `Where <feature is included>, the <system> shall <response>.` | behaviour that exists only if a feature is present |
| Unwanted behaviour | `If <trigger>, then the <system> shall <response>.` | errors, faults, edge conditions — **this is the bug-fix pattern** |
| Complex | `While <precondition>, when <trigger>, the <system> shall <response>.` | one precondition plus one trigger |

Worked examples, one per pattern:

```
The search API shall answer in under 200 ms at p95.
While a review is unpublished, the profile page shall exclude it from the average score.
When a vendor submits a review reply, the system shall notify the review author within 60 seconds.
Where SSO is enabled, the login page shall hide the password field.
If the uploaded logo exceeds 2 MB, then the system shall reject it and name the limit.
While an import is running, when the user requests a second import, the system shall queue it.
```

**Only "unwanted behaviour" uses `then`.** `When ... then ...` is not EARS — it collapses the
event-driven and unwanted-behaviour patterns into one shape and loses the distinction between a
normal event and a fault. Kiro's generated requirements make this mistake; do not copy them.

**Do not drop the ubiquitous pattern.** It has no trigger and no precondition, which is exactly
why non-functional requirements live there: latency, accessibility, retention, locale. A
requirement set with no ubiquitous lines has usually forgotten its constraints.

**Stop at three preconditions.** Past that the sentence is longer than the thing it specifies.
Split it into two requirements, or write a short paragraph and say plainly that it does not fit
the template. Conveying the meaning beats forcing the shape.

### Replace adjectives with numbers

Not "fast" but "p95 < 200 ms". Not "a large file" but "at least 50,000 rows". Not "intuitive"
but a named, observable outcome. A vague requirement does not stop an agent — it makes the agent
invent its own target, silently, and the invented target is what ships.

### Number every requirement

`F1`, `F2`, ... for functional, `N1`, `N2`, ... for non-functional. The number is the handle the
plan, the test and the verification block all use. Without it there is no way to say which
requirement a test covers, and coverage stops being checkable.

---

## 2. Gherkin — the optional proof

A Gherkin scenario is one concrete example of a requirement holding:

```
Scenario: <name>
  Given <context, with concrete data>
  When  <action>
  Then  <observable outcome, with a number where one exists>
```

Add one **when it earns its place**:

- the flow is conditional and the branches are not obvious from the EARS line
- concrete data removes a real ambiguity ("a review with 0 ratings", not "a review")
- an unhappy path needs naming: empty input, duplicate, permission denied, timeout

Skip it when the EARS line already says everything. A scenario that restates its requirement in
three lines instead of one is noise, and noise is what makes people stop reading specs.

**EARS states the rule; Gherkin proves it.** The rule is universal, the scenario is one case. That
is why both exist, and why neither replaces the other. A requirement with no scenario is fine. A
scenario with no requirement above it is orphaned — write the rule it is proving.

---

## 3. `[NEEDS CLARIFICATION: <question>]`

Write this literal marker inline, wherever the answer is unknown:

```
When a vendor deletes their account, the system shall [NEEDS CLARIFICATION: anonymise or hard-delete
their existing reviews?].
```

The marker is not decoration. It is the one mechanism that stops an agent resolving an ambiguity
by guessing, and a guess is invisible — it arrives as working code with a confident commit message.
Every open marker blocks implementation. Resolve them, then delete the marker.

---

## 4. Where each grammar belongs

| Document | EARS | Gherkin | Why |
|---|---|---|---|
| Agent-ready issue | required | optional | the agent implements from it |
| PRD requirements | required | optional | Must/Should/Could items are behaviour |
| `sdlc-run` `facts.md` | required | optional | the acceptance record of one change |
| Bug report | required | recommended | the EARS line is the rule that broke, the scenario reproduces it |
| Simple task | no | no | too small to spec — the escape hatch, use it |
| ADR | no | no | records a decision, not a behaviour |
| RFC | no | no | proposes an approach; it has Goals instead |
| Technical research note | no | no | records findings, not obligations |

The last four matter as much as the first four. Over-specifying small work is the best-documented
failure of spec-driven development — Böckeler watched Kiro turn one bug fix into four user stories
and sixteen acceptance criteria. If you could describe the change in one sentence, write the
sentence.
