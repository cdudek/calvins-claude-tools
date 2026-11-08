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

Preserve and refresh the readable Decision4 section using [Decision4 PR writing](../../sdlc-run/references/decision4-pr.md) and the template's writing-rules comment. Recompute the whole-diff boundary-map floor after fixes, update the concrete recovery steps and responsible role/person, record a classification change when needed, and validate the actual body before publishing successful statuses.

Propose appending an "Addressed feedback" section to the PR body listing what was fixed.

```bash
gh pr edit {number} --body "$(cat <<'PREOF'
{updated_body}
PREOF
)"
```

### Push

Run the full local gate on the final head after merging the base and batching all fixes.
`scripts/ci-local` owns push and status publication when installed; the raw push below is
only for repositories still using a full local suite without that script.

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
