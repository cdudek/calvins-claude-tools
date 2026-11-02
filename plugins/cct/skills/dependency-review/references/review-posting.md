# Review Posting

**NEVER post automatically. Only post when the user explicitly requests it.**

## User Request Examples
- "Post findings 1, 3, 5 as request_changes"
- "Post all as comment"
- "Approve with summary"

## Posting Flow

### 1. Get latest commit SHA
```bash
COMMIT_SHA=$(gh pr view <pr_number> --json headRefOid -q .headRefOid)
```

### 2. Build and submit review payload
```bash
gh api repos/{owner}/{repo}/pulls/<pr_number>/reviews \
  -X POST --input - <<EOF
{
  "commit_id": "<commit_sha>",
  "event": "APPROVE|COMMENT|REQUEST_CHANGES",
  "body": "Dependabot PR review summary\n\n🤖 Reviewed with Claude Code (Opus)",
  "comments": [
    {
      "path": "relative/file/path",
      "line": 42,
      "side": "RIGHT",
      "body": "The finding description"
    }
  ]
}
EOF
```

### Line side rules
- Comments on **added/modified lines**: `"side": "RIGHT"`
- Comments on **deleted lines**: `"side": "LEFT"`
- **Multi-line comments**: add `"start_line"` and `"start_side"`

### 3. Confirm before submitting
Show the user the exact payload (formatted readably) and ask for final confirmation. Only submit after they confirm.
