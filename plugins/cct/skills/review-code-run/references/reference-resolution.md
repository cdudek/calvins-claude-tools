# References → INPUT.md

`INPUT.md` is the human framing of a review: the ticket, its acceptance criteria, linked issues, and any note the user passed. `review-dimensions-selector`, `review-code-reviewer` and `review-feedback-run` read it. `ac-gate.sh` reads it too, and the acceptance criteria it finds here are the only ones the review will ever audit.

Write it when there is content, **including when the only content is a reference you could not resolve**. A failed fetch is information: it separates "this PR has no ticket" from "this PR has a ticket nobody could read", and only the second one is worth re-running. With no content at all, do not create the file.

## 1. Find references

Scan the PR title and body, the branch name, and the commit messages.

| Pattern | Example |
|---|---|
| GitHub issue or PR | `#123`, `github.com/.../issues/123`, `.../pull/123` |
| Linear issue | `ENG-123`, or a Linear URL |

Deduplicate. Classify each as **closes** (keywords: closes, fixes, resolves), **related**, or **blocked-by**.

## 2. Resolve them

Skip if none found. Otherwise spawn one subagent (model: sonnet) that fetches all of them:

- GitHub issue: `gh issue view <n> --json title,body,state,labels`
- GitHub PR: `gh pr view <n> --json title,body,state,files`
- Linear issue: Linear MCP `get_issue`

For each reference it returns:

```
[REF] #123 (closes | related | blocked-by)
Title: ...
Status: ...
Purpose: 1-2 sentences
Acceptance criteria: bullet list, verbatim
Constraints/decisions: key items
Out of scope: if stated
```

If a related PR defines an API or schema this change uses, it also lists that contract: signatures, schema changes, new constants, error contracts.

**Acceptance criteria are copied, never summarised.** One bullet per criterion, in the ticket's own words. `ac-gate.sh` splits this list into the `AC-1..AC-N` the audit grades, so a paraphrase grades the paraphrase. A ticket that states none gets no `Acceptance criteria:` label at all — write `Acceptance criteria: none stated` rather than inventing one.

**A fetch that fails is recorded, not dropped.** Retry 2-3 times first — the Linear connector returns intermittent 500s. Still failing, or access denied: report the reference as unresolved and carry it to step 3.

## 3. Write `$STATE_DIR/INPUT.md`

```markdown
## User commentary
<what the user passed, verbatim — omit the section if nothing>

## Resolved references
<the [REF] blocks — omit the section if none>

## Unresolved references
<one line per reference that could not be fetched — omit the section if none>
```

Copy the user's text as-is. Do not summarise it.

An unresolved line names the reference, its classification and what went wrong:

```markdown
## Unresolved references
- SUPPLY-577 (closes) — Linear returned 500 after 3 attempts
```

The heading is the exact string `## Unresolved references`. `ac-gate.sh` matches it to tell `unresolved` from `no-reference`.

**The `[REF]` labels are a closed set, and `ac-gate.sh` depends on it.** `Title:`, `Status:`, `Purpose:`, `Acceptance criteria:`, `Constraints/decisions:` and `Out of scope:` — those, and nothing else, end the acceptance-criteria list. The gate used to end it on any line shaped like `Word:`, which read an ordinary sentence starting `Note:` as a label and dropped every criterion below it. Adding a label here without adding it to `is_label()` in `ac-gate.sh` swallows the new label into the criterion above it.

## 4. Gate the acceptance-criteria audit

```sh
bash "${CLAUDE_SKILL_DIR}/scripts/ac-gate.sh" "$STATE_DIR" "$STATE_DIR/INPUT.md"
```

Pass the path even when you wrote no file — the script handles a missing one. Read `- mode:` as `$AC_MODE` and `- reason:` as `$AC_REASON`. The lane reads `$AC_MODE`; the report reads `$AC_REASON`.

The script extracts the criteria itself, from the `Acceptance criteria:` bullets. Do not extract them yourself and do not write `ac.json` by hand — a gate that two paths can set answers differently on a resume.

## 5. Tell the user

Show the resolved context, 2-3 lines per item. Point out anything that changes the review. Say the file was saved.

State the AC gate in one line, always — `mode: ac` with the criterion count, or `mode: none` with the reason. A review that silently skips the audit reads as a review that passed it.
