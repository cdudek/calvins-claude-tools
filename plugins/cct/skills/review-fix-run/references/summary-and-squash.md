# Post-loop summary and squash offer

Read at loop end to render the summary and decide whether to offer a squash — the template,
the DISCUSS-listing rule, and the unpushed-iteration-commit detection.

#### Show Summary

```
## Review-Fix Loop Complete

Mode: {changes | changes-max | files | files-max}
Codex co-review: {auto | on | off}
Iterations run: {count}
Starting iteration: {start_number}

| Iteration | Findings | Fix set | Changes | Convergence |
|-----------|----------|---------|---------|-------------|
| {N}       | {count}  | {fix_set count} | {files} | —           |
| {N+1}     | 0        | —       | —       | clean code  |

Reason stopped: {clean code | all-out-of-scope | all-rejected | all-unverifiable | no changes | test-only | fixes-failed | max iterations | repeated findings | aborted: <reason>}
```

For files / files-max, also show `Files reviewed: {final file list}`. If any DISCUSS items were collected across iterations, list them with reasons — identify each by `file:line` + its `body`, **not** by `F<id>`: `discuss.json` is the cross-iteration accumulator, so its stored ids come from whichever revision first raised each item and mean nothing outside it (see step 4 → *Finding identity*). Within a single iteration's report, `F<id>` is the identifier.

#### Offer Squash

Only offer if (1) more than 1 iteration commit was created and (2) those commits have NOT been pushed.

```bash
upstream=$(git rev-parse --abbrev-ref @{u} 2>/dev/null)
if [ -z "$upstream" ]; then
  git log --oneline HEAD
else
  git log --oneline @{u}..HEAD
fi
```

Count only commits matching the `review-fix iteration` prefix. If unpushed iteration commits exist, offer: "Squash {count} unpushed iteration commits into one?"

- **yes** → delegate to `/cct:git-commits-squash branch`.
- **no** → keep individual commits.
