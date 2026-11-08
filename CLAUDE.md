# calvins-claude-tools

One Claude Code plugin (`cct`) in `plugins/cct/`. It is the source of truth: edit it directly. Nothing in this repo reads from, builds from or needs access to any other repository.

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
```
