# The living spec: one file per rule

What the product does today is `specs/` at the repo root, kept current by the PR that changes the
behaviour. (`livingSpecs` in `sdlc.json` renames the folder; `specsDir` is the old key for
`docs/designs/` and must not be reused.)

```
specs/CAPABILITIES.md                 generated; one line per capability, no counts
specs/<capability>/manifest.yaml      purpose, aliases, owner, code, tests, related, coverage
specs/<capability>/rules/R123.md      one requirement
.sdlc/last-rule-id                    the highest rule number ever used (a floor, see below)
```

A capability is a thing a person can name ("billing", "series and webinars"), not a ticket. Split
one when a reviewer can name two responsibilities in it.

## A rule file

```
---
id: R123
summary: six to twelve plain words; `spec find` matches on this
status: live
proof: test
since: <change id>
---
When a charge fails, the system shall retry it once after ten minutes.
```

- `status`: `live`, or `planned` for a rule of a later milestone (no test needed yet).
- `proof`: `test` (a test tagged `@R123`), `manual` (also needs `evidence:`, who checks and how) or
  `check:<name>` (an `sdlc.json` check proves it: a performance budget, an accessibility rule). Only
  `test` demands a tag; this keeps `manual` and `check` rules from forcing fake tests.
- One EARS sentence ([grammar](requirements-grammar.md)). The capability is the folder, not a field,
  so moving a rule is `git mv` and nothing is retagged.

## Ids

`R` and a number with no fixed width: R1, R123, R10000. Never reused. The next one is the highest ever
used plus one, from the live files, `.sdlc/last-rule-id` and the git history of added rule files
(`--no-renames`, so a move hides no add): `python3 scripts/spec.py next`, or `spec.py new <capability>
<summary>` which creates the file with it. The tag is `@R123`, never `#`. (`R` also names a review
finding in the old layout's findings; the two never share a document.)

Two PRs can take the same number in different capabilities and merge cleanly. `check` refuses a
number already on the base branch or removed from it earlier, and `spec.py renumber [--base REF]`
fixes it before merge: the later PR's colliding rules get the next free numbers, and only what that
branch added is rewritten (its rule files, the `@R` tags and `R<n>` words on the lines it added).
`spec.py last-id --write` records the floor; run it once at milestone close, not per rule, or it
becomes a conflict file in every PR.

## Tests and the drift check

`python3 scripts/spec.py check [--base REF]` fails on: a rule file that is malformed or duplicated; a
capability with no manifest or no purpose; an `@R` tag that names no rule; a live `test` rule with no
tagged test, or tagged only in skipped tests (`skip`, `xit`, `test.skip`, `fixme`,
`pytest.mark.skip`, `unittest.skip` on the tag's line or the two above: a heuristic); and, against a
base, a changed rule with no changed test tagged with it (a pure move is exempt), and a new number
already used. A repo with no `specs/` passes. Tag presence cannot show the test still asserts the
sentence: the reviewer reads the assertion when a rule changes, and for a consequential invariant
the test is shown to fail when the rule is broken.

## Finding the right rules

```
python3 scripts/spec.py find invoice retries --paths src/billing --prs
```

Up to ten rules with their path, the matched words, `stale?` (three code commits since the rule
last changed) and `! open PR #n edits it` (only with `--prs`, needs `gh`, silent without it). Ranking:
exact id, summary words, capability name and aliases, purpose, the paths given; ties go to the older
git date, because a five-year-old duplicate-charge rule outranks yesterday's copy edit. A miss lists
the capabilities that match with their `code` and `tests`, and says when a capability is only
partly catalogued, so an empty answer is not read as "no rule". The index is `.git/spec-index.json`
(id, capability, summary, status): never committed, one per worktree, rebuilt when any rule or
manifest changes. Read `specs/CAPABILITIES.md` first (`spec.py capabilities --write`), then `find`,
then open only the rules it names.

## Measuring recall before a repo turns it on

`spec.py eval fixture.json --k 10` replays past changes: each case has the `query` known at intake,
the `paths`, the pre-existing rule ids that mattered (`relevant`) and optionally `rev` (the parent
revision). It prints recall@k for `find` and for a grep over the rule files, the misses, and counts
new-feature cases (no relevant rule) apart. About a hundred cases per repo, labelled by a reviewer;
`templates/specs/eval-fixture.example.json` shows the shape. The number is a gate for turning on
blocking drift checks in that repo, not a claim about it.

## Rollout

Seed `specs/` as changes touch a capability; no back-fill. Mark a half-catalogued capability
`coverage: partial`. Run `check` report-only in a repo until its baseline is clean, then blocking for
the capabilities that are clean. Existing archives are removed once their changes are complete (the
integrator's step, not this layout's); new work is never archived.
