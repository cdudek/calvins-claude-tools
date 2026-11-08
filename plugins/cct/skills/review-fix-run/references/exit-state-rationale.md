# Why `fixes-failed` and `test-only` stop the loop

Read in step 6 when a decision-table outcome needs justifying, and before changing any row of
that table. Sibling paths written `../<skill>/…` below are relative to the **skill folder** (`plugins/cct/skills/review-fix-run/`), one level up from this file.

## `clean` + `yes` → `fixes-failed`, read the token before the tree

The `clean` + `yes` row is why the token is read **before** the tree is inspected, not after. A fix set of only `FIX` / `REFACTOR` items is entirely plausible (both are `GATE`-independent, `GREEN only` verbs — see `../role-review-vocabulary/SKILL.md` → Action Verbs), and those items write no Phase RED test, so nothing is ever staged; when their fixes fail, `../role-test-fixer/references/revert-on-failure.md` runs `git restore .` and hands back a **completely clean** tree. An unconditional "no files changed → converged" exit would then report a run in which every single fix failed as clean no-op convergence — the exact masking this token exists to prevent. Stopping with `fixes-failed` reaches the same conclusion the repeated-findings check would, one iteration sooner and without spending it: continuing instead would re-enter step 1 on an unchanged `HEAD`, reuse the same `rev-<revid>` checkpoints, and re-derive the identical fix set, so the loop would re-run the fix stage every remaining round with nothing new to work from.

## `changed` + `no` → `test-only` is convergence, not a normal round

Why this is a convergence case and not a normal round: a phase-gate outcome of "validates existing behavior → skip Phase GREEN", or an `INVESTIGATE` item that turns out not to be reproducible, leaves `test-behavior-writer`'s new test staged (`../../agents/test-behavior-writer.md` stages, never commits) with production code untouched. `git status --porcelain` is then non-empty, so the no-op exit above does not fire; the commit lands, and the **next** iteration's `review_base = HEAD~1` (step 1) points at a delta consisting of that new test — which the reviewer duly flags, with fresh `body` text, so step 4's file + `body` repeat check never matches either. Under `files` / `files-max` the new test file also joins the review surface below, so the surface grows every round. The loop would keep spending full iterations reviewing the tests it just wrote, until `max_iterations` stops it. There is no fix left to converge on once production code is untouched, so stop here.

## Why the token is read as the final line only

Read the address stage's **last non-empty output line** first and match it exactly against `^PRODUCTION_CHANGES=(yes|no)$` — the same anchoring step 2 applies to `STATE_DIR=`, and for the same reason: the stage's report quotes fix-set `body` text and file paths earlier, so an incidental mid-report `PRODUCTION_CHANGES=` literal is **not** the control signal. This repo's own prose carries that literal dozens of times, so a dogfood run reviewing these files is a concrete case, not a hypothetical. A final line that matches neither value → treat as `yes` (the conservative reading: never conclude convergence from a signal you could not parse).
