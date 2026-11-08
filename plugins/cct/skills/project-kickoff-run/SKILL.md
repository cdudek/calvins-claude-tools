---
name: project-kickoff-run
user_invocable: true
description: Sets up a new product before any app code exists - the context repo (product, ICP, personas, jobs to be done, market, roadmap, glossary), the brand guide, the design system and DESIGN.md, the UX docs (interaction guidelines, information architecture and sitemap, owner's words) and the repos from the blueprint. Use when someone starts a new product, app, side project or startup, says "new project", "kickoff", "set up the brand", "we need a design system first", "write the PRODUCT.md", or wants to start building something that has no context yet.
---

# Project kickoff

A new product gets its words, its look and its rules written down before the first screen is built. Agents build far better when they can read who the product is for, what things are called, how the interface behaves and which tokens to use. Without that, every screen invents its own answers and the UX review later finds the same inconsistency forty times.

This skill writes the product, brand and UX documents. Wiring the repo's plugins, sdlc, Decision4 contract and gates is `cct:project-repository-run`; run it too.

Work through the five stages in order. Each ends with an owner gate: show the result, get a yes or corrections, then move on. Write every document in plain, short sentences. Date every decision and say what was chosen over what.

The finished example of every document is in `${CLAUDE_PLUGIN_ROOT}/examples/heydiff/`. Read the matching example before writing each one, and copy its shape, not its content.

## Stage 1: the context repo

Create a private repo `<product>-context` (no code). Its `CLAUDE.md` is the index every code repo imports. Example: `examples/heydiff/context/CLAUDE.md`.

| File | What it holds |
| --- | --- |
| `CLAUDE.md` | the repos and where each lives, what is where, the rules for decisions |
| `PRODUCT.md` | the promise in one line, the descriptor, the problem, who it is for, the job, what it is not, beliefs, pricing idea, how success is measured, platform(s) |
| `audience/audiences.md` | the ICP: primary audiences (designed, priced, marketed for), secondary ones (supported, not designed around), and who wins when they conflict |
| `audience/personas.md` | a few named personas per audience: role, goals, frustrations, current tools |
| `audience/jobs-to-be-done.md` | the job broken into steps, with how to measure each |
| `market/` | competitors, feature comparison, pricing research, positioning and marketing brief |
| `strategy/roadmap.md` | milestones, each one shippable on its own |
| `strategy/YYYY-MM-DD-<topic>.md` | one dated file per strategic decision (name, hosting, pricing, scope) |
| `glossary.md` | one name per thing, the words users see, words to avoid, German and English |

Interview the owner for what only they know (who it is for, why now, what it must never become). Research the rest. `cct:ux-jobs-write` structures the job, `cct:ux-brief-write` the problem, audience, constraints and success criteria.

Gate: the owner confirms PRODUCT.md, the audiences and the glossary.

## Stage 2: the brand guide

The brand guide is one numbered document. Rules first, examples after, research in an appendix. A lower page number wins over a higher one. Read `examples/heydiff/heydiff-brand-guide-selection.pdf` and `examples/heydiff/context/brand/v4/heydiff-brand-guide-v4/` for the full shape.

Sections, in this order:

- **Brand identity (for anyone who puts the name on something):** cover with the promise; positioning (who it is for, the job, what we believe, what it is not); logo; lockup, spacing and minimum sizes; logo use and misuse; how to write the name; artwork and gradients.
- **Brand expression:** colour palette and what each colour means; product colour (light and dark tokens, statuses); typography (typefaces, scale, rules); voice (how the product talks, with do and don't pairs); visual language (icons, illustration, screenshots); the system in use; templates (social, slides, email, docs).
- **Product foundations and components (for people who design and build):** layout (spacing, grid, breakpoints, layers); tokens (semantic tokens, motion, target sizes); components on the chosen library with the brand theme; component rules (buttons, toasts, the spec format); navigation; overlays and menus; forms; system feedback (loading, empty, error, offline); tables; files, search and structure.
- **Product-specific patterns:** one page per core object and flow of this product, plus one page per surface (web app, extension, desktop, phone) and the main journey in light and dark.
- **Examples and assets:** an example screen, the landing page, where the asset files are and who owns the guide.
- **Appendix (not rules):** the tests and explorations behind the choices.

Export it in forms both people and agents read: `brand-guide.md` (all pages as text), `implementation-brief.md` (what a coding agent needs to build the design system), `llms.txt` (an index for other agents), `decisions.md` (dated choices), `tokens/tokens.json` and `tokens/tokens.css`, `manifest.json`, and a PDF.

Use `cct:design-system-write` for the design-system decisions (library, palette, type, density), `cct:design-system-write` for the grid and breakpoints, `cct:ux-copy-write` for the voice page, and `cct:design-mockups-create` to generate high-resolution options of the key pages for the owner to pick from.

Gate: the owner picks the logo, palette, type and voice, and signs off the guide.

## Stage 3: the design system

1. Create `<product>-kit` from `blueprint/design-system-kit-heroui/`: packages for `tokens`, `ui` (wrappers on HeroUI v3 or MUI, themed with the tokens) and `contracts` (shared types), published to GitHub Packages, with Storybook in light and dark.
2. Build it from `implementation-brief.md`, token by token, component by component. Use `cct:design-system-write` for the system, and `cct:ux-states-design` for components with several states.
3. Write `DESIGN.md` in the kit (and point every app repo at it): the visual direction, the tokens and their meaning, the components and when to use each, motion, accessibility targets. Check it against the built kit with `cct:ux-accessibility-audit` and `cct:ux-responsive-audit`.

Gate: the owner reviews Storybook.

## Stage 4: the UX rules, in each code repo

Every repo that has screens gets `docs/ux/`. The ux skills read and write these files, so they live with the code. Examples: `examples/heydiff/web/docs/ux/` and `examples/snapmark/docs/ux/`.

- `setup.md`: product, audience, design rules, screens, how to run the app, what is read only. Written by `cct:ux-setup`.
- `owner-words.md`: the owner's own words about the product, quoted and dated.
- `sitemap.md` and `sitemap.json`: the information architecture, every page, how people reach it, Back, breadcrumbs, states. Planned from the job stories with `cct:ux-sitemap-create` before the routes exist.
- `interaction-guidelines.md`: how the whole app behaves (editing, saving, dialogs and panels, feedback, confirmation and undo, navigation, lists, keyboard), with examples and an enforcement map. `cct:ux-guidelines-write`.
- `glossary-proposal.md`: the UI vocabulary, aligned with the context repo's glossary.
- `states-contract.md`: loading, empty, error and offline for every screen.
- `decisions.md`: accepted UX decisions, from `cct:ux-decision-log`.

Gate: the owner accepts the sitemap and the interaction guidelines.

## Stage 5: the code repos

1. One repo per product surface: `<product>-web`, `<product>-desktop`, `<product>-chrome`, `<product>-mobile`, plus `<product>-terraform`. Pick the stack from `${CLAUDE_PLUGIN_ROOT}/docs/stack.md`.
2. Copy CI/CD from `${CLAUDE_PLUGIN_ROOT}/blueprint/` (read its README first; swap the GCP parts if the target cloud differs).
3. Each repo's `CLAUDE.md` imports the context repo's `CLAUDE.md` and names its `DESIGN.md` and `docs/ux/`.
4. Run `cct:sdlc-run adopt` in each repo, then start the first milestone with `cct:sdlc-run`.

From here on, every change goes through the SDLC: `cct:ux-design-run` before building a new screen, `cct:ux-assessment-run` and `cct:review-code-run` on every UI PR, `cct:ux-assessment-run` after each milestone.
