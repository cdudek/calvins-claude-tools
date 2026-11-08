---
description: PR-finalize recipes — merge base, finalize (push + body), re-request review. Each H2 is dispatched by name from a step in references/commands/pr.md.
---

# PR Finalize

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

Propose appending an "Addressed feedback" section to the PR body listing what was fixed.

```bash
gh pr edit {number} --body "$(cat <<'PREOF'
{updated_body}
PREOF
)"
```

### Push

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
