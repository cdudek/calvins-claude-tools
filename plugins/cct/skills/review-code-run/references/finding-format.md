# Finding format

Severity emojis, categories and confidence bands come from `../../role-review-vocabulary/SKILL.md`. This file only sets the layout.

## Section A — detailed findings

Used by every validated report. Group by file. The `F<id>` is the finding's `findings.json` `id`, never its position; ids are non-contiguous after sorting and that is correct.

```markdown
### F7. 🔴 **[security]** SQL injection risk — `controllers/bar.rb:15` (95%, both) ⛓ entrenches

The `params[:query]` is interpolated into the SQL string without sanitization.

**Fails when:** a query of `%' OR 1=1 --` reaches the action; the LIKE clause matches every row.

Suggested fix:
```ruby
Review.where("title LIKE ?", "%#{ActiveRecord::Base.sanitize_sql_like(params[:query])}%")
```

**Idiomatic fix:** move the search into a scope on `Review`. The one-line patch works but leaves query construction in the controller, which the next action will copy.
```

Each finding shows:

| Part | Rule |
|---|---|
| `F<id>`, emoji, severity, category, title, full path, confidence | always |
| `(…, both)` or `(…, codex)` after the confidence | only on a co-review; omit for `claude` |
| `⛓ entrenches` after the header | only when `reversibility: entrenches`; omit for `cheap` |
| **Fails when:** | always — the `failure_scenario`, on its own line |
| Suggested fix | when there is one |
| **Idiomatic fix:** | when `idiomatic_fix` is present; render it after the suggested fix, with what the patch leaves behind |

Group findings that must be fixed together. Say why.

## Section B — review action plan

Used by `pr` inline, and by `pr-deep` / `pr-max` only during posting (`posting-pipeline.md` Phase 2).

```markdown
## Review Action Plan

Existing threads: 6 (3 resolved, 2 active from you, 1 from @sznajderm) | —
Pending review: yes (4 comments) | no
Findings: 4

| ID | Finding | Location | Conf | Action | Reason |
|----|---------|----------|------|--------|--------|
| F7 | 🔴 **[security]** SQL injection risk | `bar.rb:15` | 95%, both | reopen | Resolved thread missed this vector |
| F2 | 🟠 **[bug]** Missing validation | `foo.rb:42` | 85% | skip | Your pending comment covers this |
| F4 | 🟠 **[performance]** N+1 query | `review.rb:23` | 80% | new | — |

Accept all? Type 'ok', or override: "F2:append, F11:new" / "append all except F7,F4"
```

`ID` is the same `F<id>` as Section A. Overrides name rows by that id. `Location` is the short filename. `Conf` carries the same provenance marker as Section A.

| Command | Differences |
|---|---|
| `pr` | no `findings.json`, so `ID` is plain `1..N`. Every action is `new`. `Existing threads: —`. `Pending review` from `$PENDING_REVIEW`. |
| `pr-deep`, `pr-max` | all six actions possible. Header counts from `posting-pipeline.md` Phase 1. |

Show the whole table even when every row is `skip`.

## Actions

| Action | Posting does |
|---|---|
| `skip` | nothing |
| `reply` | a threaded reply on the matched thread, in the pending review |
| `reopen` | a reply on the matched resolved thread, then unresolve it after submit |
| `append` | PATCH the matched comment body to add context; author unchanged |
| `new` | a new thread at `path:line` |
| `flag` | undecided; the user picks `skip` / `reply` / `new` / `append` |

Script mapping: `review-posting.md`.

## Section C — the posted comment

The body of a review thread on GitHub. Section A renders for whoever ran the review; this renders for the PR author, who never saw the report and cannot open `$STATE_DIR`.

One line of grammar, from [Conventional Comments](https://conventionalcomments.org/). GitLab mandates that format in its own handbook, so this is an adopted standard rather than a local invention.

````
<emoji> <label> (<dimension>[, blocking]): <what is wrong> `F<id>`

<when it breaks>

```suggestion
<the fix>
```
````

### Emoji and label

Both come from `severity`. The emoji is not redundant with the label — `issue` covers two severities and the emoji is what splits them.

| `severity` | Emoji | Label | Posts? |
|---|---|---|---|
| `critical` | 🔴 | `issue` | yes |
| `warning` | 🟠 | `issue` | yes |
| `suggestion` | 🟡 | `suggestion` | yes |
| `nit` | — | — | **no** |

`suggestion` is the floor. `posting-findings.sh` drops every `nit` before the plan is built, so a nit renders in Section A and reaches the fix loop but never becomes a thread. `pr-quick` runs no script and drops them itself.

### `blocking`

Append `, blocking` when the finding blocks the verdict per `report-sections.md` → Verdict: a confirmed `critical` or `warning`, or **any** severity carrying `reversibility: entrenches`. Write nothing otherwise.

The decoration marks the exception because every convention in this space reads an unmarked comment as blocking. `🟡 suggestion (design, blocking)` is the combination that carries the most information — it says the change is small, and says it still cannot wait.

`pr-quick` runs no validator and collects no `reversibility`, so there the marker follows `severity` alone: `critical` and `warning` carry it, `suggestion` never does.

### The two sentences

| Line | From | Holds |
|---|---|---|
| subject | `body` | what is wrong |
| second | `failure_scenario` | when it breaks |

Both, every time. Short here means no padding, not no reason. A comment that names a defect and skips the scenario is the most common defect in real review comments, and it is the one this pipeline already has the data to avoid.

Render `idiomatic_fix` as the suggestion block when it is present — the framework-native form is the fix worth committing.

### What never reaches GitHub

`confidence`, `source`, `evidence`, `file:line`, and the validator verdict. Confidence and provenance are inputs for whoever ran the review; the author cannot act on either. GitHub already anchors the thread to the line and renders the code above it.

`F<id>` closes the subject line so a reader can match the thread to the report without spending a line on it.

### The suggestion block

Add ` ```suggestion ` when the finding's line sits in the diff and the fix is known. It gives the author a one-click commit, and a fix the author can apply is what separates a useful comment from a complaint.

GitHub refuses a suggestion on a line outside the diff. An off-diff finding carries no block and goes to the review body instead (`posting-pipeline.md` Phase 2).

### Length and language

Two sentences of prose, at most 20 words each. Code blocks do not count.

Both sentences arrive already written — `reviewer-rules.md` → Write in plain English owns the rules, including the 20-word cap and "state the defect, never ask about it". Enforcing them here would be too late: this layer posts `body` and `failure_scenario` byte-exact and has nothing to rewrite them from.

### Examples

A blocking defect with a committable fix:

````
🔴 issue (security, blocking): The code puts `params[:query]` into the SQL string without sanitization. `F3`

A query of `%' OR 1=1 --` makes the LIKE clause match every row.

```suggestion
    Review.where("title LIKE ?", "%#{ActiveRecord::Base.sanitize_sql_like(params[:query])}%")
```
````

A small change that still cannot wait, with no committable fix:

```
🟡 suggestion (design, blocking): The controller builds the query string itself. `F11`

The next search action copies this pattern, and then two places need the fix.
```

A warning the author can weigh:

```
🟠 issue (test-quality): The spec asserts the status code but never the body. `F7`

A handler that returns 200 with an empty payload passes this spec.
```
