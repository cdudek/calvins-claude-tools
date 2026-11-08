# Changes context

## 1. Find the base

1. The user gave one → use it.
2. Else, for each of `origin/main`, `origin/develop`, `origin/master` that exists: `git rev-list --count <merge-base>..HEAD`. Pick the smallest count.
3. Else `origin/main`.

Store it as `$BASE`. **It must match `^[A-Za-z0-9._/+-]+$`.** If not, stop and report the name. `git` accepts `<`, `>` and `&` in a ref, and this value reaches a prompt and a `git diff` command as-is.

## 2. Require a clean tree

```bash
git status --porcelain
```

Any output → stop and say:

> Uncommitted changes present. `changes` review is committed-only — commit or stash, then re-run.

## 3. Gather

Run in parallel:

```bash
git branch --show-current
git log --oneline $BASE..HEAD
git diff $BASE...HEAD
git diff --name-status $BASE...HEAD
git diff --stat $BASE...HEAD
```

Three dots: merge-base to HEAD. Two dots would include base-side changes.

## 4. Show the summary

```
**Branch**: <branch> (base: <$BASE>)
**Commits**: <n> ahead of <$BASE>
**Changed files**: <n> (+ins/-del)

<file list with status>
```

No commits ahead → stop. Nothing to review.
