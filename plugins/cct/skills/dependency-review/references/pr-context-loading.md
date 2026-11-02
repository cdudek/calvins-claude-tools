# PR Context Loading

Run these commands in parallel to gather PR context:

```bash
# PR metadata
gh pr view <pr_number> --json title,body,state,author,baseRefName,headRefName,additions,deletions,changedFiles,files,commits,labels

# Full diff
gh pr diff <pr_number>

# Changed file names only
gh pr diff <pr_number> --name-only

# CI status
gh pr checks <pr_number>
```

Extract `{owner}/{repo}` from: `git remote get-url origin` (parse the GitHub URL).
