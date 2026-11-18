# Readability: plain words, ids in brackets, a map of the folder

A change folder holds many documents and hundreds of short ids. This file says how to keep it
readable for someone who was not there. Four small tools do the work; all are in `scripts/` and
read only the change's files.

## Plain words first, the id in brackets after

Say the thing in words, then the id: "Designs win over today's app (Q202)". Never "per Q202" and
never "B19 blocks the build". The id is a pointer for whoever wants the source, not the sentence.

- **Id families:** `A` an ask, `J` a job story (both in `intent.md`), `F` a fact and `N` a
  non-functional fact (`facts.md`), `X` an analysis finding (`analyze.md`), `H` a challenge
  finding (`challenge.md`), `Q` a question asked during the build (`questions.md`), `R` a review
  finding (`findings.md`), `B` any other numbered item.
- **The lint:** `python3 scripts/verify_gate.py lint <id>` flags an id outside brackets in the
  files the owner reads: `intent.md`, `plan.md`, `milestone.md`, `questions.md` and a drafted
  `pr-body.md`. Only ids the change defines count (a table row that opens with the id, or a
  definition label), so "Press F5" or "before Q4" pass. Headings, code, test tags such as `@F1`,
  the first cell of a table row, a cell of ids only and a definition label (`- **Q1 (date) the
  question?**`, `**F3**`) are structure and pass; any other table cell is prose and is checked, and
  `**B19 blocks the build.**` is flagged. A bracket may span a line wrap. `facts.md` is a list of
  ids and is not checked. The same lint keeps sentences at 25 words or less.
- **Where it runs:** on the drafts before a reviewer is dispatched, again right before the owner
  gate, first thing in `approve` (which refuses on any line it names), and on the PR body you
  publish: `verify_gate.py lint <id> --pr-body <file>` (`-` reads stdin), before `gh pr create` or
  `gh pr edit`. It reads files only.
- **The templates** in `templates/change/` carry the rule in a comment under the title.

## The id glossary

`python3 ${CLAUDE_SKILL_DIR}/scripts/sdlc_status.py ids [<id>]` prints every id the change defines
as `F1   <one-line meaning>  (facts.md)`: the meaning, then the file that decides it. An id that is
used but never defined is listed last. For an analysis or challenge row the meaning is its
`Finding` or `Challenge` column, never the `Where` cell. The milestone report template points at
this command. Use it before asking the owner what "Q202" is.

## The reading map

`python3 ${CLAUDE_SKILL_DIR}/scripts/sdlc_status.py readme [<id>]` writes `README.md` into the
change folder. It is generated: never edit it, regenerate it. Run it just before each stage commit so
the commit carries it; `status` never writes it, so a clean head stays clean for `verify`.
It writes only when the content changed, only inside a change folder directly under
`changesDir`, and only over a README that carries its generator marker; a hand-written README
is left alone and reported.

- **Three entry points on top:** understand the change (`intent.md`), review it (`facts.md`, then
  `plan.md`), pick up the work (the stage and the latest `handover*.md`, by the date or number in
  its name).
- **One row per document:** the question it answers, who writes it, at which stage, and whether a
  newcomer needs it. A document not written yet is named and marked. Any other file in the
  folder is listed under "Other files in this folder".
- **For agents:** evidence, run logs, audits and locks sit below a line of that name. A newcomer
  skips them.

One level up, `docs/designs/INDEX.md` (`scripts/design_index.py`) gives each design and decision
a second line, "Read when:", from the `read_when` field of its frontmatter. Without the field it
is built from the type and the tags.

## What `goal` says when it is not done

`sdlc_status.py goal <id>` keeps its first line (`GOAL <id> DONE|OPEN|BLOCKED ...`) for the
evaluator. When the goal is not done it adds one sentence: `Blocking: <what>, because <why>; <who>
runs `<step>`.` The sentence names only the first thing in the way.

## The newcomer page

`docs/sdlc-run.md` describes the seven stages for a person new to the chain. It states the
sdlc-run version it describes on a "Describes sdlc-run <version>" line; a test fails when that is
behind the version in `SKILL.md`. Bump it in the same change as the skill.
