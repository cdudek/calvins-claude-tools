# Prototype

## Purpose

Make the spec visible before build: high-resolution GENERATED IMAGES of every screen and state
(Codex image generation), prompted with the design system and fed reference screenshots of the
product's own screens and the owner's UX shots, in one local gallery the owner opens.

**The tool is Codex's `image_generation`** (`codex features list` shows it on). When the
installed `cct:design-mockups-create` has a spec mode (its SKILL.md has a "Spec mode" section), run
`cct:design-mockups-create spec <spec>`, which follows these steps. Otherwise drive the Codex CLI
yourself with the steps below; `cct:design-mockups-create` in its HTML form is not a substitute.
Never build the prototype from code (no HTML, no product components), and never use Figma or
low-fi wireframes. No Codex: skip with `skip -- no image generator` and say so once.

## Inputs

- `<spec>/ia.md`, `<spec>/interaction.md` (state tables), `<spec>/screens.md`.
- The design system named in `docs/ux/setup.md` (tokens, type, components, colour meanings).
- Reference images: screenshots of the product's existing screens, and the owner's annotated
  screenshots under `<spec>/asks/` (standalone mode) or the change's `asks/` (sdlc mode).

## Steps

Driving Codex directly: one `codex exec` run per image, its prompt holding the design system in
words (tokens with hex and meaning, type scale, spacing, components), the screen's spec and the
state, with two to six reference images passed by `-i`. An edit passes the image it edits by `-i`
and says "change ONLY ...".

0. **Only from a validated spec.** `<spec>/validation.md` must say `verdict: ready` (the
   validation loop ran), or validation is skipped. Otherwise stop and run
   `cct:ux-spec-validate spec <spec>` first.
   A direction may be explored earlier (step 2), but no screen-by-state images.
1. Inventory every screen and state from the state tables (default, loading, empty, partial,
   error, disabled with reason, plus product-specific states).
2. No direction chosen yet: three directions on the most important screen; the owner picks.
3. **Anchor first.** For each screen, generate its main state once and check it yourself before
   anything else is drawn from it. Count every repeated element (cells, pads, rows, columns) on an
   enlarged crop; the eye misses 6 against 8 at full size.
4. **Every other state is an edit of its screen's anchor**, changing only what that state needs.
   A fresh redraw per state drifts (grid sizes, colours, header positions). A fix to one image is
   an edit of that image, never a redraw.
5. **Image check as a loop.** Follow the shared `visual-pass.md`: open each image with the
   image-reading tool, record every image (clean ones too), and validate each issue against
   the repo's conventions. Use `<spec>/visual/spec/<round>/` as the run and run `visual-check.py`
   before declaring the loop complete. Failure means the review did not run; report BLOCKED.
   Edit faulty images and open them again. After 3 rounds, list what is still wrong in `<spec>/prototype/known-image-faults.md`
   (the spec wins) and stop.
6. Treat a mock gap that is a SPEC gap as a finding: fix the spec, re-run the validation loop's
   re-check, then edit the affected images.

## Output Template

Write `<spec>/prototype/index.md`.

```markdown
# Prototype

## Form

Codex image generation; chosen direction: <name>

## How To Open

| Gallery | Command | Notes |
|---|---|---|

## Screen State Matrix

| Screen | State | 100 % | 150 % | Notes |
|---|---|---|---|---|

## Moves

| Control | To screen | Type |
|---|---|---|

## Gaps Found

| Gap | Spec file changed | Status |
|---|---|---|
```

## Checks

- No raw colour or pixel values appear outside tokens.
- No invented component appears outside conformance's missing list.
- Every IA move is in the Moves table, with the image it leads to.
- No screen-state cell is empty.
- 150 percent fits without clipping or overlap.
- Words match the glossary and `<spec>/screens.md`.
- No CSS art, fake SVG icons, generic rounded cards, low-fi wireframes, or Figma.

## Skip Rule

Skip when the `prototype` skip is set (the shared `spec-folder.md`, section 2).
The reason is already recorded; write no file.
For S size, put the delta screenshot in `<spec>/screens.md`.

## Optional Skills

Used only when installed; the activity runs fully without them.

- `cct:design-mockups-create`, when it has a spec mode.
- `cct:design-system-write`.
- `cct:ux-copy-write`.

Sources: github.com/openai/plugins · github.com/ratacat/claude-skills · github.com/nexu-io/open-design
