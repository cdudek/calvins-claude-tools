# Mode: pr

Collects the review surface for `pr-deep` and `pr-max`. Sets `$STATE_DIR`, `$ROOT`, `$DIFF`, `$INPUT_MD`, `$TARGET_BRANCH`, and the posting inputs. The lane reads these.

`$ARGUMENTS` = `<pr_number>`. Not numeric → report and stop. Store it as `$PR_NUMBER`.

## 1. Enter the PR branch

Already on the head branch, or told to review in place → `$ROOT` = current dir. Skip the rest of this step.

Otherwise:
1. `head=$(gh pr view <pr_number> --json headRefName --jq .headRefName)`
2. `git fetch origin "$head:$head"`
3. Enter a worktree on a real local branch, so `review-feedback-run` can push fixes later.

| `head` contains `/`? | Do |
|---|---|
| no | `EnterWorktree(name: <head>)`. Safe to repeat. |
| yes (bot branches) | Check `git worktree list` first. Already in it → use current dir. Exists elsewhere → `EnterWorktree(path: <it>)`. Else `git worktree add -b <head> <workspace>/<prefix>pr-<n>-<slug> origin/<head>`, then `EnterWorktree(path: <it>)`. |

Both routes run the repo's worktree-setup hook (`make worktree_setup` / Docker) the same way: it fires on the `EnterWorktree` call itself, not on the parameter. The bot-branch row is the same 3-case dispatch as `review-feedback-run/references/pr-worktree.md`; change both together.

`$ROOT` = the worktree path.

## 2. Gather context

`$OWNER`/`$REPO` from `git remote get-url origin`.

Follow `pr-context-loading.md`. From its output keep `id` → `$PR_NODE_ID`, `baseRefName` → `$BASE_BRANCH` and `$TARGET_BRANCH`, and the pending review → `$PENDING_REVIEW`.

**Check `baseRefName` matches `^[A-Za-z0-9._/+-]+$`.** If not, stop and report it. It reaches a prompt unescaped.

## 3. State and diff

```sh
bash "${CLAUDE_SKILL_DIR}/scripts/state-dir.sh" pr "$LANE" "$PR_NUMBER"
```
Read `$STATE_BASE` and `$STATE_DIR` from its output. Skip the remote-sync step of `state-dir.md` — step 1 already fetched.

Skip if `$STATE_DIR/pr.diff` exists:
```sh
bash "${CLAUDE_SKILL_DIR}/scripts/save-pr-diff.sh" "$BASE_BRANCH" "$STATE_DIR/pr.diff"
```
`$DIFF` = that file. `$EXTRA_TAGS` = empty. Do not use `gh pr diff` here; it truncates large PRs.

## 4. References

Follow `reference-resolution.md`. `$INPUT_MD` = `$STATE_DIR/INPUT.md`, or absent. It also runs the AC gate and sets `$AC_MODE` and `$AC_REASON`.

## Report header

**PR Summary**: 2-3 sentences.

## Posting — only when the user asks

Follow `posting-pipeline.md`. Build its input:
```sh
bash "${CLAUDE_SKILL_DIR}/scripts/posting-findings.sh" "$STATE_DIR/findings.json" "$STATE_DIR/verdicts.json"
```
Pass the result with `$OWNER`, `$REPO`, `$PR_NUMBER`, `$PR_NODE_ID`, `$PENDING_REVIEW`, `$ROOT`. Never post without a request.
