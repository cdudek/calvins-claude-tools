# Design inputs

Stage 1 asks which design the change follows and records the answer once, in
`decisions.json`, as `visualSource`: `{"kind": "export-bundle" | "canvas" | "figma" | "image",
"path": "<where it is stored, or the Figma file URL>"}`. A change with no interface leaves the
key out or writes `"none"`. This is the change's one **visual source of truth**. Every other
input (more images, annotated screenshots, generated mockups, today's app) is a reference.

## Kinds of input

| Input | Where it is stored | What is extracted | Which checks apply |
|---|---|---|---|
| Design export bundle (HTML or React from a code tool) | a folder under `asks/`, pinned by a hash, never edited, outside the app's code | one image per screen, structure (headings, text, tokens, element boxes), copy lines | all six layers |
| Design-tool canvas artifact | as an export bundle, after rendering it with its own runtime; when it cannot be rendered, ask for an export bundle | the same | all six layers |
| Figma file | the file link in `decisions.json`; read through the Figma tools: node tree, variables, a screenshot per frame | structure, tokens from variables, element boxes | all six layers; map the variables to design-system tokens once |
| Image only (a Figma picture, a screenshot of a design, a mockup) | `asks/`, as supplied | text positions by text recognition, colours by sampling | structure, copy and geometry within the tolerances; tokens only against the design system |
| Annotated screenshot | `asks/`, copied whole as today | each note becomes an ask | each ask lands in a fact; the picture shows intent and is not a pixel target |
| Generated mockup | `spec/prototype/` | nothing | the spec wins; a mockup is never a gate |

## Export bundles and `marks.py`

`marks.py init` lists a bundle (any folder under `asks/` with an `index.html`) as one input, kind
`bundle`, with the hash of all its files. A changed hash fails `marks.py check` as a changed
source: the bundle is pinned, so edit the app, never the bundle. The bundle's own images are not
listed as references.

A bundle is not an image, so it shows as "needs rendering" and fails the check until it has been
rendered. Render every screen to images with
`bash plugins/cct/skills/design-mockups-create/scripts/render.sh <folder>` (a folder of copied
HTML; React exports run through their own dev server or build first), put the images in a folder
under `asks/` such as `asks/<bundle>-render/`, and set the bundle row's `rendered` to that
folder. The images then become reference rows and are compared like any other reference image.

## What wins when inputs disagree

1. The owner's written words and decisions.
2. The declared visual source of truth.
3. The spec.
4. The design system.
5. Images.

A built screen that differs from the source of truth for a good reason (security, data loss, a
value the design lacks) is a ruled deviation: the row says why, in words. A difference without
a reason is a defect.

## Challenge, do not just follow

The source of truth is not beyond question. Raise a design decision when it goes against a
feature or decision the team already agreed on. Ask when something is unclear or contradicts
itself: two screens that disagree, a sentence describing behaviour the product does not have,
a state the design never shows.

Each challenge quotes both sides, says what it would mean for the user, and recommends one.
Outside a goal run, ask the owner. Inside a goal run, take the safer option, record it in
`questions.md` with the default taken, and list it for the owner's review at the end. The run
does not stop.

## Prototypes are not design inputs

The ban on HTML and Figma in the prototype rules covers prototypes the agent makes (generated
images only). It does not cover designs the team supplies: those are read as in the table above.
