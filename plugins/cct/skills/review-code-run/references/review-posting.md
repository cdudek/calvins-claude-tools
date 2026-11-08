# Review posting

**Only run this when the user has asked to post.**

Takes the confirmed action plan and pushes it to GitHub. No matching here, and no composing — every `body` arrives already rendered per `finding-format.md` → Section C.

## Inputs

- `$PR_NODE_ID`, `$PENDING_REVIEW` (empty or `{id, node_id, comment_count, current_user}`), `$OWNER`, `$REPO`
- the action plan: each entry has `action`, `path`, `line`, `side`, `body`, `reason`, and for matched actions `matched_thread_id` / `matched_comment_database_id`. `body` is the finished comment from `finding-format.md` → Section C — emoji, label, decoration, two sentences, `F<id>`, and a suggestion block where the line is in the diff. Post it byte-exact.

Drop every `skip`. Any `flag` left → stop: "Cannot post: N finding(s) still flagged. Pick skip / reply / reopen / new / append for each, then ask again." Nothing left → say so and stop.

Split the rest: `NEW` (`new`), `REPLY_LIKE` (`reply`, `reopen`), `APPEND` (`append`).

## 1. Get a pending review

GitHub allows one pending review per user. The path depends on `$PENDING_REVIEW`.

**A — no pending review.**

| Plan has | Do |
|---|---|
| any `NEW` | create the review and all new threads in one call. `$NEW_JSON` is an array of `{path, line, side, body, start_line?, start_side?}`. |
| `REPLY_LIKE` only | create an empty pending review. |
| `APPEND` only | nothing. Appends are REST PATCHes. Go to step 2; `$REVIEW_NODE_ID` stays unset and step 3 does not run. |

```bash
# any NEW:
REVIEW_NODE_ID=$(printf '%s' "$NEW_JSON" | bash "${CLAUDE_SKILL_DIR}/scripts/review-create-pending-with-threads.sh" "$PR_NODE_ID" | jq -r '.review_node_id')
# REPLY_LIKE only:
REVIEW_NODE_ID=$(bash "${CLAUDE_SKILL_DIR}/scripts/review-create-pending.sh" "$PR_NODE_ID" | jq -r '.node_id')
```

**B — a pending review exists.** Reuse it, then add each new thread one call at a time:

```bash
REVIEW_NODE_ID="$(printf '%s' "$PENDING_REVIEW" | jq -r '.node_id')"
# for each NEW finding:
cat <<'EOF' | bash "${CLAUDE_SKILL_DIR}/scripts/review-add-thread.sh" "$REVIEW_NODE_ID" "$path" "$line" "$side" [start_line start_side]
${finding.body}
EOF
```

A non-zero exit from `review-add-thread.sh` → stop and show the raw response. Part of the plan is already in the pending review; the user decides.

## 2. Appends, replies, reopens

In this order. Reply and reopen need `$REVIEW_NODE_ID`; skip them when it is unset.

```bash
# append — body is original + delimiter + new text; uses the numeric databaseId
cat <<'EOF' | bash "${CLAUDE_SKILL_DIR}/scripts/review-update-comment.sh" "$OWNER" "$REPO" "$MATCHED_COMMENT_DATABASE_ID"
${composed_body}
EOF
# reply
cat <<'EOF' | bash "${CLAUDE_SKILL_DIR}/scripts/review-reply.sh" "$MATCHED_THREAD_ID" "$REVIEW_NODE_ID"
${finding.body}
EOF
# reopen — one line saying why, a blank line, then the Section C comment unchanged;
# remember the thread for step 4
cat <<'EOF' | bash "${CLAUDE_SKILL_DIR}/scripts/review-reply.sh" "$MATCHED_THREAD_ID" "$REVIEW_NODE_ID"
Reopening this thread. ${reason}

${finding.body}
EOF
REOPEN_THREAD_IDS+=("$MATCHED_THREAD_ID")
```

`${reason}` is the reconciler's own `reason` for choosing `reopen` (`reconcile-threads.md` → Return). Do not compose a second one: the reader is being told why a closed thread came back, which is exactly what that field already says.

The append delimiter:
```
<original_body>

---
🤖 **Additional context from Claude review:**

<the Section C comment, unchanged>
```

## 3. Ask about submitting

Only when `$REVIEW_NODE_ID` is set.

Suggest an event: 1+ critical or 2+ warnings → `REQUEST_CHANGES`; else `COMMENT`. Strong objections in the user's own pending comments → `REQUEST_CHANGES`. Never suggest `APPROVE`.

```
Suggested submit: REQUEST_CHANGES (3 warnings, 1 critical)
Summary: "..."

- 'ok' — submit as suggested
- 'comment' / 'approve' / 'request_changes' — override
- 'no submit' — leave it pending
- 'edit: <summary>' — custom summary
```

`no submit` with reopens pending → say: the unresolves run when the review is submitted.

## 4. Submit

```bash
cat <<'EOF' | bash "${CLAUDE_SKILL_DIR}/scripts/review-submit.sh" "$REVIEW_NODE_ID" "$EVENT"
${summary}
EOF
for thread_id in "${REOPEN_THREAD_IDS[@]}"; do
  bash "${CLAUDE_SKILL_DIR}/scripts/review-unresolve.sh" "$thread_id"
done
```

`review-submit.sh` adds the Co-reviewed footer. A failed unresolve → report it and continue with the rest.

## Errors

A failed script in step 1 or 2 → print its stderr, stop, and say what is already in the pending review. Never skip a failed action silently.
