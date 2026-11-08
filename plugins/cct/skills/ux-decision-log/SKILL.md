---
name: ux-decision-log
description: "Records the owner's interaction decisions: turns UX findings and proposed interaction rules into decisions the owner can make without reading anything else (shared rules first, five related decisions at a time, each accepted, swapped, deferred or answered in the owner's words), then writes one decision record per answer. Use when the user says 'let's decide the UX findings', 'go through the UX decisions', 'record this interaction decision', 'log the owner's UX decision', 'make a decision page for the owner'. Skip for: technical, architecture or data ADRs (cct:arch-decision-log); writing the interaction rules themselves (cct:ux-guidelines-write)."
user_invocable: true
metadata:
  version: 1.0.0
  author: calvindudek
---

# cct:ux-decision-log

**Arguments:** `[next | routine | page]`

The owner decides; the skill makes each decision easy and records it.

**Scope.** This skill records the owner's *interaction* decisions (how the product behaves for its users: shared rules, screen behaviour, wording choices). A technical decision (architecture, stack, data model, infrastructure) is not recorded here: hand it to `cct:arch-decision-log`, which owns technical ADRs. When a UX decision forces a technical one, record the interaction half here and name the technical half for `cct:arch-decision-log`.

Shared files are in `references/`, two levels up from this skill's base directory:
`finding-format.md`, `rule-areas.md`, `writing.md`. Read `docs/ux/setup.md` first.

## 1. Build the decision list

From the latest `findings.md` and the proposed rules in the interaction guidelines:

1. **Shared rules first.** Every proposed rule becomes one decision, shown once with every screen
   it affects. Findings that the rule settles are grouped under it, not deleted or merged.
2. **Then screen-specific choices** that no rule settles.
3. **Routine fixes** (corrections with no real choice) go into one separate group for one review.
   A change in behaviour is never routine.
4. **Order:** by what each decision unblocks. Groups of five related decisions. The first group
   says in one or two sentences why it comes first.

Write it to `docs/ux/decisions-<YYYY-MM-DD>.md` (or where `setup.md` says).

## 2. Every decision, self-contained

```markdown
### <Plain-language title>
- **Today:** what happens now, with a concrete example and the exact words on screen.
- **Recommended:** the change, concretely: what the user will see and do.
- **Why it helps you:** the benefit to the owner's actual workflow.
- **Downside:** the main tradeoff. **Alternative:** only if meaningfully different, shown just as
  concretely.
- **Before / after:** a screenshot and a labelled "Proposal" mockup, or the exact text before and
  after.
- **Applies to:** every screen it touches (for a shared rule).
- **Question:** one specific question the owner can answer.
- **Verified:** which parts are seen on screen, read in code, assumed, or a preference.
- **You said:** the owner's earlier words, quoted with date, or "no earlier request found".
<details><summary>Supporting notes</summary>Finding numbers · codes · file:line · other products.</details>
```

Never justify a recommendation only because it is already built or matches a reference product.
Never ask "modal or drawer?" without showing what each means for the task.

## 3. Go through it with the owner

- Show the five decisions of the current group, in full, in the conversation or on the decision
  page.
- Ask with `AskUserQuestion`, at most four questions per call, so a group of five takes two calls.
  Each question offers: **Accept the recommendation** · **Choose the alternative** (only when
  there is one) · **Defer**. "Other" lets the owner answer in their own words.
- Routine fixes: one question for the whole group ("Apply all", "Show me the list first", "Hold"),
  with the list visible.
- After each group, write **one file per answered decision**, never a row in a log:
  `<designsDir>/<YYYY-MM-DD>-adr-<slug>.md` (`designsDir` from `sdlc.json`, else `docs/designs`;
  nest by `<year>/<year-month>/` when that folder already does). Frontmatter: `title`,
  `type: adr`, `status: accepted`, `created`, `decided_by: owner`, `tags: [ux, <area>]`, and
  `supersedes: [<id>]` when it replaces an earlier decision — then set that file's
  `status: superseded` and `superseded_by`. Body: the decision as shown, then the answer
  verbatim. A deferred decision gets no file; it stays in the round's list. Then run
  `python3 scripts/design_index.py write` when the repo has it, and `cct:ux-guidelines-write record`.
  One file per decision is what lets the next agent read `INDEX.md` and open one file: the
  appended log it replaces had reached 2,910 lines within 19 days in one repo.
- Stop after each group and wait. Never answer for the owner, and never treat silence or an
  earlier message as acceptance.

## 4. The decision page (optional, `page`)

When the owner wants a page: write the decision document as one local HTML file in the repo, following
`references/decision-page.md` point by point. Never publish it to claude.ai (no Artifact, no Claude
Docs) or any hosted page: the owner opens the file from disk. Answers save in the browser and an
Export button downloads `answers.json`; read that file, not a page, when the owner says they have
answered. Keep the same content and order, one group at a time, with the supporting notes folded away.
Rewrite the same file each time (the path is in `setup.md`).
