---
name: accessibility-audit
description: Audits web applications for WCAG 2.2 accessibility compliance (Level A and AA, with AAA listed). Does not cover EU Accessibility Act or EN 301 549 requirements beyond WCAG. Use when user says "accessibility audit", "WCAG", "a11y", "screen reader", "aria", "accessibility check", or asks about accessibility compliance.
allowed-tools: "Read Grep Glob Edit Write Bash(npx *)"
user_invocable: true
metadata:
  version: 1.0.0
  author: Addy Osmani
context: fork
model: sonnet
effort: high
background: false
---

# Accessibility (a11y)

Comprehensive accessibility guidelines based on WCAG 2.2 and Lighthouse accessibility audits. Goal: make content usable by everyone, including people with disabilities.

## Reference Files

- `references/wcag-guidelines.md` — Detailed code examples for all WCAG principles (Perceivable, Operable, Understandable, Robust) including WCAG 2.2 additions
- `references/A11Y-PATTERNS.md` — Reusable accessibility component patterns (modals, skip links, tabs, forms, notifications, dragging alternatives)
- `references/WCAG.md` — Full WCAG criteria reference table

Read `references/wcag-guidelines.md` when implementing fixes or auditing specific WCAG criteria. Read `references/A11Y-PATTERNS.md` when building accessible components.

## WCAG Principles: POUR

| Principle | Description | Key Areas |
|-----------|-------------|-----------|
| **P**erceivable | Content can be perceived through different senses | Alt text, contrast, captions, media alternatives |
| **O**perable | Interface can be operated by all users | Keyboard access, focus management, target size, timing, motion |
| **U**nderstandable | Content and interface are understandable | Language, navigation consistency, form labels, error handling, authentication |
| **R**obust | Content works with assistive technologies | Native elements over ARIA, live regions, correct roles/states |

## Conformance Levels

| Level | Requirement | Target |
|-------|-------------|--------|
| **A** | Minimum accessibility | Must pass |
| **AA** | Standard compliance | Should pass (legal requirement in many jurisdictions) |
| **AAA** | Enhanced accessibility | Nice to have |

## New in WCAG 2.2

These criteria were added in WCAG 2.2 — check `references/wcag-guidelines.md` for code examples:

- **Focus not obscured (2.4.11)** — focused elements must not be entirely hidden by sticky headers/overlays
- **Target size (2.5.8)** — interactive targets must be at least 24x24 CSS pixels (AA)
- **Dragging movements (2.5.7)** — dragging must have a single-pointer alternative
- **Consistent help (3.2.6)** — help mechanisms must appear in same relative order across pages
- **Redundant entry (3.3.7)** — don't force re-entry of previously provided information
- **Accessible authentication (3.3.8)** — login must not rely on cognitive function tests without alternatives

## Testing Checklist

### Automated testing
```bash
# Lighthouse accessibility audit
npx lighthouse https://example.com --only-categories=accessibility

# axe-core
npm install @axe-core/cli -g
axe https://example.com
```

### Manual testing

- [ ] **Keyboard navigation:** Tab through entire page, use Enter/Space to activate
- [ ] **Screen reader:** Test with VoiceOver (Mac), NVDA (Windows), or TalkBack (Android)
- [ ] **Text resize:** text resizes to 200% without loss of content or function (1.4.4); content reflows at 320 CSS px wide (1.4.10), tested at 320 × 640: the 256 px height of 1.4.10 is only for content that scrolls sideways (vertical writing), never combined with the width
- [ ] **High contrast:** Test with Windows High Contrast Mode
- [ ] **Reduced motion:** Test with `prefers-reduced-motion: reduce`
- [ ] **Focus order:** Logical and follows visual order
- [ ] **Target size:** targets at least 24x24 CSS px, or an undersized target whose 24 px circle intersects no other target (2.5.8)

See the [screen reader commands reference](references/A11Y-PATTERNS.md#screen-reader-commands) for VoiceOver and NVDA shortcuts.

## Common Issues by Impact

These levels are the `omr-ux` finding scale under other names: Critical is Critical, Serious is
High, Moderate is Medium, Minor is Low. Any Level A or AA failure is at least Serious, and
Critical when it blocks a task.

### Critical (blocks a task)
1. Keyboard traps (2.1.2)
2. Functionality not operable by keyboard (2.1.1)
3. Form fields or icon buttons with no accessible name (1.3.1, 3.3.2, 4.1.2)
4. No visible focus indicator (2.4.7)
5. Informative images the task depends on, without alt text (1.1.1)

### Serious (any other A or AA failure)
1. Insufficient color contrast (1.4.3, 1.4.11)
2. Missing page language (3.1.1)
3. Heading structure that does not match the content (1.3.1, 2.4.6)
4. Non-descriptive link text (2.4.4)
5. Auto-playing media without pause or stop (1.4.2, 2.2.2)
6. Inconsistent navigation (3.2.3)
7. Errors not identified in text (3.3.1)
8. Time limits without controls (2.2.1)
9. No way to bypass repeated blocks (2.4.1)

### Moderate (no criterion fails on its own)
1. Missing landmark regions, where headings still structure the page
2. Missing skip link, where landmarks and headings already bypass blocks (2.4.1 is met by technique ARIA11)

## References

- [WCAG 2.2 Quick Reference](https://www.w3.org/WAI/WCAG22/quickref/)
- [WAI-ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)
- [Deque axe Rules](https://dequeuniversity.com/rules/axe/)
- [WCAG criteria reference](references/WCAG.md)
- [Accessibility code patterns](references/A11Y-PATTERNS.md)

## Sources

| Origin | Author | License |
|--------|--------|---------|
| [addyosmani/web-quality-skills](https://github.com/addyosmani/web-quality-skills) — `skills/accessibility` | Addy Osmani | MIT |
