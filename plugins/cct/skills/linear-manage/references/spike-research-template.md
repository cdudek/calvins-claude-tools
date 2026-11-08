# Research Note Template

**Linear object:** Document (attached to the spike Issue)
**Source:** this file, trimmed from the Linear workspace template of the same name.
The Linear workspace held a template of the same name until 2026-09-12; it was deleted,
so there is no live version to fetch.

**No EARS, no Gherkin.** A research note records findings, not obligations. If the research
produced a decision, write an ADR. If it produced a proposed solution, write an RFC. This document
is for what we learned when neither of those is ready yet.

## MCP Steps

```
create_document:
  title: "Research: <topic>"
  issue: "<spike-issue-id>"
  icon: ":microscope:"
```

Attach it to the **issue**, not the project — the reader finds it on the spike it came from.

## Template

```markdown
# Research: [Topic]

**Author:** [Name] · **Date:** [YYYY-MM-DD] · **Status:** [Draft | Complete | Archived]
**Prompted by:** [Link to the initiative, project or issue]

## Summary

> Two or three sentences: what was investigated and what we concluded.

[Summary]

## Questions

- [Question 1]
- [Question 2]

## Context and Motivation

**Background:** [What led to this investigation]
**Business impact:** [Why it matters]
**Technical context:** [Current system state or constraint]

## Approach

**Methods:** [Benchmarking, profiling, competitor analysis, prototype]
**Tools:** [What was used]
**Time spent:** [Duration]

## Findings

### [Finding title]

**What we learned:** [Description]
**Evidence:** [Data, metrics, observations. Evidence, not impressions.]
**Implications:** [What this means for our system or approach]

> Repeat per finding. Two strong findings beat six thin ones.

## Data

| Metric | Current | Target | Notes |
|---|---|---|---|
| [Metric] | [Value] | [Goal] | [Context] |

**Raw data:** [Resolvable link to the spreadsheet, dashboard or logs — never a local path]

## Conclusions

**What we now know:**

- [Insight]

**What we still do not know:**

- [Open question]

**Confidence:**

- **High:** [What we are sure about]
- **Medium:** [What seems likely but needs validation]
- **Low:** [What needs more investigation before anyone relies on it]

## Recommendations

**Immediate:**

1. [Action, with the reason]

**Next:**

1. [Next step]

## References

- [Documentation, prototypes, external sources, related RFCs and ADRs]

---

> If this research led to a technical decision, write an ADR. If it led to a proposed solution,
> write an RFC. If it led to neither yet, this note is the record, and it is enough.
```

## Why the confidence block is the part that matters

Most research notes present every finding at the same volume, so the reader cannot tell which
conclusion is load-bearing and which was a Tuesday-afternoon impression. Splitting them into high,
medium and low is the cheapest possible honesty, and it is what makes the note safe to act on
months later, when the author is not in the room.

## What was trimmed from the Linear version

The appendix (detailed data, code snippets, screenshots) and the three pre-stubbed finding blocks.
Pre-stubbing three findings tells the author to produce three, which is how a two-finding spike
grows a third. Attach the long material as files on the issue instead.
