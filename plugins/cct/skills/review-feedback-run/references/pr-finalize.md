---
description: PR-finalize recipes — merge base, finalize (push + body), re-request review. Each H2 is dispatched by name from a step in references/commands/pr.md.
---

# PR Finalize

Verification and every push follow the [local-first contract](../../sdlc-run/references/local-first.md); read it before running checks or preparing a push.

Each H2 is a named recipe dispatched from `references/commands/pr.md`. Run only the block named by the active step.

## Merge base

```bash
git fetch origin {base}
```
```bash
git merge origin/{base}
```

If conflicts arise, stop and show them to the user. Ask them to resolve manually, or abort with `git merge --abort`. Do not force-resolve.

## Finalize (push + body)

### Update PR body

Read [scannable bodies and the full example](../../sdlc-run/references/pr-body.md). If feedback changed the risk, refresh the PR's Decision4 section ([advisory](../../sdlc-run/references/decision4-pr.md)): level, recovery steps, responsible role.
Edit the existing body: put addressed feedback under What, reasons under Why, and named
checks with results under Proof. Preserve human checklist state;
never append a competing “Addressed feedback” section or regenerate the body blindly.

```bash
gh pr view {number} --json body --jq .body > "${TMPDIR:-/tmp}/pr-body.md"
# Edit the file under the scannable rules.
gh pr edit {number} --body-file "${TMPDIR:-/tmp}/pr-body.md"
```

### Push

Run the full suite on the final head after merging the base and batching all fixes, then push.

```bash
git push
```

Capture the new HEAD SHA for the *Apply thread actions* "comment+resolve" replies:

```bash
git rev-parse HEAD
```

## Re-request review

Only run if the user opts in at the re-request prompt.

```bash
gh api repos/{owner}/{repo}/pulls/{number}/requested_reviewers --field 'reviewers[]=username'
```

Show the final PR URL.
