# PR context

Run in parallel:

```bash
gh pr view <pr_number> --json title,body,state,author,baseRefName,headRefName,additions,deletions,changedFiles,files,commits,labels,id
# quick mode (`pr`) only. pr-deep and pr-max build the diff locally instead; this one truncates large PRs.
gh pr diff <pr_number>
gh pr diff <pr_number> --name-only
gh pr diff <pr_number> --stat
gh pr checks <pr_number>
PENDING_REVIEW=$(bash "${CLAUDE_SKILL_DIR}/scripts/review-pending.sh" <owner> <repo> <pr_number>)
```

`id` is the PR's GraphQL node id (`PR_...`); posting needs it. `$PENDING_REVIEW` is empty, or JSON with `id`, `node_id`, `comment_count`, `current_user`. Posting uses it to pick Scenario A or B.

`pr-deep` and `pr-max` also fetch, in the same batch:

```bash
gh api repos/{owner}/{repo}/pulls/<pr_number>/reviews
gh api repos/{owner}/{repo}/pulls/<pr_number>/comments
```

Do not fetch review threads here. `posting-pipeline.md` does that, into a temp file, when the user asks to post.
