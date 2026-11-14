# calvins-claude-tools

Verification and every push follow the [local-first contract](plugins/cct/skills/sdlc-run/references/local-first.md); read it before running checks or preparing a push.

Two Claude Code plugins: `cct` in `plugins/cct/` (skills, agents, hooks) and `agent-tracker` in `plugins/agent-tracker/` (a mod: a band above every prompt and a `/tracker` pane). They are the source of truth: edit them directly. Nothing in this repo reads from, builds from or needs access to any other repository.

## Naming a skill or agent (enforced by the tests)

Full rules and the old-to-new table: `docs/adr/0001-skill-taxonomy.md`.

- Action: `<family>-<object>-<verb>`, object omitted when the family supplies it (`ux-audit` style). Families: sdlc, project, product, ux, design, arch, db, review, test, git, data, tracking, docs. UX owns behavior and words; design owns visual expression.
- The last segment is a verb from `VERBS` in `scripts/taxonomy.py`. Synonyms are rejected: write not author, create not generate, run not execute, validate not check or verify.
- write authors language; create makes a finished non-language artifact; scaffold makes boilerplate; design specifies something to be built; audit judges against a standard; review examines an authored change; analyze returns insight and writes nothing; validate returns a binary verdict.
- A process ends in `-run`. A knowledge skill ends in a noun and needs a `NOUN_TAILS` entry with a reason; its description never dispatches creation. Vendor adapters are `<vendor>-<verb>`. Internal helpers are `role-<subject>` with `user_invocable: false`; every other skill sets `user_invocable: true`.
- Agents: family-prefixed noun (`review-code-reviewer`), the noun registered in `AGENT_NOUNS`.
- No repeated word, 64 characters at most, folder equals frontmatter `name`, description 1024 characters at most, and no quoted trigger phrase shared with another skill.
- A new skill: write it under `plugins/cct/skills/<name>/`, run the tests. No forwarding skills when renaming; record the move in an ADR.

## Never publish to claude.ai

No skill, agent or reference in the plugin may use the Artifact tool, Claude Docs or any hosted page. Pages and documents are local markdown or HTML (the owner's rule). `tests/test_no_claude_ai_publishing.py` fails on a publishing site; a prohibition may name the tools, nothing else.

## Public repo rule

No internal names, private repo names, people, URLs or local paths of any employer or client. `tests/test_plugin.py` greps for the known ones.

## Checks

```bash
python3 -m unittest discover -s tests
scripts/run-plugin-tests.sh
claude plugin validate --strict plugins/agent-tracker
claude plugin test plugins/agent-tracker
```

@AGENTS.md


Verification and every push follow the [local-first contract](https://github.com/cdudek/calvins-claude-tools/blob/main/plugins/cct/skills/sdlc-run/references/local-first.md); read it before running checks or preparing a push.

## How work moves: the SDLC




This repo uses `cct:sdlc-run`, configured by `sdlc.json`. A change is one PR and one folder:
`changes/<date>-<KEY>-<slug>/` (no key when there is no Linear issue). Designs that outlive
one PR live in `docs/designs/`, one decision per file. Read `docs/designs/INDEX.md` first and
open only the files it points you to; `python3 scripts/design_index.py write` after adding one.
The seven stages are Intent, UX plan,
Facts, Tech plan, Build, Milestone and Outcome.

The agent drafts intent, UX plan, facts and plan; the engineer confirms the intent, then all
three documents in one gate. After that every feature is built inside `/goal` as a PR into
`milestone/<slug>`, and ends on `python3 scripts/verify_gate.py feature <id>`. Each milestone
gets the heavy checks once, then one PR to its parent.

Branches:

```
<default> ─── milestone/<slug> ─── <feature branches>             one milestone
<default> ─── project/<slug> ─── milestone/<slug> ─── <features>  a project
```

A milestone branch stays local until its gate passes, then gets one push and one PR, merged
with a merge commit. Milestones are independent unless the plan says `needs:`. A project is
planning; a `project/<slug>` branch exists only when the engineer asked for one.

**The code is reviewed once, locally, at the milestone close** (Claude and Codex). Nothing
reviews in CI. Feature PRs into `milestone/*` and milestone PRs into `project/*` are interior
merges inside one change: no code owner, auto-merge on their checks alone.

There are no Ship/Show/Ask tiers here, so that PR auto-merges on green too.

New keys: `checks`, `milestones`, `projects`, `hotfix`, `goal`, `languages`, `responsiveTier`,
`ux`, `protected`. The reference is
**[docs/sdlc.md](docs/sdlc.md)**.

## Verifying your work

    python3 -m unittest discover -s tests && scripts/run-plugin-tests.sh

Run it before reporting done and before pushing. Use the linked targeted local failure loop; the full gate runs once on the final head before push. The Stop hook runs
`python3 -m unittest discover -s tests` for dirty source files.

## Pull requests, issues and PR comments: scannable, never a text blob

- **Order:** `## What` → `## Why` → `## Proof` → `## Before merge` (only while something is open) → `## How hard is it to undo this PR after merging?` → `## Decision record` (Repair, Migrate and Answer only).
- **Bullets:** Every section is a list; start each bullet with a bold label (`- **Source plan:** 0 adds, 8 updates, 38 destroys.`). Keep one idea per bullet, at most two lines, and no paragraph longer than two sentences. Keep checklist syntax and bold-label the item.
- **Proof:** Name the check and result (`- **Unit tests:** 1,320 passed.`). Put links on the label or result, never a bare URL in prose. Preserve claims and human checklist attestations when restructuring an existing body.
- **Decision4 (advisory):** Copy the section from the repo's PR template. Pick one level (🟢 Undo, 🟡 Repair, 🟠 Migrate, 🔴 Answer) at or above the lowest level `boundary-map.yaml` gives the changed paths; unsure, take the higher. Give concrete recovery steps and who is responsible. Nothing checks it and it never blocks a merge.
- **Decision record:** Only above Undo, as `AGENTS.md` says: Repair names what was chosen, over what, why and what it commits us to; Migrate lists at least two options; Answer lists facts marked observed, inferred, asked or unknown and recommends nothing.
- **Milestone and review text:** The same layout covers milestone-close PRs, issue bodies and PR comments. Put addressed feedback under What, its rationale under Why and its check results under Proof. A short thread reply can be one bold-labelled bullet; include only applicable sections.
- **Validation:** Validate the proposed body before pushing and the actual body after creation or edits against these rules. Use `--body-file`.

Full example for a Repair change (illustrative evidence, not claims to copy). Omit Before merge when nothing is open, and omit Decision record at Undo.

```markdown
## What

- **Change:** Move saved filters to the versioned format.
- **Requirement F1:** Existing filters remain readable during rollout.

## Why

- **Compatibility:** Clients need time to adopt the new format.

## Proof

- **Migration tests:** 12 passed, including reading the old format.
- **Local gate:** `scripts/ci-local --check` passed on the proposed head.

## Before merge

- [ ] **Owner review:** Confirm the rollout window.

## How hard is it to undo this PR after merging?

**🟡 Repair** — The team must correct stored filters and redeploy the compatible reader.

**Recovery steps**

1. Convert saved filters back with the reverse migration.
2. Redeploy the previous reader and check that existing filters load.

- **Responsible for recovery:** Service owner

## Decision record

- **Chose:** A versioned format with a reversible migration.
- **Over:** Replacing stored filters in place without a compatibility window.
- **Because:** Existing clients must keep reading their saved filters.
- **Commits us to:** Keeping the reverse migration until rollout is verified.

🤖 Generated with Codex
```
