# Design inputs

Stage 1 asks which design the change follows and records the answer once, in
`decisions.json`, as `visualSource`: `{"kind": "export-bundle" | "canvas" | "figma" | "image",
"path": "<where it is stored, or the Figma file URL>"}`. A change with no interface leaves the
key out or writes `"none"`. This is the change's one **visual source of truth**. Every other
input (more images, annotated screenshots, generated mockups, today's app) is a reference.

## The six layers

Build QA checks a screen on six layers, and the table below says which apply to each input.

- **Structure:** the elements, their order and nesting.
- **Copy:** every word on the screen.
- **Tokens:** colours, type and spacing as design-system tokens, not raw values.
- **Geometry:** sizes and positions of the element boxes.
- **Rules and access:** the product's interaction rules, keyboard and accessibility.
- **Review:** the owner's notes and the reviewer's own findings, one verdict each.

The tolerances for each layer live in `cct:ux-build-validate`.

## Kinds of input

| Input | Where it is stored | What is extracted | Which checks apply |
|---|---|---|---|
| Design export bundle (HTML or React from a code tool) | a folder under `asks/`, pinned by a hash, never edited, outside the app's code | one image per screen, structure (headings, text, tokens, element boxes), copy lines | all six layers |
| Design-tool canvas artifact | as an export bundle, after rendering it with its own runtime; when it cannot be rendered, ask for an export bundle | the same | all six layers |
| Figma file | the file link in `decisions.json`; read through the Figma tools: node tree, variables, a screenshot per frame | structure, tokens from variables, element boxes | all six layers; map the variables to design-system tokens once |
| Image only (a Figma picture, a screenshot of a design, a mockup) | `asks/`, as supplied | text positions by text recognition, colours by sampling | structure, copy and geometry within the tolerances; tokens only against the design system |
| Annotated screenshot | `asks/`, copied whole as today | each note becomes an ask | each ask lands in a fact; the picture shows intent and is not a pixel target |
| Generated mockup | `spec/prototype/` | nothing | advisory only: the spec and the declared source win; a mockup is never a gate and never a `marks.py` row |

## Export bundles and `marks.py`

`marks.py init` lists a bundle as one input, kind `bundle`, with the hash of all its files. A
bundle is any folder under `asks/` with an `index.html`, or the folder `visualSource.path` names
(a React export has no `index.html`). A changed hash fails `marks.py check`: the bundle is
pinned, so edit the app, never the bundle. Its own images are not listed as references.
`verify_gate.py milestone` runs the marks check whenever a bundle exists, ledger or not.

A bundle is not an image, so it shows as "needs rendering" and fails the check until it has been
rendered. Rendering never touches the pinned folder:

1. Copy the bundle to a scratch folder outside `changes/`.
2. Run the renderer from the installed plugin, not a repo path:
   `bash "${CLAUDE_SKILL_DIR}/../design-mockups-create/scripts/render.sh" <copy>`. It writes
   `shots/` beside each HTML file; React exports run through their own dev server or build first.
3. Copy the images to a new folder under `asks/`, such as `asks/<bundle>-render/`, outside the
   bundle, and set the bundle row's `rendered` to it.

`marks.py check` fails a `rendered` folder that sits inside the bundle (or holds it) or that has
fewer images than the bundle has HTML screens, so missing screens show up in stage 2, before any
build or browser. The images become reference rows, and every one needs a checked row.

## What wins when inputs disagree

1. The owner's written words and decisions: the owner is accountable, and later words replace earlier ones.
2. The declared visual source of truth: the one design the owner chose to build against.
3. The spec: it turns the design into testable facts and states the design leaves out.
4. The design system: shared rules fill what the design and spec do not say.
5. Images: they show intent only; generated mockups are advisory and come last.

A built screen that differs from the source of truth for a good reason (security, data loss, a
value the design lacks) is a ruled deviation: the row says why, in words. A difference without
a reason is a defect.

## Question the design source

The source of truth is not beyond question. Raise a design decision when it goes against a
feature or decision the team already agreed on. Ask when something is unclear or contradicts
itself: two screens that disagree, a sentence describing behaviour the product does not have,
a state the design never shows.

Each question quotes both sides, says what it would mean for the user, and recommends one.
Outside a goal run, ask the owner. Inside a goal run, take the safer option, write it to
`questions.md` with the default taken, and list it for the owner's review at the end. The run
does not stop. This is separate from the stage 4 `challenge.md`, where a reviewer challenges
the tech plan; this rule challenges the design the owner supplied.

## Prototypes are not design inputs

The ban on HTML and Figma in the prototype rules covers prototypes the agent makes (generated
images only). It does not cover designs the team supplies: those are read as in the table above.
