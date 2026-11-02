---
name: variants-create
description: "Generates multiple parallel UI/visual design variants for rapid side-by-side comparison and selection. Use when user says 'show me design variants', 'design alternatives', 'explore UI options', 'shotgun this', 'try a few directions', 'A/B/C this layout', or wants to see several visual directions for the same screen/component before committing. Skip for: generating multiple code refactor options or non-visual implementation alternatives. Skip for rendered, high-resolution directions drawn by Codex with a local comparison gallery — use cct:designs-explore."
allowed-tools: "Read Grep Glob Edit Write"
user_invocable: true
metadata:
  version: 1.0.0
  author: Garry Tan
---

# Visual Design Exploration

Generate multiple distinct design variants for rapid comparison. The goal is divergent thinking — explore meaningfully different approaches, not minor tweaks.

## Process

### 1. Understand the Brief

What are we designing variants for?
- A full page layout?
- A component (card, nav, form)?
- A color/typography direction?

Read DESIGN.md if it exists — variants should work within or deliberately push beyond the design system.

**OMR surface?** If the target is an OMR product or OMR-branded surface, invoke
`cct:design-system-apply` first and generate every variant within the OMR
token/component system — variants explore layout, density, hierarchy, and
composition, never off-brand fonts or colors. Build the variant HTML files via
that skill's **Prototype mode**, so they render fully OMR-styled without a
Tailwind build. For brand collateral (decks, social assets), calibrate against
`brand` (OMR AI Kit only, OMR's brand; not in cct) instead. The variant dimensions below apply fully
only to non-OMR/greenfield work.

### 2. Generate 3-5 Variants

Each variant must be **meaningfully different**, not just color swaps:

**Variant dimensions to explore:**
- **Layout:** grid vs single-column vs split-screen vs asymmetric
- **Typography:** serif vs sans-serif, condensed vs expanded, light vs heavy
- **Color mood:** warm vs cool, monochrome vs colorful, dark vs light
- **Density:** spacious/editorial vs dense/dashboard
- **Visual personality:** serious vs playful, minimal vs detailed, traditional vs modern

**Rules:**
- Each variant gets a name (e.g., "Clean Minimal", "Bold Editorial", "Dense Dashboard")
- Each variant has a 1-sentence design rationale
- No variant should use AI slop patterns (purple gradients, 3-column icon grids, etc.)
- At least one variant should be the "safe" choice, one the "bold" choice

### 3. Output Format

For each variant, produce:
- Self-contained HTML file that can be opened in a browser
- Named clearly: `variant-1-clean-minimal.html`, `variant-2-bold-editorial.html`
- Responsive (works at mobile and desktop widths)

### 4. Comparison

After generating all variants, present a comparison:

```
VARIANT COMPARISON

| # | Name | Personality | Best for | Risk |
|---|------|------------|----------|------|
| 1 | Clean Minimal | Professional, calm | Enterprise SaaS | Safe — may feel generic |
| 2 | Bold Editorial | Opinionated, distinctive | Content-driven | Could feel too editorial |
| 3 | Dense Dashboard | Efficient, data-rich | Power users | Intimidating for new users |

RECOMMENDATION: Variant [N] because [reason tied to the product's memorable thing]
```

### 5. Iterate

After the user picks a direction, refine that variant:
- Incorporate specific feedback
- Polish typography, spacing, color
- Add interaction states
- Test at all breakpoints

## Anti-Patterns

Never generate variants that are:
- Just color swaps of the same layout
- All centered with symmetric grids (that's one variant, not three)
- All using the same font pairing
- All following the same section rhythm

## Sources

| Origin | Author | License |
|--------|--------|---------|
| [garrytan/gstack](https://github.com/garrytan/gstack) — `design-shotgun` | Garry Tan | MIT |
