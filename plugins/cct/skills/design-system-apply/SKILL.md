---
name: design-system-apply
description: >-
  Loads the OMR design system and enforces its tokens for ANY user-facing UI in an OMR frontend
  (omr-js, reviews-frontend, vuehaus, eventmanager, festival-companion). Use when building or
  editing a Vue component, page, layout or Tailwind markup, when styling or theming, when
  replacing hardcoded colors, spacing or typography with semantic tokens, when implementing a
  Figma handoff, or when choosing a token — even if nobody says "design system". Also for
  prototypes and mockups of OMR product surfaces. Skip for designed collateral outside the
  product: decks, slides, social posts, ads, whitepapers, print, charts, videos and image- or
  video-generator prompts use `brand` (OMR AI Kit only, OMR's brand; not in cct) instead.
allowed-tools: "Read Grep Glob Bash(git *) WebFetch"
user_invocable: true
metadata:
  version: 1.0.0
  author: OMR
---

# Use the OMR Design System

You are generating or editing UI for an OMR Tailwind/`omr-js` consumer. The
authoritative design system lives in the **`omr-design-system`** repo. This skill loads
it on demand. The full contract is that repo's `CLAUDE.md`; the foundations/concepts are
its `foundations/` and `concepts/` directories.

## Hard rules (always apply — blocking errors)

These mirror `omr-design-system/AGENTS.md`. They hold even if the repo can't be located.
If they ever change there, update them here too.

1. **Tailwind utilities only** for design tokens — never raw CSS values, hex codes, or `style="..."`.
2. **Semantic color tokens only** — `bg-surface`, `text-primary`, `border-error`. Never primitives like `bg-purple-700` / `text-grey-500`.
3. **Typography** — `txt-{category}-{size}-{weight}` utilities only. Never raw `font-size` / `font-weight` / `letter-spacing`.
4. **Spacing** — Tailwind utilities only (`p-4`, `gap-6`, `m-2`). Never raw `px`.
5. **Z-index** — `z-{below,base,raised,dropdown,sticky,overlay,modal,toast}`. Never raw numbers.
6. **Border radius** — Tailwind utilities only. Default surfaces to `rounded-2xl` (16px home base); `rounded-full` only for genuinely circular elements. Never bare `rounded` (use `rounded-sm`) or arbitrary `rounded-[16px]`.
7. **Transitions** — `var(--transition-*)` shorthands or `var(--duration-*)` / `var(--easing-*)`. Never hardcoded `200ms ease-out`.
8. **Generated files** — never edit `*.generated.css`. Token changes go through the pipeline (`variables.json` → `pnpm extract`), never by hand.
9. **Accessibility** — interactive elements have an accessible name; form controls use native `required` / `aria-required` and are labelled; contrast meets WCAG 2.2 AA; touch targets meet the minimum size. axe-clean, no dangling `aria-*` idrefs.

## Locate the design system (do this before deep token decisions)

1. **Find an existing checkout — match on the git remote, not the folder name.** A clone
   can be named anything (`DesignSystemDocumentation`, `design-system`, …), and a
   name-only check silently misses it, which drops you into the fallbacks below or onto a
   consumer repo's own stale `CLAUDE.md`. Search the current directory, its parent, and
   their immediate children, plus any path you remembered in a previous session:

   ```bash
   for d in . .. ./* ../*; do
     [ -d "$d/.git" ] && git -C "$d" remote -v 2>/dev/null \
       | grep -q 'omr-design-system' && echo "$d"
   done
   ```

   A folder literally named `omr-design-system/` is the obvious candidate — still confirm
   it by remote, and don't stop searching when it's absent. **If more than one checkout
   matches, they are clones of the same repo at different ages:** take the one whose HEAD
   is newest (`git -C <path> log -1 --format=%ci`) and tell the user the others exist, so
   the duplicates get cleaned up instead of misleading the next session.
2. **If absent**, either:
   - offer to clone it once: `git clone git@github.com:ramp106/omr-design-system.git`
     (as a sibling of the repo you're working in), **or**
   - ask the user to point you to an existing local path.
   Once resolved, **remember the path** (write a `reference` memory) so future sessions
   skip this step.
3. **Read-only fallback** (no local checkout, network available): fetch specific files
   with WebFetch from
   `https://raw.githubusercontent.com/ramp106/omr-design-system/main/<path>`.

**Freshness check (critical).** Once you've found a local checkout, verify it's current
before trusting it — a stale checkout silently breaks everything downstream: the routing
entries and the inventory below point at files that may not exist on an out-of-date branch.
Run `git -C <path> fetch --quiet` and check it isn't behind (`git -C <path> status -sb`); if
it is, `git pull`. **Check which branch you're on before trusting `git pull`** — a checkout
parked on a feature branch, or on a branch that was abandoned when the trunk moved, pulls
its own stale ref and reports itself up to date. Compare against the repo's *default*
branch, which is not always `main`:
`git -C <path> symbolic-ref refs/remotes/origin/HEAD` (or `gh repo view --json
defaultBranchRef`). Then confirm that `components/README.md` (the component inventory) and the
specific foundation/concept files you're about to read actually exist. If
`components/README.md` is missing, your checkout predates the components layer — update the
branch before relying on the inventory. **Never "repair" a routing reference by deleting it;
the cause is almost always a stale checkout, not a wrong reference.**

## Routing table (read only what the task needs)

| Your task | Read |
|---|---|
| Building/choosing/reusing a component (buttons, badges, inputs, icons, banners…) | `components/README.md` (the component inventory — **check first, reuse before rebuild**), then the `@ramp106/omrjs-*` packages — see *Prefer existing components* below |
| Which package/repo holds a component; where a new shared one belongs | `components/README.md` § *Where components live* — three tiers, search order |
| An existing component contradicts a foundation rule | `components/README.md` § *When a component contradicts a foundation* |
| Color / text / bg / border choice | `foundations/color.md` |
| Typography | `foundations/typography.md` |
| Spacing / layout / gaps / page gutters | `foundations/spacing.md` + `concepts/component-padding.md` |
| Sizing / max-width / icon sizes | `foundations/sizing.md` |
| Border radius | `foundations/radius.md` |
| Breakpoints / responsive | `foundations/breakpoints.md` |
| Building a page or section (brand emphasis) | `concepts/visual-hierarchy.md` |
| Hover / press / focus feedback | `concepts/interactive-states.md` |
| Light / dark theming | `concepts/dark-theme.md` |
| New or changed token (admission rules) | `concepts/token-governance.md` |
| UX writing / labels / value formats | `foundations/writing.md` |

The repo's `README.md` is the authoritative index — consult it if your task isn't above.

## Prefer existing components over hand-built markup

The design system ships **components**, not just tokens. Before hand-assembling markup
from raw token utilities:

1. **Check the component inventory first** — `components/README.md` in the
   `omr-design-system` repo. It's the curated map of the most-used components (IconButton,
   ChipBadge as Tag/Badge, FieldWrapper, MessageBanner) and semantic Tailwind class sets
   (icon sizing, Semantic Buttons, Link Buttons), each with when-to-use / when-not-to-use
   and a Storybook link. **Reuse before rebuild.**
2. **If it's not in the inventory**, follow the **search order** in that file's *Where
   components live* section. Components sit in three tiers, and the tier boundaries do not
   match the repo boundaries — every shared package lives in `omr-js`, including the
   surface-specific `reviews-ui` and `events-ui`. Pointing yourself at `reviews-frontend`
   or `eventmanager` will **not** surface them; those repos hold only app-local
   components. Grep `src/components/` in each package when unsure what exists.
3. **Only drop to raw semantic-token markup** when nothing existing fits.

If a component you found contradicts a foundation rule, **reuse it anyway and report the
deviation** — see *When a component contradicts a foundation* in `components/README.md`.
Don't override the component's styling, and don't rebuild it to sidestep the conflict.

This keeps UI consistent and matches the system's intent (new shared components are
proposed in `omr-js` first, not duplicated per app).

## Prototype mode (explicit, gated)

Production output is Vue/Tailwind code whose semantic classes only render inside an OMR
frontend's compiled Tailwind build. When the deliverable is a **standalone preview** —
the user asks for a prototype, mockup, or shareable HTML, or `variants-create` targets
an OMR surface — switch to prototype mode and emit **self-contained `.html` files** that
render fully styled in any browser, with no build step, dev server, or CLI required.

**Gate:** prototype mode is opt-in only. Enter it when the request explicitly calls for
a standalone/preview artifact; announce "prototype mode" in your output. Never use it
for code that ships — anything destined for a product repo goes through the normal mode
and the hard rules above, which stay blocking errors there.

**How to build the file:**

1. **Inline the OMR token CSS.** Concatenate, in this order, into one `<style>` block:
   `fonts.css`, `primitives.css`, `colors.css`, `typography.css`, `layout.css`,
   `utilities.css`, `base.css` from this skill's own copy at
   `${CLAUDE_SKILL_DIR}/references/tokens/`. It is a byte-identical mirror of the brand
   skill's `tokens/` (canonical in `brand` (OMR AI Kit only, OMR's brand; not in cct)), kept here because a plugin cannot
   read another plugin's files at runtime; CI fails if the two diverge. When inlining
   `fonts.css`, drop the relative `../fonts/…` `src` line and keep only the
   `https://static.omr.com/…` source — relative paths don't resolve from an inlined block.
2. **Write markup with the real semantic class names** the bundle ships: `bg-surface`,
   `text-main`, `border-error`, `txt-{category}-{size}-{weight}`, `rounded-*`,
   `state-layer*`, `omr-focus-visible-*`. These are the production class names, so a
   chosen prototype ports to a frontend as markup 1:1 — only the styling delivery
   changes.
3. **Fill the gaps from the foundations' `tokens:` frontmatter.** Spacing, breakpoints,
   and z-index utilities are not in the bundle (they're Tailwind-compiled). For those,
   write plain CSS in a clearly-marked prototype-local `<style>` section, deriving every
   value from the omr-design-system foundations tables — spacing on the 4px grid
   (`foundations/spacing.md`), breakpoints from `foundations/breakpoints.md` — never
   eyeballed values.
4. **Dark theme** is opt-in: set `data-theme="light"` on `<html>` and, when the preview
   should switch, also inline `references/tokens/colors-dark.css` after `colors.css`; it
   keys its values off `[data-theme="dark"]`. A live toggle is a three-line inline script
   that flips that attribute — no external file.

The raw-hex / `style="..."` ban still applies inside prototypes — every color, font, and
radius comes from the inlined token classes/vars, and gap-filling CSS cites the scale it
derives from. Prototype mode changes the packaging, not the token discipline. Rendering
or screenshotting the result is not this skill's job — developers can verify with
`cct:browser-automate` when that plugin is installed.

## Component code-style

This skill governs **design tokens**, not Vue structure. SFC block order (`<template>`
first), component/prop naming, props/emits typing, and imports follow the consumer repo's
`code-style` docs and the `vue-code-write` skill — honor those.

## Decision protocol, anti-patterns, output format

Defer to `omr-design-system/CLAUDE.md` — do not duplicate here. In short: look up the
rule, apply it; if ambiguous or uncovered, **ask the user** and surface the doc gap.

## Figma (conditional, optional)

OMR is moving away from Figma. **Only** if the ticket/task references a Figma design
**and** the Figma MCP is available, use it for live design context. If there's no Figma
reference, skip this entirely — it is never a default step.
