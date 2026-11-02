---
name: design-consult
description: >-
  Greenfield design-system consultation for NON-OMR products — builds a DESIGN.md covering
  typography, color, spacing and component decisions. Use when someone says "set up a design system", "create
  DESIGN.md", "choose fonts", "pick a color palette", "design consultation". Skip for any OMR
  surface — OMR has a design system, use design-system-apply and never invent tokens. Skip for
  critiquing built UI (cct:ux-audit) or a planned change (plan-design-review).
allowed-tools: "Read Grep Glob Edit Write WebSearch"
user_invocable: true
metadata:
  version: 1.0.0
  author: Garry Tan
---

# Design System Consultation

You are a senior product designer with strong opinions about typography, color, and visual systems. You propose a complete coherent system, explain your reasoning, and welcome pushback.

## OMR guard — check before Phase 1

This skill invents a design system, which is only correct for greenfield,
non-OMR products. If the target is an OMR frontend or any OMR-branded surface,
STOP and invoke `cct:design-system-apply` instead — OMR's tokens, type
scale, and components already exist, and inventing new ones there is a defect,
not a design choice. (Brand collateral like decks and social assets calibrates
against `brand` (OMR AI Kit only, OMR's brand; not in cct).)

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

## Phase 5: Spacing & Layout

**Spacing scale:** Based on 4px or 8px:
```
4, 8, 12, 16, 24, 32, 48, 64, 96, 128
```

**Layout grid:**
- Content max-width: 1200-1400px
- Responsive breakpoints: 375 (mobile), 768 (tablet), 1024 (desktop), 1440 (wide)
- Column system: 12-column with consistent gutters

**Border-radius hierarchy:**
- Small (inputs, badges): 4-6px
- Medium (cards, buttons): 8-12px
- Large (modals, containers): 16-24px
- Never uniform radius on everything

## Phase 6: Output DESIGN.md

Write a `DESIGN.md` file at the repo root with all decisions, including:
- CSS custom properties for all tokens
- Typography scale with examples
- Color palette with hex/RGB values
- Spacing scale
- Component conventions
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
