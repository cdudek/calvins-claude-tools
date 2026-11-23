# Design inputs

Stage 1 asks which design the change follows and records the answer once, in
`decisions.json`, as `visualSource`: `{"kind": "export-bundle" | "canvas" | "figma" | "image",
"path": "<where it is stored, or the Figma file URL>"}`. A change with no interface leaves the
key out or writes `"none"`. This is the change's one **visual source of truth**. Every other
input (more images, annotated screenshots, generated mockups, today's app) is a reference.

## The design is binding for what exists (changes approved from 3.26.0)

For a change locked with `"visual": "app"` the design binds **which screens and states exist and how
each is structured**. Nothing measures pixels against it: pixel detail is decided by the owner on the
real app's screenshots ([visual work](visual-work.md)), and a pinned design export, a `marks.py` row
and the six layers below stay retired. A canvas link, a Figma file, an export bundle, images or
annotated screenshots go to `asks/` for the UX plan to read. A change with no design input is
unchanged.

**The inventory.** When the change has a design input (`decisions.json` `visualSource`, or files in
`asks/design/`), the UX plan writes `changes/<id>/design.json` and lists **every** board or frame of
the source: it reads the canvas, the Figma file or the export it was given, never a sample.

```json
{"source": "<link or path>",
 "boards": [{"id": "<stable board id>", "name": "Leads, empty", "image": "asks/design/<id>.png"}],
 "dropped": [{"board": "<board id>", "reason": "replaced by the detail panel"}]}
```

`image` is optional (an exported picture of the board, stored in the change). A board id is a plain
name that stays the same when the board is renamed in the tool.

**The mapping.** A `screens.json` entry may carry `"design": ["<board id>", ...]`. Every board is
either named by at least one entry or listed in `dropped` with a reason; `verify_gate.py approve`
fails naming each unmapped board, each entry that names a board `design.json` does not list, and an
entry that names a board when there is no `design.json`.

**The owner confirms the inventory.** An agent could list only some of the boards, so at approval the
owner answers one dialog bound to a hash of the whole list (board ids, names, count, and the dropped
list with its reasons): `Change <id>, finding inventory-<hash>: these N boards are the whole design:
...` (options `Confirm inventory` | `Hold`), the same transcript-backed owner answer the findings
use (this confirms the board list, not any screenshot). One dialog covers both the board list and the dropped boards, so a dropped board is
the owner's decision, never the agent's. The lock records the inventory (`"design": "inventory"`,
`"inventory": <id>`) and the sha256 of every board image (`"designImages"`); `design.json` is locked
like `screens.json`, so editing it after approval voids the approval, and the close
refuse an image that changed or went missing, naming the board. Every hash behind these ids is made of
canonical JSON, so record boundaries bind.

**A design input makes it an app change.** The change has a design input when `visualSource` is set
or `asks/design/` holds at least one file (an empty folder counts for nothing; `ux: off` waives it).
Such a change needs `screens.json` and `design.json` whatever its size.

**Deviations are explicit.** A built screen that differs from its board (a section left out, another
layout, different content structure) says so in the entry's `"deviates": "<what differs and why>"`.
The build may add or change `deviates` after approval: it is the one field of an entry that does not
void the approval (the lock hashes `screens.json` without it, and the edit hook lets an edit through
that changes nothing else). It is not free, though: the comparison judges the screen against the board
plus the `deviates` text, which the report must quote, and a deviation added or changed after a screen
matched needs a new comparison before the baseline moves. The baseline is bound to the shot's sha256 only.

Changes approved before 3.26.0 keep their path: the lock says whether it holds an inventory
(`"design": "inventory"`). An in-flight 3.25 change gets its `design.json` at its next approval;
nothing forces it earlier.

The rest of this file, including the six layers, describes changes approved before 3.25.0.

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

## The design system is frozen at approval

Set `sdlc.json` `designSystem` to `{"package": "<npm name>", "consumers": ["package.json",
"apps/x/package.json"], "auditAbove": 20}`. `approve` reads the declared version and the version the
lockfile installed (`package-lock.json`, `pnpm-lock.yaml` or `yarn.lock`, beside the consumer or in a
parent folder) from each consumer and locks the package and all consumers in `lock.json`;
`verify_gate.py milestone` blocks when the package, a pin, an installed version or the list of
consumers has moved, naming the file. Re-approve with the new release, because every screen is
re-judged against it, or pin it back.

A change with more than `auditAbove` approved screens (notes, loose images and the pages of a bundle
all count) also needs `design-system-audit.md` before approval: a table of screen group,
design-system part, status `have` or `gap`; every row must say one of the two. Any `gap` means one
design-system release that closes them all comes first, so the design system does not move while
the screens are built.

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
