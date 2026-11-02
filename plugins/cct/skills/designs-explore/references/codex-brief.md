# The brief handed to Codex, one per direction

Read this when assembling the `codex exec` prompt. One Codex run produces **one** direction, so
three directions are three runs. Never ask a single run for all three: a model that writes three
designs in one pass converges them, and converged directions are the failure this skill exists to
prevent.

## The call

```bash
codex exec \
  -c model="gpt-5.5" \
  -c model_reasoning_effort="high" \
  --sandbox workspace-write \
  --skip-git-repo-check \
  --cd "<RUN>/<NN>-<slug>" \
  --output-last-message "<RUN>/<NN>-<slug>/codex-summary.txt" \
  "$(cat <RUN>/<NN>-<slug>/prompt.txt)"
```

Write the prompt to `prompt.txt` first and pass it with `$(cat …)` or on stdin. A prompt this long
inline is unreadable in the transcript and quoting breaks on the first backtick.

`--sandbox workspace-write` is the point: Codex writes the HTML itself. `--cd` keeps it inside its
own direction folder so three parallel runs cannot overwrite each other.

**Run the three in parallel** — three background shells, then wait. They share nothing.

## The prompt, assembled from these blocks

### 1. Role and the one output

> You are a senior product designer. Produce ONE design direction as GENERATED IMAGES, made with
> your image generation tool, and nothing else.
>
> First read the design documents this prompt names (the repo's DESIGN.md, INTERACTION.md and the
> pages it routes to, PRODUCT.md, the design-system repository) and look at every attached
> reference image: they are the product's own screens and the owner's annotated screenshots.
>
> Write exactly these files in the current directory:
> - `shots/<screen>--<state>.png` — one generated image per screen and state (flow mode: one per
>   step, `shots/01-<step-slug>.png`, …), landscape, 1536 x 1024 or larger, a desktop window.
> - `notes.md` — first line `# <Direction name>`, then one paragraph on the idea, then a short
>   list of what you deliberately did NOT do.
>
> Do not write HTML, code, a build or a README.

### 2. The hard constraints

> - Only the design system's colours, type, spacing, radii and components. Colours carry their
>   meanings; a colour the system does not have is a failure.
> - It must look like the attached product screens: same chrome (rail, header, footer), same
>   density, same controls. A screen that looks like another product is rejected.
> - The exact words from the spec. Real content, never lorem ipsum.
> - Ship the states that matter: empty, loading and error, where the screen has them.
> - Legible: text sharp and readable at full size; nothing cut off.

### 3. The direction

Paste the chosen row from `directions.md` verbatim, then:

> This is your direction. Commit to it. Do not hedge toward the middle, and do not try to also
> cover what the other directions are doing — you are one of three, and the reviewer needs them
> to be genuinely different.

### 4. The design system, for OMR surfaces

When the brief says the surface is an OMR product, paste the token rules the skill collected from
`cct:design-system-apply`, then:

> These tokens are binding. Explore layout, density, hierarchy, rhythm and composition. Never
> invent a colour, a font or a spacing value that is not in this list. A direction that breaks the
> token system is rejected before it is looked at.

For an OMR-branded surface that is not a product, use `brand` (OMR AI Kit only, OMR's brand; not in cct) instead and say so.
For non-OMR work, drop this block entirely — then typography and colour are fair game as axes.

### 5. The brief itself

Paste `brief.md` verbatim: what is being designed, for whom, the job the screen does, the
constraints the user named.

## Checking what came back

Before the gallery, confirm per direction:

| Check | Why |
|---|---|
| every `shots/*.png` named in the prompt exists | Codex sometimes answers in prose instead of generating |
| `notes.md` starts with `# ` | the gallery takes the direction name from it |
| you looked at each image | tokens, components, words, nothing cut off — re-generate the one that fails |

A direction that fails a check gets one re-run with the failure named. Two failures and it is
reported as failed rather than quietly dropped: three directions minus one silently is a worse
review than three minus one stated.
