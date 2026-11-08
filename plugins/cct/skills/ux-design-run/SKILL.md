---
name: ux-design-run
description: "Coordinates the design of one change before it is built: UX brief with job stories, information architecture, state table per screen, screen specs, rule conformance, a validation loop and a prototype of high-resolution images, written to one spec folder. Delegates verdicts to cct:ux-rules-validate, cct:ux-spec-validate and cct:ux-assessment-run, and sitemap work to cct:ux-sitemap-create. Use when the user says 'design this change', 'spec this screen', 'run the interaction design for this change', 'write the spec folder'. Skip for: the whole product process from setup to decisions, which belongs to cct:ux-run."
user_invocable: true
allowed-tools: "Bash(python3 */review/scripts/*)"
metadata:
  version: 1.0.0
  author: calvindudek
---

# cct:ux-design-run

**Arguments:** `<change-id | change-folder | spec-folder>`

Design one change in this order: brief, IA, interaction, screens, conformance, a validation loop,
then the prototype. Write only inside the spec folder. The prototype is generated images, never
code.

Shared files are in `references/`, two levels up from this skill's base directory.

## Prerequisites

| Need | For | Without it |
|---|---|---|
| `docs/ux/setup.md` | every activity | stop and run `cct:ux-setup` |
| Codex CLI with `image_generation` on (`codex features list`) | the prototype only | skip the prototype with `skip -- no image generator`; say so once |
| Python 3.10+ and an image-reading tool | Check the prototype images | Report BLOCKED for the image check |

## Read first

1. Read `docs/ux/setup.md`. Missing: stop and run `cct:ux-setup`.
2. Resolve the spec folder and the mode with the shared `references/spec-folder.md`.
3. **sdlc mode:** read `decisions.json` (`size`, `skips`, `design`) and the change's `intent.md`
   `## Asks`. **Standalone mode:** read `decisions.json` and `intent.md` when they exist, for the
   ticket and the problem only.
4. Read the design file named by `decisions.json` `design`, when present.
5. Read the setup paths for the guidelines, screen goals, components, owner words and feedback.

## Ask once

Ask the user only what the repo, the asks and the guidelines cannot answer, in one batch. In
standalone mode the size question (`spec-folder.md` section 3) is part of that batch. Each
question names the blocker and a recommended answer. Never ask the user to invent missing asks.

## Activities, in order

Before each activity, read its skip (`spec-folder.md` section 2). A skipped activity writes no
file; its reason is already recorded.

1. **Brief.** In standalone mode, first collect the asks (`spec-folder.md` section 4). Then use
   `references/brief.md`. Write `<spec>/brief.md`.
2. **Information architecture.** Use `references/ia.md`. Write `<spec>/ia.md`.
3. **Interaction.** Use `references/interaction.md`. Write `<spec>/interaction.md`.
4. **Screens.** Use `references/screens.md`. Write `<spec>/screens.md`.
5. **Conformance.** Run `cct:ux-rules-validate spec <spec>`. It writes `<spec>/conformance.md`.
6. **Validate the spec, as a loop.** Run `cct:ux-spec-validate spec <spec>` as a `/goal` loop:
   review, fix the spec, re-check, until `<spec>/validation.md` says `verdict: ready`. The loop
   is in `../ux-spec-validate/references/spec.md`.
7. **Prototype, only from a validated spec.** Start only when `<spec>/validation.md` says
   `verdict: ready`, or validation is skipped. Use `references/prototype.md`. Write
   `<spec>/prototype/index.md` and the images under `<spec>/prototype/`. Run the shared
   `references/visual-pass.md` on every image, including its `visual-check.py` command, before
   reporting the image loop complete. A failed check means the review did not run.
8. **Gate pass.** Standalone mode: run `cct:ux-spec-validate spec <spec>` once more; it checks the
   images against the validated spec (no full re-review) and hands `<spec>/validation.md` to the
   owner. sdlc mode: stop here; the SDLC writes `facts.md` and then runs the same gate pass.

Why this order: images drawn before validation get redrawn after every spec fix. On one product
(2026-10-07), validation after the images found 19 severity-3 issues and about 250 images were
redrawn.

## Stop points

- `docs/ux/setup.md` is missing.
- sdlc mode, and `intent.md` has no non-empty `## Asks`.
- Standalone mode, and no source holds an ask and the user gave none.
- A required setup value cannot be discovered and the user has not answered.
- Any write would land outside the spec folder.
- Never stop for a deliberate inconsistency: record it in conformance; validation puts it to the
  owner.

## Never

- Write facts, plans or product code, or edit `decisions.json` or `intent.md`.
- Invent an ask.
- Decide a deliberate inconsistency for the owner.
- Make low-fi wireframes, or use Figma.
