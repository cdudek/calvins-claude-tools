# The change folder, layout 4: three documents

A change folder holds three documents a person reads. Everything else in it is a record a script
reads. This is layout 4. A change on the old layout (`intent.md`, `facts.md`, `plan.md`) finishes on
it: nothing here blocks it, and every reader falls back to the old names.

## The three documents

| File | Answers | Replaces |
|---|---|---|
| `spec.md` | Why and what: intent, asks, job stories, success measure, the requirements table, UX, clarifications, assumptions, out of scope | `intent.md`, `facts.md`, and the reading map `README.md` |
| `design.md` | How: approach and the rejected option, ground truth, rules check, interfaces, data, errors, test strategy per rule, risks with a proof each, rollout and rollback | the approach half of `plan.md` |
| `tasks.md` | In what order: tasks that each name their rules, test, dependencies and milestone; the task state; the handover | the feature rows of `plan.md`, `milestone.md` |

The requirement itself is not in `spec.md`. It is one file per rule in the living spec
(`specs/<capability>/rules/R123.md`, see [living-spec](living-spec.md)); the requirements table in
`spec.md` lists the rules this change adds, changes or removes with plain words and the asks they
answer. The PR's git diff of `specs/` is the delta, so the owner reads the old rule next to the new
one. There is no delta format and nothing to apply.

`spec.md` here is the change's proposal. The living spec has no file of that name (its parts are
rule files), so the word means one thing.

## Which documents a change gets: scope S, M or L

Chosen by the **risk of the change**, written as `scope` in `spec.md`. It is not the UX size
(`ux`), which only says how much interface changes: a database migration with no screen is still L.

| Scope | Documents | When | Gate |
|---|---|---|---|
| S | `spec.md` only; the builder reads it | one plain behaviour, no data, API, auth, money or new dependency | one owner gate; no reviewer |
| M | `spec.md` + `tasks.md` (design notes and risks inside `tasks.md`) | one behaviour or flow, touches existing code only | one owner gate; the reviewer runs on a narrow brief |
| L | all three | data, an API or contract, auth, money, a new dependency, a cross-module boundary or a new screen | two owner gates: `spec.md` first, then `design.md` and `tasks.md` |

A wrong spec found after the design is written wastes the design; that is why L asks twice. On S and
M the intent confirmation and the plan gate are one round on the same files.

## Machine records stay where they are

Layout 4 moves no machine file. `decisions.json`, `done.json`, `lock.json`, `asks/`, `marks.json`,
`verify/` and the findings keep their paths and readers; `decisions.json` gains `"layout": 4`,
written once at intake and never changed (the pin per change). A repo opts in with `"layout": 4` in
`sdlc.json`, only after its hooks, status and verifier read the new documents; adopt never sets it.
A `state/` folder was proposed first and is not built: the readers of every one of those files
would have to ship before it, and bypass words (`protectedEdit`, `prExceptions`) must stay where a
reviewer sees them.

Three things the lock covers: the whole of `spec.md`, the task rows of `tasks.md` (not the `State`
column, not the handover) and `design.md`. A tick never invalidates an approval.

## What a script checks before a model is asked

`python3 scripts/spec.py consistency <change dir> --phase draft|approve [--base REF]`, seconds, no
tokens:

- Every ask is answered by a rule in the table, `out of scope`, or (draft only) `pending`.
- Every requirement cites asks that exist; each `new` or `changed` row has a rule file in the
  named capability; each `removed` row has none; and the table equals the rules the git diff
  touched.
- M and L: every new or changed rule has a task; every task cites rules that exist and names a
  test; `Needs` has no cycle.
- L: `design.md` has a Test strategy line per rule, and every risk has a Proof before build.
- A UI change records `prototype: required` or `prototype: none` at Stage 2 (see S1 below).

Only then one reviewer reads the three documents in a fresh context. It replaces the checklist,
analyze and challenge passes (the old passes stay for a change on the old layout). Its brief carries
every old lens: gaps and ambiguities; coverage and consistency; existence, simpler alternative,
failure assumptions, implicit choices, who else is affected; and the cold read: "build this from
these documents alone and list every question you would have to ask". It returns findings as data
with a `phase` (`plan` or `milestone`), so a plan finding never blocks a milestone close. It never
edits; the agent fixes at the source and marks the finding fixed. `approve` still refuses an open
Critical.

## Planning content that moved into `design.md`

From the planning research: **ground truth** (what exists, cited `file:line`, found by one
read-only search); **proof before build** for every risk; **rollout and rollback** when data, an API
or config changes; the `cct:arch-plan-write` checklists as a trigger when a schema, endpoint, new
dependency or boundary appears; the **cold read** in the reviewer brief; a **test strategy** per
rule. Appetite, a security threat model and a plan-proportion check are not built.

## Closing: the folder is removed, never archived

There is no archive. After the change reaches the default branch the folder is removed in a
records-only close PR: `spec.py outcome write <folder>` first copies the success measure to
`.sdlc/outcomes/<change id>.json`, the pass record stays in `.sdlc/receipts/`, and `git rm -r` takes
the folder. Never before the merge: the folder is what a red-CI rerun needs. A reference into the
folder blocks the removal, as it blocked the move (Stage 7 guard). History lives in git, the PR and
the receipts.

## Deadlocks and stuck states this layout closes

- **D1, a spec that needs facts that do not exist yet.** Intent and requirements are now one file,
  and the UX validation runs once, single pass, as a draft: an ask may be `pending`, the validator
  never starts a goal of its own, and the owner gate is the only place `pending` must be gone
  (`consistency --phase approve` refuses it, naming the ask).
- **S1, a skip behind a prerequisite.** Stage 2 writes `prototype: required|none` into `spec.md`
  before anything else. Build QA asks `spec.py` (`qa_applicability`) first: with `none` or
  `ux: none` it skips with a printed reason and asks for no readiness file and no second gate; with
  `required` it runs, and the joint gate approves the readiness file.
- **S3, an outcome with no later PR.** The measure leaves the folder before the folder goes, into
  `.sdlc/outcomes/<id>.json` (`due`, `observed: null`). The scheduled read and the tracker comment
  record the value with `spec.py outcome record`; with no tracker and no next change it is one
  records-only PR. The route never needs the removed folder, a tracker or a future change.
  `spec.py outcome due` lists what is waiting.
