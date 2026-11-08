#!/usr/bin/env bash
# Gather PR review feedback grouped by review thread.
# Usage: gather-pr-feedback.sh <pr_number>
# Output: Sections separated by `-#-#-` markers.
#   -#-#- BEGIN REVIEW_THREADS -#-#- ... -#-#- END REVIEW_THREADS -#-#-
#     JSONL — one thread per line with id, isResolved, isOutdated, viewerCanResolve,
#     comments[] (comment_id, body, path, line, author, created_at), pr_author (for guardrails),
#     comments_truncated (true if any thread had >100 comments).
#   -#-#- BEGIN PR_REVIEWS -#-#- ... -#-#- END PR_REVIEWS -#-#-
#     JSONL — one review per line with id, author, state, body, submittedAt.
#   -#-#- BEGIN ISSUE_COMMENTS -#-#- ... -#-#- END ISSUE_COMMENTS -#-#-
#     JSONL — one general PR comment per line with id, author, body, createdAt, url.
set -euo pipefail

PR_NUMBER="${1:?Usage: gather-pr-feedback.sh <pr_number>}"
[[ "$PR_NUMBER" =~ ^[0-9]+$ ]] || { echo "Error: PR number must be numeric, got '$PR_NUMBER'"; exit 1; }

OWNER=$(gh repo view --json owner -q '.owner.login')
REPO=$(gh repo view --json name -q '.name')

THREADS_QUERY='query($owner:String!,$repo:String!,$pr:Int!,$cursor:String){
  repository(owner:$owner,name:$repo){
    pullRequest(number:$pr){
      author{login}
      reviewThreads(first:50, after:$cursor){
        pageInfo{hasNextPage endCursor}
        nodes{
          id
          isResolved
          isOutdated
          viewerCanResolve
          comments(first:100){
            nodes{
              databaseId
              body
              path
              line
              originalLine
              author{login}
              createdAt
            }
            pageInfo{hasNextPage}
          }
        }
      }
    }
  }
}'

REVIEWS_JQ='.[] | {
  id: .id,
  author: .user.login,
  state: .state,
  body: .body,
  submitted_at: .submitted_at
}'

ISSUE_COMMENTS_JQ='.[] | {
  id: .id,
  author: .user.login,
  body: .body,
  created_at: .created_at,
  updated_at: .updated_at,
  url: .html_url
}'

echo "-#-#- BEGIN REVIEW_THREADS -#-#-"
cursor=""
pr_author=""
while :; do
  if [ -z "$cursor" ]; then
    response=$(gh api graphql -f query="$THREADS_QUERY" -F owner="$OWNER" -F repo="$REPO" -F pr="$PR_NUMBER")
  else
    response=$(gh api graphql -f query="$THREADS_QUERY" -F owner="$OWNER" -F repo="$REPO" -F pr="$PR_NUMBER" -F cursor="$cursor")
  fi
  pr=$(echo "$response" | jq -r '.data.repository.pullRequest.author.login')
  [ -z "$pr_author" ] && pr_author="$pr"

  truncated=$(echo "$response" | jq -r '
    [.data.repository.pullRequest.reviewThreads.nodes[]
     | select(.comments.pageInfo.hasNextPage == true) | .id] | .[]
  ')
  if [ -n "$truncated" ]; then
    echo "Warning: review thread(s) had >100 comments and were truncated. Thread IDs:" >&2
    echo "$truncated" | sed 's/^/  /' >&2
  fi

  echo "$response" | jq -c --arg pr_author "$pr_author" '
    .data.repository.pullRequest.reviewThreads.nodes[]
    | {
        id,
        isResolved,
        isOutdated,
        viewerCanResolve,
        pr_author: $pr_author,
        comments_truncated: .comments.pageInfo.hasNextPage,
        comments: [.comments.nodes[] | {
          comment_id: .databaseId,
          body,
          path,
          line: (.line // .originalLine),
          author: .author.login,
          created_at: .createdAt
        }]
      }
  '

  has_next=$(echo "$response" | jq -r '.data.repository.pullRequest.reviewThreads.pageInfo.hasNextPage')
  if [ "$has_next" != "true" ]; then break; fi
  cursor=$(echo "$response" | jq -r '.data.repository.pullRequest.reviewThreads.pageInfo.endCursor')
done
echo "-#-#- END REVIEW_THREADS -#-#-"

echo "-#-#- BEGIN PR_REVIEWS -#-#-"
gh api --paginate "repos/$OWNER/$REPO/pulls/$PR_NUMBER/reviews?per_page=100" --jq "$REVIEWS_JQ"
echo "-#-#- END PR_REVIEWS -#-#-"

echo "-#-#- BEGIN ISSUE_COMMENTS -#-#-"
gh api --paginate "repos/$OWNER/$REPO/issues/$PR_NUMBER/comments?per_page=100" --jq "$ISSUE_COMMENTS_JQ"
echo "-#-#- END ISSUE_COMMENTS -#-#-"
