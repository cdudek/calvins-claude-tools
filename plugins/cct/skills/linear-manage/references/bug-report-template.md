# Bug Report Template

**Linear object:** Issue (with the `bug` label)
**Merged from:** this kit's version (which keeps Expected and Actual apart) plus the Linear
workspace template's "Tests Needed" block and its Impact prompt.

**The fix gets an EARS line; the reproduction gets a Gherkin scenario.** A bug is the textbook
case for the unwanted-behaviour pattern — `If <trigger>, then the system shall <response>` is the
pattern EARS was built for. The grammar lives in `../sdlc-run/references/requirements-grammar.md`.

## MCP Steps

```
save_issue:
  title: "Fix: [what is broken] in [where]"
  team: "team-name"
  labels: ["bug"]
  priority: 2
```

For a root-cause analysis worth keeping, attach a document to the issue:

```
create_document:
  title: "Bug investigation: [what is broken]"
  issue: "<issue-id>"
```

## Template

```markdown
## Bug summary

[One sentence: what is broken, where, and for whom]

## Steps to Reproduce

1. Go to [...]
2. Click [...]
3. See [...]

## Expected Behavior

[What should happen]

## Actual Behavior

[What happens instead. Include the exact error text, not a paraphrase]

## Environment

- **Browser:** [Chrome 120]
- **Device:** [iPhone 15 / Desktop]
- **URL:** [/reviews/software/detail]
- **Environment:** [production / staging]
- **First seen:** [YYYY-MM-DD, or the release that introduced it]

## Impact

[Who is affected and how badly. All users, one segment, or one account? Is work blocked?
Is there a workaround?]

## Technical Context

- **Suspected area:** `src/path/to/module/`
- **Related issues:** LIN-XXX
- **Logs or traces:** [resolvable link, never a local path]

## The rule that broke (EARS)

- **F1** If [the trigger that produces the bug], then the system shall [the correct response].

## Acceptance criteria

Scenario: [the reported case] — proves F1
  Given [the exact state that reproduces it, with concrete data]
  When  [the action]
  Then  [the correct observable outcome]

- [ ] No regression in [the related feature most likely to break]

## Tests Needed

- [ ] A test reproducing this case, committed failing first
- [ ] Verify the fix on mobile
- [ ] Check the edge case with [...]
```

## Why Expected and Actual stay apart

The Linear workspace template merges them into one "What's Wrong" field. That merge is the one
change not to adopt: the gap between expected and actual **is** the bug report. Collapsed into a
single paragraph, the reader has to infer which half is the defect, and a reader who infers wrong
fixes the wrong thing.

## Why the EARS line is worth the extra line

Without it the ticket says what went wrong once, for one input. With it the ticket says what must
now always hold. That is the difference between a fix that closes this report and a fix that closes
the class — and it is the line the regression test gets its name from.
