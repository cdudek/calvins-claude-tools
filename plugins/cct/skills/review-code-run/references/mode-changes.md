# Mode: changes

Collects the review surface for `changes-deep` and `changes-max`. `$ROOT` = the current working tree. No worktree entry.

`$ARGUMENTS` = `[base_branch]`, optional.

## 1. Gather context

Follow `changes-context-loading.md`. It sets `$BASE`, stops on a dirty tree, and shows the change summary. No committed changes → stop.

`$TARGET_BRANCH` = the caller's `Target branch:` if given, else `$BASE`. They differ when a caller narrows the diff to a commit-ish: `$BASE` is the diff window, `$TARGET_BRANCH` is what the branch merges into. Only `$TARGET_BRANCH` reaches the dead-code rule in `reviewer-rules.md`.

## 2. State and diff

Follow `state-dir.md` step 1 (remote sync), then:
```sh
bash "${CLAUDE_SKILL_DIR}/scripts/state-dir.sh" changes "$LANE" "$(git branch --show-current)"
```
Read `$STATE_BASE` and `$STATE_DIR` from its output.

Skip if `$STATE_DIR/changes.diff` exists:
```sh
git diff "$BASE"...HEAD > "$STATE_DIR/changes.diff"
```
`$DIFF` = that file. `$EXTRA_TAGS` = empty.

## 3. References

Follow `reference-resolution.md`. Scan the branch name and `git log --oneline $BASE..HEAD`. `$INPUT_MD` = `$STATE_DIR/INPUT.md`, or absent. It also runs the AC gate and sets `$AC_MODE` and `$AC_REASON`.

## Report header

**Change Summary**: branch, base, commit count, changed files. No posting.
