# Spike Template

**Linear object:** Issue (with the `spike` label)
**Merged from:** this kit's version (Time Box, Scope, Success Criteria — the three things that stop
a spike running forever) plus the Linear workspace template "Spike Research Template" (Approach and
the Deliverable Type routing).

**No EARS, no Gherkin.** A spike answers a question; it does not specify behaviour. The
requirements come *after*, in whatever the Deliverable Type routes to.

## MCP Steps

```
save_issue:
  title: "Spike: [question to answer]"
  team: "team-name"
  labels: ["spike"]
  estimate: <the time box, in your team's unit>
```

## Template

```markdown
## Question

[The single question this spike answers. One question. A spike with three questions is three
spikes, or one that finishes none of them.]

## Time Box

[e.g. 2 days. Hard stop. When it expires, write up what you know and what you do not.]

## Context

- **Why now:** [what is blocked, or what decision is waiting on this]
- **Supports:** [the initiative, project or issue this unblocks]
- **Related issues:** LIN-XXX

## Approach

> How will we investigate? Methods, tools, experiments, data sources.

- [Review the API documentation and its rate limits]
- [Build a small harness to simulate real traffic]
- [Benchmark response times and error rates]

## Scope

### Investigate

- [What is in]

### Out of Scope

- [What is deliberately not investigated]
- No production code — spike output is disposable

## Deliverable Type

> Tick one. This is what the spike routes to when it ends, and it decides who reviews the outcome.

- [ ] **ADR** — the answer is a clear technical decision → `references/adr-template.md`
- [ ] **RFC** — the answer is a proposed solution that needs review → `references/rfc-template.md`
- [ ] **Research Note** — learnings without a final decision → `references/spike-research-template.md`
- [ ] **POC Report** — a prototype feasibility result, no standing document needed

## Success Criteria

- [ ] The question is answered with evidence, not opinion
- [ ] The deliverable above exists and is linked
- [ ] Next step is named: build / do not build / need more information

## Findings

> Fill in when the spike ends, inside the time box.

### Summary

[What we now know]

### Evidence

[Numbers, benchmarks, test output, screenshots. Evidence, not impressions.]

### Recommendation

[Build / Do not build / Needs further investigation — and why]

### Next Steps

- [What happens now, with an owner]

## References

- [Code, prototypes, vendor docs, benchmarks — resolvable links, never local paths]
```

## Why Deliverable Type is ticked at the start, not the end

A spike that does not know what it is producing produces a Slack message. Ticking the box up front
tells the reader which review the outcome needs and stops the finding evaporating into a thread
nobody can find in three months.

## Why the time box is a hard stop

The value of a spike is the decision it unblocks, and a decision late is a decision made without
it. When the box expires, write up what you know and name what you do not. An honest gap is worth
more than a week more of investigation nobody scheduled.
