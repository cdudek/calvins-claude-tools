# The spec folder: where a design lives, and which mode it runs in

Read by `cct:ux-design-run`, `cct:ux-spec-validate`, `cct:ux-rules-validate spec` and `cct:ux-assessment-run`. Every
path below written `<spec>/...` is relative to the spec folder this file resolves.

## 1. Find the spec folder

The argument is a change id, a change folder, or a spec folder.

1. **A change folder exists** (the argument names one, or the current branch's change folder
   under `changes/`, or the `changesDir` in `sdlc.json`): `<spec>` is `<change folder>/spec/`.
2. **No change folder:** `<spec>` is `docs/ux/specs/<YYYY-MM-DD>-<slug>/`, dated the day it is
   created and never renamed, unless `setup.md` names another place under "Specs without a
   change folder". Say the path to the user in one line before writing anything.

`<id>` in a frontmatter `change:` field is the change folder's name, or the spec folder's name
when there is no change folder.

## 2. Two modes

| | sdlc mode | standalone mode |
|---|---|---|
| **When** | the change folder's `decisions.json` has a `size` key (an SDLC whose change folders carry a design size and skips) | anything else: a change folder whose `decisions.json` has no `size` (the kit's `cct:sdlc-run` writes none), or no change folder at all |
| **Size and skips** | `decisions.json` `size` and `skips` | `cct:ux-design-run` asks the size once (section 3) and writes `size` and `skips` into the frontmatter of `<spec>/brief.md` |
| **Asks** | the `## Asks` table (`A1`, `A2` ...) in the change's `intent.md` | `cct:ux-design-run` collects them (section 4) into the `## Owner Asks` table of `<spec>/brief.md` |
| **Asks to facts** | `facts.md` cites asks as `(A1, A3)` | `facts.md` when it cites asks; otherwise the brief's `## Ask Map` is the trace |
| **Never writes** | `decisions.json`, `intent.md`, `facts.md`, `plan.md` | anything outside `<spec>` |

Reading a skip means: `skips.<activity>` from `decisions.json` in sdlc mode, from the brief's
frontmatter in standalone mode. A skip value always reads `skip -- <reason>`.

The activity ids are `brief`, `ia`, `interaction`, `screens`, `conformance`, `validation` and
`prototype`.

**Stage numbers.** When the repo runs `cct:sdlc-run` with a Design stage (sdlc mode), the
activities are its stages 2.1 brief, 2.2 IA, 2.3 interaction, 2.4 screens, 2.5 conformance, 2.6
spec validation loop, 2.7 prototype, 2.8 facts and the validation gate pass, and build QA is its
4.2. Everywhere else this plugin names them by activity, never by number.

## 3. Size and preset skips

Standalone mode asks this once, in the same question round as any other open question, with a
recommended answer and one line per size:

| Size | Meaning | Preset skips |
|---|---|---|
| `none` | no interface change | all seven activities, `skip -- no interface change` |
| `S` | words or visuals on an existing screen; no new state, route or control | `brief`, `ia`, `interaction`, `prototype`, `validation`; runs `screens` and `conformance` on the delta |
| `M` | one screen's behaviour, or one flow | `ia`, `skip -- M: no route, object or name changes` |
| `L` | a new screen, flow or feature | none |

Remove a preset skip when the work needs the activity, and say so. Never add a skip silently:
adding one needs the user's yes and the reason.

Size `none` writes nothing at all: say in one line that there is no interface change to design.

## 4. Collecting the asks (standalone mode)

Copy every ask verbatim, never paraphrased, in this order:

1. the ticket: the one `decisions.json` `ticket` or `intent.md` names, or the one the user names;
2. this conversation;
3. the owner-words file named in `docs/ux/setup.md`;
4. every feedback folder named in `setup.md`, since the last spec for the same screen.

Resources that came with an ask (annotated screenshots, exports) are copied into
`<spec>/asks/<source-date>/` and linked from the row. Nothing links to `/Users/`, `~/` or
`file://`. No ask from any source: ask the user once; never invent one.

The table, in `<spec>/brief.md`:

```markdown
---
type: ux-brief-write
mode: standalone
change: <id>
size: none | S | M | L
skips:
  ia: "skip -- M: no route, object or name changes"
created: YYYY-MM-DD
---

## Owner Asks

| # | Date | Source | Words | Screen | Resources |
|---|---|---|---|---|---|
| A1 | YYYY-MM-DD | owner, chat | "<exact words>" | <screen or "none"> | [resource](asks/<date>/<file>) or none |
```

When `brief` is skipped (size `S`), the file still holds this frontmatter, the `## Owner Asks`
table and the `## Ask Map`, and one line saying the rest of the brief is skipped and why.
