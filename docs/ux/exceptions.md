---
type: ux-exceptions
updated: 2026-11-13
---

# Exceptions register

Every deliberate exception to a UX rule, written once and cited by its id (`EX-<n>`). Format: the shared `conflicts.md`, section 2. R1 and R2 rules accept only "SC exception named", "scope finding" or "deferral".

### EX-1 Singular page ids in the tracker pane
- Overridden: RC-1, RC-2 (route conventions: a plural list plus an id)
- Decided by: owner decision (the sitemap's SM-10)
- Kind: owner exception
- Situation and screens: the pane's `repo/<repo>` and `session/<sessionId>` pages, and milestone 2's `#/repo/...` and `#/session/...` web routes; nowhere else
- Why: the ids match the object names, and no list page exists for a plural to name
- Compensating measure: one id form in the pane, the sitemap and the web page; Home is the list
- Decided: the owner, 2026-11-13, "Keep singular (Recommended)"
- Revisit when: a repos or sessions list page is added
