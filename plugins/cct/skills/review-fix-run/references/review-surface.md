# Review surface — base detection, diff window, established decisions

Read before launching `review-code-runner` in step 1 (changes / changes-max) when the base or the
diff window is in question: why the detected branch name is validated rather than escaped, why
`review_base` keys on `HEAD`, why `Target branch:` never carries `review_base`, and what the
established-decisions block buys. Sibling paths written `../<skill>/…` below are relative to the **skill folder** (`plugins/cct/skills/review-fix-run/`), one level up from this file.

## Branch-name validation — validate at mint, pass through byte-exact

**Validate the result before using it anywhere.** Reject a name outside `^[A-Za-z0-9._/+-]+$` and stop, reporting the offending name (`../CLAUDE.md` → branch-name handoffs). `git check-ref-format` accepts `<`, `>` and `&` in a ref name, and `base_branch` reaches this loop's `review-code-runner` prompt on two consecutive lines (`Base branch:` and `Target branch:`), both outside the `<established_decisions>` fence — so a forged fence tag in a branch name is a real vector. Validating once here is why neither line escapes its value: `review_base` is fed byte-exact into `git diff $BASE...HEAD`, and escaping it would review the wrong range for any branch containing `&`.

## Why `review_base` keys on `HEAD`, not on run position

  Keying on `HEAD` rather than on run position is what makes a resume cheap. A usage-limit kill in iteration 3 leaves `HEAD` at iteration 2's commit; the re-run reads `HEAD~1` and reviews iteration 2's delta — exactly the surface the killed iteration was working on. Keying on the run position instead would hand it `<base_branch>`, paying a full-branch review and re-litigating iterations 1-2 every time the limit window closed — the resumability promised in step 2 and under Safety would hold only *inside* one iteration.

## `review_base` is the diff window, not the review's target

  **`review_base` is the diff window, not the review's target.** Pass the real `<base_branch>` as `Target branch:` in the prompt below, always — never `review_base`. From iteration 2 on `review_base` is `HEAD~1`, and a commit-ish reaching the reviewer's dead-code gate (`../review-code-run/references/reviewer-rules.md` → Dead-code severity) buckets the review as "feature branch", silently downgrading every dead-code finding and attaching a false "sibling sub-ticket" note to it. The target is a property of the branch and does not change between iterations.

## What narrowing the base costs

  The reviewer still reads full files; narrowing the base narrows only what it *flags*. files / files-max keep their file-list surface — this applies only to the diff modes. (Trade-off: a later iteration won't re-examine earlier-committed lines it didn't touch — a bounded cross-iteration regression blindspot.)

## Established decisions — the full rule

- **Established decisions.** Gather the branch's own already-made decisions so the reviewer doesn't re-litigate settled work — run `git log <base_branch>..HEAD --format='- %s%n%b'` (always the full `base_branch` range, independent of `review_base`) and pass its output as the **Established decisions** block in the prompt below. (files / files-max have no commit range — skip the block.) This supplies the *rationale* the diff alone can't — most of all once `review_base = HEAD~1` narrows what the reviewer sees: decisions get reverted not because the reviewer can't see the code but because it has no record of *why* a line is the way it is.
