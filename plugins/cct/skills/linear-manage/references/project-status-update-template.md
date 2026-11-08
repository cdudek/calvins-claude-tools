# Project Status Update Template

**Linear object:** Status Update (on a Project)

## MCP Steps

```
save_status_update:
  project: "<project-name>"
  health: "onTrack"  # onTrack | atRisk | offTrack
  icon: ":bar_chart:"
```

Then update with content.

## Template

```markdown
## Summary
One paragraph: what happened this period and where we stand.

## Progress
- [x] Completed item 1
- [x] Completed item 2
- [ ] In progress: item 3 (expected by YYYY-MM-DD)

## Key Metrics
| Metric | Last Period | This Period | Target |
|--------|-----------|-------------|--------|
|        |           |             |        |

## Risks & Blockers
| Risk/Blocker | Impact | Status | Owner |
|-------------|--------|--------|-------|
|             |        |        |       |

## Next Period
- Priority 1
- Priority 2
- Priority 3

## Decisions Needed
- [ ] Decision 1 — context and options
```

## Health Status Guide

| Health | When to use |
|--------|------------|
| `onTrack` | Milestones on schedule, no blockers |
| `atRisk` | Potential delays, blockers identified but mitigation in progress |
| `offTrack` | Missed milestones, unresolved blockers, needs escalation |
