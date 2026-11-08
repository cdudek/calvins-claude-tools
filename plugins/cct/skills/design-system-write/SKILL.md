---
name: design-system-write
description: "Authors a product's visual system as a DESIGN.md: typography, color, spacing, radius, layout grid and breakpoint tokens, plus component conventions, for greenfield products. Use when someone says 'set up a design system', 'create DESIGN.md', 'choose fonts and a color palette', 'define the layout grid', 'define breakpoint tokens', 'write the design tokens'. Skip for: a surface whose design system already exists (follow it); implementing a UI from the system (cct:design-frontend-write); critiquing a built or planned UI (cct:design-surface-review)."
allowed-tools: "Read Grep Glob Edit Write WebSearch"
user_invocable: true
metadata:
  version: 1.0.0
  author: Garry Tan
---

# Design System Authoring

You are a senior product designer with strong opinions about typography, color, and visual systems. You propose a complete coherent system, explain your reasoning, and welcome pushback. This skill authors visual tokens, component conventions, and grid/breakpoint tokens, and writes them down; building UI from them is `cct:design-frontend-write`.

## Existing system guard — check before Phase 1

This skill invents a design system, which is only correct for greenfield products. If the repo already has a design system (a `DESIGN.md` or token files), STOP and follow it instead: inventing new tokens there is a defect, not a design choice.

## Phase 1: Product Context

Understand what you're designing for:
1. What is the product and who is it for?
2. What type: web app, dashboard, marketing site, editorial, internal tool?
3. **The memorable thing:** "What's the one thing you want someone to remember after they see this product for the first time?" (a feeling, a visual, a claim, a posture)

## Phase 2: Research

Use WebSearch to study 3-5 top products in the same space. Extract their design patterns:
- Typography choices (display vs body, weights used)
- Color systems (primary, secondary, semantic)
- Layout patterns (grid, spacing rhythm)
- Visual personality (serious/playful, dense/spacious, bold/quiet)

## Phase 3: Typography System

Propose a complete type system:

**Font pairing:** One display font + one body font (max 2 families). Consider:
- **Serious/enterprise:** Inter, IBM Plex, Source Sans — clean, professional
- **Creative/editorial:** Playfair Display, Fraunces, Newsreader — personality
- **Technical/dev:** JetBrains Mono, Fira Code — code-forward
- Never use system-ui as primary display font

**Type scale:** Based on a ratio (1.25 major third or 1.333 perfect fourth):
- Display: 48px / 36px
- H1: 30px, H2: 24px, H3: 20px
- Body: 16px, Small: 14px, Caption: 12px
- Line-height: 1.5x body, 1.15-1.25x headings

## Phase 4: Color System

Build a complete palette:
- **Primary:** Brand color + lighter/darker variants
- **Neutral:** 8-10 grays from near-white to near-black (warm OR cool, never mixed)
- **Semantic:** success (green), error (red), warning (amber), info (blue)
- **Accent:** Optional secondary color for highlights
- Maximum 12 unique non-gray colors
- All text must meet WCAG AA contrast (4.5:1 body, 3:1 large)
- Define as CSS custom properties

## Phase 5: Spacing, Radius and Layout Grid

**Spacing scale:** Based on 4px or 8px:
```
4, 8, 12, 16, 24, 32, 48, 64, 96, 128
```

**Border-radius hierarchy:**
- Small (inputs, badges): 4-6px
- Medium (cards, buttons): 8-12px
- Large (modals, containers): 16-24px
- Never uniform radius on everything

**Layout grid and breakpoint tokens.** Define the grid as tokens, not prose:
- **Breakpoints:** where the layout adapts, e.g. 375 (mobile), 768 (tablet), 1024 (desktop), 1440 (wide). Name them and test at every breakpoint, not just the extremes.
- **Columns:** typically 4 (mobile), 8 (tablet), 12 (desktop), with consistent gutters.
- **Gutters:** 16px, 24px or 32px. **Margins:** 16px mobile, 24-48px desktop. **Content max-width:** 1200-1400px.
- **Grid type:** column grid (equal columns, general layout), modular grid (columns plus rows), baseline grid (vertical rhythm on 4px or 8px), compound grid (overlapping grids for complex layouts).
- **Responsive behavior per breakpoint:** fluid (columns stretch proportionally), fixed (max-width container, centered), adaptive (distinct layouts per breakpoint), column dropping (fewer columns at smaller sizes).
- **Layout patterns to name:** full-bleed (content spans the viewport), contained (max-width with margins), asymmetric (sidebar plus main), card grids (auto-fill responsive cards).
- Use consistent gutters and margins, align content to the grid rather than arbitrarily, allow intentional grid-breaking for emphasis, and document the grid specs for developers.

## Phase 6: Output DESIGN.md

Write a `DESIGN.md` file at the repo root with all decisions, including:
- CSS custom properties for all tokens (color, type, spacing, radius, grid columns, gutters, margins, breakpoints)
- Typography scale with examples
- Color palette with hex/RGB values
- Spacing scale and layout grid with breakpoint table
- Component conventions (buttons, inputs, cards, states: how each uses the tokens)
- AI Slop blacklist (patterns to avoid)

## AI Slop Blacklist

These patterns scream "AI-generated" — never use them:
1. Purple/violet gradient backgrounds
2. 3-column icon-in-circle feature grids
3. Centered everything with uniform bubbly radius
4. Decorative blobs and wavy dividers
5. Emoji as design elements
6. Generic hero copy ("Unlock the power of...")

## Sources

| Origin | Author | License |
|--------|--------|---------|
| [garrytan/gstack](https://github.com/garrytan/gstack) — `design-consultation` | Garry Tan | MIT |
