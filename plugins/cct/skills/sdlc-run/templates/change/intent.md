---
linear: {{LINEAR}}
type: intent
change: {{CHANGE}}
design: {{DESIGN}}
author: {{AUTHOR}}
class: null
status: draft
reviewed_by: null
approved_at: null
created: {{DATE}}
---

# Intent: {{TITLE}}

> One sentence. What we want, and for whom.

## Asks

Every request that this change answers, in the asker's own words. Never paraphrased.

| # | Date | Source | Words | Screen | Resources |
|---|---|---|---|---|---|
| A1 | {{DATE}} | owner, chat | "<exact words>" | <screen or "none"> | [resource](asks/{{DATE}}/<file>) or none |

## Job stories

Drafted by the agent from the asks; the engineer confirms them. Label every story with its
evidence: **observed** (seen in data or a session), **reported** (someone said it), or
**assumed** (nobody has seen it yet).

| # | When … | I want to … | So I can … | Evidence |
|---|---|---|---|---|
| J1 | <situation> | <motivation> | <outcome> | reported — A1 |

## Success measure

How we know after release that it worked. One number, where it is read, and the target.

- **Measure:** <event or metric> — **read in:** <PostHog insight, query> — **target:** <number by date>

## Problem

- **What is wrong or missing:** <one sentence>
- **Who feels it:** <the user, the team, or the system>
- **Evidence:** <a number, a ticket, a log line, or a quote>

## Proposed outcome

What is true when this is done. Write it in the user's words. Do not say how.

- <outcome 1>
- <outcome 2>

## Affected users and systems

| Kind | Name | How |
|------|------|-----|
| users | <role or segment> | <what changes for them> |
| service | `<service>` | <what changes> |
| data | `<table or field>` | <what changes> |

## Constraints

- **Must not change:** <what stays as it is>
- **Deadline:** <date, or "none">
- **Rules that apply:** <rule IDs or names from the files in `sdlc.json` `rules`, one per line>
- **Class:** <Undo | Repair | Migrate | Answer> — <if this is wrong, what does it take to put right? Unsure: the higher>

## Open questions

Only questions the originator must answer. Everything else is inferred.

1. <question>
